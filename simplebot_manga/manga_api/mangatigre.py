"""Manga Tigre site downloader"""

from typing import Iterable, Set
from urllib.parse import quote

from bs4 import BeautifulSoup

from .base import Chapter, ChapterImage, Language, Manga, Site


class MangaTigre(Site):
    @property
    def name(self) -> str:
        return "Manga Tigre"

    @property
    def url(self) -> str:
        return "https://www.mangatigre.net"

    @property
    def supported_languages(self) -> Set[Language]:
        return {Language.es}

    def search(self, query: str, lang: Language = None) -> Iterable[Manga]:
        with self.session.get(self.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        soup = soup.find("div", {"class": "input-group"})
        token = soup.find("input")["data-csrf"]
        with self.session.post(
            f"{self.url}/mangas/search", data={"query": query, "_token": token}
        ) as resp:
            resp.raise_for_status()
            mangas = resp.json()["result"]
        for manga in mangas:
            yield Manga(
                url=f"{self.url}/manga/{manga['slug']}",
                name=manga["name"],
                cover=f"https://i2.mtcdn.xyz/mangas/{manga['image']}",
            )

    def get_chapters(self, manga: Manga) -> Iterable[Chapter]:
        with self.session.get(manga.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        token = soup.find("button", {"class": "btn-load-more-chapters"})["data-token"]
        with self.session.post(manga.url, data={"_token": token}) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        soup = soup.find("ul", {"class": "list-unstyled"})
        for item in soup("li"):
            item = item.findNext("a")
            yield Chapter(name=item.text.strip(), url=item["href"])

    def get_images(self, chapter: Chapter) -> Iterable[ChapterImage]:
        with self.session.get(chapter.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            btn = soup.find("button", {"data-read-type": 2})
            if btn:
                data = {"_method": "patch", "_token": btn["data-token"], "read_type": 2}
                with self.session.post(f"{resp.url}/read-type", data=data) as resp:
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, "html.parser")

        soup = soup.find("div", {"class": "display-zone"})
        for img in soup("img"):
            yield ChapterImage(
                url=quote(f"https:{img.get('data-src') or img['src']}", safe=":/%")
            )
