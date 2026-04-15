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

## Text Rendering

The library can render text to raster images and print them directly,
providing an ESC/POS-like plain-text workflow for a raster-only printer.

```python
with StarTSP() as printer:
    # Simple text
    printer.print_text("Hello, World!")

    # Styled text
    printer.print_text("Bold + Underline", bold=True, underline=True)

    # White on black with border
    printer.print_text(
        "ALERT",
        invert=True,
        box_fill=True,
        border=True,
        border_thickness=3,
        font_size=28,
    )
```

### Standalone rendering (without a printer)

```python
from py_star_tsp import render_text, RasterImage

img = render_text(
    "Receipt line 1\nReceipt line 2",
    font_size=20,
    bold=True,
    underline=True,
    width=384,
)
img.save("receipt.png")
```

### Style options

| Parameter | Type | Default | Description |
|---|---|---|---|
| `font_name` | `str \| None` | `None` | Font stem to search for (e.g. `"DejaVuSansMono"`). `None` uses the fallback list. |
| `font_size` | `int` | `20` | Font size in pixels. |
| `bold` | `bool` | `False` | Use bold font variant. |
| `italic` | `bool` | `False` | Use italic font variant. |
| `underline` | `bool` | `False` | Draw underline beneath text. |
| `width` | `int` | `384` | Image width in pixels. |
| `border` | `bool` | `False` | Draw a rectangular border. |
| `border_thickness` | `int` | `2` | Border width in pixels. |
| `box_fill` | `bool` | `False` | Fill the text background. |
| `invert` | `bool` | `False` | Swap foreground/background (white-on-black). |
| `line_spacing` | `int` | `4` | Extra vertical spacing between lines. |

---

## Font Discovery and Fallback

The text renderer automatically scans standard OS directories for
`.ttf` and `.otf` fonts:

| OS | Search paths |
|---|---|
| Linux | `/usr/share/fonts`, `/usr/local/share/fonts`, `~/.local/share/fonts`, `~/.fonts` |
| macOS | `/System/Library/Fonts`, `/Library/Fonts`, `~/Library/Fonts` |
| Windows | `%WINDIR%\Fonts` |

You can also set the `FONTPATH` environment variable to add custom directories
(separated by `os.pathsep`).

### Fallback font order

When no specific font is requested, the following are tried in order:

1. DejaVu Sans Mono
2. Liberation Mono
3. FreeMono
4. Arial
5. Consolas
6. Courier New

If **no TrueType/OpenType fonts are found at all**, Pillow's built-in
bitmap font is used.  This bitmap font does **not** support sizing,
bold, italic, or underline — a warning is logged.

### Font source packages

Install these Python/system packages to ensure fonts are available:

- **matplotlib** — ships DejaVu Sans / DejaVu Sans Mono
- **fonttools** — useful for font metadata inspection
- **fonts-dejavu** (Debian/Ubuntu) / **dejavu-sans-mono-fonts** (Fedora/Rocky) — DejaVu family
- **fonts-liberation** (Debian/Ubuntu) / **liberation-mono-fonts** (Fedora/Rocky) — Liberation family

### Programmatic font discovery

```python
from py_star_tsp import discover_fonts, find_font

# List all detected fonts
fonts = discover_fonts()
for stem, path in fonts.items():
    print(f"{stem}: {path}")

# Find a specific font (with bold variant)
path = find_font("DejaVuSansMono", bold=True)
```

---

## Midtones / Grayscale (Dithering)

The TSP100 is a **monochrome** thermal printer — each dot is either
printed (black) or not (white).  True grayscale is **not possible**.

However, the *appearance* of midtones can be approximated using
**dithering** before rasterising:

```python
from PIL import Image

grey = Image.new("L", (384, 100), color=128)
dithered = grey.convert("1")  # Floyd-Steinberg dithering (Pillow default)
```

Pillow's `Image.convert("1")` applies Floyd-Steinberg error-diffusion
dithering by default.  You may also apply ordered (Bayer) dithering or
other halftone algorithms before passing the image to `RasterImage`.
Results vary with print density and paper quality; experimentation is
recommended.

---

## ESC/POS Compatibility

The `print_text()` method provides an **ESC/POS-like** plain-text
printing experience.  Key differences from a native ESC/POS printer:

| Feature | ESC/POS | py-star-tsp |
|---|---|---|
| Text encoding | Code page (e.g. CP437) | Any Unicode (font-dependent) |
| Inline escape codes | `ESC E 1` etc. | Not interpreted; use keyword args |
| Characters per line | Fixed (e.g. 42 col) | Depends on font/size (~38–42 at 20 px mono) |
| Barcode/QR | Native commands | Render as image, then `print_raster_image()` |
| Paper cut | `GS V` | Use `raster_execute_ff()` / form-feed |
| Cash drawer | `ESC p` | `printer.drive_drawer()` |

**Caveats:**
- All text is rendered to a bitmap and sent as raster graphics, so
  print speed is somewhat lower than native ESC/POS text.
- Inline ESC/POS control codes in the text string are **not** parsed.
  Formatting must be specified via function parameters.

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
printer.print_text("Hello", bold=True)    # text rendering + print
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

## Logging

All library modules use Python's `logging` module.  No `print()`
statements are used for status, warning, or error output.

To see debug output:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Running the Demo

```bash
python demo.py
```

---

## Running the Tests

### Unit tests

```bash
python -m pytest tests/
```

### Integration tests (real printer)

Integration tests require a Star TSP100 connected via USB.  They are
**skipped by default**.  To enable:

```bash
PY_STAR_TSP_INTEGRATION=1 python -m pytest tests/test_integration.py -v
```

**Requirements:**
- Star TSP100 USB printer connected and powered on
- Linux: udev rule granting USB access (see above)
- Default device: `/dev/usb/lp0` (Rocky 9 / RHEL 9)
- `pyusb` and `Pillow` installed

The integration tests cover:
- Raster image printing (all-black, all-white bands)
- Text rendering with all formatting options
- Multiline text
- Bordered, inverted (white-on-black) text

---

## Command Spec Compliance

All command byte sequences are implemented per the **STAR Graphic Mode
Command Specifications Rev. 2.31**.  Notes:

- All parameter values are validated against their specified ranges
  (`0–255`).  `PrinterCommandError` is raised for out-of-range values.
- Raster transfer commands (`b n1 n2 data`, `k n1 n2 data`) accept
  raw `bytes` data; the caller is responsible for correct line width.
- The `register_usb_serial` command enforces the 255-byte data limit.
- Multi-byte length fields (e.g. `n1`/`n2` in raster transfer) use
  little-endian byte order per the spec.
- The `register_printer_info` command passes data bytes unchanged;
  the caller must format them per the spec for the specific info type.
- Customer display commands are implemented but depend on the display
  peripheral being connected and supported by the printer model.

---

## Specification Reference

Commands are implemented from the **STAR Graphic Mode Command Specifications Rev. 2.31** (`star_graphic_cm_en.pdf`).

## Licensing

* Kitten in the demos by Deni Sudibyo

