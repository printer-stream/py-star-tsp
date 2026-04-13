"""
demo.py — Demonstration script for the py-star-tsp library.

This script shows how to connect to a Star TSP100 printer, enter raster
graphics mode, print a test image, and cleanly disconnect.

Usage:
    python demo.py

You will need:
  - A Star TSP100 USB printer connected to the system.
  - The ``pyusb`` and ``Pillow`` packages installed.
  - On Linux: a udev rule granting user access to the printer USB device
    (see README.md).
"""

import logging
import sys

logger = logging.getLogger(__name__)

try:
    from PIL import Image
except ImportError:
    logger.error("Pillow is required. Install it with:  pip install Pillow")
    sys.exit(1)

try:
    from py_star_tsp import StarTSP, RasterImage
    from py_star_tsp.exceptions import PrinterNotFoundError, PrinterCommunicationError
except ImportError:
    logger.error("py_star_tsp is not installed. Run:  pip install .")
    sys.exit(1)


def build_test_image(width: int = 384, height: int = 100) -> RasterImage:
    """Create a test image: all-black band of *width* × *height* pixels."""
    img = Image.new("L", (width, height), color=0)  # 0 = black
    return RasterImage(img)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("py-star-tsp demo — Star TSP100 Graphic Mode")

    try:
        with StarTSP() as printer:
            logger.info("Printer found and opened successfully.")

            logger.info("Printing a 384×100 all-black test band …")
            ri = build_test_image(384, 100)
            printer.print_raster_image(ri)
            logger.info("Done. Check the printer output.")

    except PrinterNotFoundError as exc:
        logger.error("Printer not found: %s", exc)
        logger.info(
            "Make sure the printer is connected and powered on. "
            "On Linux, ensure the udev rule grants your user access "
            "(see README.md)."
        )
        sys.exit(1)
    except PrinterCommunicationError as exc:
        logger.error("Communication error: %s", exc)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
