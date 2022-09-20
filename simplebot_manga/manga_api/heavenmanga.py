"""HeavenManga site downloader"""

import re
from typing import Iterable, Set

import json5
from bs4 import BeautifulSoup

from .base import Chapter, ChapterImage, Language, Manga, Site


class HeavenManga(Site):
    @property
    def name(self) -> str:
        return "HeavenManga"

    @property
    def url(self) -> str:
        return "https://heavenmanga.com"

    @property
    def supported_languages(self) -> Set[Language]:
        return {Language.es}

    def search(self, query: str, lang: Language = None) -> Iterable[Manga]:
        with self.session.get(f"{self.url}/buscar", params={"query": query}) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        for card in soup("div", {"class": "c-tabs-item"}):
            anchor = card.a
            if not anchor:
                continue
            yield Manga(
                url=anchor["href"],
                name=anchor["title"],
                cover=anchor.img.get("src"),
            )

    def get_chapters(self, manga: Manga) -> Iterable[Chapter]:
        params = (
            "draw=1&columns[0][data]=number&columns[0][name]=number&columns[0][searchable]=true"
            "&columns[0][orderable]=true&columns[0][search][value]=&columns[0][search][regex]=false"
            "&columns[1][data]=created_at&columns[1][name]=created_at&columns[1][searchable]=false"
            "&columns[1][orderable]=true&columns[1][search][value]=&columns[1][search][regex]=false"
            "&order[0][column]=1&order[0][dir]=desc&start=0&search[value]=&search[regex]=false"
        )
        headers = {"X-Requested-With": "XMLHttpRequest", "Referer": manga.url}
        with self.session.get(manga.url, params=params, headers=headers) as resp:
            resp.raise_for_status()
            data = resp.json()["data"]
        for item in data:
            yield Chapter(
                name=f"Capítulo {item['slug']}",
                url=f"https://heavenmanga.com/manga/leer/{item['id']}",
            )

    def get_images(self, chapter: Chapter) -> Iterable[ChapterImage]:
        with self.session.get(chapter.url) as resp:
            resp.raise_for_status()
            for img in json5.loads(re.findall(r"var pUrl=(.*);", resp.text)[0]):
                yield ChapterImage(url=img["imgURL"].strip())
