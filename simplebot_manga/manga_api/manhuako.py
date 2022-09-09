"""ManhuaKO site downloader"""

import time
from typing import Iterable, Set
from urllib.parse import quote

from bs4 import BeautifulSoup

from .base import Chapter, ChapterImage, Language, Manga, Site


class ManhuaKO(Site):
    @property
    def name(self) -> str:
        return "ManhuaKO"

    @property
    def url(self) -> str:
        return "https://manhuako.com"

    @property
    def supported_languages(self) -> Set[Language]:
        return {Language.es}

    def search(self, query: str, lang: Language = None) -> Iterable[Manga]:
        with self.session.get(f"{self.url}/home/search", params={"mq": query}) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        pages = [soup]
        pagelist = soup.find("ul", class_="pagination")
        if pagelist:
            # get only the second page
            for page in pagelist("a")[1:2]:
                with self.session.get(page["href"]) as resp:
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, "html.parser")
                pages.append(soup)

        for page in pages:
            for card in page("div", {"class": "card"}):
                if card.findNext("p", {"class": "type"}).text == "Novela":
                    continue
                anchor = card.findNext("a", {"class": "white-text"})
                yield Manga(
                    url=anchor["href"],
                    name=anchor.text.strip(),
                    cover=card.findNext("img")["src"],
                )

    def get_chapters(self, manga: Manga) -> Iterable[Chapter]:
        with self.session.get(manga.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        pages = [soup]
        pagelist = soup.find("ul", class_="pagination")
        if pagelist:
            last_page = int(
                pagelist("a")[-1]["href"].strip("/").rsplit("/", maxsplit=1)[-1]
            )
            for page_number in range(2, last_page + 1):
                with self.session.get(f"{manga.url}/page/{page_number}") as resp:
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, "html.parser")
                pages.append(soup)
                time.sleep(0.1)
        for page in pages:
            page = page.find("table", {"class": "table-chapters"})
            for item in page("tr"):
                item = item.findNext("a")
                yield Chapter(name=item.text.strip(), url=item["href"])

    def get_images(self, chapter: Chapter) -> Iterable[ChapterImage]:
        with self.session.get(chapter.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        soup = soup.find("div", {"id": "pantallaCompleta"})
        for img in soup("img"):
            yield ChapterImage(url=quote(img["src"], safe=":/%"))
