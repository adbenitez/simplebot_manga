"""Utilities"""

from io import BytesIO
from typing import Iterable

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


def bytes2jpeg(blob: bytes) -> BytesIO:
    img = Image.open(BytesIO(blob))
    if img.mode != "RGB":
        img = img.convert("RGB")
    try:
        img_file = BytesIO()
        img.save(img_file, format="JPEG")
        img_file.seek(0)
        return img_file
    finally:
        img.close()


def images2pdf(images: Iterable[bytes], title: str) -> BytesIO:
    pdf = FPDF("P", "pt")
    for img_bytes in images:
        img = Image.open(BytesIO(img_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        width, height = img.width, img.height

        try:
            img_file = BytesIO()
            img.save(img_file, format="JPEG")
            img_file.seek(0)
        finally:
            img.close()

        pdf.add_page(format=(width, height))
        pdf.image(img_file, 0, 0, width, height)
        img_file.close()

    pdf.set_title(title)
    output = pdf.output()
    pdf.close()
    return BytesIO(output)
