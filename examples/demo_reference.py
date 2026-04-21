import logging

import py_star_tsp
from py_star_tsp.ref_page import (
    print_bar_hit_right,
    print_bar_widths,
    print_kittens,
    print_kittens_kittens,
    print_text_cpi_1inch,
    print_text_cpi_2inch,
    print_text_cpi_05inch,
    print_text_sizes,
    print_timestamp_bar
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("demo")

logger.info("py-star-tsp demo - Star TSP100 in Graphic Mode")

printer = py_star_tsp.StarTSP100()
printer.print_speed = 0
printer.print_density = 3
printer.raster_print_quality = 0

printer.find_device()
printer.open()
printer.get_status()

printer.cut = False

print_timestamp_bar(printer)
print_kittens_kittens(printer)
printer.print()

print_text_sizes(printer, font_name="orator_15cpi")
printer.print()

printer.add_text(f"\n\nKITTIES:\n", font_size=15)
print_kittens(printer, invert=True)

print_bar_widths(printer)
printer.add_bar(width=0, height=30)

print_kittens(printer, invert=True)
printer.add_bar(width=0, height=15)
printer.print()

print_text_cpi_2inch(printer, font_name="orator_15cpi")
printer.add_bar(width=0, height=15)

print_text_cpi_1inch(printer, font_name="orator_15cpi")
printer.add_bar(width=0, height=15)

print_text_cpi_05inch(printer, font_name="orator_15cpi")
printer.add_bar(width=0, height=15)

print_bar_hit_right(printer)

printer.save_rendered("demo_output.bmp")

printer.cut = True
printer.print()
printer.close()
