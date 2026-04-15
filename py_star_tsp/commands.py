"""
Low-level byte-sequence command builders for the Star TSP100 Graphic Mode.

All functions return ``bytes``.  Parameter values are validated against the
ranges defined in STAR Graphic Mode Command Specifications Rev. 2.31, and
``PrinterCommandError`` is raised for out-of-range values.
"""

from .exceptions import PrinterCommandError

# ---------------------------------------------------------------------------
# Control-character constants used throughout the spec
# ---------------------------------------------------------------------------
NUL = b"\x00"
BEL = b"\x07"
ETB = b"\x17"
EM  = b"\x19"
SUB = b"\x1a"
FS  = b"\x1c"
ESC = b"\x1b"
ACK = b"\x06"
SOH = b"\x01"
LF  = b"\x0a"
FF  = b"\x0c"
DC1 = b"\x11"
DC2 = b"\x12"
EOT = b"\x04"
GS  = b"\x1d"
RS  = b"\x1e"


def _byte(value: int, name: str, lo: int, hi: int) -> bytes:
    """Validate *value* is in [lo, hi] and return it as a single byte."""
    if not (lo <= value <= hi):
        raise PrinterCommandError(
            f"{name} must be in [{lo}, {hi}], got {value!r}"
        )
    return bytes([value])


# ===========================================================================
# 3-1-1  External Device Drive
# ===========================================================================

def set_external_drive_pulse(n1: int, n2: int) -> bytes:
    """ESC BEL n1 n2 — set external device drive pulse."""
    return (
        ESC + BEL
        + _byte(n1, "n1", 0, 255)
        + _byte(n2, "n2", 0, 255)
    )


def drive_external_device_1_bel() -> bytes:
    """BEL (0x07) — drive external device 1."""
    return BEL


def drive_external_device_1_fs() -> bytes:
    """FS (0x1C) — drive external device 1 (FS variant)."""
    return FS


def drive_external_device_2_sub() -> bytes:
    """SUB (0x1A) — drive external device 2."""
    return SUB


def drive_external_device_2_em() -> bytes:
    """EM (0x19) — drive external device 2 (EM variant)."""
    return EM


def ring_buzzer(m: int, n1: int, n2: int) -> bytes:
    """ESC GS BEL m n1 n2 — ring buzzer."""
    return (
        ESC + GS + BEL
        + _byte(m, "m", 0, 255)
        + _byte(n1, "n1", 0, 255)
        + _byte(n2, "n2", 0, 255)
    )


def set_buzzer_pulse(m: int, n1: int, n2: int) -> bytes:
    """ESC GS EM DC1 m n1 n2 — set buzzer pulse."""
    return (
        ESC + GS + EM + DC1
        + _byte(m, "m", 0, 255)
        + _byte(n1, "n1", 0, 255)
        + _byte(n2, "n2", 0, 255)
    )


def output_buzzer_pulse(m: int, n1: int, n2: int) -> bytes:
    """ESC GS EM DC2 m n1 n2 — output buzzer pulse."""
    return (
        ESC + GS + EM + DC2
        + _byte(m, "m", 0, 255)
        + _byte(n1, "n1", 0, 255)
        + _byte(n2, "n2", 0, 255)
    )


# ===========================================================================
# 3-1-2  Print Settings
# ===========================================================================

def set_print_area(n: int) -> bytes:
    """ESC RS A n — set print area."""
    return ESC + RS + b"A" + _byte(n, "n", 0, 255)


def set_print_density(n: int) -> bytes:
    """ESC RS d n — set print density (single-color mode).

    n=0: density +3 (darkest)
    n=1: density +2
    n=2: density +1
    n=3: density standard (default)
    n=4: density -1
    n=5: density -2
    n=6: density -3 (lightest)
    """
    return ESC + RS + b"d" + _byte(n, "n", 0, 255)


def set_print_speed(n: int) -> bytes:
    """ESC RS r n — set print speed (single-color mode).

    n=0: high speed
    n=1: mid-speed
    n=2: slow speed

    Speed settings are ignored in two-color and energy saving mode 1.
    """
    return ESC + RS + b"r" + _byte(n, "n", 0, 255)


def set_reduced_printing(h: int, v: int) -> bytes:
    """ESC GS c h v — set reduced printing."""
    return (
        ESC + GS + b"c"
        + _byte(h, "h", 0, 255)
        + _byte(v, "v", 0, 255)
    )


# ===========================================================================
# 3-1-3  Status
# ===========================================================================

def set_status_transmission(n: int) -> bytes:
    """ESC RS a n — set status transmission."""
    return ESC + RS + b"a" + _byte(n, "n", 0, 255)


def get_asb_status() -> bytes:
    """ESC ACK SOH — request ASB status."""
    return ESC + ACK + SOH


def update_etb_status() -> bytes:
    """ETB (0x17) — update ETB status."""
    return ETB


def clear_etb_counter(n: int) -> bytes:
    """ESC RS E n — clear ETB counter."""
    return ESC + RS + b"E" + _byte(n, "n", 0, 255)


def document_control(s: int, n1: int, n2: int) -> bytes:
    """ESC GS ETX s n1 n2 — document control."""
    return (
        ESC + GS + b"\x03"
        + _byte(s, "s", 0, 255)
        + _byte(n1, "n1", 0, 255)
        + _byte(n2, "n2", 0, 255)
    )


# ===========================================================================
# 3-1-4  Other
# ===========================================================================

def set_memory_switch(m: int, N: int, n1: int, n2: int, n3: int, n4: int) -> bytes:
    """ESC GS # m N n1 n2 n3 n4 LF NUL — set memory switch."""
    return (
        ESC + GS + b"#"
        + _byte(m, "m", 0, 255)
        + _byte(N, "N", 0, 255)
        + _byte(n1, "n1", 0, 255)
        + _byte(n2, "n2", 0, 255)
        + _byte(n3, "n3", 0, 255)
        + _byte(n4, "n4", 0, 255)
        + LF + NUL
    )


def reset_printer() -> bytes:
    """ESC ? LF NUL — reset printer."""
    return ESC + b"?" + LF + NUL


def set_led_blink(m: int, n1: int, n2: int) -> bytes:
    """ESC GS L DC1 m n1 n2 — set LED blink condition.

    m selects the LED:
      m=1: ERROR LED (Red)
      m=2: READY LED (Blue)

    n1: lit time in units of 20 ms (lit duration = 20 * n1 ms)
    n2: off time in units of 20 ms (off duration = 20 * n2 ms)

    When n1=0, the LED flash command (ESC GS L DC2) is ignored
    regardless of n2.  Not reset by a soft reset.
    """
    if m not in (1, 2, 49, 50):
        raise PrinterCommandError(
            f"m must be 1, 2, 49, or 50, got {m!r}"
        )
    return (
        ESC + GS + b"L" + DC1
        + bytes([m])
        + _byte(n1, "n1", 0, 255)
        + _byte(n2, "n2", 0, 255)
    )


def led_blink(m: int, n1: int, n2: int) -> bytes:
    """ESC GS L DC2 m n1 n2 — trigger LED blink.

    Uses the ON/OFF timing configured by ``set_led_blink`` (DC1).

    m selects the LED:
      m=1: ERROR LED (Red)
      m=2: READY LED (Blue)
      m=3: ERROR LED (Red) + READY LED (Blue)

    Repetitions = n2 * 256 + n1.
    If off time (from DC1) is 0, the LED stays continuously lit
    for n1 cycles (e.g. on=5s, off=0, n1=20 → lit for 100s).
    """
    if m not in (1, 2, 3, 49, 50, 51):
        raise PrinterCommandError(
            f"m must be 1, 2, 3, 49, 50, or 51, got {m!r}"
        )
    return (
        ESC + GS + b"L" + DC2
        + bytes([m])
        + _byte(n1, "n1", 1, 20)
        + _byte(n2, "n2", 0, 255)
    )


# ===========================================================================
# 3-2  Raster Graphics
# ===========================================================================

def raster_initialize() -> bytes:
    """ESC * r R — initialize raster mode."""
    return ESC + b"*rR"


def raster_enter() -> bytes:
    """ESC * r A — enter raster mode."""
    return ESC + b"*rA"


def raster_quit() -> bytes:
    """ESC * r B — quit raster mode."""
    return ESC + b"*rB"


def raster_clear() -> bytes:
    """ESC * r C — clear raster buffer."""
    return ESC + b"*rC"


def raster_set_eot_mode(n: int) -> bytes:
    """ESC * r E n NUL — set EOT mode."""
    return ESC + b"*rE" + _byte(n, "n", 0, 255) + NUL


_VALID_FF_MODES = {0, 1, 2, 3, 8, 9, 12, 13, 32, 33, 36, 37}


def raster_set_ff_mode(n: int) -> bytes:
    """ESC * r F n NUL — set raster FF (form feed) mode.

    Controls the action performed by the document end command (ESC FF NUL).
    n is sent as a decimal ASCII string (up to 255 digits).
    Ignored if raster data already exists in the image buffer.

    Default: n=13 (cutter model), n=3 (tear bar model).

    n=0:  set to default (FormFeed, Cut Feed, Cutter all default)
    n=1:  FormFeed OK (cutter + tear bar valid)
    n=2:  FormFeed OK, Cut Feed OK (cutter only)
    n=3:  FormFeed OK, Cut Feed = TearBar (tear bar only)
    n=8:  FormFeed OK, Cutter = Full Cut (cutter only)
    n=9:  FormFeed OK, Cut Feed OK, Cutter = Full Cut (cutter only)
    n=12: FormFeed OK, Cutter = Partial Cut (cutter only)
    n=13: FormFeed OK, Cut Feed OK, Cutter = Partial Cut (cutter only)
    n=32, 33, 36, 37: invalid for both models
    """
    if n not in _VALID_FF_MODES:
        raise PrinterCommandError(
            f"n must be one of {sorted(_VALID_FF_MODES)}, got {n!r}"
        )
    return ESC + b"*rF" + str(n).encode("ascii") + NUL


def raster_set_page_length(n: int) -> bytes:
    """ESC * r P n NUL — set raster page length.

    n is sent as a decimal ASCII string (up to 255 digits).
    Ignored if raster data already exists in the image buffer.

    n=0: continuous printing mode (max 64000 dots)
    200 ≤ n ≤ 64000: specified page length in dots
         (TSP100IIU max is 32000)
    """
    if n != 0 and not (200 <= n <= 64000):
        raise PrinterCommandError(
            f"n must be 0 or in [200, 64000], got {n!r}"
        )
    return ESC + b"*rP" + str(n).encode("ascii") + NUL


def raster_set_print_quality(n: int) -> bytes:
    """ESC * r Q n NUL — set raster print quality.

    n is sent as a decimal ASCII string (up to 255 digits).
    Ignored if raster data already exists in the image buffer.

    n=0: high-speed printing specified (default)
    n=1: normal print quality
    n=2: high print quality
    """
    if not (0 <= n <= 2):
        raise PrinterCommandError(
            f"n must be in [0, 2], got {n!r}"
        )
    return ESC + b"*rQ" + str(n).encode("ascii") + NUL


def raster_set_left_margin(n: int) -> bytes:
    """ESC * r m l n NUL — set left margin."""
    return ESC + b"*rml" + _byte(n, "n", 0, 255) + NUL


def raster_set_right_margin(n: int) -> bytes:
    """ESC * r m r n NUL — set right margin."""
    return ESC + b"*rmr" + _byte(n, "n", 0, 255) + NUL


def raster_set_top_margin(n: int) -> bytes:
    """ESC * r t n NUL — set top margin."""
    return ESC + b"*rt" + _byte(n, "n", 0, 255) + NUL


def raster_set_color(n: int) -> bytes:
    """ESC * r K n NUL — set raster color."""
    return ESC + b"*rK" + _byte(n, "n", 0, 255) + NUL


def raster_transfer_auto_lf(n1: int, n2: int, data: bytes) -> bytes:
    """b n1 n2 data — transfer raster data with automatic line feed.

    Sends (n1 + n2 * 256) bytes of binary raster data.
    After deploying data to the one-dot-column image buffer, performs
    an automatic line feed and moves to the left margin of the next line.

    Data beyond the current print area is cut off.
    Data is OR-merged with existing image buffer contents.

    k = n1 + n2 * 256 (must be ≥ 1), len(data) must equal k.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise PrinterCommandError("data must be bytes")
    k = n1 + n2 * 256
    if k < 1:
        raise PrinterCommandError(
            f"k (n1 + n2 * 256) must be >= 1, got {k}"
        )
    if len(data) != k:
        raise PrinterCommandError(
            f"data length must equal n1 + n2 * 256 ({k}), got {len(data)}"
        )
    return (
        b"b"
        + _byte(n1, "n1", 0, 255)
        + _byte(n2, "n2", 0, 255)
        + bytes(data)
    )


def raster_transfer(n1: int, n2: int, data: bytes) -> bytes:
    """k n1 n2 data — transfer raster line (no automatic LF)."""
    if not isinstance(data, (bytes, bytearray)):
        raise PrinterCommandError("data must be bytes")
    return (
        b"k"
        + _byte(n1, "n1", 0, 255)
        + _byte(n2, "n2", 0, 255)
        + bytes(data)
    )


def raster_vertical_move(n: int) -> bytes:
    """ESC * r Y n NUL — move position in the vertical direction.

    Moves the raster position by n dots vertically (line break).
    n is sent as a decimal ASCII string (up to 255 digits).

    If the movement exceeds the page:
    - Continuous mode: n is clamped to the maximum page length.
    - Specified page length mode: prints up to end of page,
      overflow is treated as the beginning of the next page.
    """
    if n < 0:
        raise PrinterCommandError(f"n must be >= 0, got {n!r}")
    return ESC + b"*rY" + str(n).encode("ascii") + NUL


def raster_execute_ff() -> bytes:
    """ESC FF NUL — execute form feed."""
    return ESC + FF + NUL


def raster_execute_eot() -> bytes:
    """ESC FF EOT — execute EOT."""
    return ESC + FF + EOT


def raster_start_block() -> bytes:
    """ESC * r a — start raster block."""
    return ESC + b"*ra"


def raster_end_block() -> bytes:
    """ESC * r b — end raster block."""
    return ESC + b"*rb"


def raster_set_em_mode(n: int) -> bytes:
    """ESC * r e n NUL — set EM mode."""
    return ESC + b"*re" + _byte(n, "n", 0, 255) + NUL


def raster_execute_em() -> bytes:
    """ESC FF EM — execute EM."""
    return ESC + FF + EM


def raster_execute_lf() -> bytes:
    """ESC FF LF — execute LF."""
    return ESC + FF + LF


# ===========================================================================
# 3-3  USB Interface
# ===========================================================================

def register_usb_serial(data: bytes) -> bytes:
    """ESC # # W n , d1 d2 ... dk LF NUL — register USB serial number."""
    if not isinstance(data, (bytes, bytearray)):
        raise PrinterCommandError("data must be bytes")
    data = bytes(data)
    n = len(data)
    if n > 255:
        raise PrinterCommandError("data length must not exceed 255 bytes")
    return ESC + b"##W" + bytes([n]) + b"," + data + LF + NUL


# ===========================================================================
# 3-4  Print Mode
# ===========================================================================

def select_print_mode(n: int) -> bytes:
    """ESC RS C n — select print mode."""
    return ESC + RS + b"C" + _byte(n, "n", 0, 255)


def select_print_startup(n: int) -> bytes:
    """ESC RS S n — select print startup."""
    return ESC + RS + b"S" + _byte(n, "n", 0, 255)


# ===========================================================================
# 3-5  Printer Information
# ===========================================================================

def register_printer_info(n: int, m: int, data: bytes) -> bytes:
    """ESC GS ( S n m [d1...dm] — register printer information."""
    if not isinstance(data, (bytes, bytearray)):
        raise PrinterCommandError("data must be bytes")
    return (
        ESC + GS + b"(S"
        + _byte(n, "n", 0, 255)
        + _byte(m, "m", 0, 255)
        + bytes(data)
    )


def send_printer_info(pL: int, pH: int, fn: int) -> bytes:
    """ESC GS ) I pL pH fn — send printer information."""
    return (
        ESC + GS + b")I"
        + _byte(pL, "pL", 0, 255)
        + _byte(pH, "pH", 0, 255)
        + _byte(fn, "fn", 0, 255)
    )


def inquire_printer_version() -> bytes:
    """ESC # * LF NUL — inquire printer version."""
    return ESC + b"#*" + LF + NUL


# ===========================================================================
# 3-6  Customer Display
# ===========================================================================

def customer_display_send(data: bytes) -> bytes:
    """ESC GS B @ [data] — send data to customer display."""
    if not isinstance(data, (bytes, bytearray)):
        raise PrinterCommandError("data must be bytes")
    return ESC + GS + b"B@" + bytes(data)


def customer_display_status_request() -> bytes:
    """ESC RS B A — request customer display status."""
    return ESC + RS + b"BA"


def customer_display_data_request() -> bytes:
    """ESC GS B B — request customer display data."""
    return ESC + GS + b"BB"


def customer_display_buffer_clear() -> bytes:
    """ESC GS B C — clear customer display buffer."""
    return ESC + GS + b"BC"
