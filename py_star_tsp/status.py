"""
ASB (Automatic Status Back) status parser for the Star TSP100.

The printer sends a 4-byte status word in response to ``ESC ACK SOH``.
The bit layout follows Appendix-1 of the STAR Graphic Mode Command
Specifications Rev. 2.31.
"""

from __future__ import annotations


class AsbStatus:
    """Parse a 4-byte ASB status response from a Star TSP100 printer.

    Parameters
    ----------
    data:
        Exactly 4 bytes returned by the printer after an ASB status
        request (``ESC ACK SOH``).

    Raises
    ------
    ValueError
        If *data* is not exactly 4 bytes.
    """

    def __init__(self, data: bytes) -> None:
        if len(data) != 4:
            raise ValueError(
                f"ASB status must be exactly 4 bytes, got {len(data)}"
            )
        self._b = data

    # ------------------------------------------------------------------
    # Byte 0
    # ------------------------------------------------------------------

    @property
    def drawer_open(self) -> bool:
        """True if the cash drawer is open (byte 0, bit 2)."""
        return bool(self._b[0] & 0x04)

    @property
    def offline(self) -> bool:
        """True if the printer is offline (byte 0, bit 3)."""
        return bool(self._b[0] & 0x08)

    # ------------------------------------------------------------------
    # Byte 1
    # ------------------------------------------------------------------

    @property
    def cover_open(self) -> bool:
        """True if the printer cover is open (byte 1, bit 2)."""
        return bool(self._b[1] & 0x04)

    @property
    def paper_feed(self) -> bool:
        """True if the paper is being fed by the FEED button (byte 1, bit 3)."""
        return bool(self._b[1] & 0x08)

    @property
    def paper_near_end(self) -> bool:
        """True if paper is near end (byte 1, bit 5)."""
        return bool(self._b[1] & 0x20)

    @property
    def paper_end(self) -> bool:
        """True if paper has run out (byte 1, bit 6)."""
        return bool(self._b[1] & 0x40)

    # ------------------------------------------------------------------
    # Byte 2
    # ------------------------------------------------------------------

    @property
    def error(self) -> bool:
        """True if any error condition is set (byte 2, bit 6)."""
        return bool(self._b[2] & 0x40)

    @property
    def auto_cutter_error(self) -> bool:
        """True if an auto-cutter error has occurred (byte 2, bit 3)."""
        return bool(self._b[2] & 0x08)

    @property
    def unrecoverable_error(self) -> bool:
        """True if an unrecoverable error has occurred (byte 2, bit 5)."""
        return bool(self._b[2] & 0x20)

    @property
    def auto_recoverable_error(self) -> bool:
        """True if an auto-recoverable error has occurred (byte 2, bit 2)."""
        return bool(self._b[2] & 0x04)

    # ------------------------------------------------------------------
    # Byte 3 — additional status
    # ------------------------------------------------------------------

    @property
    def raw(self) -> bytes:
        """The raw 4-byte status data."""
        return self._b

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        flags = {
            "drawer_open": self.drawer_open,
            "offline": self.offline,
            "cover_open": self.cover_open,
            "paper_feed": self.paper_feed,
            "paper_near_end": self.paper_near_end,
            "paper_end": self.paper_end,
            "error": self.error,
            "auto_cutter_error": self.auto_cutter_error,
            "unrecoverable_error": self.unrecoverable_error,
            "auto_recoverable_error": self.auto_recoverable_error,
        }
        active = [k for k, v in flags.items() if v]
        raw_hex = self._b.hex()
        if active:
            return f"AsbStatus(raw={raw_hex!r}, flags={active})"
        return f"AsbStatus(raw={raw_hex!r}, ok)"
