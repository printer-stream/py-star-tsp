#!/usr/bin/env python3
"""
Using python-escpos with py-star-tsp's print server.

python-escpos (pip install python-escpos) is a popular library for
generating ESC/POS receipt content.  It normally targets Epson printers
directly over USB or the network, but Star TSP100 printers don't support
native ESC/POS — that's exactly the problem py-star-tsp solves.

The trick: point python-escpos at our EscposServer (localhost:9100) instead
of a real Epson printer.  The server receives the raw ESC/POS byte stream,
renders it to raster, and forwards the result to your Star TSP100.

                 python-escpos                py-star-tsp
    ┌──────────────────────────┐   TCP    ┌──────────────────────────┐
    │ Network("127.0.0.1")     │─────────▶│ EscposServer :9100       │
    │  .text() / .image() etc. │          │  EscposEmulator → raster │
    └──────────────────────────┘          │  StarTSP100.print()      │
                                          └──────────────────────────┘

Requirements
------------
    pip install python-escpos

Run the print server first (in a separate terminal):
    python examples/print_server.py

Then run this script:
    python examples/python_escpos_client.py
"""

import logging
import os

from escpos.printer import Network, Dummy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

# ── Connect to the print server ───────────────────────────────────────────────
# Override with environment variables when running in production:
#   ESCPOS_SERVER_HOST=192.168.1.10 ESCPOS_SERVER_PORT=9100 python ...
SERVER_HOST = os.environ.get("ESCPOS_SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("ESCPOS_SERVER_PORT", "9100"))


# ---------------------------------------------------------------------------
# The Jolly Bailiff — faithful reproduction of the sample receipt
# ---------------------------------------------------------------------------
# Paper: 80 mm / 42 chars per line (Font A, default)
# Layout constants

_W = 42          # characters per line (Font A, 80 mm paper)
_DOTS = "." * (_W)          # ". . . . . …"  (42 chars)
_EQUALS = "=" * _W


def _row(left: str, right: str, width: int = _W) -> str:
    """Return a left+right line padded to *width* chars."""
    gap = width - len(left) - len(right)
    return left + " " * max(1, gap) + right + "\n"


def jolly_bailiff_receipt():
    """Reproduce the 'The Jolly Bailiff' receipt shown in the documentation."""
    d = Dummy()
    d.set_with_default()  # reset all print-mode flags to defaults

    # ── Header ───────────────────────────────────────────────────────────────
    d.set(align="center", bold=True)
    d.text("The Jolly Bailiff\n")
    d.set(align="center", bold=False)
    d.text("Frying Pan Alley 12\n")
    d.text("DY9 9TN Bell End\n")
    d.text("Worcestershire, UK\n")
    d.text("Org Nr: 30922888293\n")

    d.set(align="left")
    d.text(_DOTS + "\n")

    # ── Table / session info ─────────────────────────────────────────────────
    d.set(align="center")
    d.text("Bord Nr: 909\n")
    d.set(align="left")
    d.text(_DOTS + "\n")

    d.text("Datum: 2023-05-21 21:10:13\n")
    d.text("Kvittonr: 01-00310324\n")
    d.text("Kassör: Kassör 1 (1011)\n")
    d.text(_DOTS + "\n")

    # ── Line items ───────────────────────────────────────────────────────────
    d.text(_row("En God Öl", "624,00"))
    d.text("  12 st * 52,00 kr/st\n")
    d.text(_EQUALS + "\n")

    # Item count
    d.text(_row("Antal art.", "12"))
    d.text("\n")

    # ── Grand total ──────────────────────────────────────────────────────────
    d.set(bold=True, double_width=True)
    # double_width gives the line twice the character width without
    # extra height; set_with_default() sends ESC ! 0x00 to clear all flags.
    d.text("ATT BETALA  624,00\n")
    d.set_with_default()
    d.text("\n")

    # ── Payment lines ────────────────────────────────────────────────────────
    d.text(_row("KORT", "684,00"))
    d.text(_row("(EXTRA", "60,00)"))
    d.text("\n")

    # ── Tax table ────────────────────────────────────────────────────────────
    d.text(_DOTS + "\n")
    # Fixed-width columns: Moms(6) BeLopp(8) Netto(8) Brutto(8)
    d.text(f"{'Moms':<6}{'BeLopp':<9}{'Netto':<9}{'Brutto'}\n")
    d.text(f"{'25%':<6}{'20,80':<9}{'83,20':<9}{'624,00'}\n")
    d.text(_DOTS + "\n")

    # ── Transaction reference ────────────────────────────────────────────────
    d.set(align="center")
    d.text("RIHTT0D0000044371\n")
    d.set(align="left")

    # ── Card / payment details ───────────────────────────────────────────────
    # Two-column lines: left label, right value
    d.text(_row("TOTAL:", "664,00 kr"))
    d.text(_row("PAN: **** **** **** 9329", "Debit Visa"))
    d.text(_row("AID: A0000000010302", "Betalning"))
    d.text(_row("2023-05-21 21:09:56", "Kontaktlös"))
    d.text("Transaktion: 0000084959839\n")
    d.text("Auktorisation: 520124\n")
    d.text("Butik: 62230593\n")
    d.text("TermId: 00000001\n")
    d.text("APPROVED\n")
    d.text(_DOTS + "\n")

    # ── QR code ──────────────────────────────────────────────────────────────
    d.set(align="center")
    d.qr("0000084959839", size=6)
    d.text("\n")

    # ── Barcode ──────────────────────────────────────────────────────────────
    d.set(align="center")
    # force_software=True makes python-escpos render the barcode as a raster
    # image (GS ( L) rather than sending a hardware GS k command that the
    # Star TSP100 cannot interpret natively.
    d.barcode("0000084959839", "CODE39", height=64, width=2, pos="BELOW", force_software=True)
    d.text("\n")

    # ── Footer ───────────────────────────────────────────────────────────────
    d.set(align="center", bold=False)
    d.text("The Jolly Bailiff\n")
    d.text("Tack för besöket\n")
    d.text("Välkommen åter!\n")
    d.set(align="center", bold=True)
    d.text("Spara kvitto\n")
    d.set(bold=False)

    d.cut()

    # Send to print server in one shot
    p = Network(SERVER_HOST, port=SERVER_PORT)
    p._raw(d.output)
    p.close()


def preprocessed_receipt():
    """
    Build the receipt into a Dummy (in-memory) printer first, then send
    the raw bytes in a single TCP write.  Useful when you want to prepare
    content ahead of time or send the same job to multiple printers.
    """
    d = Dummy()

    d.set(align="center", bold=True)
    d.text("PREPROCESSED RECEIPT\n")
    d.set(align="left", bold=False)
    d.text("Built with Dummy, sent as one blob.\n\n")
    d.text("Item 1 ............... $9.99\n")
    d.text("Item 2 ............... $4.99\n\n")
    d.set(bold=True)
    d.text("Total ............... $14.98\n")
    d.cut()

    # d.output holds the complete raw ESC/POS byte string
    raw: bytes = d.output

    # Open a Network printer just for the raw write
    p = Network(SERVER_HOST, port=SERVER_PORT)
    p._raw(raw)
    p.close()


if __name__ == "__main__":
    print("Sending The Jolly Bailiff receipt …")
    jolly_bailiff_receipt()
    print("Done.")
