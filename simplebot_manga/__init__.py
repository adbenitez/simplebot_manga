"""hooks, filters and commands"""

import base64
import os
import time
from io import BytesIO
from typing import Callable, Iterable, List, Tuple
from urllib.parse import quote_plus

import simplebot
from cachelib import FileSystemCache
from deltachat import Message
from requests import HTTPError
from simplebot.bot import DeltaBot, Replies

from .manga_api import get_site, lang2sites
from .manga_api.base import Chapter, Language, Manga, Site
from .templates import get_template
from .util import convert_image, getdefault, images2pdf

cache: FileSystemCache = None  # noqa
blobs_cache: FileSystemCache = None  # noqa


@simplebot.hookimpl
def deltabot_init(bot: DeltaBot) -> None:
    pdf_max_size = getdefault(bot, "pdf_max_size", str(1024**2 * 10))
    html_max_size = getdefault(bot, "html_max_size", str(1024**2 * 10))
    bot.add_preference(
        "pdf_max_size", f"PDF maximum size in bytes (default: {pdf_max_size})"
    )
    bot.add_preference(
        "html_max_size", f"HTML-view maximum size in bytes (default: {html_max_size})"
    )


@simplebot.hookimpl
def deltabot_start(bot: DeltaBot) -> None:
    global cache, blobs_cache  # noqa
    plugin_dir = os.path.join(os.path.dirname(bot.account.db_path), __name__)
    if not os.path.exists(plugin_dir):
        os.makedirs(plugin_dir)

    cache_dir = os.path.join(plugin_dir, "cache")
    cache = FileSystemCache(cache_dir, threshold=0, default_timeout=60 * 60 * 24 * 60)

    blobs_cache_dir = os.path.join(plugin_dir, "blobs_cache")
    blobs_cache = FileSystemCache(
        blobs_cache_dir, threshold=9000, default_timeout=60 * 60 * 24 * 7  # 7days
    )


@simplebot.filter
def filter_messages(bot: DeltaBot, message: Message, replies: Replies) -> None:
    """Write to me in private to search for a manga.

    For example, send me a message with the text:
    Death Note

    Then I will send you a list of websites to choose where to perform your search.
    Then you can select a manga from the search results, and choose a chapter to download.
    The chapters are sorted according to the website.
    """
    if message.chat.is_multiuser() or not message.text:
        return

    html = get_template("site_list.j2").render(
        bot_addr=bot.self_contact.addr,
        lang2sites=lang2sites,
        query=message.text,
        quote_plus=quote_plus,
    )
    replies.add(text="🔍 Select a site to search", html=html, quote=message)


@simplebot.command(hidden=True)
def search(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Search for mangas in the given site."""
    try:
        lang_code, url, query = payload.split(maxsplit=2)
        lang = Language[lang_code]
        site = get_site(url)
        assert site and lang in site.supported_languages

        try:
            search_key = f"{lang_code}|{url}|{hash(query)}"
            mangas = cache.get(search_key)
            if mangas is None:
                mangas = list(site.search(query, lang))
                cache.set(search_key, mangas, timeout=60 * 60)
                for manga in mangas:
                    cache.set(manga.url, manga)

            if mangas:
                html = get_template("manga_list.j2").render(
                    bot_addr=bot.self_contact.addr,
                    site_name=site.name,
                    mangas=mangas,
                    quote_plus=quote_plus,
                )
                text = f"{site.name} Search Results"
            else:
                html = None
                text = f"❌ No matches found at {site.name}"
            replies.add(text=text, html=html, quote=message)
        except Exception as ex:
            bot.logger.exception(ex)
            replies.add(text=f"❌ Error: {ex}", quote=message)
    except Exception as ex:
        bot.logger.exception(ex)
        replies.add(text="❌ Wrong usage", quote=message)


@simplebot.command(hidden=True)
def info(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Get the info and chapters list for the given manga."""
    try:
        site = get_site(payload)
        assert site
        manga = cache.get(payload)
        if not manga:  # fallback to basic object with missing metadata
            manga = Manga(url=payload)

        args: dict = {}
        try:
            chapters = _get_chapters(site, manga)
            if chapters:
                args["html"] = get_template("chapter_list.j2").render(
                    bot_addr=bot.self_contact.addr,
                    manga_name=manga.name,
                    chapters=chapters,
                    quote_plus=quote_plus,
                )
            args["text"] = f"{manga.name}\n{manga.url}\n\n({len(chapters)} chapters)"
            if manga.cover:
                cover_bytes = blobs_cache.get(manga.cover)
                if not cover_bytes:
                    try:
                        cover_bytes = site.download_cover(manga)
                        blobs_cache.set(manga.cover, cover_bytes)
                    except HTTPError as ex:
                        bot.logger.exception(ex)

                if cover_bytes:
                    args["filename"] = "cover.jpg"
                    args["bytefile"] = convert_image(cover_bytes)[0]
            replies.add(**args)
        except Exception as ex:
            bot.logger.exception(ex)
            replies.add(text=f"❌ Error: {ex}", quote=message)
    except Exception as ex:
        bot.logger.exception(ex)
        replies.add(text="❌ Wrong usage", quote=message)


@simplebot.command(hidden=True)
def read(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Read the given manga chapter."""
    max_size = int(
        bot.get("html_max_size", scope=message.get_sender_contact().addr)
        or getdefault(bot, "html_max_size")
    )
    _download(bot, payload, message, replies, _send_html, max_size)


@simplebot.command(hidden=True)
def download(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Download the given manga chapter."""
    max_size = int(
        bot.get("pdf_max_size", scope=message.get_sender_contact().addr)
        or getdefault(bot, "pdf_max_size")
    )
    _download(bot, payload, message, replies, _send_pdf, max_size)


def _download(
    bot: DeltaBot,
    payload: str,
    message: Message,
    replies: Replies,
    send_part: Callable,
    max_size: int,
) -> None:
    try:
        site = get_site(payload)
        assert site
        chapter = cache.get(payload)
        if not chapter:  # fallback to basic object with missing metadata
            chapter = Chapter(url=payload)

        try:
            imgs: List[Tuple[BytesIO, int, int]] = []
            size = 0
            part = 0
            for img_bytes in _get_images(site, chapter):
                if size >= max_size:
                    part += 1
                    send_part(imgs, part, chapter, replies)
                    imgs, size = [], 0
                img = convert_image(img_bytes)
                size += img[0].getbuffer().nbytes
                imgs.append(img)
            if part > 0:
                part += 1
            send_part(imgs, part, chapter, replies)
        except Exception as ex:
            bot.logger.exception(ex)
            replies.add(text=f"❌ Error: {ex}", quote=message)
    except Exception as ex:
        bot.logger.exception(ex)
        replies.add(text="❌ Wrong usage", quote=message)


def _get_images(site: Site, chapter: Chapter) -> Iterable[bytes]:
    imgs_key = f"imgs|{chapter.url}"
    imgs = cache.get(imgs_key)
    if not imgs:
        imgs = list(site.get_images(chapter))
        cache.set(imgs_key, imgs, timeout=60 * 60)

    for img in imgs:
        img_bytes = blobs_cache.get(img.url)
        if not img_bytes:
            img_bytes = site.download_image(img)
            blobs_cache.set(img.url, img_bytes)
            time.sleep(0.1)
        yield img_bytes


def _get_chapters(site: Site, manga: Manga) -> List[Chapter]:
    chapters_key = f"chaps|{manga.url}"
    chapters = cache.get(chapters_key)
    if not chapters:
        chapters = list(site.get_chapters(manga))
        cache.set(chapters_key, chapters, timeout=60 * 60)
        for chapter in chapters:
            cache.set(chapter.url, chapter)
    return chapters


def _send_pdf(
    imgs: List[Tuple[BytesIO, int, int]], part: int, chapter: Chapter, replies: Replies
) -> None:
    title = f"{chapter.name or chapter.url}"
    if part > 0:
        title += f" (Part {part})"
    pdf = images2pdf(imgs, title)
    title = f"{chapter.name} (Part {part})" if part > 0 else chapter.name
    replies.add(
        text=f"{title}\n{chapter.url}",
        filename="chapter.pdf",
        bytefile=pdf,
    )


def _send_html(
    imgs: List[Tuple[BytesIO, int, int]], part: int, chapter: Chapter, replies: Replies
) -> None:
    html = (
        '<!DOCTYPE html><html><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        "<style>html,body{padding:0;margin:0;}img{width:100%;height:auto;}</style>"
        "</head><body>"
    )
    for img_file, _, _ in imgs:
        img = base64.b64encode(img_file.read()).decode()
        html += f'<img src="data:image/jpeg;base64,{img}"/>'
        img_file.close()
    html += "</body></html>"
    title = f"{chapter.name} (Part {part})" if part > 0 else chapter.name
    replies.add(text=f"{title}\n{chapter.url}", html=html)
