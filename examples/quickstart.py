#!/usr/bin/env python3
# pylint: disable=line-too-long, missing-function-docstring, logging-fstring-interpolation
# pylint: disable=too-many-locals, broad-except, too-many-arguments,
# pylint: disable=raise-missing-from
"""
    py-star-tsp example

"""

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

