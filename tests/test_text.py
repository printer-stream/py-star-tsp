"""Unit tests for py_star_tsp.text — text rendering and font discovery."""

import unittest
from unittest.mock import patch

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

if HAS_PIL:
    from py_star_tsp.text import (
        render_text,
        discover_fonts,
        find_font,
        _load_font,
        FALLBACK_FONT_NAMES,
        _font_search_dirs,
    )


@unittest.skipUnless(HAS_PIL, "Pillow is not installed")
class TestRenderTextBasic(unittest.TestCase):
    """Basic smoke tests for render_text."""

    def test_returns_1bit_image(self):
        img = render_text("Hello")
        self.assertEqual(img.mode, "1")

    def test_default_width(self):
        img = render_text("Hello")
        self.assertEqual(img.width, 384)

    def test_custom_width(self):
        img = render_text("Hello", width=200)
        self.assertEqual(img.width, 200)

    def test_multiline(self):
        single = render_text("Hello")
        multi = render_text("Hello\nWorld")
        # Multi-line should be taller
        self.assertGreater(multi.height, single.height)

    def test_empty_string(self):
        img = render_text("")
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.mode, "1")

    def test_height_positive(self):
        img = render_text("Test")
        self.assertGreater(img.height, 0)


@unittest.skipUnless(HAS_PIL, "Pillow is not installed")
class TestRenderTextStyles(unittest.TestCase):
    """Test style options for render_text."""

    def test_bold_renders(self):
        img = render_text("Bold", bold=True)
        self.assertEqual(img.mode, "1")

    def test_italic_renders(self):
        img = render_text("Italic", italic=True)
        self.assertEqual(img.mode, "1")

    def test_underline_renders(self):
        img = render_text("Underline", underline=True)
        self.assertEqual(img.mode, "1")

    def test_bold_italic_underline(self):
        img = render_text("All styles", bold=True, italic=True, underline=True)
        self.assertEqual(img.mode, "1")


@unittest.skipUnless(HAS_PIL, "Pillow is not installed")
class TestRenderTextBox(unittest.TestCase):
    """Test border and box-fill options."""

    def test_border(self):
        img = render_text("Bordered", border=True)
        self.assertEqual(img.mode, "1")

    def test_border_thickness(self):
        img = render_text("Thick border", border=True, border_thickness=5)
        self.assertEqual(img.mode, "1")

    def test_box_fill(self):
        img = render_text("Filled box", box_fill=True)
        self.assertEqual(img.mode, "1")

    def test_invert(self):
        img = render_text("Inverted", invert=True)
        self.assertEqual(img.mode, "1")

    def test_white_on_black_with_border(self):
        """White text on black background with a border."""
        img = render_text(
            "White on Black",
            invert=True,
            box_fill=True,
            border=True,
            border_thickness=3,
        )
        self.assertEqual(img.mode, "1")

    def test_box_fill_changes_output(self):
        plain = render_text("Test")
        filled = render_text("Test", box_fill=True)
        # The images should differ
        self.assertNotEqual(list(plain.tobytes()), list(filled.tobytes()))


@unittest.skipUnless(HAS_PIL, "Pillow is not installed")
class TestRenderTextFontSize(unittest.TestCase):
    """Test that font_size affects output dimensions."""

    def test_larger_font_taller_image(self):
        small = render_text("Hello", font_size=12)
        large = render_text("Hello", font_size=30)
        self.assertGreater(large.height, small.height)


@unittest.skipUnless(HAS_PIL, "Pillow is not installed")
class TestDiscoverFonts(unittest.TestCase):
    """Test font discovery."""

    def test_returns_dict(self):
        fonts = discover_fonts()
        self.assertIsInstance(fonts, dict)

    def test_font_paths_are_strings(self):
        fonts = discover_fonts()
        for stem, path in fonts.items():
            self.assertIsInstance(stem, str)
            self.assertIsInstance(path, str)


@unittest.skipUnless(HAS_PIL, "Pillow is not installed")
class TestFindFont(unittest.TestCase):
    """Test find_font fallback logic."""

    def test_returns_string_or_none(self):
        result = find_font()
        self.assertTrue(result is None or isinstance(result, str))

    def test_nonexistent_font_falls_back(self):
        result = find_font("ThisFontDefinitelyDoesNotExist12345")
        # Should fall back to something or None, not raise
        self.assertTrue(result is None or isinstance(result, str))

    @patch("py_star_tsp.text.discover_fonts", return_value={})
    def test_no_fonts_returns_none(self, _mock):
        result = find_font()
        self.assertIsNone(result)


@unittest.skipUnless(HAS_PIL, "Pillow is not installed")
class TestLoadFont(unittest.TestCase):
    """Test _load_font fallback."""

    def test_none_path_loads_default(self):
        font = _load_font(None, 20)
        self.assertIsNotNone(font)

    def test_invalid_path_loads_default(self):
        font = _load_font("/nonexistent/path/font.ttf", 20)
        self.assertIsNotNone(font)


@unittest.skipUnless(HAS_PIL, "Pillow is not installed")
class TestFontSearchDirs(unittest.TestCase):
    """Test that _font_search_dirs returns a list."""

    def test_returns_list(self):
        dirs = _font_search_dirs()
        self.assertIsInstance(dirs, list)

    @patch.dict("os.environ", {"FONTPATH": "/tmp/custom_fonts"})
    def test_fontpath_env(self):
        dirs = _font_search_dirs()
        self.assertIn("/tmp/custom_fonts", dirs)


@unittest.skipUnless(HAS_PIL, "Pillow is not installed")
class TestFallbackFontNames(unittest.TestCase):
    def test_fallback_list_nonempty(self):
        self.assertGreater(len(FALLBACK_FONT_NAMES), 0)

    def test_fallback_list_contains_dejavu(self):
        self.assertTrue(
            any("DejaVu" in name for name in FALLBACK_FONT_NAMES)
        )


if __name__ == "__main__":
    unittest.main()
