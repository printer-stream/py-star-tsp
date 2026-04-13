"""Unit tests for py_star_tsp.printer.StarTSP (mocked USB, no hardware)."""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from py_star_tsp.exceptions import (
    PrinterCommunicationError,
    PrinterNotFoundError,
)
from py_star_tsp.status import AsbStatus


def _make_mock_device():
    """Return a minimal mock of a usb.core.Device."""
    device = MagicMock()
    device.is_kernel_driver_active.return_value = False

    # Build a mock endpoint pair
    ep_out = MagicMock()
    ep_out.bEndpointAddress = 0x01  # OUT

    ep_in = MagicMock()
    ep_in.bEndpointAddress = 0x81  # IN (bit 7 set)

    # cfg[(0, 0)] → interface → find_descriptor returns endpoints
    intf = MagicMock()
    cfg = MagicMock()
    cfg.__getitem__ = MagicMock(return_value=intf)
    device.get_active_configuration.return_value = cfg

    return device, ep_out, ep_in


class TestStarTSPOpen(unittest.TestCase):
    @patch("py_star_tsp.printer.usb.core.find")
    @patch("py_star_tsp.printer.usb.util.find_descriptor")
    @patch("py_star_tsp.printer.usb.util.ENDPOINT_OUT", 0x00)
    @patch("py_star_tsp.printer.usb.util.ENDPOINT_IN", 0x80)
    def test_open_success(self, mock_find_desc, mock_usb_find):
        from py_star_tsp.printer import StarTSP

        device, ep_out, ep_in = _make_mock_device()
        mock_usb_find.return_value = device
        mock_find_desc.side_effect = [ep_out, ep_in]

        printer = StarTSP()
        printer.open()

        mock_usb_find.assert_called_once_with(idVendor=0x0519)
        self.assertIsNotNone(printer._device)

    @patch("py_star_tsp.printer.usb.core.find", return_value=None)
    def test_open_device_not_found(self, _):
        from py_star_tsp.printer import StarTSP

        printer = StarTSP()
        with self.assertRaises(PrinterNotFoundError):
            printer.open()

    @patch("py_star_tsp.printer.usb.core.find")
    @patch("py_star_tsp.printer.usb.util.find_descriptor")
    @patch("py_star_tsp.printer.usb.util.ENDPOINT_OUT", 0x00)
    @patch("py_star_tsp.printer.usb.util.ENDPOINT_IN", 0x80)
    def test_context_manager(self, mock_find_desc, mock_usb_find):
        from py_star_tsp.printer import StarTSP

        device, ep_out, ep_in = _make_mock_device()
        mock_usb_find.return_value = device
        mock_find_desc.side_effect = [ep_out, ep_in]

        with patch("py_star_tsp.printer.usb.util.dispose_resources") as mock_dispose:
            with StarTSP() as printer:
                self.assertIsNotNone(printer._device)
            mock_dispose.assert_called_once()


class TestStarTSPSend(unittest.TestCase):
    def _get_open_printer(self):
        """Helper: return a StarTSP with _ep_out mocked directly."""
        from py_star_tsp.printer import StarTSP

        printer = StarTSP()
        printer._ep_out = MagicMock()
        printer._ep_in = MagicMock()
        printer._device = MagicMock()
        return printer

    def test_send_calls_write(self):
        printer = self._get_open_printer()
        printer.send(b"\x1b*rA")
        printer._ep_out.write.assert_called_once_with(b"\x1b*rA", timeout=5000)

    def test_send_raises_on_write_error(self):
        printer = self._get_open_printer()
        printer._ep_out.write.side_effect = Exception("USB error")
        with self.assertRaises(PrinterCommunicationError):
            printer.send(b"\x00")

    def test_send_without_open_raises(self):
        from py_star_tsp.printer import StarTSP

        printer = StarTSP()
        with self.assertRaises(PrinterCommunicationError):
            printer.send(b"\x00")


class TestStarTSPRead(unittest.TestCase):
    def _get_open_printer(self):
        from py_star_tsp.printer import StarTSP

        printer = StarTSP()
        printer._ep_out = MagicMock()
        printer._ep_in = MagicMock()
        printer._device = MagicMock()
        return printer

    def test_read_returns_bytes(self):
        printer = self._get_open_printer()
        printer._ep_in.read.return_value = bytearray(b"\x00\x00\x00\x00")
        result = printer.read(4)
        self.assertEqual(result, b"\x00\x00\x00\x00")

    def test_read_raises_on_error(self):
        printer = self._get_open_printer()
        printer._ep_in.read.side_effect = Exception("timeout")
        with self.assertRaises(PrinterCommunicationError):
            printer.read(4)

    def test_read_without_open_raises(self):
        from py_star_tsp.printer import StarTSP

        printer = StarTSP()
        with self.assertRaises(PrinterCommunicationError):
            printer.read(4)


class TestStarTSPHighLevel(unittest.TestCase):
    def _get_open_printer(self):
        from py_star_tsp.printer import StarTSP

        printer = StarTSP()
        printer._ep_out = MagicMock()
        printer._ep_in = MagicMock()
        printer._device = MagicMock()
        return printer

    def test_initialize_raster(self):
        printer = self._get_open_printer()
        printer.initialize_raster()
        printer._ep_out.write.assert_called_once()
        written = printer._ep_out.write.call_args[0][0]
        self.assertIn(b"*rR", written)

    def test_enter_raster_mode(self):
        printer = self._get_open_printer()
        printer.enter_raster_mode()
        written = printer._ep_out.write.call_args[0][0]
        self.assertIn(b"*rA", written)

    def test_quit_raster_mode(self):
        printer = self._get_open_printer()
        printer.quit_raster_mode()
        written = printer._ep_out.write.call_args[0][0]
        self.assertIn(b"*rB", written)

    def test_drive_drawer(self):
        printer = self._get_open_printer()
        printer.drive_drawer()
        written = printer._ep_out.write.call_args[0][0]
        self.assertEqual(written, b"\x07")

    def test_reset(self):
        printer = self._get_open_printer()
        printer.reset()
        written = printer._ep_out.write.call_args[0][0]
        self.assertIn(b"?", written)

    def test_set_density(self):
        printer = self._get_open_printer()
        printer.set_density(3)
        written = printer._ep_out.write.call_args[0][0]
        self.assertIn(b"d", written)
        self.assertIn(bytes([3]), written)

    def test_set_speed(self):
        printer = self._get_open_printer()
        printer.set_speed(2)
        written = printer._ep_out.write.call_args[0][0]
        self.assertIn(b"r", written)

    def test_set_print_area(self):
        printer = self._get_open_printer()
        printer.set_print_area(1)
        written = printer._ep_out.write.call_args[0][0]
        self.assertIn(b"A", written)

    def test_get_status(self):
        printer = self._get_open_printer()
        printer._ep_in.read.return_value = bytearray(b"\x00\x00\x00\x00")
        status = printer.get_status()
        self.assertIsInstance(status, AsbStatus)
        self.assertFalse(status.offline)

    def test_ring_buzzer(self):
        printer = self._get_open_printer()
        printer.ring_buzzer(1, 50, 100)
        written = printer._ep_out.write.call_args[0][0]
        self.assertIn(bytes([1, 50, 100]), written)


class TestPrintRasterImage(unittest.TestCase):
    def test_print_raster_image(self):
        """print_raster_image should send init, enter, lines, ff, quit."""
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")

        from py_star_tsp.printer import StarTSP
        from py_star_tsp.raster import RasterImage

        printer = StarTSP()
        printer._ep_out = MagicMock()
        printer._ep_in = MagicMock()
        printer._device = MagicMock()

        img = Image.new("L", (8, 2), color=0)  # 8×2 all-black
        ri = RasterImage(img)
        printer.print_raster_image(ri)

        calls = printer._ep_out.write.call_args_list
        # At minimum: init, enter, 2 data lines, ff, quit = 6 calls
        self.assertGreaterEqual(len(calls), 6)

        # First call should be raster_initialize
        first = calls[0][0][0]
        self.assertIn(b"*rR", first)

        # Second call: enter raster mode
        second = calls[1][0][0]
        self.assertIn(b"*rA", second)

        # Last call: quit raster mode
        last = calls[-1][0][0]
        self.assertIn(b"*rB", last)


class TestPrintText(unittest.TestCase):
    """Test StarTSP.print_text renders text and sends raster data."""

    def test_print_text_sends_data(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")

        from py_star_tsp.printer import StarTSP

        printer = StarTSP()
        printer._ep_out = MagicMock()
        printer._ep_in = MagicMock()
        printer._device = MagicMock()

        printer.print_text("Hello")

        calls = printer._ep_out.write.call_args_list
        # At minimum: init, enter, data lines, ff, quit
        self.assertGreaterEqual(len(calls), 5)

        # First call should be raster_initialize
        first = calls[0][0][0]
        self.assertIn(b"*rR", first)

        # Last call: quit raster mode
        last = calls[-1][0][0]
        self.assertIn(b"*rB", last)

    def test_print_text_with_styles(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")

        from py_star_tsp.printer import StarTSP

        printer = StarTSP()
        printer._ep_out = MagicMock()
        printer._ep_in = MagicMock()
        printer._device = MagicMock()

        # Should not raise
        printer.print_text(
            "Styled",
            bold=True,
            italic=True,
            underline=True,
            border=True,
            box_fill=True,
            invert=True,
        )

        calls = printer._ep_out.write.call_args_list
        self.assertGreaterEqual(len(calls), 5)


if __name__ == "__main__":
    unittest.main()
