"""TuMangaOnline site downloader"""

from typing import Iterable, Set
from urllib.parse import quote

from bs4 import BeautifulSoup

from .base import Chapter, ChapterImage, Language, Manga, Site


class TMOChapterImage(ChapterImage):
    def __init__(self, chapter_url: str, url: str) -> None:
        super().__init__(url)
        self.chapter_url = chapter_url


class TuMangaOnline(Site):
    @property
    def name(self) -> str:
        return "TuMangaOnline"

    @property
    def url(self) -> str:
        return "https://lectortmo.com"

    @property
    def supported_languages(self) -> Set[Language]:
        return {Language.es}

    def search(self, query: str, lang: Language = None) -> Iterable[Manga]:
        with self.session.get(
            f"{self.url}/library", params={"_pg": "1", "title": query}
        ) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        for card in soup("div", {"class": "element"}):
            name = (
                card.findNext("div", {"class": "thumbnail-title"}).h4["title"].strip()
            )
            yield Manga(
                name=name,
                url=card.a["href"].strip(),
                cover=str(card.style).split("url('")[1].split("')")[0].strip(),
            )

    def get_chapters(self, manga: Manga) -> Iterable[Chapter]:
        with self.session.get(manga.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        soup = soup.find("div", {"id": "chapters"})
        for item in soup.select("li.list-group-item.upload-link"):
            name = item.findNext("a").text.strip().replace("\xa0", " ")
            url = (
                item.findNext("a", {"class": "btn btn-default btn-sm".split()})
                .get("href")
                .strip()
            )
            yield Chapter(name=name, url=url)

    def get_images(self, chapter: Chapter) -> Iterable[ChapterImage]:
        with self.session.get(chapter.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

        cascade = soup.find("a", {"title": "Cascada"})
        if cascade:
            with self.session.get(cascade["href"]) as resp:
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

        soup = soup.find("div", {"class": "viewer-container container"})
        for img in soup("img"):
            yield TMOChapterImage(
                chapter.url, url=quote(img["data-src"].strip(), safe=":/%")
            )

    def download_image(self, image: ChapterImage) -> bytes:
        with self.session.get(
            image.url, headers={"referer": image.chapter_url}  # noqa
        ) as resp:
            resp.raise_for_status()
            return resp.content
