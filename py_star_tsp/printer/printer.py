"""
StarTSP — high-level USB printer class.

TODO: Multiple loggers to levels of events, and make logleveling more flexible
"""

from __future__ import annotations

import logging
from typing import Optional

from py_star_tsp.exceptions import (
    PrinterCommunicationError,
    PrinterNotFoundError,
)
from py_star_tsp import commands
from py_star_tsp.raster import RasterImage, RasterSet, SolidBar
from py_star_tsp.status import AsbStatus
from py_star_tsp.text import TextBlock
from py_star_tsp.status import _HEADER1_TO_LEN

try:
    import usb.core
    import usb.util
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "pyusb is required. Install it with: pip install pyusb"
    ) from exc

logger = logging.getLogger("py_star_tsp")

# Star TSP USB vendor ID
_STAR_VID = 0x0519

# Endpoint directions
_EP_OUT = usb.util.ENDPOINT_OUT
_EP_IN  = usb.util.ENDPOINT_IN


class StarTSP:
    """High-level interface to a Star TSP series thermal printer over USB.

    Args:
        vendor_id (int): USB vendor ID.
        product_id (int, optional): USB product ID.
            If ``None``, the first device with the matching vendor ID is used.
        timeout (int): USB transfer timeout in milliseconds.
    """

    def __init__(
        self,
        vendor_id: int = _STAR_VID,
        product_id: Optional[int] = None,
        timeout: int = 5000,
    ) -> None:
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.timeout = timeout

        self._device = None
        self._ep_out = None
        self._ep_in = None

        self.paper_width_mm = 80
        self.raster_dpi = 203
        self.raster_width = 576

        self.cut = True

        self.print_speed = 2           # n=0: high speed
                                       # n=1: mid-speed
                                       # n=2: slow speed
        self.raster_print_quality = 1  # n=0: high-speed printing specified (default)
                                       # n=1: normal print quality
                                       # n=2: high print quality
        self.print_density = 2         # n=0: density +3 (darkest)
                                       # n=1: density +2
                                       # n=2: density +1
                                       # n=3: density standard (default)
                                       # n=4: density -1
                                       # n=5: density -2
                                       # n=6: density -3 (lightest)
        self.set = RasterSet()

    @property
    def raster_ff_mode(self) -> int:
        if self.cut is True:
            return 13
        elif self.cut is False:
            return 2
        else:
            return 13

    def find_device(self):
        """Scan USB and return the first matching device.

        Raises:
            PrinterNotFoundError: If no device with the configured vendor
                (and optionally product) ID is found.
        """
        kwargs = {"idVendor": self.vendor_id}
        if self.product_id is not None:
            kwargs["idProduct"] = self.product_id

        logger.debug(f"Looking for USB devices with criteria: {kwargs}")
        device = usb.core.find(**kwargs)
        logger.debug(f"USB device search: VID={self.vendor_id}, PID={self.product_id} => {device}")

        if device is None:
            pid_info = f"0x{self.product_id:04x}" if self.product_id else "(any)"

            logger.error(f"Star printer not found (VID=0x{self.vendor_id:04x}, PID={pid_info})")
            raise PrinterNotFoundError(f"Star printer not found (VID=0x{self.vendor_id:04x}, PID={pid_info})")

        return device

    def open(self) -> None:
        """Open the USB connection to the printer.

        TODO: Why detaching kernel driver?
        TODO: How would it work on Windows and OS X?
        TODO: Finding descriptors and endpoints: is this robust across different OSes and printer models?

        """
        logger.debug("Opening printer connection")
        self._device = self.find_device()

        # Detach kernel driver if active (Linux)
        if self._device.is_kernel_driver_active(0):
            logger.info("Detaching kernel driver")
            self._device.detach_kernel_driver(0)
            logger.debug("Kernel driver detached")

        logger.debug("Flushing device configuration")
        self._device.set_configuration()
        cfg = self._device.get_active_configuration()
        interface_obj = cfg[(0, 0)]

        self._ep_out = usb.util.find_descriptor(
            interface_obj,
            custom_match=lambda e: (
                usb.util.endpoint_direction(e.bEndpointAddress) == _EP_OUT
            ),
        )
        self._ep_in = usb.util.find_descriptor(
            interface_obj,
            custom_match=lambda e: (
                usb.util.endpoint_direction(e.bEndpointAddress) == _EP_IN
            ),
        )

        if self._ep_out is None:
            raise PrinterCommunicationError("Bulk-OUT endpoint not found")

        if self._ep_in is None:
            raise PrinterCommunicationError("Bulk-IN endpoint not found")

        logger.info("Printer opened successfully")

    def close(self) -> None:
        """Release the USB interface and close the connection."""
        if self._device is not None:
            usb.util.dispose_resources(self._device)
            self._device = None
            self._ep_out = None
            self._ep_in = None
            logger.info("Printer connection closed")

    def __enter__(self) -> "StarTSP":
        logger.debug("Opening printer connection in context manager")
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        logger.debug("Closing printer connection in context manager")
        self.close()

    def send(self, data: bytes) -> None:
        """Write raw *data* bytes to the USB bulk-OUT endpoint.

        Args:
            data (bytes): The data to send.

        Raises:
            PrinterCommunicationError: If the USB write fails.
        """
        if self._ep_out is None:
            raise PrinterCommunicationError("Printer is not open")

        try:
            hex_str = " ".join(f"0x{b:02x}" for b in data)
            logger.debug("Sending %d bytes: %s", len(data), hex_str)

            ascii_str = "".join(chr(b) if 0x20 <= b < 0x7f else f"\\x{b:02x}" for b in data)
            logger.debug("Sending %d ASCII: %s", len(data), ascii_str)

            self._ep_out.write(data, timeout=self.timeout)
            logger.debug("Data sent successfully")

        except Exception as exc:
            logger.exception(f"USB write failed: {exc}")
            raise PrinterCommunicationError(f"USB write failed: {exc}") from exc

    def read(self, length: int) -> bytes:
        """Read up to *length* bytes from the USB bulk-IN endpoint.

        Args:
            length (int): The maximum number of bytes to read.

        Raises:
            PrinterCommunicationError: If the USB read fails or no bulk-IN endpoint is available.
        """
        if self._ep_in is None:
            raise PrinterCommunicationError("Printer is not open or has no bulk-IN endpoint")

        try:
            result = self._ep_in.read(length, timeout=self.timeout)
            logger.debug("Read %d bytes: %s", len(result), result.hex())
            return bytes(result)

        except Exception as exc:
            logger.exception(f"USB read failed: {exc}")
            raise PrinterCommunicationError(f"USB read failed: {exc}") from exc

    def initialize_raster(self) -> None:
        """Send the raster-mode initialisation command."""
        self.send(commands.raster_initialize())

    def enter_raster_mode(self) -> None:
        """Enter raster graphics mode."""
        self.send(commands.raster_enter())

    def quit_raster_mode(self) -> None:
        """Quit raster graphics mode."""
        self.send(commands.raster_quit())

    def reset(self) -> None:
        """Send the printer reset command."""
        self.send(commands.reset_printer())
        logger.debug("Printer has been reset")

    def drive_drawer(self) -> None:
        """Pulse the cash-drawer port (external device 1)."""
        self.send(commands.drive_external_device_1_bel())
        logger.debug("Cash drawer pulsed")

    def set_raster_ff_mode(self, mode: int) -> None:
        """Set the raster FF mode (form feed behavior).

        Args:
            mode (int): The FF mode to set.
        """
        self.send(commands.raster_set_ff_mode(mode))
        logger.debug(f"Raster FF mode set to {mode}")

    def set_raster_print_quality(self, n: int) -> None:
        """Set the print quality.

            n=0: high-speed printing specified (default)
            n=1: normal print quality
            n=2: high print quality
        """
        if n < 0 or n > 2:
            raise ValueError(f"Invalid quality value {n}; must be between 0 and 2")

        self.send(commands.raster_set_print_quality(n))

    def set_raster_page_length(self, length_dots: int) -> None:
        """Set the page length in dots.

        Args:
            length_dots (int): The page length in dots. Minimum is 200 dots per spec.
        """
        if length_dots < 200:
            logger.warning(f"Requested page length {length_dots} is less than minimum 200; it may be ignored by the printer")

        self.send(commands.raster_set_page_length(length_dots))
        logger.debug(f"Raster page length set to {length_dots} dots")

    def set_density(self, n: int) -> None:
        """Set the print density.

            n=0: density +3 (darkest)
            n=1: density +2
            n=2: density +1
            n=3: density standard (default)
            n=4: density -1
            n=5: density -2
            n=6: density -3 (lightest)
        """
        if n < 0 or n > 6:
            raise ValueError(f"Invalid density value {n}; must be between 0 and 6")

        self.send(commands.set_print_density(n))

    def set_print_speed(self, n: int) -> None:
        """Set the print speed.
            n=0: high speed
            n=1: mid-speed
            n=2: slow speed
        """
        if n < 0 or n > 2:
            raise ValueError(f"Invalid speed value {n}; must be between 0 and 2")

        self.send(commands.set_print_speed(n))

    def set_led_blink(self, led_id: int = 1, on_time: int=100, off_time: int=50) -> None:
        """Set the printer's LED to blink with the specified pattern."""
        self.send(commands.set_led_blink(m=led_id, n1=on_time, n2=off_time))

    def led_blink(self) -> None:
        """Blink the printer's LED (for testing)."""
        self.send(commands.led_blink(m=1, n1=10, n2=0))
        logger.debug("Blinking printer LED")

    def raster_ff(self) -> None:
        """Send a form feed in raster mode."""
        self.send(commands.raster_execute_ff())
        logger.debug("Executed raster form feed")

    def get_status(self) -> AsbStatus:
        """Request and parse the standard printer status.

        Sends ``ESC ACK SOH`` to guarantee a fresh response, then
        reads packets in a short loop keeping only the **last** one.
        Because the OS buffers unsolicited ASB packets FIFO, the
        last successful read before the timeout is the most recent
        printer state.

        Returns:
            AsbStatus: Parsed status object reflecting the latest printer state.

        TODO: Allegedly, the printer may send unsolicited ASB status packets continuously
        TODO: Flushing used to help, but what about having a thread that reads the usb input
        TODO: How the input buffer works in this case?
        """
        self.send(commands.get_asb_status())

        raw: bytes | None = None

        try:
            raw = bytes(self._ep_in.read(64, timeout=200))
        except usb.core.USBError:
            logger.warning("No status response received within timeout")

        if raw is None:
            raise PrinterCommunicationError("No status response received from printer")

        logger.debug("ASB raw response (%d bytes): %s", len(raw), raw.hex())
        status = AsbStatus(raw)
        logger.info(f"Printer ASB status: {status}")
        return status

    def print_raster_line(self, n1: int, n2: int, line_data: bytes) -> None:
        """Send a single raster line to the printer.

        Args:
            n1 (int): The low byte of the raster line width in bytes.
            n2 (int): The high byte of the raster line width in bytes.
            line_data (bytes): The raster line data, where each bit represents a pixel (1=black, 0=white).
        """
        self.send(commands.raster_transfer_auto_lf(n1, n2, line_data))

    def render_all(self):
        """Render all elements in the RasterSet as raw raster lines."""
        logger.debug("Rendering all elements in the RasterSet")
        return self.set.raster_lines

    def render_image(self):
        """Render the queued raster content into a Pillow image."""
        logger.debug("Rendering queued raster content to a Pillow image")
        return self.set.to_image()

    def save_rendered(self, filename: str, format: Optional[str] = None, **save_kwargs) -> None:
        """Save the queued raster content to an image file.

        BMP preserves the original 1-bit output exactly. JPEG export is also
        supported by converting the preview to grayscale before saving.
        """
        logger.info(f"Saving rendered raster output to {filename}")
        self.set.save(filename, format=format, **save_kwargs)

    def print(self) -> None:
        """Send a full raster print sequence.

        The sequence is:
            1. Initialise raster mode.
            2. Enter raster mode.
            3. Set page length to match the image height.
            4. Transfer each raster line using ``raster_transfer_auto_lf``.
            5. Execute a form-feed to trigger printing.
            6. Quit raster mode.

        Notes:
            * We're assuming auto LF is the only correct way to go.

        TODO: Try-except with exiting raster mode etc.
        TODO: Defining n1 and n2 per element in the RasterSet. Currently we ensure all blocks are exactly correct width (or do we?).
        """
        logger.info("Preparing to print raster image")

        self.initialize_raster()
        self.enter_raster_mode()

        self.set_density(self.print_density)
        self.set_raster_print_quality(self.raster_print_quality)
        self.set_raster_ff_mode(self.raster_ff_mode)
        self.set_print_speed(self.print_speed)

        # Set page length to image height (min 200 dots per spec)
        page_len = max(self.set.total_height, 200)
        logger.info(f"Setting page length to {page_len} dots for image height {self.set.total_height}")
        self.set_raster_page_length(page_len)

        # Each pixel is 1 bit. To convert pixel width to byte width,
        # divide by 8 — but round up so partial bytes are included.
        # Adding 7 before integer division by 8 is the standard
        # ceiling-divide trick: ceil(x / 8) == (x + 7) // 8
        # Example: 576 pixels → (576 + 7) // 8 = 583 // 8 = 72 bytes
        bytes_per_row = (self.set.total_width + 7) // 8
        logger.info(f"Raster image width: {self.set.total_width} pixels, {bytes_per_row} bytes per row")

        n1 = bytes_per_row & 0xFF
        n2 = (bytes_per_row >> 8) & 0xFF

        for line in self.set.raster_lines:
            self.print_raster_line(n1, n2, line)

        self.raster_ff()
        self.quit_raster_mode()


    def add_image(self, filename: str, invert=False) -> None:
        """
        Add an image to the print queue and print it.

        TODO: Shrinking is inevitable, but should we have other options?
        """
        logger.info("Preparing to add an image")

        img = RasterImage.from_file(filename)
        logger.info(f"Fetched image: {img}")

        img.shrink_to_fit(max_width=self.raster_width)
        logger.info(f"Shrunk image: {img}")

        if invert:
            img.invert()
            logger.info(f"Inverted image: {img}")

        self.set.add(img)


    def add_text(
        self,
        text: str,
        *,
        font_name: Optional[str] = None,
        font_size: int = 20,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        width: int = 576,
        border: bool = False,
        border_thickness: int = 2,
        box_fill: bool = False,
        invert: bool = False,
        line_spacing: int = 4,
    ) -> None:
        """Render *text* as a raster image and print it.

        This provides an ESC/POS-like plain-text printing workflow:
        pass a string and optional formatting flags; the library
        renders the text to a bitmap and sends it to the printer
        in raster graphics mode.

        See :func:`py_star_tsp.text.render_text` for full parameter
        documentation and :mod:`py_star_tsp.escpos_compat` for
        compatibility notes.
        """

        logger.debug(f"print_text: rendering {len(text)} chars: '{text}'")

        text_block = TextBlock(
            text,
            font_name=font_name,
            font_size=font_size,
            width=self.raster_width,
            border=border,
            border_thickness=border_thickness,
            invert=invert,
            line_spacing=line_spacing,
        )
        self.set.add(text_block.render())
        logger.debug("print_text: done")


    def add_bar(self, width: int, height: int, margin_left: int = 0, margin_right: int = 0) -> None:
        """Add a solid black bar of the specified dimensions to the print queue.

        TODO: That margin_right workaround must be cleaned up.
        """
        logger.info(f"Adding a bar: width={width}, height={height}, margin_left={margin_left}, margin_right={margin_right}")

        if width+margin_left > self.raster_width:
            logger.warning(f"Requested bar width {width} with margin {margin_left} exceeds raster width {self.raster_width}; it will be truncated")
            width = self.raster_width - margin_left

        bar = SolidBar(width=width, height=height, margin_left=margin_left, margin_right=margin_right)
        self.set.add(bar)
