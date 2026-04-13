"""
RasterImage — converts a PIL Image to 1-bit raster lines suitable for
sending to a Star TSP100 printer in Graphic Mode.
"""

from __future__ import annotations

from typing import List

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Pillow is required for RasterImage. Install it with: pip install Pillow"
    ) from exc


class RasterImage:
    """Wrap a PIL Image and expose it as packed 1-bit raster lines.

    Parameters
    ----------
    image:
        A PIL ``Image`` object.  Any mode is accepted; the image is
        converted to ``'1'`` (1-bit black-and-white) internally.
    """

    def __init__(self, image: "Image.Image") -> None:
        self._image = image.convert("1")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def width(self) -> int:
        """Image width in pixels."""
        return self._image.width

    @property
    def height(self) -> int:
        """Image height in pixels."""
        return self._image.height

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def to_raster_lines(self) -> List[bytes]:
        """Return a list of packed raster lines, one ``bytes`` per row.

        Each row is packed MSB-first: the leftmost pixel occupies bit 7
        of the first byte.  Rows are padded with zero-bits to the next
        byte boundary.
        """
        img = self._image
        w = img.width
        h = img.height
        bytes_per_row = (w + 7) // 8
        lines: List[bytes] = []
        pixels = img.load()
        for y in range(h):
            row = bytearray(bytes_per_row)
            for x in range(w):
                pixel = pixels[x, y]
                # PIL mode '1': 0 = black (printed), 255 = white (not printed)
                if pixel == 0:
                    byte_index = x // 8
                    bit_index = 7 - (x % 8)  # MSB first
                    row[byte_index] |= 1 << bit_index
            lines.append(bytes(row))
        return lines
