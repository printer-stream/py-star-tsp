"""
StarTSP — high-level USB printer class for the Star TSP100 series.

Uses ``pyusb`` (``usb.core``) for all USB communication.  No third-party
printer libraries are used; all commands are built from the byte-level
builders in ``commands.py``.
"""

from __future__ import annotations

from typing import Optional

from .exceptions import (
    PrinterCommunicationError,
    PrinterNotFoundError,
)
from . import commands as cmd
from .raster import RasterImage
from .status import AsbStatus

try:
    import usb.core
    import usb.util
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "pyusb is required. Install it with: pip install pyusb"
    ) from exc

# Star TSP100 USB vendor ID
_STAR_VID = 0x0519

# Endpoint directions
_EP_OUT = usb.util.ENDPOINT_OUT
_EP_IN  = usb.util.ENDPOINT_IN


class StarTSP:
    """High-level interface to a Star TSP100 series thermal printer over USB.

    Parameters
    ----------
    vendor_id:
        USB vendor ID.  Defaults to ``0x0519`` (Star Micronics).
    product_id:
        USB product ID.  If ``None``, the first device with the matching
        vendor ID is used.
    timeout:
        USB transfer timeout in milliseconds.
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

    # ------------------------------------------------------------------
    # Device lifecycle
    # ------------------------------------------------------------------

    def find_device(self):
        """Scan USB and return the first matching device.

        Raises
        ------
        PrinterNotFoundError
            If no device with the configured vendor (and optionally
            product) ID is found.
        """
        kwargs = {"idVendor": self.vendor_id}
        if self.product_id is not None:
            kwargs["idProduct"] = self.product_id
        device = usb.core.find(**kwargs)
        if device is None:
            pid_info = (
                f"0x{self.product_id:04x}" if self.product_id else "(any)"
            )
            raise PrinterNotFoundError(
                f"Star TSP100 printer not found "
                f"(VID=0x{self.vendor_id:04x}, PID={pid_info})"
            )
        return device

    def open(self) -> None:
        """Open the USB connection to the printer."""
        self._device = self.find_device()

        # Detach kernel driver if active (Linux)
        if self._device.is_kernel_driver_active(0):
            self._device.detach_kernel_driver(0)

        self._device.set_configuration()
        cfg = self._device.get_active_configuration()
        intf = cfg[(0, 0)]

        self._ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: (
                usb.util.endpoint_direction(e.bEndpointAddress) == _EP_OUT
            ),
        )
        self._ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: (
                usb.util.endpoint_direction(e.bEndpointAddress) == _EP_IN
            ),
        )

        if self._ep_out is None:
            raise PrinterCommunicationError("Bulk-OUT endpoint not found")

    def close(self) -> None:
        """Release the USB interface and close the connection."""
        if self._device is not None:
            usb.util.dispose_resources(self._device)
            self._device = None
            self._ep_out = None
            self._ep_in = None

    def __enter__(self) -> "StarTSP":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Low-level I/O
    # ------------------------------------------------------------------

    def send(self, data: bytes) -> None:
        """Write raw *data* bytes to the USB bulk-OUT endpoint.

        Raises
        ------
        PrinterCommunicationError
            If the USB write fails.
        """
        if self._ep_out is None:
            raise PrinterCommunicationError("Printer is not open")
        try:
            self._ep_out.write(data, timeout=self.timeout)
        except Exception as exc:
            raise PrinterCommunicationError(
                f"USB write failed: {exc}"
            ) from exc

    def read(self, length: int) -> bytes:
        """Read up to *length* bytes from the USB bulk-IN endpoint.

        Raises
        ------
        PrinterCommunicationError
            If the USB read fails or no bulk-IN endpoint is available.
        """
        if self._ep_in is None:
            raise PrinterCommunicationError(
                "Printer is not open or has no bulk-IN endpoint"
            )
        try:
            result = self._ep_in.read(length, timeout=self.timeout)
            return bytes(result)
        except Exception as exc:
            raise PrinterCommunicationError(
                f"USB read failed: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # High-level convenience methods
    # ------------------------------------------------------------------

    def initialize_raster(self) -> None:
        """Send the raster-mode initialisation command."""
        self.send(cmd.raster_initialize())

    def enter_raster_mode(self) -> None:
        """Enter raster graphics mode."""
        self.send(cmd.raster_enter())

    def quit_raster_mode(self) -> None:
        """Quit raster graphics mode."""
        self.send(cmd.raster_quit())

    def print_raster_image(self, raster_image: RasterImage) -> None:
        """Send a full raster print sequence for *raster_image*.

        The sequence is:
        1. Initialise raster mode.
        2. Enter raster mode.
        3. Transfer each raster line using ``raster_transfer_auto_lf``.
        4. Execute a form-feed to trigger printing.
        5. Quit raster mode.
        """
        self.initialize_raster()
        self.enter_raster_mode()

        lines = raster_image.to_raster_lines()
        bytes_per_row = (raster_image.width + 7) // 8
        n1 = bytes_per_row & 0xFF
        n2 = (bytes_per_row >> 8) & 0xFF

        for line in lines:
            self.send(cmd.raster_transfer_auto_lf(n1, n2, line))

        self.send(cmd.raster_execute_ff())
        self.quit_raster_mode()

    def drive_drawer(self) -> None:
        """Pulse the cash-drawer port (external device 1)."""
        self.send(cmd.drive_external_device_1_bel())

    def ring_buzzer(self, m: int, n1: int, n2: int) -> None:
        """Ring the built-in buzzer."""
        self.send(cmd.ring_buzzer(m, n1, n2))

    def set_density(self, n: int) -> None:
        """Set the print density."""
        self.send(cmd.set_print_density(n))

    def set_speed(self, n: int) -> None:
        """Set the print speed."""
        self.send(cmd.set_print_speed(n))

    def set_print_area(self, n: int) -> None:
        """Set the print area."""
        self.send(cmd.set_print_area(n))

    def get_status(self) -> AsbStatus:
        """Request and parse the ASB printer status.

        Sends ``ESC ACK SOH`` and reads 4 bytes from the bulk-IN endpoint.

        Returns
        -------
        AsbStatus
            Parsed status object.
        """
        self.send(cmd.get_asb_status())
        raw = self.read(4)
        return AsbStatus(raw)

    def reset(self) -> None:
        """Send the printer reset command."""
        self.send(cmd.reset_printer())
