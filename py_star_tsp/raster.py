"""
RasterImage — converts a PIL Image to 1-bit raster lines suitable for
sending to a Star printer in Graphic Mode.
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
    """A set of raster blocks, with associated metadata.

    That's what Printer holds internally as it builds up the print "queue".
    The blocks from the RasterSet are then supposed to be converted to raster lines
    and sent to the printer.

    TODO: Variable block width breaks the printer's line-by-line processing.
          At this point we just make sure all widths are "correct",
          meaning they don't break the printing. The way of passing down the lines
          must be redesigned.

    TODO: At this point the only block type is RasterImage,
          but there could be other types in the future.

    TODO: Make sure the order of blocks is preserved.
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
            total_height += block.height
            logger.debug(f"Gathered block height: +{block.height}px subtotal={total_height}px")
        return total_height

    @property
    def raster_lines(self) -> List[bytes]:
        lines: List[bytes] = []
        for block in self.blocks:
            logger.debug(f"Converting block to raster lines: {block}")
            lines.extend(block.to_raster_lines(padding_width=self.total_width))
        return lines

    def to_image(self) -> "Image.Image":
        """Render the full raster queue into a Pillow image."""
        if self.total_width <= 0 or self.total_height <= 0:
            raise ValueError("Cannot render an empty RasterSet")

        # Printer raster bytes use 1 = black, 0 = white.
        # Pillow mode '1' expects the opposite bit polarity.
        preview_bytes = bytearray()
        for line in self.raster_lines:
            preview_bytes.extend((~byte) & 0xFF for byte in line)

        return Image.frombytes(
            "1",
            (self.total_width, self.total_height),
            bytes(preview_bytes),
        )

    def save(self, filename: str, format: Optional[str] = None, **save_kwargs) -> None:
        """Save the rendered raster queue to an image file.

        Args:
            filename: Output file path.
            format: Optional Pillow format override. If omitted, Pillow infers
                the format from *filename*.
            **save_kwargs: Extra keyword arguments passed to ``Image.save``.

        Notes:
            JPEG does not support 1-bit mode, so the image is converted to
            8-bit grayscale automatically for that format.
        """
        image = self.to_image()
        image_format = (format or Path(filename).suffix.lstrip(".")).upper()

        if image_format.upper() in {"JPG", "JPEG"}:
            image = image.convert("L")

        image.save(filename, format=format, **save_kwargs)

    def add(self, block) -> None:
        logger.debug(f"Adding block to RasterSet: {block}")
        self.blocks.append(block)

    def flush(self) -> None:
        logger.debug("Flushing RasterSet blocks")
        self.blocks.clear()

class RasterImage:
    """Wrap a PIL Image and expose it as packed 1-bit raster lines.

    Args:
        image (Image.Image): A PIL ``Image`` object.  Any mode is accepted; the image is
               converted to ``'1'`` (1-bit black-and-white) internally.

    """

    def __init__(self, image: "Image.Image", bw_threshold: int = 200) -> None:
        fn = lambda x: 255 if x > bw_threshold else 0
        self._image = image.convert("L").point(fn, mode="1")

    def __repr__(self) -> str:
        return f"RasterImage({self.width}x{self.height})"

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
            logger.info(f"Shrinking image from {self.width}px to fit max width {max_width}px")
            new_height = int(self.height * (max_width / self.width) + 0.5)
            self._image.thumbnail((max_width, new_height), Image.Resampling.LANCZOS)

    def to_raster_lines(self, padding_width: Optional[int] = None) -> List[bytes]:
        """Return a list of packed raster lines, one ``bytes`` per row.

        Each row is packed MSB-first: the leftmost pixel occupies bit 7
        of the first byte.  Rows are padded with zero-bits to the next
        byte boundary.
        """
        img = self._image
        img_width = img.width
        img_height = img.height
        logger.debug(f"Converting RasterImage {img} to raster lines: {img_width}×{img_height} pixels")

        if padding_width is not None:
            bytes_per_row = (padding_width + 7) // 8
            logger.debug(f"Using padding width {padding_width} pixels -> {bytes_per_row} bytes per row")
        else:
            bytes_per_row = (img_width + 7) // 8
            logger.debug(f"No padding width specified, using image width {img_width} pixels -> {bytes_per_row} bytes per row")

        lines: List[bytes] = []

        # Invert so that black=1 bit (printer convention) instead of
        # PIL's black=0 bit, then pack with tobytes().
        logger.debug("Inverting image for printer convention (black=1 bit)")
        inverted = Image.eval(img, lambda p: 255 - p)
        raw = inverted.tobytes()

        img_bytes_per_row = (img_width + 7) // 8
        logger.debug(f"Image bytes per row: {img_bytes_per_row}, total bytes: {len(raw)}")

        pad = bytes_per_row - img_bytes_per_row
        logger.debug(f"Calculated padding: {pad} bytes per row")

        logger.debug("Packing raster lines with padding")
        for y in range(img_height):
            offset = y * img_bytes_per_row
            row = raw[offset:offset + img_bytes_per_row]
            if pad > 0:
                row += b'\x00' * pad
            lines.append(row)

        logger.debug(f"Generated {len(lines)} raster lines, length={bytes_per_row} padding={pad}")
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

        Notes:
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
        logger.debug(f"Creating SolidBar: width={width}px, height={height}px, margin_left={margin_left}px, margin_right={margin_right}px, total_width={img_width}px")

        for y in range(img_height):
            for x in range(margin_left, margin_left + width):
                pixels[x, y] = 0  # 0 = black (printed)

        super().__init__(image=img)

