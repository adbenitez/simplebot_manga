"""Nine Manga site downloader"""

from typing import Iterable, Set

from bs4 import BeautifulSoup, Tag

from .base import Chapter, ChapterImage, Language, Manga, Site


class NineManga(Site):
    @property
    def name(self) -> str:
        return "Nine Manga"

    @property
    def url(self) -> str:
        return "https://ninemanga.com"

    @property
    def supported_languages(self) -> Set[Language]:
        return {
            Language.de,
            Language.en,
            Language.es,
            Language.fr,
            Language.it,
            Language.pt,
            Language.ru,
        }

    def search(self, query: str, lang: Language = None) -> Iterable[Manga]:
        if lang is None:
            lang = Language.en
        assert lang in self.supported_languages
        site_url = f"https://{'br' if lang.name == 'pt' else lang.name}.ninemanga.com"

        with self.session.get(f"{site_url}/search/", params={"wd": query}) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

        pages = [soup.find("ul", class_="direlist")]
        pagelist = soup.find("ul", class_="pagelist")
        if pagelist:
            # get only first few pages:
            for page in pagelist.find_all("a")[1:-1]:
                with self.session.get(page["href"]) as resp:
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, "html.parser")
                pages.append(soup.find("ul", class_="direlist"))

        for page in pages:
            for card in page.find_all("dl", class_="bookinfo"):
                anchor = card.find("a", class_="bookname")
                img = card.find("img")
                yield Manga(
                    name=_get_text(anchor),
                    url=anchor["href"],
                    cover=img.get("src") if img else None,
                )

    def get_chapters(self, manga: Manga) -> Iterable[Chapter]:
        with self.session.get(manga.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        tag = soup.find("div", class_="warning")
        if tag:
            with self.session.get(tag.a["href"]) as resp:
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
        tag = soup.find("div", class_="silde")
        for anchor in tag.find_all("a", class_="chapter_list_a"):
            yield Chapter(name=anchor["title"], url=anchor["href"])

    def get_images(self, chapter: Chapter) -> Iterable[ChapterImage]:
        with self.session.get(chapter.url) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        tag = soup.find("select", id="page")
        site_url = chapter.url[: chapter.url.find("/", 8)]
        for opt in tag.find_all("option"):
            yield ChapterImage(url=f'{site_url}{opt["value"]}')

    def download_image(self, image: ChapterImage) -> bytes:
        with self.session.get(
            image.url, headers={"Accept-Language": "en-US,en;q=0.5"}
        ) as resp:
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        with self.session.get(soup.find("img", class_="manga_pic")["src"]) as resp:
            resp.raise_for_status()
            return resp.content

    def contains(self, url: str) -> bool:
        for lang in self.supported_languages:
            site_url = (
                f"https://{'br' if lang.name == 'pt' else lang.name}.ninemanga.com/"
            )
            if url.startswith(site_url):
                return True
        return False


def _get_text(tag: Tag) -> str:
    return tag.get_text().replace("\n", " ").strip()
