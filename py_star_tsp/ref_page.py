"""
Reference Pages — Examples to print and look at.
"""

import datetime
from typing import Optional

from .printer.printer import StarTSP
from .version import __version__
from . import KITTENS_SPINNING

DEFAULT_FONT_NAME = "ocr_a_std"
DEFAULT_FONT_SIZE_SET_A = [10, 15, 20, 25, 30, 40, 60, 80, 100, 120, 200, 300, 500]
DEFAULT_FONT_SIZE_SET_CPI_2inch = [63, 64, 65, 66, 67, 68, 69]
DEFAULT_FONT_SIZE_SET_CPI_1inch = [30, 32, 33, 33.5, 34, 36, 38, 40]
DEFAULT_FONT_SIZE_SET_CPI_05inch = [15, 16, 16.5, 17, 18, 19, 20]
DEFAULT_FONT_SIZE_SET_CPI_FULL = [12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40]

DEFAULT_BAR_WIDTH_SET = [50, 100, 200, 203, 300, 400, 500, 576, 580, 600]
DEFAULT_BAR_HIT_RIGHT_SET = [570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580]

def print_kittens(printer: StarTSP, invert: bool = False) -> None:
    printer.add_image(KITTENS_SPINNING, invert=invert)

def print_kittens_kittens(printer: StarTSP) -> None:
    printer.add_image(KITTENS_SPINNING)
    printer.add_text("KITTENS! KITTENS!", font_size=80, invert=True)
    printer.add_image(KITTENS_SPINNING, invert=True)

def print_timestamp_bar(printer: StarTSP) -> None:
    # Instead of having top margin for a text block, we can print a bar.
    printer.add_bar(width=900, height=3)

    # Then the actual text block.
    printer.add_text(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} v{__version__}", font_size=30, invert=True)

    # Instead of having bottom margin for a text block, we can print a bar as well.
    printer.add_bar(width=900, height=3)

    # And just to space out the next block, we can print a blank bar.
    # Zero-width bars should produce a blank line.
    printer.add_bar(width=0, height=20)

def print_text_sizes(printer: StarTSP, font_name: str = DEFAULT_FONT_NAME, font_size_set: list[int] = DEFAULT_FONT_SIZE_SET_A) -> None:
    for font_size in font_size_set:
        printer.add_bar(width=0, height=5)
        printer.add_text(f"{font_size}:", font_size=20, font_name=DEFAULT_FONT_NAME)
        printer.add_text("Eat some more of these fresh french buns and drink some tea", font_size=font_size, font_name=font_name)

def print_text_cpi_2inch(printer: StarTSP, font_name: str = DEFAULT_FONT_NAME, font_size_set: list[int] = DEFAULT_FONT_SIZE_SET_CPI_2inch) -> None:
    printer.add_text(f"TARGETING 7.5 CPI at 203 DPI (15chars on 406px)", font_size=20)
    printer.add_text(f"FONT NAME: {font_name}", font_size=20)

    for font_size in font_size_set:
        printer.add_bar(width=0, height=5)
        printer.add_text(f"{font_size}:", font_size=20, font_name=DEFAULT_FONT_NAME)
        printer.add_text("123456789-12345", font_size=font_size, font_name=font_name)
        printer.add_bar(width=406, height=20, margin_left=0)

def print_text_cpi_1inch(printer: StarTSP, font_name: str = DEFAULT_FONT_NAME, font_size_set: list[int] = DEFAULT_FONT_SIZE_SET_CPI_1inch) -> None:
    printer.add_text(f"TARGETING 15 CPI at 203 DPI (15chars on 203px)", font_size=20)
    printer.add_text(f"FONT NAME: {font_name}", font_size=20)

    for font_size in font_size_set:
        printer.add_bar(width=0, height=5)
        printer.add_text(f"{font_size}:", font_size=20, font_name=DEFAULT_FONT_NAME)
        printer.add_text("123456789-12345", font_size=font_size, font_name=font_name)
        printer.add_bar(width=203, height=20, margin_left=0)

def print_text_cpi_05inch(printer: StarTSP, font_name: str = DEFAULT_FONT_NAME, font_size_set: list[int] = DEFAULT_FONT_SIZE_SET_CPI_05inch) -> None:
    printer.add_text(f"TARGETING 30 CPI at 203 DPI (15chars on 203px)", font_size=20)
    printer.add_text(f"FONT NAME: {font_name}", font_size=20)

    for font_size in font_size_set:
        printer.add_bar(width=0, height=5)
        printer.add_text(f"{font_size}:", font_size=20, font_name=DEFAULT_FONT_NAME)
        printer.add_text("123456789-123456789-123456789-", font_size=font_size, font_name=font_name)
        printer.add_bar(width=203, height=20)

def print_text_cpi_full(printer: StarTSP, font_name: str = DEFAULT_FONT_NAME, font_size_set: list[int] = DEFAULT_FONT_SIZE_SET_CPI_FULL) -> None:
    stub_text = (
        "abcdefgh>1abcdefgh>2abcdefgh>3abcdefgh>4abcdefgh>5abcdefgh>6"
        "abcdefgh>7abcdefgh>8abcdefgh>9abcdefgh>1abcdefgh>2abcdefgh>3"
    )
    printer.add_text(f"TARGETING FULL LINE", font_size=20)
    printer.add_text(f"FONT NAME: {font_name}", font_size=20)

    for font_size in font_size_set:
        printer.add_bar(width=0, height=5)
        printer.add_text(f"{font_size}:", font_size=20, font_name=DEFAULT_FONT_NAME)
        printer.add_text(stub_text, font_size=font_size, font_name=font_name)
        printer.add_bar(width=203, height=20, margin_left=203)

def print_bar_widths(printer: StarTSP, height: int = 20, width_set: list[int] = DEFAULT_BAR_WIDTH_SET) -> None:
    for bar_width in width_set:
        printer.add_text(f"\nBAR {bar_width}:", font_size=20, font_name=DEFAULT_FONT_NAME)
        printer.add_bar(width=bar_width, height=height)

def print_bar_hit_right(printer: StarTSP, margin_set: list[int] = DEFAULT_BAR_HIT_RIGHT_SET) -> None:
    printer.add_text(f"TARGETING THE RIGHT END OF PAGE:", font_size=20, font_name=DEFAULT_FONT_NAME)
    printer.add_bar(width=0, height=15)

    for margin in margin_set:
        printer.add_bar(width=0, height=5)
        printer.add_text(f"->{margin}px ->1px:", font_size=15, font_name=DEFAULT_FONT_NAME)
        printer.add_bar(width=10, height=20, margin_left=margin)
        printer.add_bar(width=1000, height=3)
