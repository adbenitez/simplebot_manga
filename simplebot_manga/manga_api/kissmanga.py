"""KissManga site downloader"""

from typing import Iterable, Set

from bs4 import BeautifulSoup

from .base import Chapter, ChapterImage, Language, Manga, Site


class KissManga(Site):
    @property
    def name(self) -> str:
        return "KissManga"

    @property
    def url(self) -> str:
        return "http://kissmanga.nl"

    @property
    def supported_languages(self) -> Set[Language]:
        return {Language.en}

    def search(self, query: str, lang: Language = None) -> Iterable[Manga]:
        with self.session.get(f"{self.url}/search", params={"q": query}) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        for card in soup("div", {"class": "mainpage-manga"}):
            anchor = card.findNext("div", {"class": "media-body"}).findNext("a")
            yield Manga(
                url=anchor["href"],
                name=anchor["title"],
                cover=card.findNext("img")["src"],
            )

    def get_chapters(self, manga: Manga) -> Iterable[Chapter]:
        with self.session.get(manga.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        soup = soup("div", {"class": "chapter-list"})[1]
        for item in soup("h4"):
            item = item.findNext("a")
            yield Chapter(name=item["title"].strip(), url=item["href"])

    def get_images(self, chapter: Chapter) -> Iterable[ChapterImage]:
        with self.session.get(chapter.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        soup = soup.find("p", {"id": "arraydata"})
        for url in soup.text.split(","):
            yield ChapterImage(url=url)
