"""Utilities"""

from io import BytesIO
from typing import Iterable, Tuple

from fpdf import FPDF
from PIL import Image
from simplebot.bot import DeltaBot


def getdefault(bot: DeltaBot, key: str, value: str = None) -> str:
    scope = __name__.split(".", maxsplit=1)[0]
    val = bot.get(key, scope=scope)
    if val is None and value is not None:
        bot.set(key, value, scope=scope)
        val = value
    return val


def convert_image(img_bytes: bytes) -> Tuple[BytesIO, int, int]:
    img = Image.open(BytesIO(img_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    width, height = img.width, img.height

    img_file = BytesIO()
    try:
        img.save(img_file, format="JPEG")
        img_file.seek(0)
    finally:
        img.close()

    return img_file, width, height


def images2pdf(images: Iterable[Tuple[BytesIO, int, int]], title: str) -> BytesIO:
    pdf = FPDF("P", "pt")
    for img_file, width, height in images:
        pdf.add_page(format=(width, height))
        pdf.image(img_file, 0, 0, width, height)
        img_file.close()

    pdf.set_title(title)
    output = pdf.output()
    return BytesIO(output)
