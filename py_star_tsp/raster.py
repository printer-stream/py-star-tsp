"""
RasterImage — converts a PIL Image to 1-bit raster lines suitable for
sending to a Star TSP100 printer in Graphic Mode.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from pathlib import Path


try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Pillow is required for RasterImage. Install it with: pip install Pillow"
    ) from exc

logger = logging.getLogger("py_star_tsp")

class RasterSet:
    """A set of raster lines, with associated metadata.

    This is the data structure passed to the printer's ``print_raster_image()`` method.
    """

    def __init__(self, blocks=None) -> None:
        if blocks:
            self.blocks = blocks
        else:
            self.blocks = []

    @property
    def total_width(self) -> int:
        total_width = 0
        for block in self.blocks:
            total_width = max(total_width, block.width)
        return total_width

    @property
    def total_height(self) -> int:
        total_height = 0
        for block in self.blocks:
            logger.info(f"Block: {block}")
            total_height += block.height
        return total_height

    @property
    def raster_lines(self) -> List[bytes]:
        lines: List[bytes] = []
        for block in self.blocks:
            lines.extend(block.to_raster_lines())
        return lines

    def add(self, block) -> None:
        logger.info(f"Adding block to RasterSet: {block}")
        self.blocks.append(block)


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

    def __repr__(self) -> str:
        return f"RasterImage(width={self.width}, height={self.height})"

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

    @staticmethod
    def from_file(filename: str) -> "RasterImage":
        """Create a RasterImage from an image file."""
        filename_path = Path(filename)
        if not filename_path.is_file():
            raise FileNotFoundError(f"Image file not found: {filename}")
        img = Image.open(filename_path)
        return RasterImage(img)

    def invert(self) -> None:
        """Invert the image in-place (black pixels become white and vice versa)."""
        self._image = Image.eval(self._image, lambda p: 255 - p)

    def shrink_to_fit(self, max_width: int) -> None:
        """
            Shrink the image to fit within the given maximum width, 
            preserving aspect ratio.
        """
        if self.width > max_width:
            new_height = int(self.height * (max_width / self.width))
            self._image.thumbnail((max_width, new_height), Image.Resampling.LANCZOS)

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


class SolidBar(RasterImage):
    """A solid black bar of the specified dimensions."""

    def __init__(self, width: int, height: int, margin_left: int = 0, margin_right: int = 0) -> None:
        """Initialize a solid black bar with optional margins.

        Args:
            width (int): Width of the black bar in pixels.
            height (int): Height of the black bar in pixels.
            margin_left (int, optional): Left margin in pixels. Defaults to 0.
            margin_right (int, optional): Right margin in pixels. Defaults to 0.
            
            margin_right is a workaround for the fact that the printer 
            may ignore trailing bits of the last byte in a row if 
            the total width is not a multiple of 8. By adding margin pixels 
            to the right, we can ensure that the black bar extends into 
            those bits and is printed correctly.
        """
        img_width = margin_left + width + margin_right
        img_height = height

        img = Image.new("1", (img_width, img_height), color=255)  # 255 = white (not printed)
        pixels = img.load()

        for y in range(img_height):
            for x in range(margin_left, margin_left + width):
                pixels[x, y] = 0  # 0 = black (printed)

        super().__init__(img)

