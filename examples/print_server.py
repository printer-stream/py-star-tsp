#!/usr/bin/env python3
"""
Example of a simple print server.

Listens for ESC/POS raster data and prints it
using a Star TSP100 printer.  Run this script
and then send ESC/POS data to localhost:9100
(e.g. using netcat or a custom print source)
to trigger a print.

Printer preset
--------------
The preset controls the paper width, DPI, and font metrics used to
render the incoming ESC/POS byte stream into raster dots.  Choose the
preset that matches the Epson printer you are emulating:

    PRESET_EPSON_TM_T88  — 80 mm paper, 576 dots wide (default)
    PRESET_58MM          — 58 mm paper, 384 dots wide

You can also customise any field on-the-fly with .copy():

    preset = PRESET_EPSON_TM_T88.copy(print_width_dots=512, dpi=180)

"""
import asyncio
import logging

from py_star_tsp import StarTSP100
from py_star_tsp.escpos import PRESET_EPSON_TM_T88, PRESET_58MM  # noqa: F401
from py_star_tsp.server import EscposServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

# ── Choose your preset ────────────────────────────────────────────────────────
# Uncomment the line that matches the Epson printer you are emulating, or
# call .copy(**overrides) to tweak individual parameters.

preset = PRESET_EPSON_TM_T88            # 80 mm paper (default)
# preset = PRESET_58MM                  # 58 mm paper
# preset = PRESET_EPSON_TM_T88.copy(font_a_chars_per_line=48)  # custom
# ─────────────────────────────────────────────────────────────────────────────


def on_print(raster_set):
    with StarTSP100() as printer:
        for block in raster_set.blocks:
            printer.add_raster(block)
        printer.print()


async def main():
    server = EscposServer(preset=preset, on_print=on_print)
    await server.start()


asyncio.run(main())
