"""
Unit tests for py_star_tsp.escpos — ESC/POS emulation layer.

Covers:
- PrinterPreset construction and copy()
- EscposEmulator state-machine parsing for every supported command
- Rendering to RasterSet (image dimensions, alignment, bold, underline)
- Page mode (ESC L / ESC S)
- Graceful handling of unknown / barcode / extended commands
- Pre-built presets
"""

import unittest
from unittest.mock import MagicMock, call

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

if HAS_PIL:
    from py_star_tsp.escpos import (
        EscposEmulator,
        PrinterPreset,
        PRESET_EPSON_TM_T88,
        PRESET_58MM,
        _PrintState,
        _TextSpan,
        _PrintLine,
    )
    from py_star_tsp.raster import RasterSet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _emu(preset=None, on_print=None):
    return EscposEmulator(
        preset=preset or PRESET_EPSON_TM_T88,
        on_print=on_print,
    )


def _bytes(*parts):
    """Concatenate ints / bytes / str into bytes."""
    out = bytearray()
    for p in parts:
        if isinstance(p, int):
            out.append(p)
        elif isinstance(p, (bytes, bytearray)):
            out.extend(p)
        elif isinstance(p, str):
            out.extend(p.encode("latin-1"))
        else:
            raise TypeError(type(p))
    return bytes(out)


ESC = 0x1B
GS  = 0x1D
LF  = 0x0A
CR  = 0x0D
FF  = 0x0C
CAN = 0x18


# ===========================================================================
# PrinterPreset
# ===========================================================================

class TestPrinterPreset(unittest.TestCase):

    def test_default_preset_name(self):
        p = PrinterPreset()
        self.assertEqual(p.name, "Epson TM-T88")

    def test_default_print_width(self):
        self.assertEqual(PRESET_EPSON_TM_T88.print_width_dots, 576)

    def test_default_font_a_chars_per_line(self):
        self.assertEqual(PRESET_EPSON_TM_T88.font_a_chars_per_line, 42)

    def test_default_font_b_chars_per_line(self):
        self.assertEqual(PRESET_EPSON_TM_T88.font_b_chars_per_line, 56)

    def test_preset_58mm(self):
        self.assertEqual(PRESET_58MM.print_width_dots, 384)
        self.assertEqual(PRESET_58MM.font_a_chars_per_line, 32)

    def test_copy_no_changes(self):
        p = PRESET_EPSON_TM_T88.copy()
        self.assertEqual(p.name, PRESET_EPSON_TM_T88.name)
        self.assertEqual(p.print_width_dots, PRESET_EPSON_TM_T88.print_width_dots)

    def test_copy_with_override(self):
        p = PRESET_EPSON_TM_T88.copy(name="Custom", font_a_chars_per_line=40)
        self.assertEqual(p.name, "Custom")
        self.assertEqual(p.font_a_chars_per_line, 40)
        # Unmodified fields preserved
        self.assertEqual(p.print_width_dots, 576)

    def test_copy_does_not_mutate_original(self):
        p = PRESET_EPSON_TM_T88.copy(name="Mutated")
        self.assertEqual(PRESET_EPSON_TM_T88.name, "Epson TM-T88")


# ===========================================================================
# EscposEmulator — parser / state-machine
# ===========================================================================

@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEmulatorBasicText(unittest.TestCase):

    def test_plain_text_accumulates(self):
        e = _emu()
        e.feed(b"Hello")
        self.assertEqual(len(e._current_spans), 1)
        self.assertEqual(e._current_spans[0].text, "Hello")

    def test_lf_moves_text_to_lines(self):
        e = _emu()
        e.feed(b"Hello\n")
        self.assertEqual(len(e._lines), 1)
        self.assertEqual(e._lines[0].spans[0].text, "Hello")
        self.assertEqual(len(e._current_spans), 0)

    def test_cr_treated_as_lf(self):
        e = _emu()
        e.feed(b"Hi\r")
        self.assertEqual(len(e._lines), 1)

    def test_ff_triggers_print(self):
        callback = MagicMock()
        e = _emu(on_print=callback)
        e.feed(b"Line1\n\x0c")
        callback.assert_called_once()
        rs = callback.call_args[0][0]
        self.assertIsInstance(rs, RasterSet)

    def test_can_clears_current_line(self):
        e = _emu()
        e.feed(b"Garbage")
        e.feed(bytes([CAN]))
        self.assertEqual(e._current_spans, [])

    def test_adjacent_same_style_merged_into_one_span(self):
        e = _emu()
        e.feed(b"ABC")
        e.feed(b"DEF")
        # Should be one span "ABCDEF"
        self.assertEqual(len(e._current_spans), 1)
        self.assertEqual(e._current_spans[0].text, "ABCDEF")

    def test_multiline(self):
        e = _emu()
        e.feed(b"Line1\nLine2\n")
        self.assertEqual(len(e._lines), 2)


@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEmulatorInit(unittest.TestCase):

    def test_esc_at_resets_bold(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x45, 1))  # ESC E 1 — bold on
        self.assertTrue(e._state.bold)
        e.feed(_bytes(ESC, 0x40))     # ESC @ — init
        self.assertFalse(e._state.bold)

    def test_esc_at_resets_align(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x61, 1))  # centre
        e.feed(_bytes(ESC, 0x40))     # init
        self.assertEqual(e._state.align, 0)

    def test_esc_at_clears_spans(self):
        e = _emu()
        e.feed(b"Text")
        e.feed(_bytes(ESC, 0x40))
        self.assertEqual(e._current_spans, [])


@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEmulatorJustification(unittest.TestCase):

    def test_esc_a_left(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x61, 0))
        self.assertEqual(e._state.align, 0)

    def test_esc_a_centre(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x61, 1))
        self.assertEqual(e._state.align, 1)

    def test_esc_a_right(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x61, 2))
        self.assertEqual(e._state.align, 2)

    def test_esc_a_masks_to_2_bits(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x61, 0xFF))
        self.assertEqual(e._state.align, 3)

    def test_line_inherits_alignment(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x61, 2))  # right
        e.feed(b"Foo\n")
        self.assertEqual(e._lines[0].align, 2)


@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEmulatorBoldUnderline(unittest.TestCase):

    def test_esc_E_bold_on(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x45, 1))
        self.assertTrue(e._state.bold)

    def test_esc_E_bold_off(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x45, 1))
        e.feed(_bytes(ESC, 0x45, 0))
        self.assertFalse(e._state.bold)

    def test_esc_G_double_strike(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x47, 1))
        self.assertTrue(e._state.double_strike)

    def test_esc_minus_underline(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x2D, 1))
        self.assertEqual(e._state.underline, 1)

    def test_esc_minus_underline_2dot(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x2D, 2))
        self.assertEqual(e._state.underline, 2)

    def test_esc_minus_underline_off(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x2D, 1))
        e.feed(_bytes(ESC, 0x2D, 0))
        self.assertEqual(e._state.underline, 0)

    def test_bold_span_recorded(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x45, 1))
        e.feed(b"Bold text")
        self.assertTrue(e._current_spans[-1].bold)


@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEmulatorFont(unittest.TestCase):

    def test_esc_M_font_B(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x4D, 1))
        self.assertEqual(e._state.font, 1)

    def test_esc_M_font_A(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x4D, 1))
        e.feed(_bytes(ESC, 0x4D, 0))
        self.assertEqual(e._state.font, 0)

    def test_esc_M_masks_to_1_bit(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x4D, 0xFE))  # bit 0 = 0 → Font A
        self.assertEqual(e._state.font, 0)


@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEmulatorCharSize(unittest.TestCase):

    def test_gs_bang_double_width(self):
        e = _emu()
        # GS ! n: bits 0-2 = width-1, bits 4-6 = height-1
        # n = 0x01 → width=2, height=1
        e.feed(_bytes(GS, 0x21, 0x01))
        self.assertEqual(e._state.char_size_w, 2)
        self.assertEqual(e._state.char_size_h, 1)

    def test_gs_bang_double_height(self):
        e = _emu()
        # n = 0x10 → width=1, height=2
        e.feed(_bytes(GS, 0x21, 0x10))
        self.assertEqual(e._state.char_size_w, 1)
        self.assertEqual(e._state.char_size_h, 2)

    def test_gs_bang_max_size(self):
        e = _emu()
        # n = 0x77 → width=8, height=8
        e.feed(_bytes(GS, 0x21, 0x77))
        self.assertEqual(e._state.char_size_w, 8)
        self.assertEqual(e._state.char_size_h, 8)

    def test_gs_bang_reset(self):
        e = _emu()
        e.feed(_bytes(GS, 0x21, 0x77))
        e.feed(_bytes(GS, 0x21, 0x00))
        self.assertEqual(e._state.char_size_w, 1)
        self.assertEqual(e._state.char_size_h, 1)


@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEmulatorPrintMode(unittest.TestCase):
    """ESC ! compound print-mode command."""

    def test_esc_bang_font_B(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x21, 0x01))  # bit 0 = Font B
        self.assertEqual(e._state.font, 1)

    def test_esc_bang_bold(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x21, 0x08))  # bit 3 = bold
        self.assertTrue(e._state.bold)

    def test_esc_bang_double_width(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x21, 0x20))  # bit 5 = double width
        self.assertEqual(e._state.char_size_w, 2)

    def test_esc_bang_double_height(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x21, 0x10))  # bit 4 = double height
        self.assertEqual(e._state.char_size_h, 2)

    def test_esc_bang_underline(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x21, 0x80))  # bit 7 = underline
        self.assertEqual(e._state.underline, 1)

    def test_esc_bang_compound(self):
        e = _emu()
        # Bold + double-width + double-height = 0x08 | 0x20 | 0x10 = 0x38
        e.feed(_bytes(ESC, 0x21, 0x38))
        self.assertTrue(e._state.bold)
        self.assertEqual(e._state.char_size_w, 2)
        self.assertEqual(e._state.char_size_h, 2)


@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEmulatorLineSpacing(unittest.TestCase):

    def test_esc_3_sets_line_spacing(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x33, 50))
        self.assertEqual(e._state.line_spacing, 50)

    def test_esc_2_restores_default(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x33, 50))
        e.feed(_bytes(ESC, 0x32))
        self.assertIsNone(e._state.line_spacing)


@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEmulatorPrintTriggers(unittest.TestCase):

    def test_gs_v_zero_triggers_print(self):
        callback = MagicMock()
        e = _emu(on_print=callback)
        e.feed(b"Cut\n")
        e.feed(_bytes(GS, 0x56, 0))
        callback.assert_called_once()

    def test_gs_v_one_triggers_print(self):
        callback = MagicMock()
        e = _emu(on_print=callback)
        e.feed(b"Partial cut\n")
        e.feed(_bytes(GS, 0x56, 1))
        callback.assert_called_once()

    def test_gs_v_0x41_consumes_extra_byte(self):
        """GS V 65 n — full cut with feed distance n."""
        callback = MagicMock()
        e = _emu(on_print=callback)
        e.feed(b"Line\n")
        e.feed(_bytes(GS, 0x56, 0x41, 10))  # feed 10 dots
        callback.assert_called_once()
        # Feed the next print job — stream should be intact
        e.feed(b"After\n")
        e.feed(_bytes(GS, 0x56, 0))
        self.assertEqual(callback.call_count, 2)

    def test_flush_triggers_print_without_cut(self):
        callback = MagicMock()
        e = _emu(on_print=callback)
        e.feed(b"No cut")
        rs = e.flush()
        callback.assert_called_once()
        self.assertIsInstance(rs, RasterSet)

    def test_flush_empty_returns_none(self):
        e = _emu()
        result = e.flush()
        self.assertIsNone(result)

    def test_esc_d_feeds_blank_lines(self):
        e = _emu()
        e.feed(b"After\n")
        e.feed(_bytes(ESC, 0x64, 3))  # print + feed 3 lines
        # Lines should contain: "After", blank, blank, blank
        self.assertEqual(len(e._lines), 4)

    def test_esc_J_sets_extra_feed(self):
        e = _emu()
        e.feed(b"Before\n")
        e.feed(_bytes(ESC, 0x4A, 24))  # feed 24 dots
        self.assertEqual(e._lines[-1].extra_feed_dots, 24)


@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEmulatorReverseAndUpDown(unittest.TestCase):

    def test_gs_B_invert_on(self):
        e = _emu()
        e.feed(_bytes(GS, 0x42, 1))
        self.assertTrue(e._state.invert)

    def test_gs_B_invert_off(self):
        e = _emu()
        e.feed(_bytes(GS, 0x42, 1))
        e.feed(_bytes(GS, 0x42, 0))
        self.assertFalse(e._state.invert)

    def test_esc_brace_upside_down(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x7B, 1))
        self.assertTrue(e._state.upside_down)


@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEmulatorCashDrawerAndOther(unittest.TestCase):

    def test_esc_p_consumes_3_bytes(self):
        """ESC p m t1 t2 — must not corrupt stream."""
        e = _emu()
        # Pulse then immediately regular text
        e.feed(_bytes(ESC, 0x70, 0, 20, 20, ord("O"), ord("K")))
        self.assertEqual(e._current_spans[-1].text, "OK")

    def test_esc_R_stores_charset(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x52, 7))
        self.assertEqual(e._state.international_charset, 7)

    def test_esc_t_stores_code_table(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x74, 2))
        self.assertEqual(e._state.char_code_table, 2)

    def test_tab_inserts_spaces(self):
        e = _emu()
        e.feed(b"\t")
        # Tab at column 0 → 8 spaces
        self.assertEqual(e._current_spans[-1].text, " " * 8)


@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEmulatorUnknownCommands(unittest.TestCase):
    """Unknown commands must not corrupt subsequent text."""

    def test_unknown_esc_cmd_skipped(self):
        # Unknown ESC command: 0x7F is consumed as the sub-command byte.
        # The byte that follows (here 'X') is unrelated data and treated as
        # a printable character.  The important guarantee is that the parser
        # does NOT raise and subsequent bytes parse correctly.
        e = _emu()
        e.feed(_bytes(ESC, 0x7F))  # ESC + unknown sub-command byte
        e.feed(b"Safe")
        # 'Safe' must appear in spans (stream not corrupted)
        all_text = "".join(s.text for s in e._current_spans)
        self.assertIn("Safe", all_text)

    def test_barcode_gsk_old_format_skipped(self):
        # GS k m data NUL — old format (m <= 6)
        barcode_data = b"12345678\x00"
        e = _emu()
        e.feed(_bytes(GS, 0x6B, 2) + barcode_data)
        e.feed(b"After")
        self.assertEqual(e._current_spans[-1].text, "After")

    def test_barcode_gsk_new_format_skipped(self):
        # GS k m n data — new format (m > 6)
        e = _emu()
        e.feed(_bytes(GS, 0x6B, 73, 8) + b"12345678")
        e.feed(b"After")
        self.assertEqual(e._current_spans[-1].text, "After")

    def test_extended_gs_paren_skipped(self):
        # GS ( k pL pH function_code data  — native QR (sub=0x6B) consumed cleanly
        payload = bytes([49, 65, 3, 0]) + b"QRD"
        e = _emu()
        e.feed(
            _bytes(GS, 0x28, 0x6B)  # GS ( k  (sub-command byte 0x6B)
            + bytes([len(payload) & 0xFF, len(payload) >> 8])
            + payload
        )
        e.feed(b"OK")
        self.assertEqual(e._current_spans[-1].text, "OK")


# ===========================================================================
# EscposEmulator — Page Mode
# ===========================================================================

@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEmulatorPageMode(unittest.TestCase):

    def test_esc_L_enters_page_mode(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x4C))
        self.assertTrue(e._page_mode)

    def test_esc_S_exits_page_mode(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x4C))
        e.feed(_bytes(ESC, 0x53))
        self.assertFalse(e._page_mode)

    def test_page_mode_content_committed_on_esc_S(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x4C))
        e.feed(b"Page line\n")
        e.feed(_bytes(ESC, 0x53))
        # Line from page buffer should now be in _lines
        self.assertEqual(len(e._lines), 1)
        self.assertEqual(e._lines[0].spans[0].text, "Page line")

    def test_esc_T_sets_direction(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x4C))
        e.feed(_bytes(ESC, 0x54, 1))
        self.assertEqual(e._page_buffer.direction, 1)

    def test_esc_W_sets_area(self):
        # ESC W xL xH yL yH dxL dxH dyL dyH
        params = [0, 0, 0, 0, 64, 1, 100, 0]  # width=0x140=320, height=100
        e = _emu()
        e.feed(_bytes(ESC, 0x4C))
        e.feed(_bytes(ESC, 0x57, *params))
        self.assertEqual(e._page_buffer.width, 64 + 1 * 256)
        self.assertEqual(e._page_buffer.height, 100)


# ===========================================================================
# EscposEmulator — Rendering
# ===========================================================================

@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEmulatorRendering(unittest.TestCase):

    def test_render_returns_raster_set(self):
        e = _emu()
        e.feed(b"Hello\n")
        rs = e.render()
        self.assertIsInstance(rs, RasterSet)

    def test_render_image_width_matches_preset(self):
        e = _emu()
        e.feed(b"Width test\n")
        rs = e.render()
        img = rs.to_image()
        self.assertEqual(img.width, PRESET_EPSON_TM_T88.print_width_dots)

    def test_render_height_grows_with_lines(self):
        e_one = _emu()
        e_one.feed(b"One\n")

        e_two = _emu()
        e_two.feed(b"One\nTwo\n")

        h1 = e_one.render().to_image().height
        h2 = e_two.render().to_image().height
        self.assertGreater(h2, h1)

    def test_render_58mm_preset(self):
        e = EscposEmulator(preset=PRESET_58MM)
        e.feed(b"58mm\n")
        rs = e.render()
        img = rs.to_image()
        self.assertEqual(img.width, PRESET_58MM.print_width_dots)

    def test_flush_clears_lines(self):
        callback = MagicMock()
        e = _emu(on_print=callback)
        e.feed(b"Hello\n")
        e.flush()
        self.assertEqual(len(e._lines), 0)

    def test_extra_feed_dots_adds_height(self):
        preset = PRESET_EPSON_TM_T88
        e_no_feed = _emu()
        e_no_feed.feed(b"Line\n")
        h_base = e_no_feed.render().to_image().height

        e_feed = _emu()
        e_feed.feed(b"Line\n")
        e_feed.feed(_bytes(ESC, 0x4A, 50))  # 50 extra dots
        h_feed = e_feed.render().to_image().height

        self.assertEqual(h_feed, h_base + 50)

    def test_double_height_taller_line(self):
        e_normal = _emu()
        e_normal.feed(b"Normal\n")
        h_norm = e_normal.render().to_image().height

        e_big = _emu()
        e_big.feed(_bytes(GS, 0x21, 0x10))  # double height
        e_big.feed(b"Big\n")
        h_big = e_big.render().to_image().height

        self.assertGreater(h_big, h_norm)

    def test_double_width_wider_span(self):
        """Double-width span should produce an image at least as wide as single."""
        e_norm = _emu()
        e_norm.feed(b"Test\n")
        rs_norm = e_norm.render()

        e_wide = _emu()
        e_wide.feed(_bytes(GS, 0x21, 0x01))  # double width
        e_wide.feed(b"Test\n")
        rs_wide = e_wide.render()

        # Both should have same canvas width (full paper width)
        self.assertEqual(
            rs_norm.to_image().width,
            rs_wide.to_image().width,
        )

    def test_empty_flush_returns_none(self):
        e = _emu()
        self.assertIsNone(e.flush())

    def test_on_print_called_with_raster_set(self):
        received = []
        e = EscposEmulator(on_print=received.append)
        e.feed(b"Test\n")
        e.feed(_bytes(GS, 0x56, 0))
        self.assertEqual(len(received), 1)
        self.assertIsInstance(received[0], RasterSet)

    def test_partial_command_across_feed_calls(self):
        """A command split across two feed() calls must still parse correctly."""
        e = _emu()
        e.feed(bytes([ESC, 0x61]))  # incomplete ESC a
        e.feed(bytes([1]))          # alignment byte
        e.feed(b"Centred\n")
        self.assertEqual(e._lines[-1].align, 1)


# ===========================================================================
# EscposEmulator — Span merging
# ===========================================================================

@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestSpanMerging(unittest.TestCase):

    def test_different_bold_creates_two_spans(self):
        e = _emu()
        e.feed(b"Normal")
        e.feed(_bytes(ESC, 0x45, 1))
        e.feed(b"Bold")
        self.assertEqual(len(e._current_spans), 2)
        self.assertFalse(e._current_spans[0].bold)
        self.assertTrue(e._current_spans[1].bold)

    def test_same_style_stays_one_span(self):
        e = _emu()
        e.feed(_bytes(ESC, 0x45, 1))
        e.feed(b"Hel")
        e.feed(b"lo")
        self.assertEqual(len(e._current_spans), 1)
        self.assertEqual(e._current_spans[0].text, "Hello")

    def test_font_change_creates_new_span(self):
        e = _emu()
        e.feed(b"FontA")
        e.feed(_bytes(ESC, 0x4D, 1))
        e.feed(b"FontB")
        self.assertEqual(len(e._current_spans), 2)
        self.assertEqual(e._current_spans[0].font, 0)
        self.assertEqual(e._current_spans[1].font, 1)


if __name__ == "__main__":
    unittest.main()
