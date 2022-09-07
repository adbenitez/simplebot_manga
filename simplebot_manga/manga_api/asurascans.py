"""AsuraScans site downloader"""

from typing import Iterable, Set

from bs4 import BeautifulSoup

from .base import Chapter, ChapterImage, Language, Manga, Site


class AsuraScans(Site):
    @property
    def name(self) -> str:
        return "Asura Scans"

    @property
    def url(self) -> str:
        return "https://www.asurascans.com"

    @property
    def supported_languages(self) -> Set[Language]:
        return {Language.en}

    def search(self, query: str, lang: Language = None) -> Iterable[Manga]:
        with self.session.get(self.url, params={"s": query}) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        soup = soup.find("div", {"class": "listupd"})
        cards = soup("div", {"class": "bs"})
        anchors = [card.findNext("a") for card in cards]

        for anchor in anchors:
            yield Manga(
                url=anchor["href"],
                name=anchor["title"],
                cover=anchor.findNext("img").get("src"),
            )

    def get_chapters(self, manga: Manga) -> Iterable[Chapter]:
        with self.session.get(manga.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        anchors = [
            li.findNext("a") for li in soup.find("div", {"id": "chapterlist"})("li")
        ]
        for anchor in anchors:
            title = anchor.findChild("span", {"class": "chapternum"}).string.strip()
            yield Chapter(url=anchor["href"], name=title)

    def get_images(self, chapter: Chapter) -> Iterable[ChapterImage]:
        with self.session.get(chapter.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        soup = soup.find("div", {"id": "readerarea"})
        for tag in soup("p"):
            yield ChapterImage(url=tag.findNext("img")["src"])
