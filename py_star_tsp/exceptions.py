"""Custom exceptions for the py-star-tsp library."""


class PrinterNotFoundError(Exception):
    """Raised when a USB device with VID 0x0519 is not found."""


class PrinterCommunicationError(Exception):
    """Raised on USB write/read errors."""


class PrinterCommandError(ValueError):
    """Raised on invalid command parameters."""
