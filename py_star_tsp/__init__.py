"""py_star_tsp — Python SDK for Star TSP100 Graphic Mode thermal printers."""

from pathlib import Path

from .printer.printer import StarTSP
from .printer.tsp100 import StarTSP100
from .version import __version__ as version
from .raster import RasterImage
from .status import AsbStatus
from .text import discover_fonts, find_font, TextBlock
from .exceptions import (
    PrinterNotFoundError,
    PrinterCommunicationError,
    PrinterCommandError,
)

__all__ = [
    "StarTSP",
    "StarTSP100",
    "RasterImage",
    "AsbStatus",
    "TextBlock",
    "discover_fonts",
    "find_font",
    "PrinterNotFoundError",
    "PrinterCommunicationError",
    "PrinterCommandError",
    "version",
]

KITTENS_SPINNING = str(Path(__file__).parent / "img" / "three_kittens_spinning.png")

FONTS_DIR = str(Path(__file__).parent / "fonts")
FONT_OCR_A_STD = str(Path(FONTS_DIR) / "ocr_a_std.ttf")
FONT_OCR_B = str(Path(FONTS_DIR) / "ocr_b.ttf")
FONT_ORATOR = str(Path(FONTS_DIR) / "orator_15cpi.ttf")
