# py-star-tsp

Python SDK for **Star** thermal printers operating in **Graphic Mode** over USB.

Following the **STAR Graphic Mode Command Specifications Rev. 2.31**.

> AI Generated, poorly reviewed, and hardly supervised.

## Supported Models

| Model        | Interface       | Tested |
| ---          | ---             | ---    |
| TSP100U      | USB             | -      |
| TSP100PU     | USB + Parallel  | -      |
| TSP100GT     | USB + Ethernet  | -      |
| TSP100LAN    | Ethernet        | -      |
| TSP100IIU    | USB             | Y      |
| TSP100IIIW   | USB + Wi-Fi     | -      |
| TSP100IIILAN | USB + Ethernet  | -      |
| TSP100IIIBI  | USB + Bluetooth | -      |
| TSP100IIIU   | USB             | -      |


## Installation

```bash
pip install py-star-tsp
```

## Usage example

```python
import datetime
import py_star_tsp

with py_star_tsp.StarTSP100() as printer:
    # Changing print speed to slow
    printer.print_speed = 2

    # Changing print quality to high
    printer.raster_print_quality = 2

    # Device discovery
    printer.find_device()

    # Preparing timestamp label
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Preparing content
    title = "Before Flying Circus"
    paragraph = """Jones and Palin met at Oxford University, where they performed togethe
r with the Oxford Revue. Chapman and Cleese met at Cambridge Universit
y. Idle was also at Cambridge, but started a year after Chapman and Cl
eese. Cleese met Gilliam in New York City while on tour with the Cambr
idge University Footlights revue Cambridge Circus (originally entitled
 A Clump of Plinths). Chapman, Cleese, and Idle were members of the Fo
otlights, which at that time also included the future Goodies (Tim Bro
oke-Taylor, Bill Oddie, and Graeme Garden), and Jonathan Lynn (co-writ
er of Yes Minister and Yes, Prime Minister).[12] During Idle's preside
ncy of the club, feminist writer Germaine Greer and broadcaster Clive 
James were members. Recordings of Footlights' revues (called "Smokers"
) at Pembroke College include sketches and performances by Cleese and 
Idle, which, along with tapes of Idle's performances in some of the dr
ama society's theatrical productions, are kept in the archives of the 
Pembroke Players.
    """

    # Adding content to the printing "queue"
    printer.add_text(timestamp, font_size=30, invert=True)
    printer.add_bar(width=0, height=15)
    printer.add_image(py_star_tsp.KITTENS_SPINNING)
    printer.add_bar(width=0, height=15)
    printer.add_text(title, font_size=50)
    printer.add_bar(width=0, height=15)
    printer.add_text(paragraph, font_size=20)
    printer.add_image(py_star_tsp.KITTENS_SPINNING, invert=True)

    # Exporting a preview
    printer.save_rendered("/tmp/rendered_example.bmp")

    # Printing out
    printer.print()
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

## Preview / Export

You can save the queued raster output to an image file before sending it to the printer.

```python
from py_star_tsp import StarTSP

printer = StarTSP()
printer.add_text("Preview me")
printer.add_bar(width=576, height=8)

printer.save_rendered("preview.bmp")
printer.save_rendered("preview.jpg", quality=95)

image = printer.render_image()
print(image.size)
```

Use BMP if you want an exact 1-bit preview of what will be sent to the printer. JPEG is supported too, but it is exported as grayscale because JPEG does not support 1-bit images.

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
* Generate a preview of what's rendered to be printed
