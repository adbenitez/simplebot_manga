"""Manga downloader API"""

from typing import Dict, List, Optional

from .asurascans import AsuraScans
from .base import Language, Site
from .heavenmanga import HeavenManga
from .kissmanga import KissManga
from .mangabuddy import MangaBuddy
from .manganelo import Manganelo
from .mangatigre import MangaTigre
from .manhuako import ManhuaKO
from .ninemanga import NineManga
from .tmo import TuMangaOnline
from .wiemanga import WieManga

sites = [
    AsuraScans(),
    TuMangaOnline(),
    Manganelo(),
    NineManga(),
    KissManga(),
    MangaTigre(),
    ManhuaKO(),
    MangaBuddy(),
    HeavenManga(),
    WieManga(),
]

lang2sites: Dict[Language, List[Site]] = {}
for _site in sites:
    for lang in _site.supported_languages:
        lang2sites.setdefault(lang, []).append(_site)
del _site


def get_site(url: str) -> Optional[Site]:
    for site in sites:
        if site.url == url or site.contains(url):
            return site
    return None
