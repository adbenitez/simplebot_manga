"""Base classes for manga downloaders"""
# pylama:ignore=C0103,W0622

import functools
from abc import ABC, abstractmethod
from enum import Enum
from typing import Iterable, Set

from requests import Session

_session = Session()
_session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:104.0) Gecko/20100101 Firefox/104.0"
        )
    }
)
_session.request = functools.partial(_session.request, timeout=30)  # type: ignore


class Language(Enum):
    de = "🇩🇪 Deutsch"
    en = "🇬🇧 English"
    es = "🇪🇸 Español"
    fr = "🇫🇷 Français"
    it = "🇮🇹 Italiano"
    pt = "🇵🇹 Português"
    ru = "🇷🇺 Pусский"


class Manga:
    def __init__(self, url: str, name: str = "", cover: str = None) -> None:
        self.url = url
        self.name = name
        self.cover = cover


class Chapter:
    def __init__(self, url: str, name: str = "") -> None:
        self.name = name
        self.url = url


class ChapterImage:
    def __init__(self, url: str) -> None:
        self.url = url


class Site(ABC):
    """Abstract class base of all manga sites."""

    session = _session

    @property
    @abstractmethod
    def name(self) -> str:
        """The site's name."""

    @property
    @abstractmethod
    def url(self) -> str:
        """The site's URL."""

    @property
    @abstractmethod
    def supported_languages(self) -> Set[Language]:
        """The languages supported by this site."""

    @abstractmethod
    def search(self, query: str, lang: Language = None) -> Iterable[Manga]:
        """Search for mangas matching the given query string.

        :param lang: the language to search if the site supports several languages.
        """

    @abstractmethod
    def get_chapters(self, manga: Manga) -> Iterable[Chapter]:
        """Get the chapters from the given manga."""

    @abstractmethod
    def get_images(self, chapter: Chapter) -> Iterable[ChapterImage]:
        """Get the images from a chapter."""

    def download_image(self, image: ChapterImage) -> bytes:
        """Download a chapter image."""
        with self.session.get(image.url) as resp:
            resp.raise_for_status()
            return resp.content

    def download_cover(self, manga: Manga) -> bytes:
        """Download a manga's cover image."""
        assert manga.cover
        with self.session.get(manga.cover) as resp:
            resp.raise_for_status()
            return resp.content

    def contains(self, url: str) -> bool:
        """Return True if the given manga/chapter url is from this site, False otherwise."""
        return url.startswith(f"{self.url.rstrip('/')}/")
