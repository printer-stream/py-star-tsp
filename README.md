# py-star-tsp

Python SDK for **Star TSP100** series thermal printers operating in **Graphic Mode** over USB.

Implements the full command set described in the **STAR Graphic Mode Command Specifications Rev. 2.31**.

> AI Generated, poorly reviewed, and not supervised. Soggy.

---

## Supported Models

| Model | Interface |
|---|---|
| TSP100U | USB |
| TSP100PU | USB + Parallel |
| TSP100GT | USB + Ethernet |
| TSP100LAN | Ethernet |
| TSP100IIU | USB |
| TSP100IIIW | USB + Wi-Fi |
| TSP100IIILAN | USB + Ethernet |
| TSP100IIIBI | USB + Bluetooth |
| TSP100IIIU | USB |

---

## Installation

```bash
pip install .
```

### Dependencies

- [pyusb](https://github.com/pyusb/pyusb) ≥ 1.2.1
- [Pillow](https://python-pillow.org/) ≥ 9.0.0

---

## Linux USB Access (udev rule)

By default, USB devices are accessible only to `root`. Add the following udev rule to grant access to all users in the `plugdev` group:

```
# /etc/udev/rules.d/99-star-tsp100.rules
SUBSYSTEM=="usb", ATTRS{idVendor}=="0519", MODE="0666", GROUP="plugdev"
```

Reload rules and reconnect the printer:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Add your user to the `plugdev` group if necessary:

```bash
sudo usermod -aG plugdev $USER
```

---

## Quick Start

```python
from PIL import Image
from py_star_tsp import StarTSP, RasterImage

# Create a test image (384 px wide — the TSP100 print width at 203 dpi)
img = Image.new("L", (384, 100), color=0)   # all-black band
raster = RasterImage(img)

# Print it
with StarTSP() as printer:
    printer.print_raster_image(raster)
```

---

## API Overview

### `StarTSP`

```python
from py_star_tsp import StarTSP

printer = StarTSP(
    vendor_id=0x0519,   # Star Micronics USB VID (default)
    product_id=None,    # auto-detect (default)
    timeout=5000,       # ms
)

printer.open()
printer.close()

# Context manager (recommended)
with StarTSP() as printer:
    printer.initialize_raster()
    printer.enter_raster_mode()
    # … send raster lines …
    printer.quit_raster_mode()

# Convenience methods
printer.print_raster_image(raster_image)  # full print sequence
printer.drive_drawer()                    # cash-drawer pulse
printer.ring_buzzer(m, n1, n2)
printer.set_density(n)
printer.set_speed(n)
printer.set_print_area(n)
status = printer.get_status()             # → AsbStatus
printer.reset()
```

### `RasterImage`

```python
from PIL import Image
from py_star_tsp import RasterImage

img = Image.open("receipt.png")
ri = RasterImage(img)

print(ri.width, ri.height)
lines = ri.to_raster_lines()   # list[bytes], one per print row
```

### `AsbStatus`

```python
status = printer.get_status()

print(status.offline)               # bool
print(status.paper_end)             # bool
print(status.cover_open)            # bool
print(status.auto_cutter_error)     # bool
print(repr(status))                 # human-readable summary
```

### `commands` module

Every command byte sequence from the spec is available as a standalone
builder in `py_star_tsp.commands`:

```python
from py_star_tsp import commands as cmd

raw = cmd.raster_initialize()
raw += cmd.raster_enter()
raw += cmd.raster_transfer_auto_lf(48, 0, line_bytes)
raw += cmd.raster_execute_ff()
raw += cmd.raster_quit()

printer.send(raw)
```

---

## Running the Demo

```bash
python demo.py
```

---

## Running the Tests

```bash
python -m pytest tests/
```

---

## Specification Reference

Commands are implemented from the **STAR Graphic Mode Command Specifications Rev. 2.31** (`star_graphic_cm_en.pdf`).
