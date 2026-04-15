# py-star-tsp

Python SDK for **Star** thermal printers operating in **Graphic Mode** over USB.

Following the **STAR Graphic Mode Command Specifications Rev. 2.31**.

> AI Generated, poorly reviewed, and hardly supervised.

## Supported Models

| Model | Interface | Tested |
|---|---|---|
| TSP100U | USB | - |
| TSP100PU | USB + Parallel | - |
| TSP100GT | USB + Ethernet | - |
| TSP100LAN | Ethernet | - |
| TSP100IIU | USB | + |
| TSP100IIIW | USB + Wi-Fi | - |
| TSP100IIILAN | USB + Ethernet | - |
| TSP100IIIBI | USB + Bluetooth | - |
| TSP100IIIU | USB | - |


## Installation

```bash
pip install .
```

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


## Midtones / Grayscale (Dithering)

TBD

## ESC/POS Compatibility

TBD

## Specification Reference

Commands are implemented from the **STAR Graphic Mode Command Specifications Rev. 2.31** (`star_graphic_cm_en.pdf`).

## Licensing

* Kitten in the demos by Deni Sudibyo

## TODO

* 2d code implementation (barcode, qr, etc)
* Python version compatibility
* ESC/POS compatibility (very long term)
* Usage with external rendering (just printing ready to use raster)
* Turn demo to a reference sheet
