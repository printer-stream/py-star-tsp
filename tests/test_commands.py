"""Unit tests for py_star_tsp.commands."""

import unittest

from py_star_tsp import commands as cmd
from py_star_tsp.exceptions import PrinterCommandError

ESC = b"\x1b"
GS  = b"\x1d"
RS  = b"\x1e"
NUL = b"\x00"
LF  = b"\x0a"
FF  = b"\x0c"
BEL = b"\x07"
FS  = b"\x1c"
SUB = b"\x1a"
EM  = b"\x19"
ACK = b"\x06"
SOH = b"\x01"
ETB = b"\x17"
DC1 = b"\x11"
DC2 = b"\x12"
EOT = b"\x04"


class TestExternalDeviceDrive(unittest.TestCase):
    def test_set_external_drive_pulse(self):
        result = cmd.set_external_drive_pulse(50, 200)
        self.assertEqual(result, ESC + BEL + bytes([50]) + bytes([200]))

    def test_set_external_drive_pulse_boundary(self):
        self.assertEqual(
            cmd.set_external_drive_pulse(0, 0),
            ESC + BEL + b"\x00\x00",
        )
        self.assertEqual(
            cmd.set_external_drive_pulse(255, 255),
            ESC + BEL + b"\xff\xff",
        )

    def test_drive_external_device_1_bel(self):
        self.assertEqual(cmd.drive_external_device_1_bel(), BEL)

    def test_drive_external_device_1_fs(self):
        self.assertEqual(cmd.drive_external_device_1_fs(), FS)

    def test_drive_external_device_2_sub(self):
        self.assertEqual(cmd.drive_external_device_2_sub(), SUB)

    def test_drive_external_device_2_em(self):
        self.assertEqual(cmd.drive_external_device_2_em(), EM)

    def test_ring_buzzer(self):
        result = cmd.ring_buzzer(1, 2, 3)
        self.assertEqual(result, ESC + GS + BEL + b"\x01\x02\x03")

    def test_set_buzzer_pulse(self):
        result = cmd.set_buzzer_pulse(1, 2, 3)
        self.assertEqual(result, ESC + GS + EM + DC1 + b"\x01\x02\x03")

    def test_output_buzzer_pulse(self):
        result = cmd.output_buzzer_pulse(1, 2, 3)
        self.assertEqual(result, ESC + GS + EM + DC2 + b"\x01\x02\x03")


class TestPrintSettings(unittest.TestCase):
    def test_set_print_area(self):
        self.assertEqual(
            cmd.set_print_area(5),
            ESC + RS + b"A" + bytes([5]),
        )

    def test_set_print_density(self):
        self.assertEqual(
            cmd.set_print_density(3),
            ESC + RS + b"d" + bytes([3]),
        )

    def test_set_print_speed(self):
        self.assertEqual(
            cmd.set_print_speed(2),
            ESC + RS + b"r" + bytes([2]),
        )

    def test_set_reduced_printing(self):
        self.assertEqual(
            cmd.set_reduced_printing(1, 2),
            ESC + GS + b"c" + b"\x01\x02",
        )


class TestStatus(unittest.TestCase):
    def test_set_status_transmission(self):
        self.assertEqual(
            cmd.set_status_transmission(1),
            ESC + RS + b"a" + b"\x01",
        )

    def test_get_asb_status(self):
        self.assertEqual(cmd.get_asb_status(), ESC + ACK + SOH)

    def test_update_etb_status(self):
        self.assertEqual(cmd.update_etb_status(), ETB)

    def test_clear_etb_counter(self):
        self.assertEqual(
            cmd.clear_etb_counter(0),
            ESC + RS + b"E" + NUL,
        )

    def test_document_control(self):
        self.assertEqual(
            cmd.document_control(1, 2, 3),
            ESC + GS + b"\x03" + b"\x01\x02\x03",
        )


class TestOther(unittest.TestCase):
    def test_set_memory_switch(self):
        result = cmd.set_memory_switch(1, 2, 3, 4, 5, 6)
        self.assertEqual(
            result,
            ESC + GS + b"#" + b"\x01\x02\x03\x04\x05\x06" + LF + NUL,
        )

    def test_reset_printer(self):
        self.assertEqual(cmd.reset_printer(), ESC + b"?" + LF + NUL)

    def test_set_led_blink(self):
        self.assertEqual(
            cmd.set_led_blink(1, 2, 3),
            ESC + GS + b"L" + DC1 + b"\x01\x02\x03",
        )

    def test_led_blink(self):
        self.assertEqual(
            cmd.led_blink(1, 2, 3),
            ESC + GS + b"L" + DC2 + b"\x01\x02\x03",
        )


class TestRasterCommands(unittest.TestCase):
    def test_raster_initialize(self):
        self.assertEqual(cmd.raster_initialize(), ESC + b"*rR")

    def test_raster_enter(self):
        self.assertEqual(cmd.raster_enter(), ESC + b"*rA")

    def test_raster_quit(self):
        self.assertEqual(cmd.raster_quit(), ESC + b"*rB")

    def test_raster_clear(self):
        self.assertEqual(cmd.raster_clear(), ESC + b"*rC")

    def test_raster_set_eot_mode(self):
        self.assertEqual(
            cmd.raster_set_eot_mode(1),
            ESC + b"*rE" + b"\x01" + NUL,
        )

    def test_raster_set_ff_mode(self):
        self.assertEqual(
            cmd.raster_set_ff_mode(0),
            ESC + b"*rF" + NUL + NUL,
        )

    def test_raster_set_page_length(self):
        self.assertEqual(
            cmd.raster_set_page_length(100),
            ESC + b"*rP" + bytes([100]) + NUL,
        )

    def test_raster_set_print_quality(self):
        self.assertEqual(
            cmd.raster_set_print_quality(2),
            ESC + b"*rQ" + b"\x02" + NUL,
        )

    def test_raster_set_left_margin(self):
        self.assertEqual(
            cmd.raster_set_left_margin(10),
            ESC + b"*rml" + bytes([10]) + NUL,
        )

    def test_raster_set_right_margin(self):
        self.assertEqual(
            cmd.raster_set_right_margin(10),
            ESC + b"*rmr" + bytes([10]) + NUL,
        )

    def test_raster_set_top_margin(self):
        self.assertEqual(
            cmd.raster_set_top_margin(5),
            ESC + b"*rt" + bytes([5]) + NUL,
        )

    def test_raster_set_color(self):
        self.assertEqual(
            cmd.raster_set_color(1),
            ESC + b"*rK" + b"\x01" + NUL,
        )

    def test_raster_transfer_auto_lf(self):
        data = b"\xff\x00"
        result = cmd.raster_transfer_auto_lf(2, 0, data)
        self.assertEqual(result, b"b" + b"\x02\x00" + data)

    def test_raster_transfer(self):
        data = b"\xaa\xbb"
        result = cmd.raster_transfer(2, 0, data)
        self.assertEqual(result, b"k" + b"\x02\x00" + data)

    def test_raster_transfer_invalid_data(self):
        with self.assertRaises(PrinterCommandError):
            cmd.raster_transfer_auto_lf(1, 0, "not bytes")

    def test_raster_vertical_move(self):
        self.assertEqual(
            cmd.raster_vertical_move(20),
            ESC + b"*rY" + bytes([20]) + NUL,
        )

    def test_raster_execute_ff(self):
        self.assertEqual(cmd.raster_execute_ff(), ESC + FF + NUL)

    def test_raster_execute_eot(self):
        self.assertEqual(cmd.raster_execute_eot(), ESC + FF + EOT)

    def test_raster_start_block(self):
        self.assertEqual(cmd.raster_start_block(), ESC + b"*ra")

    def test_raster_end_block(self):
        self.assertEqual(cmd.raster_end_block(), ESC + b"*rb")

    def test_raster_set_em_mode(self):
        self.assertEqual(
            cmd.raster_set_em_mode(1),
            ESC + b"*re" + b"\x01" + NUL,
        )

    def test_raster_execute_em(self):
        self.assertEqual(cmd.raster_execute_em(), ESC + FF + EM)

    def test_raster_execute_lf(self):
        self.assertEqual(cmd.raster_execute_lf(), ESC + FF + LF)


class TestUSBInterface(unittest.TestCase):
    def test_register_usb_serial(self):
        data = b"SN12345"
        result = cmd.register_usb_serial(data)
        self.assertEqual(
            result,
            ESC + b"##W" + bytes([len(data)]) + b"," + data + LF + NUL,
        )

    def test_register_usb_serial_too_long(self):
        with self.assertRaises(PrinterCommandError):
            cmd.register_usb_serial(b"x" * 256)


class TestPrintMode(unittest.TestCase):
    def test_select_print_mode(self):
        self.assertEqual(
            cmd.select_print_mode(1),
            ESC + RS + b"C" + b"\x01",
        )

    def test_select_print_startup(self):
        self.assertEqual(
            cmd.select_print_startup(0),
            ESC + RS + b"S" + NUL,
        )


class TestPrinterInformation(unittest.TestCase):
    def test_register_printer_info(self):
        data = b"test"
        self.assertEqual(
            cmd.register_printer_info(1, 4, data),
            ESC + GS + b"(S" + b"\x01\x04" + data,
        )

    def test_send_printer_info(self):
        self.assertEqual(
            cmd.send_printer_info(1, 0, 2),
            ESC + GS + b")I" + b"\x01\x00\x02",
        )

    def test_inquire_printer_version(self):
        self.assertEqual(
            cmd.inquire_printer_version(),
            ESC + b"#*" + LF + NUL,
        )


class TestCustomerDisplay(unittest.TestCase):
    def test_customer_display_send(self):
        data = b"Hello"
        self.assertEqual(
            cmd.customer_display_send(data),
            ESC + GS + b"B@" + data,
        )

    def test_customer_display_status_request(self):
        self.assertEqual(
            cmd.customer_display_status_request(),
            ESC + RS + b"BA",
        )

    def test_customer_display_data_request(self):
        self.assertEqual(
            cmd.customer_display_data_request(),
            ESC + GS + b"BB",
        )

    def test_customer_display_buffer_clear(self):
        self.assertEqual(
            cmd.customer_display_buffer_clear(),
            ESC + GS + b"BC",
        )


class TestParameterValidation(unittest.TestCase):
    def test_out_of_range_raises(self):
        with self.assertRaises(PrinterCommandError):
            cmd.set_print_density(256)

    def test_negative_raises(self):
        with self.assertRaises(PrinterCommandError):
            cmd.set_print_speed(-1)

    def test_ring_buzzer_out_of_range(self):
        with self.assertRaises(PrinterCommandError):
            cmd.ring_buzzer(256, 0, 0)


if __name__ == "__main__":
    unittest.main()
