"""
Integration tests for py-star-tsp — require a real Star TSP100 printer.

These tests are **skipped** automatically when no printer is detected
(the default).  To run them, connect a Star TSP100 via USB and set the
environment variable ``PY_STAR_TSP_INTEGRATION=1``:

    PY_STAR_TSP_INTEGRATION=1 python -m pytest tests/test_integration.py -v

Requirements
------------
* A Star TSP100 USB printer connected and powered on.
* On Linux: a udev rule granting your user access to the USB device
  (see README.md).  Default expected device path: ``/dev/usb/lp0``
  (Rocky 9 / RHEL 9).
* ``pyusb`` and ``Pillow`` installed.

What is tested
--------------
* Basic raster image printing (all-black band).
* Text rendering with various formatting options.
* Font discovery and fallback behaviour.
* Styled text: bold, underline, italic, bordered, inverted.
"""

import logging
import os
import unittest

logger = logging.getLogger(__name__)

_RUN_INTEGRATION = os.environ.get("PY_STAR_TSP_INTEGRATION", "0") == "1"

_skip_reason = (
    "Integration tests require a real printer.  "
    "Set PY_STAR_TSP_INTEGRATION=1 to enable."
)

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

if HAS_PIL:
    from py_star_tsp import StarTSP, RasterImage
    from py_star_tsp.text import render_text


@unittest.skipUnless(_RUN_INTEGRATION, _skip_reason)
@unittest.skipUnless(HAS_PIL, "Pillow is not installed")
class TestRasterPrinting(unittest.TestCase):
    """Print raster images on a real TSP100."""

    def _open_printer(self) -> "StarTSP":
        printer = StarTSP()
        printer.open()
        return printer

    def test_print_black_band(self):
        """Print a 384×50 all-black band."""
        printer = self._open_printer()
        try:
            img = Image.new("L", (384, 50), color=0)
            ri = RasterImage(img)
            printer.print_raster_image(ri)
            logger.info("Printed black band successfully")
        finally:
            printer.close()

    def test_print_white_band(self):
        """Print a 384×50 all-white band (feeds paper)."""
        printer = self._open_printer()
        try:
            img = Image.new("L", (384, 50), color=255)
            ri = RasterImage(img)
            printer.print_raster_image(ri)
            logger.info("Printed white band (feed) successfully")
        finally:
            printer.close()


@unittest.skipUnless(_RUN_INTEGRATION, _skip_reason)
@unittest.skipUnless(HAS_PIL, "Pillow is not installed")
class TestTextPrinting(unittest.TestCase):
    """Print rendered text on a real TSP100."""

    def _open_printer(self) -> "StarTSP":
        printer = StarTSP()
        printer.open()
        return printer

    def test_print_plain_text(self):
        """Print simple text."""
        printer = self._open_printer()
        try:
            printer.print_text("Hello, TSP100!")
            logger.info("Printed plain text successfully")
        finally:
            printer.close()

    def test_print_bold_text(self):
        printer = self._open_printer()
        try:
            printer.print_text("Bold text", bold=True)
            logger.info("Printed bold text successfully")
        finally:
            printer.close()

    def test_print_underline_text(self):
        printer = self._open_printer()
        try:
            printer.print_text("Underlined", underline=True)
            logger.info("Printed underline text successfully")
        finally:
            printer.close()

    def test_print_italic_text(self):
        printer = self._open_printer()
        try:
            printer.print_text("Italic text", italic=True)
            logger.info("Printed italic text successfully")
        finally:
            printer.close()

    def test_print_all_styles(self):
        printer = self._open_printer()
        try:
            printer.print_text(
                "Bold+Italic+Underline",
                bold=True,
                italic=True,
                underline=True,
            )
            logger.info("Printed all-styles text successfully")
        finally:
            printer.close()

    def test_print_bordered_text(self):
        printer = self._open_printer()
        try:
            printer.print_text("Bordered", border=True, border_thickness=3)
            logger.info("Printed bordered text successfully")
        finally:
            printer.close()

    def test_print_white_on_black(self):
        printer = self._open_printer()
        try:
            printer.print_text(
                "White on Black",
                invert=True,
                box_fill=True,
                border=True,
            )
            logger.info("Printed white-on-black text successfully")
        finally:
            printer.close()

    def test_print_multiline(self):
        printer = self._open_printer()
        try:
            printer.print_text("Line 1\nLine 2\nLine 3")
            logger.info("Printed multiline text successfully")
        finally:
            printer.close()


@unittest.skipUnless(_RUN_INTEGRATION, _skip_reason)
@unittest.skipUnless(HAS_PIL, "Pillow is not installed")
class TestTextRendering(unittest.TestCase):
    """Test text rendering produces valid images (no printer required)."""

    def test_render_returns_image(self):
        img = render_text("Test rendering")
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.mode, "1")
        self.assertEqual(img.width, 384)

    def test_render_various_sizes(self):
        for size in (10, 16, 20, 30):
            img = render_text("Size test", font_size=size)
            self.assertEqual(img.mode, "1")
            self.assertGreater(img.height, 0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
