"""
Text rendering for Star TSP100 thermal printers.

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

logger = logging.getLogger(__name__)

# ── Default printer width ──────────────────────────────────────────────
DEFAULT_WIDTH = 384  # TSP100 print width at 203 dpi

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
    ],
    "Darwin": [
        "/System/Library/Fonts",
        "/Library/Fonts",
        str(Path.home() / "Library/Fonts"),
    ],
    "Windows": [
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
    ],
}


def _font_search_dirs() -> List[str]:
    """Return a list of directories to search for fonts on this OS."""
    system = platform.system()
    dirs = list(_FONT_DIRS.get(system, []))
    # Also include any directories from the FONTPATH environment variable
    extra = os.environ.get("FONTPATH", "")
    if extra:
        dirs.extend(extra.split(os.pathsep))
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
    for d in _font_search_dirs():
        dp = Path(d)
        if not dp.is_dir():
            continue
        for p in dp.rglob("*"):
            if p.suffix.lower() in (".ttf", ".otf") and p.is_file():
                fonts[p.stem] = str(p)
    logger.debug("discover_fonts: found %d fonts", len(fonts))
    return fonts


def find_font(
    name: Optional[str] = None,
    bold: bool = False,
    italic: bool = False,
) -> Optional[str]:
    """Locate a TrueType/OpenType font file by *name*.

    If *name* is ``None`` the fallback list is tried in order.  When
    *bold* or *italic* are requested the function first looks for
    variant-specific stems (e.g. ``DejaVuSansMono-Bold``).

    Returns
    -------
    str or None
        Full path to the font file, or ``None`` if nothing was found.
    """
    available = discover_fonts()
    if not available:
        logger.warning("No system fonts found; falling back to Pillow default")
        return None

    # Build a list of candidate names
    candidates: List[str] = []
    names_to_try = [name] if name else list(FALLBACK_FONT_NAMES)

    for base in names_to_try:
        # Normalise: remove spaces for stem matching
        base_ns = base.replace(" ", "")
        suffixes: List[str] = []
        if bold and italic:
            suffixes = ["-BoldItalic", "-BoldOblique", "-Bold-Italic"]
        elif bold:
            suffixes = ["-Bold"]
        elif italic:
            suffixes = ["-Italic", "-Oblique"]
        suffixes.append("")  # plain variant as final fallback

        for sfx in suffixes:
            candidates.append(base_ns + sfx)
            candidates.append(base + sfx)  # with original spaces

    for c in candidates:
        if c in available:
            logger.debug("find_font: matched %r → %s", c, available[c])
            return available[c]

    # Last resort: return the first available font
    first = next(iter(available.values()))
    logger.info("find_font: no exact match; using first available: %s", first)
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
            logger.warning("Failed to load font %s; using default", font_path)
    logger.info("Using Pillow built-in bitmap font (no sizing/style support)")
    return ImageFont.load_default()


def render_text(
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
    box_fill: bool = False,
    invert: bool = False,
    line_spacing: int = 4,
) -> Image.Image:
    """Render *text* to a 1-bit ``PIL.Image`` suitable for raster printing.

    Parameters
    ----------
    text:
        The text string to render.  Multi-line strings are supported.
    font_name:
        Font name (stem) to search for.  ``None`` tries the fallback list.
    font_size:
        Font size in pixels (ignored when the built-in bitmap font is used).
    bold:
        Request a bold variant.
    italic:
        Request an italic variant.
    underline:
        Draw an underline beneath each line of text.
    width:
        Image width in pixels (default 384 for TSP100).
    border:
        Draw a rectangular border around the text area.
    border_thickness:
        Border line width in pixels.
    box_fill:
        Fill the background of the text area.  When combined with
        *invert* this produces white text on a black background.
    invert:
        Swap foreground/background colours (white-on-black).
    line_spacing:
        Extra vertical pixels between lines of text.

    Returns
    -------
    PIL.Image.Image
        A mode-``"1"`` (1-bit) image ready for :class:`~py_star_tsp.raster.RasterImage`.
    """
    font_path = find_font(font_name, bold=bold, italic=italic)
    font = _load_font(font_path, font_size)

    fg = 0 if not invert else 255  # foreground (text)
    bg = 255 if not invert else 0  # background

    # ── Measure text ──────────────────────────────────────────────
    lines = text.split("\n")
    # Use a scratch image to measure
    scratch = Image.new("L", (1, 1))
    draw = ImageDraw.Draw(scratch)

    line_heights: List[int] = []
    line_widths: List[int] = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        line_widths.append(lw)
        line_heights.append(lh)

    total_height = sum(line_heights) + line_spacing * max(len(lines) - 1, 0)

    # Add padding for border
    pad = (border_thickness + 2) if border else 2
    img_height = total_height + 2 * pad

    # ── Create image ──────────────────────────────────────────────
    img = Image.new("L", (width, img_height), color=bg)
    draw = ImageDraw.Draw(img)

    if box_fill:
        draw.rectangle([0, 0, width - 1, img_height - 1], fill=(255 - bg))

    # Determine text fill colour on top of box_fill
    text_fill = fg
    if box_fill:
        text_fill = bg  # text is opposite of the fill

    # ── Draw text ─────────────────────────────────────────────────
    y_cursor = pad
    for i, line in enumerate(lines):
        x = pad
        # Compute baseline offset from textbbox
        bbox = draw.textbbox((0, 0), line, font=font)
        y_offset = -bbox[1]  # compensate for font ascent
        draw.text((x, y_cursor + y_offset), line, fill=text_fill, font=font)

        if underline and line_heights[i] > 0:
            ul_y = y_cursor + y_offset + line_heights[i] + 1
            draw.line(
                [(x, ul_y), (x + line_widths[i], ul_y)],
                fill=text_fill,
                width=max(1, font_size // 12),
            )

        y_cursor += line_heights[i] + line_spacing

    # ── Border ────────────────────────────────────────────────────
    if border:
        border_fill = fg if not box_fill else text_fill
        for t in range(border_thickness):
            draw.rectangle(
                [t, t, width - 1 - t, img_height - 1 - t],
                outline=border_fill,
            )

    # ── Convert to 1-bit ──────────────────────────────────────────
    return img.convert("1")
