"""Unit tests for py_star_tsp.status.AsbStatus."""

import unittest

from py_star_tsp.status import AsbStatus


class TestAsbStatusInit(unittest.TestCase):
    def test_requires_four_bytes(self):
        with self.assertRaises(ValueError):
            AsbStatus(b"\x00\x00\x00")

    def test_requires_exactly_four_bytes(self):
        with self.assertRaises(ValueError):
            AsbStatus(b"\x00\x00\x00\x00\x00")

    def test_valid_four_bytes(self):
        status = AsbStatus(b"\x00\x00\x00\x00")
        self.assertIsInstance(status, AsbStatus)


class TestDrawerOpen(unittest.TestCase):
    def test_drawer_closed(self):
        status = AsbStatus(b"\x00\x00\x00\x00")
        self.assertFalse(status.drawer_open)

    def test_drawer_open(self):
        # byte 0, bit 2 (0x04)
        status = AsbStatus(bytes([0x04, 0x00, 0x00, 0x00]))
        self.assertTrue(status.drawer_open)


class TestOffline(unittest.TestCase):
    def test_online(self):
        status = AsbStatus(b"\x00\x00\x00\x00")
        self.assertFalse(status.offline)

    def test_offline(self):
        # byte 0, bit 3 (0x08)
        status = AsbStatus(bytes([0x08, 0x00, 0x00, 0x00]))
        self.assertTrue(status.offline)


class TestCoverOpen(unittest.TestCase):
    def test_cover_closed(self):
        status = AsbStatus(b"\x00\x00\x00\x00")
        self.assertFalse(status.cover_open)

    def test_cover_open(self):
        # byte 1, bit 2 (0x04)
        status = AsbStatus(bytes([0x00, 0x04, 0x00, 0x00]))
        self.assertTrue(status.cover_open)


class TestPaperFeed(unittest.TestCase):
    def test_not_feeding(self):
        status = AsbStatus(b"\x00\x00\x00\x00")
        self.assertFalse(status.paper_feed)

    def test_feeding(self):
        # byte 1, bit 3 (0x08)
        status = AsbStatus(bytes([0x00, 0x08, 0x00, 0x00]))
        self.assertTrue(status.paper_feed)


class TestPaperNearEnd(unittest.TestCase):
    def test_paper_ok(self):
        status = AsbStatus(b"\x00\x00\x00\x00")
        self.assertFalse(status.paper_near_end)

    def test_paper_near_end(self):
        # byte 1, bit 5 (0x20)
        status = AsbStatus(bytes([0x00, 0x20, 0x00, 0x00]))
        self.assertTrue(status.paper_near_end)


class TestPaperEnd(unittest.TestCase):
    def test_paper_present(self):
        status = AsbStatus(b"\x00\x00\x00\x00")
        self.assertFalse(status.paper_end)

    def test_paper_end(self):
        # byte 1, bit 6 (0x40)
        status = AsbStatus(bytes([0x00, 0x40, 0x00, 0x00]))
        self.assertTrue(status.paper_end)


class TestErrors(unittest.TestCase):
    def test_no_error(self):
        status = AsbStatus(b"\x00\x00\x00\x00")
        self.assertFalse(status.error)
        self.assertFalse(status.auto_cutter_error)
        self.assertFalse(status.unrecoverable_error)
        self.assertFalse(status.auto_recoverable_error)

    def test_error_flag(self):
        # byte 2, bit 6 (0x40)
        status = AsbStatus(bytes([0x00, 0x00, 0x40, 0x00]))
        self.assertTrue(status.error)

    def test_auto_cutter_error(self):
        # byte 2, bit 3 (0x08)
        status = AsbStatus(bytes([0x00, 0x00, 0x08, 0x00]))
        self.assertTrue(status.auto_cutter_error)

    def test_unrecoverable_error(self):
        # byte 2, bit 5 (0x20)
        status = AsbStatus(bytes([0x00, 0x00, 0x20, 0x00]))
        self.assertTrue(status.unrecoverable_error)

    def test_auto_recoverable_error(self):
        # byte 2, bit 2 (0x04)
        status = AsbStatus(bytes([0x00, 0x00, 0x04, 0x00]))
        self.assertTrue(status.auto_recoverable_error)


class TestRaw(unittest.TestCase):
    def test_raw_property(self):
        data = bytes([0x01, 0x02, 0x03, 0x04])
        status = AsbStatus(data)
        self.assertEqual(status.raw, data)


class TestRepr(unittest.TestCase):
    def test_repr_ok(self):
        status = AsbStatus(b"\x00\x00\x00\x00")
        r = repr(status)
        self.assertIn("AsbStatus", r)
        self.assertIn("ok", r)

    def test_repr_with_flags(self):
        # offline flag set
        status = AsbStatus(bytes([0x08, 0x00, 0x00, 0x00]))
        r = repr(status)
        self.assertIn("offline", r)

    def test_repr_multiple_flags(self):
        # drawer open + offline
        status = AsbStatus(bytes([0x0C, 0x00, 0x00, 0x00]))
        r = repr(status)
        self.assertIn("drawer_open", r)
        self.assertIn("offline", r)


if __name__ == "__main__":
    unittest.main()
