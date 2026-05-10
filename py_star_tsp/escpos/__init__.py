"""
ESC/POS emulation layer for Star TSP100 printers.

Accepts raw ESC/POS byte streams (as produced by software targeting an
Epson TM-T88 or compatible printer) and renders them as 1-bit raster
images that can be forwarded to a Star TSP100.

Architecture
------------
The module is built around three public objects:

``PrinterPreset``
    Immutable dataclass describing all physical and typographic
    parameters of the *target* (emulated) printer, e.g. printable
    width, character-cell sizes and the font to use for rendering.
    A ready-made :data:`PRESET_EPSON_TM_T88` constant is provided;
    call its :meth:`~PrinterPreset.copy` method to create variants.

``PRESET_EPSON_TM_T88``
    Default preset that mimics the Epson TM-T88V (80 mm, 203 dpi,
    Font A = 42 chars/line).

``EscposEmulator``
    State-machine parser + renderer.  Feed raw bytes with
    :meth:`~EscposEmulator.feed`; the emulator accumulates lines and
    converts them to a :class:`~py_star_tsp.raster.RasterSet` whenever
    a *print trigger* command (``GS V``, ``FF``) is received.  An
    optional ``on_print`` callback is invoked at that point.

Supported ESC/POS commands
---------------------------
=================  ==========  =============================================
Command            Bytes        Effect
=================  ==========  =============================================
LF                 0x0A        Print & feed one line
CR                 0x0D        Treated as LF
FF                 0x0C        Print & cut (standard mode)
CAN                0x18        Cancel print data in line buffer
ESC @              1B 40       Initialize (reset state)
ESC a *n*          1B 61 n     Justification: 0=left 1=centre 2=right
ESC E *n*          1B 45 n     Emphasised (bold): 0=off 1=on
ESC G *n*          1B 47 n     Double-strike (bold): 0=off 1=on
ESC - *n*          1B 2D n     Underline: 0=off 1=1-dot 2=2-dot
ESC M *n*          1B 4D n     Font: 0=A (42 cpl) 1=B (56 cpl)
ESC ! *n*          1B 21 n     Print mode (compound: font/bold/DH/DW/UL)
ESC 2              1B 32       Select default line spacing
ESC 3 *n*          1B 33 n     Set line spacing to *n* dots
ESC d *n*          1B 64 n     Print & feed *n* lines
ESC J *n*          1B 4A n     Print & feed *n* dots
ESC p *m* *t1* *t2* 1B 70 …   Cash-drawer pulse (consumed, not acted on)
ESC R *n*          1B 52 n     International character set (stored)
ESC t *n*          1B 74 n     Code table selection (stored)
ESC { *n*          1B 7B n     Upside-down print toggle
ESC L              1B 4C       Enter page mode
ESC S              1B 53       Return to standard mode
ESC W *params*     1B 57 …     Set print area in page mode (8 bytes)
ESC T *n*          1B 54 n     Print direction in page mode
GS ! *n*           1D 21 n     Character size (width & height ×1–×8)
GS B *n*           1D 42 n     Reverse (white-on-black): 0=off 1=on
GS V *m* [*n*]     1D 56 m [n] Cut paper / print trigger
GS k *m* …         1D 6B …     Barcode (bytes consumed, not rendered)
GS ( …             1D 28 …     Extended commands incl. QR (consumed)
=================  ==========  =============================================

Font selection for Epson TM-T88 emulation
------------------------------------------
The Epson TM-T88 uses a proprietary bitmap font that is not publicly
available.  This module defaults to the bundled **Orator 15 CPI** font
(``orator_15cpi.otf``), which was designed for exactly 15 characters per
inch — matching the 42 chars/line pitch at 72 mm printable width / 203
dpi.  Alternative fonts can be specified via :attr:`PrinterPreset.font_a_name`
/ :attr:`PrinterPreset.font_b_name`.  Set the value to a font file path,
or any font stem accepted by :func:`py_star_tsp.text.find_font`.

Sub-modules
-----------
- :mod:`py_star_tsp.escpos.presets` — :class:`PrinterPreset` and built-in presets.
- :mod:`py_star_tsp.escpos.emulator` — Internal models and :class:`EscposEmulator`.

References
----------
- Epson ESC/POS Command Reference (Rev. 10.13)
  https://download4.epson.biz/sec_pubs/pos/reference_en/escpos/
- Star TSP100 Programming Guide
  https://www.starmicronics.com/support/knowledgebase/
"""

from .presets import PrinterPreset, PRESET_EPSON_TM_T88, PRESET_58MM
from .emulator import EscposEmulator, _PrintState, _TextSpan, _PrintLine, _PageBuffer

__all__ = [
    "PrinterPreset",
    "PRESET_EPSON_TM_T88",
    "PRESET_58MM",
    "EscposEmulator",
    # Internal models exposed for tests / advanced use
    "_PrintState",
    "_TextSpan",
    "_PrintLine",
    "_PageBuffer",
]

