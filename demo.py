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

import sys

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow is required. Install it with:  pip install Pillow")
    sys.exit(1)

try:
    from py_star_tsp import StarTSP, RasterImage
    from py_star_tsp.exceptions import PrinterNotFoundError, PrinterCommunicationError
except ImportError:
    print("Error: py_star_tsp is not installed. Run:  pip install .")
    sys.exit(1)


def build_test_image(width: int = 384, height: int = 100) -> RasterImage:
    """Create a test image: all-black band of *width* × *height* pixels."""
    img = Image.new("L", (width, height), color=0)  # 0 = black
    return RasterImage(img)


def main() -> None:
    print("py-star-tsp demo — Star TSP100 Graphic Mode")
    print("=" * 45)

    try:
        with StarTSP() as printer:
            print("Printer found and opened successfully.")

            print("Printing a 384×100 all-black test band …")
            ri = build_test_image(384, 100)
            printer.print_raster_image(ri)
            print("Done. Check the printer output.")

    except PrinterNotFoundError as exc:
        print(f"\n[ERROR] Printer not found: {exc}")
        print("Make sure the printer is connected and powered on.")
        print(
            "On Linux, ensure the udev rule grants your user access "
            "(see README.md)."
        )
        sys.exit(1)
    except PrinterCommunicationError as exc:
        print(f"\n[ERROR] Communication error: {exc}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"\n[ERROR] Unexpected error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
