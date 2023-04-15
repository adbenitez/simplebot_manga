"""MangaBuddy site downloader"""

import re
from typing import Iterable, Set

from bs4 import BeautifulSoup

from .base import Chapter, ChapterImage, Language, Manga, Site


class MangaBuddy(Site):
    @property
    def name(self) -> str:
        return "MangaBuddy"

    @property
    def url(self) -> str:
        return "https://mangabuddy.com"

    @property
    def supported_languages(self) -> Set[Language]:
        return {Language.en}

    def search(self, query: str, lang: Language = None) -> Iterable[Manga]:
        with self.session.get(f"{self.url}/search", params={"q": query}) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        for card in soup("div", {"class": "book-item"}):
            anchor = card.a
            if anchor is None:
                continue
            yield Manga(
                url=f'{self.url}{anchor["href"].strip()}',
                name=anchor["title"].strip(),
                cover=card.findNext("img")["data-src"].strip(),
            )

    def get_chapters(self, manga: Manga) -> Iterable[Chapter]:
        url = f"https://mangabuddy.com/api/manga{manga.url[len(self.url):]}/chapters?source=detail"
        with self.session.get(url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        soup = soup.find("ul", {"id": "chapter-list"})
        for item in soup("li"):
            item = item.find("a")
            name = item.findNext("strong", {"class": "chapter-title"}).text.strip()
            yield Chapter(name=name, url=f'{self.url}{item["href"]}')

    def get_images(self, chapter: Chapter) -> Iterable[ChapterImage]:
        with self.session.get(chapter.url) as resp:
            resp.raise_for_status()
            imgs = re.findall(r"var chapImages = '(.*)'", resp.text)[0].split(",")
        for img in imgs:
            if not img.startswith(("https://", "http://")):
                img = f"https://s1.mbcdnv1.xyz/file/img-mbuddy/manga/{img}"
            yield ChapterImage(url=img)

    def download_image(self, image: ChapterImage) -> bytes:
        with self.session.get(image.url, headers={"referer": self.url}) as resp:
            resp.raise_for_status()
            return resp.content

    def download_cover(self, manga: Manga) -> bytes:
        assert manga.cover
        with self.session.get(manga.cover, headers={"referer": self.url}) as resp:
            resp.raise_for_status()
            return resp.content
