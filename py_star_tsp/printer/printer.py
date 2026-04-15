"""
StarTSP — high-level USB printer class.

Todo:
    * Multiple loggers to levels of events, and make logleveling more flexible
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

logger = logging.getLogger(__name__)

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

        self.print_speed = 2         # n=0: high speed
                                     # n=1: mid-speed
                                     # n=2: slow speed
        self.raster_quality = 1      # n=0: high-speed printing specified (default)
                                     # n=1: normal print quality
                                     # n=2: high print quality
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
        logger.info(f"USB device search: VID={self.vendor_id}, PID={self.product_id} => {device}")

        if device is None:
            pid_info = f"0x{self.product_id:04x}" if self.product_id else "(any)"

            logger.error(f"Star printer not found (VID=0x{self.vendor_id:04x}, PID={pid_info})")
            raise PrinterNotFoundError(f"Star printer not found (VID=0x{self.vendor_id:04x}, PID={pid_info})")

        return device

    def open(self) -> None:
        """Open the USB connection to the printer.
        
            Todo:
                * Why detaching kernel driver?
                * How would it work on Windows and OS X?
                * Finding descriptors and endpoints: is this robust across different OSes and printer models?

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

    _STATUS_DRAIN_MAX = 64

    def flush_input(self) -> None:
        """Drain pending data from the USB bulk-IN endpoint.

        The printer continuously pushes unsolicited ASB status
        notifications.  This method performs up to
        ``_STATUS_DRAIN_MAX`` short reads to clear whatever is
        already queued in the host-side USB buffer without chasing
        the live stream forever.

        Each flushed chunk is logged at INFO level with a hex dump and,
        if it looks like a valid standard status, a parsed summary.
        """
        if self._ep_in is None:
            return

        flushed_count = 0
        for _ in range(self._STATUS_DRAIN_MAX):
            try:
                stale = bytes(self._ep_in.read(64, timeout=100))
                flushed_count += 1
                description = self._describe_flushed(stale)

                logger.info(
                    "Flushed packet #%d (%d bytes): %s — %s",
                    flushed_count, len(stale), stale.hex(), description,
                )

            except usb.core.USBError:
                break

        if flushed_count:
            logger.info("Flushed %d stale packet(s) from IN buffer", flushed_count)

    @staticmethod
    def _describe_flushed(data: bytes) -> str:
        """Try to interpret a flushed IN-buffer chunk."""
        if len(data) < 2:
            return f"unknown ({len(data)} byte(s))"

        header1 = data[0]
        expected_len = _HEADER1_TO_LEN.get(header1)

        if expected_len is not None and len(data) >= expected_len:
            try:
                status = AsbStatus(data[:expected_len])
                return f"unsolicited ASB status: {status!r}"
            except ValueError:
                pass

        return f"unrecognised data (header1=0x{header1:02x})"

    # ------------------------------------------------------------------
    # High-level convenience methods
    # ------------------------------------------------------------------

    def initialize_raster(self) -> None:
        """Send the raster-mode initialisation command."""
        self.send(commands.raster_initialize())

    def enter_raster_mode(self) -> None:
        """Enter raster graphics mode."""
        self.send(commands.raster_enter())
        self.send(commands.raster_set_print_quality(self.raster_quality))

    def quit_raster_mode(self) -> None:
        """Quit raster graphics mode."""
        self.send(commands.raster_quit())

    def reset(self) -> None:
        """Send the printer reset command."""
        self.send(commands.reset_printer())
        logger.info("Printer reset")

    def drive_drawer(self) -> None:
        """Pulse the cash-drawer port (external device 1)."""
        self.send(commands.drive_external_device_1_bel())

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
        self.send(commands.set_print_density(n))

    def set_speed(self, n: int) -> None:
        """Set the print speed.
            n=0: high speed
            n=1: mid-speed
            n=2: slow speed
        """
        self.send(commands.set_print_speed(n))

    def set_led_blink(self, led_id: int = 1, on_time: int=100, off_time: int=50) -> None:
        """Set the printer's LED to blink with the specified pattern."""
        self.send(commands.set_led_blink(m=led_id, n1=on_time, n2=off_time))

    def led_blink(self) -> None:
        """Blink the printer's LED (for testing)."""
        self.send(commands.led_blink(m=1, n1=10, n2=0))
        logger.info("Blinking printer LED")

    def get_status(self) -> AsbStatus:
        """Request and parse the standard printer status.

        Sends ``ESC ACK SOH`` to guarantee a fresh response, then
        reads packets in a short loop keeping only the **last** one.
        Because the OS buffers unsolicited ASB packets FIFO, the
        last successful read before the timeout is the most recent
        printer state.

        Returns
        -------
        AsbStatus
            Parsed status object reflecting the latest printer state.
        """
        self.send(commands.get_asb_status())

        latest: bytes | None = None
        stale_count = 0

        for _ in range(self._STATUS_DRAIN_MAX):
            try:
                raw = bytes(self._ep_in.read(64, timeout=200))
            except usb.core.USBError:
                break

            if latest is not None:
                stale_count += 1
                description = self._describe_flushed(latest)
                logger.debug(
                    "Skipped stale packet #%d (%d bytes): %s — %s",
                    stale_count, len(latest), latest.hex(), description,
                )
            latest = raw

        if latest is None:
            raise PrinterCommunicationError(
                "No status response received from printer"
            )

        if stale_count:
            logger.info("Drained %d stale packet(s) before latest status", stale_count)

        logger.debug("ASB raw response (%d bytes): %s", len(latest), latest.hex())
        status = AsbStatus(latest)
        logger.info(f"Printer ASB status: {status}")
        return status


    def print(self) -> None:
        """Send a full raster print sequence.

        The sequence is:
        1. Initialise raster mode.
        2. Enter raster mode.
        3. Set page length to match the image height.
        4. Transfer each raster line using ``raster_transfer_auto_lf``.
        5. Execute a form-feed to trigger printing.
        6. Quit raster mode.
        """
        logger.info("Preparing to print raster image")

        self.send(commands.raster_initialize())
        self.enter_raster_mode()

        self.send(commands.raster_set_print_quality(self.raster_quality))
        self.send(commands.raster_set_ff_mode(self.raster_ff_mode))
        self.send(commands.set_print_speed(self.print_speed))

        # Set page length to image height (min 200 dots per spec)
        page_len = max(self.set.total_height, 200)
        logger.info(f"Setting page length to {page_len} dots for image height {self.set.total_height} (200 min)")
        self.send(commands.raster_set_page_length(page_len))

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
            self.send(commands.raster_transfer_auto_lf(n1, n2, line))

        self.send(commands.raster_execute_ff())
        self.quit_raster_mode()


    def add_image(self, filename: str, scale_down=True, invert=False) -> None:
        """
        Add an image to the print queue and print it.
        """
        logger.info("Preparing to add an image")

        img = RasterImage.from_file(filename)
        logger.info(f"Fetched image: {img}")

        img.shrink_to_fit(self.raster_width)
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

        logger.debug(
            "print_text: rendering %d chars (bold=%s, italic=%s, underline=%s)",
            len(text), bold, italic, underline,
        )

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
        """Add a solid black bar of the specified dimensions to the print queue."""
        logger.info(f"Adding a bar: width={width}, height={height}, margin_left={margin_left}, margin_right={margin_right}")

        if width+margin_left > self.raster_width:
            logger.warning(f"Requested bar width {width} with margin {margin_left} exceeds raster width {self.raster_width}; it will be truncated")
            width = self.raster_width - margin_left

        elif width+margin_left < self.raster_width:
            logger.info(f"Requested bar width {width} with margin {margin_left} is less than raster width {self.raster_width}; it will be right-aligned with margin")
            margin_right = self.raster_width - width - margin_left

        bar = SolidBar(width=width, height=height, margin_left=margin_left, margin_right=margin_right)
        self.set.add(bar)
