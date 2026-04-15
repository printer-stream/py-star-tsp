"""
Standard Status parser for the Star TSP100 (Graphic Mode).

The printer returns a variable-length standard status in response to
``ESC ACK SOH``.  The layout is::

    Header 1 (1 byte) + Header 2 (1 byte) + Printer Status (N bytes)

Header 1 encodes the total byte count; Header 2 encodes the status
version.  The Printer Status bytes carry the actual flags.

Bit layouts follow Appendix-1 of the STAR Graphic Mode Command
Specifications Rev. 2.31.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Header 1 → total byte count lookup (page 48)
# ---------------------------------------------------------------------------
_HEADER1_TO_LEN: dict[int, int] = {
    0x0F: 7,
    0x21: 8,
    0x23: 9,
    0x25: 10,
    0x27: 11,
    0x29: 12,
    0x2B: 13,
    0x2D: 14,
    0x2F: 15,
}


class AsbStatus:
    """Parse a standard status response from a Star TSP100 printer.

    Parameters
    ----------
    data:
        The raw bytes returned by the printer after an ASB status
        request (``ESC ACK SOH``).  Must be at least 7 bytes
        (Header 1 + Header 2 + minimum 5 printer-status bytes for
        TSP100 USB, though 9 is typical).

    Raises
    ------
    ValueError
        If *data* is shorter than the length indicated by Header 1.
    """

    def __init__(self, data: bytes) -> None:
        if len(data) < 2:
            raise ValueError(
                f"ASB status must be at least 2 bytes, got {len(data)}"
            )

        self._raw = bytes(data)
        self._header1 = data[0]
        self._header2 = data[1]

        expected = _HEADER1_TO_LEN.get(self._header1)
        if expected is not None and len(data) < expected:
            raise ValueError(
                f"Header 1 (0x{self._header1:02x}) indicates {expected} bytes "
                f"but only {len(data)} received"
            )

        # Printer Status bytes start at index 2
        self._ps = data[2:]

    # ------------------------------------------------------------------
    # Header helpers
    # ------------------------------------------------------------------

    @property
    def byte_count(self) -> int | None:
        """Total byte count indicated by Header 1, or None if unknown."""
        return _HEADER1_TO_LEN.get(self._header1)

    @property
    def version(self) -> int | None:
        """Status version from Header 2, or None if unrecognised."""
        # Bits 1-3,5 encode the version (page 49).
        # Version n → header2 = n * 2 for versions 1-31.
        v = (self._header2 >> 1) & 0x1F
        return v if v > 0 else None

    # ------------------------------------------------------------------
    # Printer Status 1 — printer state (byte index 2, _ps[0])
    # ------------------------------------------------------------------

    @property
    def cover_open(self) -> bool:
        """True if the printer cover is open (PS1 bit 5)."""
        return bool(self._ps[0] & 0x20) if len(self._ps) > 0 else False

    @property
    def offline(self) -> bool:
        """True if the printer is offline (PS1 bit 3)."""
        return bool(self._ps[0] & 0x08) if len(self._ps) > 0 else False

    @property
    def compulsion_switch(self) -> bool:
        """True if the compulsion switch is closed (PS1 bit 2)."""
        return bool(self._ps[0] & 0x04) if len(self._ps) > 0 else False

    @property
    def etb_executed(self) -> bool:
        """True if <ETB> command has been executed (PS1 bit 1)."""
        return bool(self._ps[0] & 0x02) if len(self._ps) > 0 else False

    # ------------------------------------------------------------------
    # Printer Status 2 — error information (byte index 3, _ps[1])
    # ------------------------------------------------------------------

    @property
    def head_temp_stop(self) -> bool:
        """True if printing stopped due to head high temperature (PS2 bit 6)."""
        return bool(self._ps[1] & 0x40) if len(self._ps) > 1 else False

    @property
    def unrecoverable_error(self) -> bool:
        """True if an unrecoverable error has occurred (PS2 bit 5)."""
        return bool(self._ps[1] & 0x20) if len(self._ps) > 1 else False

    @property
    def auto_cutter_error(self) -> bool:
        """True if an auto-cutter error has occurred (PS2 bit 3)."""
        return bool(self._ps[1] & 0x08) if len(self._ps) > 1 else False

    # ------------------------------------------------------------------
    # Printer Status 4 — paper (byte index 5, _ps[3])
    # ------------------------------------------------------------------

    @property
    def paper_end(self) -> bool:
        """True if paper has run out (PS4 bit 3)."""
        return bool(self._ps[3] & 0x08) if len(self._ps) > 3 else False

    # ------------------------------------------------------------------
    # Printer Status 6 — ETB counter (byte index 7, _ps[5])
    # ------------------------------------------------------------------

    @property
    def etb_counter(self) -> int | None:
        """5-bit ETB counter value (0-31), or None if not available."""
        if len(self._ps) <= 5:
            return None
        b = self._ps[5]
        # bits 6,5 → high bits; bits 3,2,1 → low bits
        return ((b >> 4) & 0x06) | ((b >> 3) & 0x04) | ((b >> 1) & 0x07)

    # ------------------------------------------------------------------
    # Raw data access
    # ------------------------------------------------------------------

    @property
    def raw(self) -> bytes:
        """The complete raw status data including headers."""
        return self._raw

    @property
    def printer_status(self) -> bytes:
        """Only the printer-status bytes (headers stripped)."""
        return self._ps

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def has_error(self) -> bool:
        """True if any error condition is set."""
        return (
            self.head_temp_stop
            or self.unrecoverable_error
            or self.auto_cutter_error
        )

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        flags = {
            "cover_open": self.cover_open,
            "offline": self.offline,
            "head_temp_stop": self.head_temp_stop,
            "unrecoverable_error": self.unrecoverable_error,
            "auto_cutter_error": self.auto_cutter_error,
            "paper_end": self.paper_end,
        }
        active = [k for k, v in flags.items() if v]
        raw_hex = self._raw.hex()
        if active:
            return f"AsbStatus(raw={raw_hex!r}, flags={active})"
        return f"AsbStatus(raw={raw_hex!r}, ok)"
