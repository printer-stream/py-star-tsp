"""TCP server that emulates a raw ESC/POS receipt printer.

See :mod:`py_star_tsp.server.escpos_server` for the full implementation.
"""

from .escpos_server import EscposServer

__all__ = ["EscposServer"]

