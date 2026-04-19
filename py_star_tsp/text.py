"""
Text rendering for Star thermal printers.

Renders text as raster images using Pillow and system fonts.
Supports font discovery, style options (bold, italic, underline),
bordered/filled boxes, and white-on-black (inverted) text.

Font Discovery
--------------
Fonts are located using :func:`discover_fonts`, which searches standard
OS directories for ``.ttf`` and ``.otf`` files.  The following Python
packages can be installed to provide additional font sources:

* **matplotlib** – ships with DejaVu Sans / DejaVu Sans Mono.
* **fonttools** – useful for inspecting font metadata.
* **font-dejavu** / **font-liberation** (system packages on most Linux
  distros) – provide DejaVu and Liberation font families.

If no TrueType/OpenType fonts are found the renderer falls back to
Pillow's built-in bitmap font (``ImageFont.load_default()``).  This
bitmap font does **not** support sizing, bold, italic, or underline;
a warning is emitted via the ``logging`` module.

Midtones / Grayscale on TSP100
------------------------------
The TSP100 is a *monochrome* thermal printer (1-bit output).  True
grayscale is not possible.  However, the appearance of midtones can be
approximated by **dithering** the source image before rasterising:

>>> from PIL import Image
>>> grey = Image.new("L", (384, 100), color=128)
>>> dithered = grey.convert("1")  # Floyd-Steinberg dithering (default)

Pillow's ``Image.convert("1")`` uses Floyd-Steinberg error-diffusion
dithering by default.  You may also apply ordered (Bayer) dithering or
other halftone algorithms before passing the image to
:class:`~py_star_tsp.raster.RasterImage`.  Results vary with print
density and paper quality; experimentation is recommended.

TODO: Docstring is not reviewed at all.
"""

from __future__ import annotations

import logging
import os
import platform
from pathlib import Path
from typing import Dict, List, Optional

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Pillow is required for text rendering. Install it with: pip install Pillow"
    ) from exc

from py_star_tsp.raster import RasterImage

logger = logging.getLogger("py_star_tsp")


# ── Default printer width ──────────────────────────────────────────────
DEFAULT_WIDTH = 576

# ── Bundled default font ──────────────────────────────────────────────
BUNDLED_FONT_PATH = str(Path(__file__).parent / "fonts" / "orator_15cpi.otf")

# ── Fallback font names (in priority order) ───────────────────────────
FALLBACK_FONT_NAMES: List[str] = [
    "DejaVuSansMono",
    "DejaVu Sans Mono",
    "LiberationMono-Regular",
    "Liberation Mono",
    "FreeMono",
    "Arial",
    "arial",
    "Consolas",
    "Courier New",
    "cour",
]

# ── OS-specific font directories ──────────────────────────────────────
_FONT_DIRS: Dict[str, List[str]] = {
    "Linux": [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        str(Path.home() / ".local/share/fonts"),
        str(Path.home() / ".fonts"),
        str(Path(__file__).parent / "fonts"),
    ],
    "Darwin": [
        "/System/Library/Fonts",
        "/Library/Fonts",
        str(Path.home() / "Library/Fonts"),
        str(Path(__file__).parent / "fonts"),
    ],
    "Windows": [
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
        str(Path(__file__).parent / "fonts"),
    ],
}


def _font_search_dirs() -> List[str]:
    """Return a list of directories to search for fonts on this OS."""
    system = platform.system()
    dirs = list(_FONT_DIRS.get(system, []))
    logger.debug(f"_font_search_dirs: OS={system}, dirs={dirs}")

    # Also include any directories from the FONTPATH environment variable
    extra = os.environ.get("FONTPATH", "")
    if extra:
        dirs.extend(extra.split(os.pathsep))
        logger.debug(f"_font_search_dirs: added FONTPATH dirs={extra}")

    logger.debug(f"Final set of font search dirs: OS={system}, dirs={dirs}")
    return dirs


def discover_fonts() -> Dict[str, str]:
    """Scan the OS font directories and return a map of name → path.

    The key is the font file stem (e.g. ``"DejaVuSansMono-Bold"``),
    and the value is the full filesystem path.

    Returns
    -------
    dict
        ``{stem: path}`` for every ``.ttf`` / ``.otf`` file found.
    """
    fonts: Dict[str, str] = {}
    for potential_font_dir in _font_search_dirs():
        potential_font_dir_path = Path(potential_font_dir)
        if not potential_font_dir_path.is_dir():
            continue
        for potential_font_filename in potential_font_dir_path.rglob("*"):
            if potential_font_filename.suffix.lower() in (".ttf", ".otf") and potential_font_filename.is_file():
                fonts[potential_font_filename.stem] = str(potential_font_filename)
                logger.debug(f"discover_fonts: found font {potential_font_filename.stem} at {potential_font_filename}")

    logger.debug(f"discover_fonts: found {len(fonts)} fonts")
    return fonts


def find_font(name: Optional[str] = None, bold: bool = False, italic: bool = False) -> Optional[str]:
    """Locate a TrueType/OpenType font file by *name*.

    If *name* is ``None`` the fallback list is tried in order.  When
    *bold* or *italic* are requested the function first looks for
    variant-specific stems (e.g. ``DejaVuSansMono-Bold``).

    Returns:
        str or None: Full path to the font file, or ``None`` if nothing was found.
    """
    # If no specific name requested, try the bundled font first
    if name is None:
        if Path(BUNDLED_FONT_PATH).is_file():
            logger.debug(f"find_font: using bundled font {BUNDLED_FONT_PATH}")
            return BUNDLED_FONT_PATH
        else:
            logger.warning(f"Bundled font not found at {BUNDLED_FONT_PATH}; falling back to system fonts")

    available = discover_fonts()
    if not available:
        logger.error("No system fonts found; falling back to Pillow default")
        return None

    # Build a list of candidate names
    candidates: List[str] = []
    names_to_try = [name] if name else list(FALLBACK_FONT_NAMES)

    for base in names_to_try:

        # Normalise: remove spaces for stem matching
        base_ns = base.replace(" ", "")
        logger.debug(f"find_font: trying base name {base!r} (normalized {base_ns!r})")

        suffixes: List[str] = []
        if bold and italic:
            suffixes = ["-BoldItalic", "-BoldOblique", "-Bold-Italic"]
        elif bold:
            suffixes = ["-Bold"]
        elif italic:
            suffixes = ["-Italic", "-Oblique"]

        suffixes.append("")  # plain variant as final fallback
        logger.debug(f"find_font: generated suffixes {suffixes} for base {base!r}")

        for sfx in suffixes:
            candidates.append(base_ns + sfx)
            candidates.append(base + sfx)  # with original spaces

    for c in candidates:
        if c in available:
            logger.debug(f"find_font: matched {c!r} → {available[c]}")
            return available[c]

    # Last resort: return the first available font
    first = next(iter(available.values()))
    logger.warning(f"find_font: no exact match '{name}'; using first available: {first}")

    return first


def _load_font(
    font_path: Optional[str],
    size: int,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a PIL font object, falling back to the built-in default."""
    if font_path is not None:
        try:
            return ImageFont.truetype(font_path, size)
        except (OSError, IOError):
            logger.warning(f"Failed to load font {font_path}; using default")
    logger.warning("Using Pillow built-in bitmap font (no sizing/style support)")
    return ImageFont.load_default()


class TextBlock:
    """Render a block of text as a raster image, with styling options.

    Args:
        text: The text string to render.  Multi-line strings are supported.
        font_name: Font name (stem) to search for.  ``None`` tries the fallback list.
        font_size: Font size in pixels (ignored when the built-in bitmap font is used).
        bold: Request a bold variant.
        italic: Request an italic variant.
        underline: Draw an underline beneath each line of text.
        width: Image width in pixels.
        border: Draw a rectangular border around the text area.
        border_thickness: Border line width in pixels.
        box_fill: Fill the background of the text area.  When combined with
            *invert* this produces white text on a black background.
        invert: Swap foreground/background colours (white-on-black).
        line_spacing: Extra vertical pixels between lines of text.

    TODO: Bold/Italic/underline support is non existent
    TODO: Alignment is not supported
    TODO: The text is multilined, and line_spacing is actually interval?

    """
    def __init__(self,
        text: str,
        *,
        font_name: Optional[str] = None,
        font_size: int = 20,

        bold: bool = False,
        italic: bool = False,
        underline: bool = False,

        width: int = DEFAULT_WIDTH,

        border: bool = False,
        border_thickness: int = 2,

        invert: bool = False,
        line_spacing: int = 4,
) -> None:
        self.text = text
        self.font_name = font_name
        self.font_size = font_size
        self.bold = bold
        self.italic = italic
        self.underline = underline

        self.width = width

        self.border = border
        self.border_thickness = border_thickness
        self.invert = invert
        self.line_spacing = line_spacing

        self.text_colour = 0 if not self.invert else 255
        self.bg_colour = 255 if not self.invert else 0

        logger.debug(f"TextBlock width={width}")

        pass

    def render(self) -> RasterImage:
        """Render *text* to a 1-bit ``PIL.Image`` suitable for raster printing.
        """
        font_path = find_font(self.font_name, bold=self.bold, italic=self.italic)
        font = _load_font(font_path, self.font_size)
        logger.debug(f"TextBlock.render: using font {font_path!r}")

        text_padding = 0

        if self.border:
            text_padding += self.border_thickness + 2  # border + gap
            logger.info(f"TextBlock.render: border enabled thickness={self.border_thickness} text_padding={text_padding}")

        scratch = Image.new("L", (1, 1))
        draw = ImageDraw.Draw(scratch)

        bbox_left, bbox_top, bbox_right, bbox_bottom = draw.multiline_textbbox(
            (0, 0), self.text, font=font, spacing=self.line_spacing,
        )
        text_width = bbox_right - bbox_left
        text_height = bbox_bottom - bbox_top
        logger.debug(f"TextBlock.render: multiline bbox {(bbox_left, bbox_top, bbox_right, bbox_bottom)} => {text_width}×{text_height}")

        if text_width > self.width - 2 * text_padding:
            logger.warning(f"TextBlock.render: text width {text_width} exceeds image width {self.width}")

        img_height = text_height + 2 * text_padding

        # ── Create image ──────────────────────────────────────────────
        img = Image.new("L", (self.width, img_height), color=self.bg_colour)
        draw = ImageDraw.Draw(img)

        # TODO: This compensation bit I don't really understand:
        # Compensate for font ascent so first line sits at pad
        # origin_bbox = draw.multiline_textbbox((0, 0), self.text, font=font, spacing=self.line_spacing)
        y_origin = text_padding - bbox_top

        draw.multiline_text(
            (text_padding, y_origin), self.text,
            fill=self.text_colour, font=font, spacing=self.line_spacing,
        )

        if self.border:
            logger.info(f"TextBlock.render: drawing border with thickness {self.border_thickness}")
            for t in range(self.border_thickness):
                logger.info(f"TextBlock.render: drawing border iteration {t}")
                draw.rectangle(
                    [t, t, self.width - 1 - t, img_height - 1 - t],
                    outline=self.text_colour,
                )

        return RasterImage(img)

