"""Wie Manga site downloader"""

from typing import Iterable, Optional, Set

from bs4 import BeautifulSoup

from .base import Chapter, ChapterImage, Language, Manga, Site


class WieManga(Site):
    @property
    def name(self) -> str:
        return "WieManga"

    @property
    def url(self) -> str:
        return "https://wiemanga.com"

    @property
    def supported_languages(self) -> Set[Language]:
        return {Language.de}

    def search(self, query: str, lang: Optional[Language] = None) -> Iterable[Manga]:
        with self.session.get(f"{self.url}/search", params={"wd": query}) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        soup = soup.find("div", {"class": "searchresult"})
        for anchor in soup("a", {"class": "resultimg"}):
            img = anchor.img
            yield Manga(
                url=anchor["href"],
                name=img["alt"],
                cover=img["src"],
            )

    def get_chapters(self, manga: Manga) -> Iterable[Chapter]:
        with self.session.get(manga.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        soup = soup.find("div", {"class": "chapterlist"})
        for item in soup("td"):
            item = item.a
            yield Chapter(name=item["title"].strip(), url=item["href"])

    def get_images(self, chapter: Chapter) -> Iterable[ChapterImage]:
        with self.session.get(chapter.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        soup = soup.find("select", id="page")
        for opt in soup("option"):
            yield ChapterImage(url=opt["value"])

    def download_image(self, image: ChapterImage) -> bytes:
        with self.session.get(image.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        with self.session.get(soup.find("img", id="comicpic")["src"]) as resp:
            resp.raise_for_status()
            return resp.content
