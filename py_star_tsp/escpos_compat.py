"""
ESC/POS-compatible plain-text printing for Star TSP100.

The TSP100 series operates exclusively in **Graphic (raster) Mode** and
does *not* natively support the ESC/POS command set used by Epson-style
thermal printers.  This module provides an *emulation* layer that
accepts plain ASCII/UTF-8 text and renders it as a raster image before
sending it to the printer.

Compatibility Notes
-------------------
* **Text encoding** – Any text that can be rendered by the selected font
  is supported (including full Unicode).  Traditional ESC/POS printers
  are limited to code-page character sets; this emulation has no such
  limitation.
* **Inline ESC/POS control codes** – Escape sequences such as
  ``ESC E 1`` (bold on) or ``ESC ! n`` (select print mode) are **not**
  interpreted.  Pass styling options through the keyword arguments of
  :func:`render_text` / :meth:`~py_star_tsp.printer.StarTSP.print_text`
  instead.
* **Line width** – The number of characters per line depends on the
  chosen font and size.  At the default 384-pixel width a 20 px
  monospace font yields roughly 38–42 characters per line, comparable
  to a 40-column ESC/POS receipt printer.
* **Cut / cash-drawer** – Use :meth:`StarTSP.drive_drawer` and the
  raster form-feed command rather than ESC/POS ``GS V`` (cut).
* **Barcode / QR** – Not covered by this text emulation.  Generate
  barcode images with a library such as ``python-barcode`` or
  ``qrcode`` and print them via :meth:`StarTSP.print_raster_image`.
"""
