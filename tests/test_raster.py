"""Unit tests for py_star_tsp.raster primitives."""

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

if HAS_PIL:
    from py_star_tsp.raster import RasterImage, RasterSet


@unittest.skipUnless(HAS_PIL, "Pillow is not installed")
class TestRasterImageProperties(unittest.TestCase):
    def _make_image(self, width: int, height: int, color: int = 255) -> "Image.Image":
        """Create a solid-colour 'L' mode image."""
        return Image.new("L", (width, height), color=color)

    def test_width_and_height(self):
        img = self._make_image(16, 8)
        ri = RasterImage(img)
        self.assertEqual(ri.width, 16)
        self.assertEqual(ri.height, 8)

    def test_converts_to_1bit(self):
        img = Image.new("RGB", (8, 1), color=(128, 128, 128))
        ri = RasterImage(img)
        # Should not raise; image is internally 1-bit
        lines = ri.to_raster_lines()
        self.assertEqual(len(lines), 1)


@unittest.skipUnless(HAS_PIL, "Pillow is not installed")
class TestRasterLines(unittest.TestCase):
    def test_all_white_image(self):
        """An all-white image should produce zero bytes (no black pixels)."""
        img = Image.new("L", (8, 2), color=255)  # 255 = white
        ri = RasterImage(img)
        lines = ri.to_raster_lines()
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertEqual(line, b"\x00")

    def test_all_black_image(self):
        """An all-black image should produce all-set bytes."""
        img = Image.new("L", (8, 1), color=0)  # 0 = black
        ri = RasterImage(img)
        lines = ri.to_raster_lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], b"\xff")

    def test_single_leftmost_pixel(self):
        """A single black pixel at x=0 should set bit 7 of first byte."""
        img = Image.new("L", (8, 1), color=255)
        pixels = img.load()
        pixels[0, 0] = 0  # black pixel at x=0
        ri = RasterImage(img)
        lines = ri.to_raster_lines()
        # bit 7 of byte 0 should be set → 0x80
        self.assertEqual(lines[0], b"\x80")

    def test_single_rightmost_pixel(self):
        """A single black pixel at x=7 should set bit 0 of first byte."""
        img = Image.new("L", (8, 1), color=255)
        pixels = img.load()
        pixels[7, 0] = 0  # black pixel at x=7
        ri = RasterImage(img)
        lines = ri.to_raster_lines()
        self.assertEqual(lines[0], b"\x01")

    def test_nine_pixel_row_padded(self):
        """Nine pixels should produce 2 bytes per row (padded to byte boundary)."""
        img = Image.new("L", (9, 1), color=255)
        pixels = img.load()
        pixels[8, 0] = 0  # black at x=8 → bit 7 of second byte
        ri = RasterImage(img)
        lines = ri.to_raster_lines()
        self.assertEqual(len(lines[0]), 2)
        self.assertEqual(lines[0], b"\x00\x80")

    def test_line_count(self):
        img = Image.new("L", (8, 10), color=255)
        ri = RasterImage(img)
        self.assertEqual(len(ri.to_raster_lines()), 10)

    def test_bytes_per_row_multiple_of_8(self):
        img = Image.new("L", (16, 1), color=0)
        ri = RasterImage(img)
        lines = ri.to_raster_lines()
        self.assertEqual(len(lines[0]), 2)
        self.assertEqual(lines[0], b"\xff\xff")

    def test_non_multiple_of_8_width(self):
        """Width not a multiple of 8 should be padded."""
        img = Image.new("L", (10, 1), color=0)
        ri = RasterImage(img)
        lines = ri.to_raster_lines()
        # 10 pixels → 2 bytes; last 6 bits of byte 1 are padding (0)
        # Byte 0: 8 black pixels = 0xff
        # Byte 1: 2 black pixels at bits 7,6 = 0xc0; remaining bits = 0
        self.assertEqual(len(lines[0]), 2)
        self.assertEqual(lines[0], b"\xff\xc0")

    def test_384_pixel_row(self):
        """Typical TSP100 print width of 384 pixels should produce 48 bytes."""
        img = Image.new("L", (384, 1), color=255)
        ri = RasterImage(img)
        lines = ri.to_raster_lines()
        self.assertEqual(len(lines[0]), 48)


@unittest.skipUnless(HAS_PIL, "Pillow is not installed")
class TestRasterSetExport(unittest.TestCase):
    def test_to_image_pads_narrower_rows_to_full_width(self):
        wide = RasterImage(Image.new("L", (16, 1), color=255))
        narrow_source = Image.new("L", (8, 1), color=255)
        narrow_source.load()[0, 0] = 0
        narrow = RasterImage(narrow_source)

        raster_set = RasterSet([wide, narrow])

        image = raster_set.to_image()

        self.assertEqual(image.size, (16, 2))
        self.assertEqual(image.getpixel((0, 1)), 0)
        self.assertEqual(image.getpixel((15, 1)), 255)

    def test_save_bmp_writes_1bit_preview(self):
        img = Image.new("L", (8, 2), color=255)
        img.load()[0, 0] = 0
        raster_set = RasterSet([RasterImage(img)])

        with TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "preview.bmp"
            raster_set.save(str(output_path))

            with Image.open(output_path) as saved:
                self.assertEqual(saved.format, "BMP")
                self.assertEqual(saved.size, (8, 2))
                self.assertEqual(saved.getpixel((0, 0)), 0)

    def test_save_jpeg_converts_to_grayscale(self):
        img = Image.new("L", (8, 2), color=255)
        img.load()[0, 0] = 0
        raster_set = RasterSet([RasterImage(img)])

        with TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "preview.jpg"
            raster_set.save(str(output_path), quality=95)

            with Image.open(output_path) as saved:
                self.assertEqual(saved.format, "JPEG")
                self.assertEqual(saved.size, (8, 2))
                self.assertEqual(saved.mode, "L")

    def test_to_image_rejects_empty_set(self):
        with self.assertRaises(ValueError):
            RasterSet().to_image()


if __name__ == "__main__":
    unittest.main()
