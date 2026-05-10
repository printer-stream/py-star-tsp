"""Printer presets for ESC/POS emulation.

Defines :class:`PrinterPreset` and ready-made constants for common
thermal receipt printer models.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Bundled default font
# ---------------------------------------------------------------------------

#: Absolute path to the bundled Orator 15 CPI font.
_BUNDLED_FONT: str = str(
    Path(__file__).parent.parent / "fonts" / "orator_15cpi.otf"
)

#: Absolute path to the bundled OCR-A font.
_FONT_OCR_A: str = str(
    Path(__file__).parent.parent / "fonts" / "ocr_a_std.otf"
)

#: Absolute path to the bundled OCR-B font.
_FONT_OCR_B: str = str(
    Path(__file__).parent.parent / "fonts" / "ocr_b.ttf"
)


# ---------------------------------------------------------------------------
# PrinterPreset
# ---------------------------------------------------------------------------

@dataclass
class PrinterPreset:
    """All configurable parameters describing a target receipt printer.

    The default values match the **Epson TM-T88V** at 203 dpi on 80 mm
    paper — the most widely deployed thermal receipt printer family.

    Attributes:
        name: Human-readable label for this preset.
        print_width_dots: Printable width in raster dots.
        dpi: Printer resolution in dots per inch.
        font_a_char_width: Font A character cell width in dots.
        font_a_char_height: Font A character cell height in dots.
        font_a_line_height: Font A line height (char + leading) in dots.
        font_a_chars_per_line: Characters per line for Font A.
        font_a_name: Font file path or stem for Font A rendering.
            ``None`` uses the bundled Orator 15 CPI font.
        font_b_char_width: Font B character cell width in dots.
        font_b_char_height: Font B character cell height in dots.
        font_b_line_height: Font B line height in dots.
        font_b_chars_per_line: Characters per line for Font B.
        font_b_name: Font file path or stem for Font B rendering.
            ``None`` falls back to :attr:`font_a_name`.
        default_line_spacing: Default inter-line spacing in dots
            (restored by ``ESC 2``).
    """

    name: str = "Epson TM-T88"

    # Physical / raster dimensions
    print_width_dots: int = 576
    dpi: int = 203

    # Font A — standard (12×24 dot cell)
    font_a_char_width: int = 12
    font_a_char_height: int = 24
    font_a_line_height: int = 33
    font_a_chars_per_line: int = 42
    font_a_name: Optional[str] = _BUNDLED_FONT  # Orator 15 CPI

    # Font B — condensed (9×17 dot cell)
    font_b_char_width: int = 9
    font_b_char_height: int = 17
    font_b_line_height: int = 24
    font_b_chars_per_line: int = 56
    font_b_name: Optional[str] = None   # None → same as font_a_name

    # Default line spacing (restored by ESC 2)
    default_line_spacing: int = 33

    def copy(self, **overrides) -> "PrinterPreset":
        """Return a new :class:`PrinterPreset` with *overrides* applied.

        Example::

            custom = PRESET_EPSON_TM_T88.copy(
                name="My Printer",
                font_a_chars_per_line=40,
            )
        """
        return replace(self, **overrides)


# ---------------------------------------------------------------------------
# Pre-built presets
# ---------------------------------------------------------------------------

#: Default preset — Epson TM-T88V, 80 mm, 203 dpi.
PRESET_EPSON_TM_T88: PrinterPreset = PrinterPreset(
    name="Epson TM-T88",
    print_width_dots=576,
    dpi=203,
    font_a_char_width=12,
    font_a_char_height=24,
    font_a_line_height=33,
    font_a_chars_per_line=42,
    font_a_name=_BUNDLED_FONT,   # Orator 15 CPI
    font_b_char_width=9,
    font_b_char_height=17,
    font_b_line_height=24,
    font_b_chars_per_line=56,
    font_b_name=None,
    default_line_spacing=33,
)

#: Preset for generic 58 mm printers.
PRESET_58MM: PrinterPreset = PrinterPreset(
    name="Generic 58mm",
    print_width_dots=384,
    dpi=203,
    font_a_char_width=12,
    font_a_char_height=24,
    font_a_line_height=33,
    font_a_chars_per_line=32,
    font_a_name=_BUNDLED_FONT,   # Orator 15 CPI
    font_b_char_width=9,
    font_b_char_height=17,
    font_b_line_height=24,
    font_b_chars_per_line=42,
    font_b_name=None,
    default_line_spacing=33,
)
