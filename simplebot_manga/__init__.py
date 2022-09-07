"""hooks, filters and commands"""

import os
import time
from typing import Iterable
from urllib.parse import quote_plus

import simplebot
from cachelib import FileSystemCache
from deltachat import Message
from simplebot.bot import DeltaBot, Replies

from .manga_api import get_site, lang2sites
from .manga_api.base import Chapter, Language, Manga
from .templates import get_template
from .util import bytes2jpeg, images2pdf

cache: FileSystemCache = None  # noqa
blobs_cache: FileSystemCache = None  # noqa


@simplebot.hookimpl
def deltabot_start(bot: DeltaBot) -> None:
    global cache, blobs_cache  # noqa
    plugin_dir = os.path.join(os.path.dirname(bot.account.db_path), __name__)
    if not os.path.exists(plugin_dir):
        os.makedirs(plugin_dir)

    cache_dir = os.path.join(plugin_dir, "cache")
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    cache = FileSystemCache(cache_dir, threshold=9000, default_timeout=0)

    blobs_cache_dir = os.path.join(plugin_dir, "blobs_cache")
    if not os.path.exists(blobs_cache_dir):
        os.makedirs(blobs_cache_dir)
    blobs_cache = FileSystemCache(
        blobs_cache_dir, threshold=5000, default_timeout=60 * 60 * 24 * 7  # 7days
    )


@simplebot.filter
def filter_messages(bot: DeltaBot, message: Message, replies: Replies) -> None:
    """Write to me in private to search for a manga.

    For example, send me a message with the text:
    Death Note

    Then you will have to choose the language of the manga. Depending on the selected language,
    you will be able to choose the website where you want to search for the manga.
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


@simplebot.command
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


@simplebot.command
def info(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Get the info and chapters list for the given manga."""
    try:
        manga = _get_manga(payload)

        args: dict = {}
        try:
            chapters_key = f"chaps|{manga.url}"
            chapters = cache.get(chapters_key)
            if not chapters:
                chapters = list(manga.get_chapters())
                cache.set(chapters_key, chapters, timeout=60 * 60)
                for chapter in chapters:
                    cache.set(chapter.url, chapter)

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
                    cover_bytes = manga.download_cover()
                    blobs_cache.set(manga.cover, cover_bytes)

                args["filename"] = "cover.jpg"
                args["bytefile"] = bytes2jpeg(cover_bytes)
            replies.add(**args, quote=message)
        except Exception as ex:
            bot.logger.exception(ex)
            replies.add(text=f"❌ Error: {ex}", quote=message)
    except Exception as ex:
        bot.logger.exception(ex)
        replies.add(text="❌ Wrong usage", quote=message)


@simplebot.command
def download(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Download the given manga chapter."""
    try:
        chapter = cache.get(payload)
        if not chapter:  # fallback to basic object with missing metadata
            site = get_site(payload)
            assert site
            chapter = Chapter(site, url=payload)

        try:
            pdf = images2pdf(_get_images(chapter), chapter.name or chapter.url)
            replies.add(
                text=f"{chapter.name}\n{chapter.url}",
                filename="chapter.pdf",
                bytefile=pdf,
                quote=message,
            )
        except Exception as ex:
            bot.logger.exception(ex)
            replies.add(text=f"❌ Error: {ex}", quote=message)
    except Exception as ex:
        bot.logger.exception(ex)
        replies.add(text="❌ Wrong usage", quote=message)


def _get_images(chapter) -> Iterable[bytes]:
    imgs_key = f"imgs|{chapter.url}"
    imgs = cache.get(imgs_key)
    if not imgs:
        imgs = list(chapter.get_images())
        cache.set(imgs_key, imgs, timeout=60 * 60)

    for img in imgs:
        img_bytes = blobs_cache.get(img.url)
        if not img_bytes:
            img_bytes = img.download()
            blobs_cache.set(img.url, img_bytes)
            time.sleep(0.1)
        yield img_bytes


def _get_manga(url: str) -> Manga:
    manga = cache.get(url)
    if not manga:  # fallback to basic object with missing metadata
        site = get_site(url)
        assert site
        manga = Manga(site, url=url)
    return manga
