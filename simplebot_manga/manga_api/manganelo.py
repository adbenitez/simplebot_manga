"""Manganelo site downloader"""

from typing import Iterable, Set
from urllib.parse import quote

from bs4 import BeautifulSoup

from .base import Chapter, ChapterImage, Language, Manga, Site


class Manganelo(Site):
    @property
    def name(self) -> str:
        return "Manganelo"

    @property
    def url(self) -> str:
        return "https://ww5.manganelo.tv"

    @property
    def supported_languages(self) -> Set[Language]:
        return {Language.en}

    def search(self, query: str, lang: Language = None) -> Iterable[Manga]:
        with self.session.get(f"{self.url}/search/{quote(query)}") as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        for card in soup("div", {"class": "search-story-item"}):
            anchor = card.findNext("a")
            yield Manga(
                url=f'{self.url}/{anchor["href"][1:]}',
                name=anchor["title"],
                cover=f'{self.url}/{anchor.findNext("img")["src"][1:]}',
            )

    def get_chapters(self, manga: Manga) -> Iterable[Chapter]:
        with self.session.get(manga.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup("li", {"class": "a-h"}):
            item = item.findNext("a")
            yield Chapter(
                name=item.string.strip(), url=f'{self.url}/{item["href"][1:]}'
            )

    def get_images(self, chapter: Chapter) -> Iterable[ChapterImage]:
        with self.session.get(chapter.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        soup = soup.find("div", {"class": "container-chapter-reader"})
        for img in soup("img"):
            yield ChapterImage(url=quote(img["data-src"].strip(), safe=":/%"))
