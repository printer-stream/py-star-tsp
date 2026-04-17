"""Unit tests for py_star_tsp.status.AsbStatus.

Standard status format (Star Graphic Mode Rev. 2.31, Appendix-1):
  Byte 0: Header 1 (total byte count)
  Byte 1: Header 2 (status version)
  Bytes 2+: Printer Status 1–N

A typical TSP100 USB response is 9 bytes (Header 1 = 0x23).
"""

import unittest

from py_star_tsp.status import AsbStatus


def _make(ps1=0, ps2=0, ps3=0, ps4=0, ps5=0, ps6=0, ps7=0):
    """Build a 9-byte standard status with given Printer Status bytes."""
    return bytes([0x23, 0x06, ps1, ps2, ps3, ps4, ps5, ps6, ps7])


class TestAsbStatusInit(unittest.TestCase):
    def test_rejects_too_short(self):
        with self.assertRaises(ValueError):
            AsbStatus(b"\x23")

    def test_rejects_truncated(self):
        # Header 1 = 0x23 means 9 bytes, but only 4 given
        with self.assertRaises(ValueError):
            AsbStatus(b"\x23\x06\x00\x00")

    def test_valid_nine_bytes(self):
        status = AsbStatus(_make())
        self.assertIsInstance(status, AsbStatus)

    def test_byte_count(self):
        status = AsbStatus(_make())
        self.assertEqual(status.byte_count, 9)

    def test_version(self):
        status = AsbStatus(_make())
        self.assertEqual(status.version, 3)


class TestCoverOpen(unittest.TestCase):
    def test_cover_closed(self):
        status = AsbStatus(_make(ps1=0x00))
        self.assertFalse(status.cover_open)

    def test_cover_open(self):
        # PS1 bit 5 (0x20)
        status = AsbStatus(_make(ps1=0x20))
        self.assertTrue(status.cover_open)


class TestOffline(unittest.TestCase):
    def test_online(self):
        status = AsbStatus(_make(ps1=0x00))
        self.assertFalse(status.offline)

    def test_offline(self):
        # PS1 bit 3 (0x08)
        status = AsbStatus(_make(ps1=0x08))
        self.assertTrue(status.offline)


class TestHeadTempStop(unittest.TestCase):
    def test_normal(self):
        status = AsbStatus(_make(ps2=0x00))
        self.assertFalse(status.head_temp_stop)

    def test_stopped(self):
        # PS2 bit 6 (0x40)
        status = AsbStatus(_make(ps2=0x40))
        self.assertTrue(status.head_temp_stop)


class TestErrors(unittest.TestCase):
    def test_no_error(self):
        status = AsbStatus(_make())
        self.assertFalse(status.has_error)
        self.assertFalse(status.auto_cutter_error)
        self.assertFalse(status.unrecoverable_error)

    def test_auto_cutter_error(self):
        # PS2 bit 3 (0x08)
        status = AsbStatus(_make(ps2=0x08))
        self.assertTrue(status.auto_cutter_error)
        self.assertTrue(status.has_error)

    def test_unrecoverable_error(self):
        # PS2 bit 5 (0x20)
        status = AsbStatus(_make(ps2=0x20))
        self.assertTrue(status.unrecoverable_error)
        self.assertTrue(status.has_error)


class TestPaperEnd(unittest.TestCase):
    def test_paper_present(self):
        status = AsbStatus(_make(ps4=0x00))
        self.assertFalse(status.paper_end)

    def test_paper_end(self):
        # PS4 bit 3 (0x08)
        status = AsbStatus(_make(ps4=0x08))
        self.assertTrue(status.paper_end)


class TestRaw(unittest.TestCase):
    def test_raw_property(self):
        data = _make()
        status = AsbStatus(data)
        self.assertEqual(status.raw, data)

    def test_printer_status_property(self):
        data = _make(ps1=0x20)
        status = AsbStatus(data)
        self.assertEqual(status.printer_status, data[2:])


class TestRepr(unittest.TestCase):
    def test_repr_ok(self):
        status = AsbStatus(_make())
        r = repr(status)
        self.assertIn("AsbStatus", r)
        self.assertIn("ok", r)

    def test_repr_with_flags(self):
        status = AsbStatus(_make(ps1=0x08))
        r = repr(status)
        self.assertIn("offline", r)

    def test_repr_multiple_flags(self):
        # cover_open + offline
        status = AsbStatus(_make(ps1=0x28))
        r = repr(status)
        self.assertIn("cover_open", r)
        self.assertIn("offline", r)


class TestRealWorldData(unittest.TestCase):
    """Verify the parser against actual printer output."""

    def test_23_06_00_00_is_ok(self):
        """The response ``23 06 00 00 00 00 00 00 00`` should report no flags."""
        data = bytes.fromhex("230600000000000000")
        status = AsbStatus(data)
        self.assertFalse(status.cover_open)
        self.assertFalse(status.offline)
        self.assertFalse(status.has_error)
        self.assertFalse(status.paper_end)


if __name__ == "__main__":
    unittest.main()
