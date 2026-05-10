"""ESC/POS state models and emulator engine."""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Pillow is required. Install it with: pip install Pillow"
    ) from exc

from py_star_tsp.raster import RasterImage, RasterSet
from .presets import PrinterPreset, PRESET_EPSON_TM_T88, _BUNDLED_FONT

logger = logging.getLogger("py_star_tsp.escpos")

# ---------------------------------------------------------------------------
# Control-byte constants
# ---------------------------------------------------------------------------
_NUL = 0x00
_HT  = 0x09  # Horizontal tab
_LF  = 0x0A  # Line feed
_FF  = 0x0C  # Form feed / cut
_CR  = 0x0D  # Carriage return (treated as LF)
_CAN = 0x18  # Cancel line buffer
_ESC = 0x1B  # Escape
_FS  = 0x1C  # File separator (Kanji commands)
_GS  = 0x1D  # Group separator
_DLE = 0x10  # Data link escape (status commands)

# ESC t n → Python codec name.  Entries for the most common ESC/POS tables.
_CODE_TABLE_CODECS: Dict[int, str] = {
    0:  "cp437",   # PC437  — US (default)
    1:  "cp850",   # PC850  — Multilingual
    2:  "cp860",   # PC860  — Portuguese
    3:  "cp863",   # PC863  — Canadian French
    4:  "cp865",   # PC865  — Nordic
    5:  "cp858",   # PC858  — Multilingual with Euro
    16: "cp1252",  # WPC1252 — Western European
    17: "cp1253",  # WPC1253 — Greek
    18: "cp1254",  # WPC1254 — Turkish
    19: "cp1255",  # WPC1255 — Hebrew
    20: "cp1256",  # WPC1256 — Arabic
    21: "cp1257",  # WPC1257 — Baltic
    22: "cp1258",  # WPC1258 — Vietnamese
}


# ===========================================================================
# Internal state objects
# ===========================================================================

@dataclass
class _PrintState:
    """Mutable snapshot of ESC/POS printer state."""

    font: int = 0               # 0 = Font A, 1 = Font B
    bold: bool = False          # ESC E / ESC G
    double_strike: bool = False # ESC G
    underline: int = 0          # 0=off, 1=1-dot, 2=2-dot
    align: int = 0              # 0=left, 1=centre, 2=right
    char_size_w: int = 1        # 1–8 width magnification
    char_size_h: int = 1        # 1–8 height magnification
    line_spacing: Optional[int] = None   # None → use preset default
    upside_down: bool = False
    invert: bool = False        # white-on-black reverse
    char_code_table: int = 0
    international_charset: int = 0

    def reset(self) -> None:
        """Restore power-on defaults."""
        self.font = 0
        self.bold = False
        self.double_strike = False
        self.underline = 0
        self.align = 0
        self.char_size_w = 1
        self.char_size_h = 1
        self.line_spacing = None
        self.upside_down = False
        self.invert = False
        self.char_code_table = 0
        self.international_charset = 0

    def snapshot(self) -> "_PrintState":
        return copy.copy(self)


@dataclass
class _TextSpan:
    """A run of text characters sharing identical formatting."""

    text: str = ""
    font: int = 0
    bold: bool = False
    double_strike: bool = False
    underline: int = 0
    char_size_w: int = 1
    char_size_h: int = 1
    invert: bool = False

    def matches(self, state: _PrintState) -> bool:
        """Return True if *state* has the same formatting as this span."""
        return (
            self.font         == state.font
            and self.bold          == state.bold
            and self.double_strike == state.double_strike
            and self.underline     == state.underline
            and self.char_size_w   == state.char_size_w
            and self.char_size_h   == state.char_size_h
            and self.invert        == state.invert
        )


@dataclass
class _PrintLine:
    """A completed logical line, ready to render."""

    spans: List[_TextSpan] = field(default_factory=list)
    align: int = 0
    line_spacing: Optional[int] = None
    extra_feed_dots: int = 0   # additional blank vertical space (ESC J)
    image: Optional[Image.Image] = None  # embedded raster image (GS v 0)


@dataclass
class _PageBuffer:
    """Content buffer for Page Mode (ESC L)."""

    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    direction: int = 0  # 0=L→R, 1=B→T, 2=R→L, 3=T→B
    lines: List[_PrintLine] = field(default_factory=list)


# ===========================================================================
# EscposEmulator
# ===========================================================================

class EscposEmulator:
    """Parse and render an ESC/POS byte stream for a Star TSP100.

    Args:
        preset: Physical/typographic parameters of the emulated printer.
            Defaults to :data:`PRESET_EPSON_TM_T88`.
        on_print: Optional callback invoked with a
            :class:`~py_star_tsp.raster.RasterSet` each time a print
            trigger is encountered (``GS V``, ``FF``).  If ``None``,
            the rendered job is returned from :meth:`flush` / internal
            helpers only.

    Example::

        def send_to_printer(rs: RasterSet) -> None:
            with StarTSP100() as p:
                for block in rs.blocks:
                    p.add_raster(block)
                p.print()

        emulator = EscposEmulator(on_print=send_to_printer)
        emulator.feed(raw_escpos_bytes)
        emulator.flush()  # flush any trailing content
    """

    def __init__(
        self,
        preset: Optional[PrinterPreset] = None,
        on_print: Optional[Callable[[RasterSet], None]] = None,
    ) -> None:
        self.preset = preset or PRESET_EPSON_TM_T88
        self.on_print = on_print

        self._state = _PrintState()
        self._current_spans: List[_TextSpan] = []
        self._lines: List[_PrintLine] = []

        # Page mode
        self._page_mode: bool = False
        self._page_buffer: Optional[_PageBuffer] = None

        # Font metric cache: (font_path, target_char_h) → PIL font
        self._font_cache: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}

        # Prime the generator-based parser
        self._gen = self._parse_gen()
        next(self._gen)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def feed(self, data: bytes) -> None:
        """Feed raw ESC/POS bytes into the emulator.

        Bytes accumulate across calls; partial command sequences are
        completed on the next :meth:`feed` invocation.
        """
        logger.debug("feed: %d byte(s)", len(data))
        for b in data:
            try:
                self._gen.send(b)
            except StopIteration:
                # Re-prime if the generator somehow exhausts (should not happen)
                self._gen = self._parse_gen()
                next(self._gen)

    def flush(self) -> Optional[RasterSet]:
        """Finalise any buffered content and return a :class:`~py_star_tsp.raster.RasterSet`.

        Useful at the end of a print job (e.g. when a TCP connection closes)
        to ensure trailing lines without an explicit cut command are rendered.
        """
        pending_spans = bool(self._current_spans)
        pending_lines = len(self._lines)
        if pending_spans:
            self._do_line_feed()
        if self._lines:
            logger.info(
                "flush: %d line(s) buffered (+ %s trailing span) — printing",
                pending_lines,
                "1" if pending_spans else "no",
            )
            return self._do_print(trigger="flush")
        logger.debug("flush: nothing buffered — no output")
        return None

    def render(self) -> RasterSet:
        """Render all buffered lines to a :class:`~py_star_tsp.raster.RasterSet`.

        Does **not** clear the line buffer.  Use :meth:`flush` to render
        and clear in one operation.
        """
        return self._render_lines(self._lines)

    # ------------------------------------------------------------------
    # Generator-based ESC/POS parser
    # ------------------------------------------------------------------

    def _parse_gen(self):  # type: ignore[return]
        """Yield-based byte-stream parser.  One ``send()`` call per byte."""
        while True:
            b = yield

            # ── Single-byte controls ──────────────────────────────────
            if b in (_LF, _CR):
                self._do_line_feed()

            elif b == _FF:
                self._do_line_feed()
                self._do_print(trigger="FF")

            elif b == _CAN:
                self._current_spans.clear()

            elif b == _HT:
                self._do_tab()

            # ── ESC sequences ─────────────────────────────────────────
            elif b == _ESC:
                b2 = yield

                if b2 == 0x40:      # ESC @ — Initialize
                    self._do_init()

                elif b2 == 0x61:    # ESC a n — Justification
                    n = yield
                    self._state.align = n & 0x03

                elif b2 == 0x45:    # ESC E n — Emphasised (bold)
                    n = yield
                    self._state.bold = bool(n & 0x01)

                elif b2 == 0x47:    # ESC G n — Double-strike
                    n = yield
                    self._state.double_strike = bool(n & 0x01)

                elif b2 == 0x2D:    # ESC - n — Underline
                    n = yield
                    self._state.underline = n & 0x03

                elif b2 == 0x4D:    # ESC M n — Font
                    n = yield
                    self._state.font = n & 0x01

                elif b2 == 0x21:    # ESC ! n — Print mode (compound)
                    n = yield
                    self._state.font = n & 0x01
                    self._state.bold = bool(n & 0x08)
                    self._state.char_size_w = 2 if (n & 0x20) else 1
                    self._state.char_size_h = 2 if (n & 0x10) else 1
                    self._state.underline = 1 if (n & 0x80) else 0

                elif b2 == 0x32:    # ESC 2 — Default line spacing
                    self._state.line_spacing = None

                elif b2 == 0x33:    # ESC 3 n — Set line spacing
                    n = yield
                    self._state.line_spacing = n

                elif b2 == 0x64:    # ESC d n — Print & feed n lines
                    n = yield
                    # Only finalise if there is buffered content
                    if self._current_spans:
                        self._do_line_feed()
                    for _ in range(n):
                        blank = _PrintLine(
                            spans=[],
                            align=self._state.align,
                            line_spacing=self._state.line_spacing,
                        )
                        self._lines.append(blank)

                elif b2 == 0x4A:    # ESC J n — Print & feed n dots
                    n = yield
                    if self._current_spans:
                        self._do_line_feed()
                        self._lines[-1].extra_feed_dots = n
                    elif self._lines:
                        self._lines[-1].extra_feed_dots += n
                    else:
                        self._lines.append(_PrintLine(extra_feed_dots=n))

                elif b2 == 0x70:    # ESC p m t1 t2 — Cash-drawer pulse
                    yield; yield; yield   # consume 3 params

                elif b2 == 0x52:    # ESC R n — International charset
                    n = yield
                    self._state.international_charset = n

                elif b2 == 0x74:    # ESC t n — Code table
                    n = yield
                    self._state.char_code_table = n

                elif b2 == 0x7B:    # ESC { n — Upside-down
                    n = yield
                    self._state.upside_down = bool(n & 0x01)

                elif b2 == 0x56:    # ESC V n — Rotate 90° (deprecated)
                    yield               # consume; not rendered

                elif b2 == 0x05:    # ESC 5 n — CR behaviour
                    yield               # consume; we always treat CR as LF

                elif b2 == 0x4C:    # ESC L — Page mode
                    self._do_page_mode()

                elif b2 == 0x53:    # ESC S — Standard mode
                    self._do_standard_mode()

                elif b2 == 0x57:    # ESC W xL xH yL yH dxL dxH dyL dyH
                    params: List[int] = []
                    for _ in range(8):
                        params.append((yield))
                    self._set_page_area(*params)

                elif b2 == 0x54:    # ESC T n — Print direction
                    n = yield
                    if self._page_buffer is not None:
                        self._page_buffer.direction = n & 0x03

                else:
                    logger.debug("Unknown ESC 0x%02X — ignored", b2)

            # ── GS sequences ─────────────────────────────────────────
            elif b == _GS:
                b2 = yield

                if b2 == 0x21:      # GS ! n — Character size
                    n = yield
                    self._state.char_size_w = (n & 0x07) + 1
                    self._state.char_size_h = ((n >> 4) & 0x07) + 1

                elif b2 == 0x42:    # GS B n — Reverse (white-on-black)
                    n = yield
                    self._state.invert = bool(n & 0x01)

                elif b2 == 0x56:    # GS V m [n] — Cut paper
                    m = yield
                    if m in (0x41, 0x42, 0x61, 0x62):
                        yield       # consume feed distance
                    self._do_line_feed()
                    self._do_print(trigger="GS V (cut)")

                elif b2 == 0x61:    # GS a n — Enable ASB
                    yield           # consume; status reporting not emulated

                elif b2 == 0x4C:    # GS L nL nH — Left margin
                    yield; yield

                elif b2 == 0x57:    # GS W nL nH — Print area width
                    yield; yield

                elif b2 == 0x50:    # GS P x y — Dots per mm
                    yield; yield

                elif b2 == 0x54:    # GS T n — Transmission of status
                    yield

                elif b2 == 0x66:    # GS f n — Font for HRI chars
                    yield

                elif b2 == 0x68:    # GS h n — Barcode height
                    yield

                elif b2 == 0x77:    # GS w n — Barcode width
                    yield

                elif b2 == 0x48:    # GS H n — HRI character position
                    yield

                elif b2 == 0x76:    # GS v 0 — Print raster bit image
                    _sub = yield    # always 0x30 ('0'); part of command opcode
                    m    = yield    # mode: 0=normal 1=2×W 2=2×H 3=4×
                    xL   = yield
                    xH   = yield
                    yL   = yield
                    yH   = yield
                    width_bytes = xL + xH * 256
                    height_px   = yL + yH * 256
                    total_bytes = width_bytes * height_px
                    raw = bytearray(total_bytes)
                    for _i in range(total_bytes):
                        raw[_i] = (yield)
                    logger.debug(
                        "GS v 0: %dx%d px mode=%d (%d bytes)",
                        width_bytes * 8, height_px, m, total_bytes,
                    )
                    if total_bytes > 0:
                        # ESC/POS: bit=1 → black dot; PIL '1': bit=1 → white.
                        # Convert then invert so dots appear black in 'L' image.
                        img_1 = Image.frombytes(
                            "1", (width_bytes * 8, height_px), bytes(raw)
                        )
                        img_l = img_1.convert("L").point(lambda x: 255 - x)
                        if m == 1:
                            img_l = img_l.resize(
                                (img_l.width * 2, img_l.height), Image.NEAREST
                            )
                        elif m == 2:
                            img_l = img_l.resize(
                                (img_l.width, img_l.height * 2), Image.NEAREST
                            )
                        elif m == 3:
                            img_l = img_l.resize(
                                (img_l.width * 2, img_l.height * 2), Image.NEAREST
                            )
                        if self._current_spans:
                            self._do_line_feed()
                        img_line = _PrintLine(image=img_l, align=self._state.align)
                        if self._page_mode and self._page_buffer is not None:
                            self._page_buffer.lines.append(img_line)
                        else:
                            self._lines.append(img_line)

                elif b2 == 0x6B:    # GS k — Barcode (consume, not rendered)
                    m = yield
                    logger.debug("GS k barcode command (m=0x%02X) — skipped", m)
                    if m <= 6:      # old format: terminated by NUL
                        while True:
                            c = yield
                            if c == _NUL:
                                break
                    else:           # new format: length-prefixed
                        n = yield
                        for _ in range(n):
                            yield

                elif b2 == 0x28:    # GS ( X — extended commands
                    sub = yield     # sub-command: 0x4C=L (graphics), 0x6B=k (native QR)
                    pL = yield
                    pH = yield
                    length = pL + pH * 256
                    if sub == 0x4C:  # GS ( L — store / print raster graphics
                        _buf: List[int] = []
                        for _ in range(length):
                            _buf.append((yield))
                        # fn=0x70: store raster image — sent by python-escpos
                        # software renderer for barcodes and QR codes.
                        # Payload: m(0x30) fn(0x70) a(0x30) bx by c xL xH yL yH data...
                        if len(_buf) >= 10 and _buf[0] == 0x30 and _buf[1] == 0x70:
                            bx = max(1, _buf[3])
                            by = max(1, _buf[4])
                            width_dots  = _buf[6] + _buf[7] * 256
                            height_dots = _buf[8] + _buf[9] * 256
                            width_bytes = (width_dots + 7) // 8
                            img_data_len = width_bytes * height_dots
                            if img_data_len > 0 and len(_buf) >= 10 + img_data_len:
                                img_bytes = bytes(_buf[10:10 + img_data_len])
                                img_1 = Image.frombytes(
                                    "1", (width_dots, height_dots),
                                    img_bytes, "raw", "1",
                                )
                                img_l = img_1.convert("L").point(lambda v: 255 - v)
                                if bx != 1 or by != 1:
                                    img_l = img_l.resize(
                                        (img_l.width * bx, img_l.height * by),
                                        Image.NEAREST,
                                    )
                                if self._current_spans:
                                    self._do_line_feed()
                                img_line = _PrintLine(
                                    image=img_l, align=self._state.align
                                )
                                if self._page_mode and self._page_buffer is not None:
                                    self._page_buffer.lines.append(img_line)
                                else:
                                    self._lines.append(img_line)
                                logger.debug(
                                    "GS ( L fn=0x70: %dx%d dots → image inserted",
                                    width_dots, height_dots,
                                )
                        # fn=0x45 (print stored image) and others: data already consumed
                    else:
                        logger.debug(
                            "GS ( 0x%02X length=%d — skipped", sub, length
                        )
                        for _ in range(length):
                            yield

                else:
                    logger.debug("Unknown GS 0x%02X — ignored", b2)

            # ── FS sequences (Kanji / Chinese) ───────────────────────
            elif b == _FS:
                b2 = yield
                if b2 == 0x43:      # FS C n — Kanji mode select
                    yield
                # FS & and FS . have no parameters; others skipped

            # ── DLE sequences (real-time status) ─────────────────────
            elif b == _DLE:
                b2 = yield
                if b2 in (0x04, 0x05):
                    yield           # consume parameter

            # ── Printable characters ──────────────────────────────────
            elif 0x20 <= b <= 0xFF:
                codec = _CODE_TABLE_CODECS.get(self._state.char_code_table, "cp437")
                self._append_char(bytes([b]).decode(codec, errors="replace"))

            # else: skip unmapped control codes silently

    # ------------------------------------------------------------------
    # Parser actions
    # ------------------------------------------------------------------

    def _do_init(self) -> None:
        """ESC @ — Reset printer state."""
        self._state.reset()
        self._current_spans.clear()
        logger.debug("EscposEmulator: state reset (ESC @)")

    def _do_line_feed(self) -> None:
        """Finalise the current line and start a new one."""
        text = "".join(s.text for s in self._current_spans)
        line = _PrintLine(
            spans=list(self._current_spans),
            align=self._state.align,
            line_spacing=self._state.line_spacing,
        )
        if self._page_mode and self._page_buffer is not None:
            self._page_buffer.lines.append(line)
        else:
            self._lines.append(line)
        self._current_spans.clear()
        preview = (text[:60] + "…") if len(text) > 60 else text
        logger.debug("LF: %r (%d char(s))", preview, len(text))

    def _do_tab(self) -> None:
        """HT — advance to next tab stop (simplified: 8-char tab stops)."""
        col = sum(len(s.text) for s in self._current_spans)
        tab_size = 8
        spaces = tab_size - (col % tab_size)
        self._append_char(" " * spaces)

    def _do_print(self, trigger: str = "unknown") -> Optional[RasterSet]:
        """Render buffered lines to a RasterSet and invoke on_print."""
        if not self._lines:
            return None
        lines_to_render = list(self._lines)
        self._lines.clear()
        logger.info("print triggered by %s: rendering %d line(s)", trigger, len(lines_to_render))
        rs = self._render_lines(lines_to_render)
        total_h = sum(b._image.height for b in rs.blocks)
        width = self.preset.print_width_dots
        logger.info("raster ready: %d×%d dots (%d block(s))", width, total_h, len(rs.blocks))
        if self.on_print is not None:
            try:
                self.on_print(rs)
            except Exception as exc:
                logger.error("on_print callback raised: %s", exc, exc_info=True)
        return rs

    def _append_char(self, ch: str) -> None:
        """Append one or more characters to the current line."""
        if self._current_spans and self._current_spans[-1].matches(self._state):
            self._current_spans[-1].text += ch
            return
        span = _TextSpan(
            text=ch,
            font=self._state.font,
            bold=self._state.bold,
            double_strike=self._state.double_strike,
            underline=self._state.underline,
            char_size_w=self._state.char_size_w,
            char_size_h=self._state.char_size_h,
            invert=self._state.invert,
        )
        self._current_spans.append(span)

    # ------------------------------------------------------------------
    # Page-mode helpers
    # ------------------------------------------------------------------

    def _do_page_mode(self) -> None:
        """ESC L — switch to page mode."""
        self._page_mode = True
        if self._page_buffer is None:
            p = self.preset
            self._page_buffer = _PageBuffer(
                x=0, y=0,
                width=p.print_width_dots,
                height=p.default_line_spacing,
            )
        logger.debug("EscposEmulator: entered page mode")

    def _do_standard_mode(self) -> None:
        """ESC S — return to standard mode; commit page buffer to print queue."""
        if self._page_mode and self._page_buffer is not None:
            self._lines.extend(self._page_buffer.lines)
            self._page_buffer = None
        self._page_mode = False
        logger.debug("EscposEmulator: returned to standard mode")

    def _set_page_area(
        self,
        xL: int, xH: int,
        yL: int, yH: int,
        dxL: int, dxH: int,
        dyL: int, dyH: int,
    ) -> None:
        """ESC W — set print area in page mode."""
        if self._page_buffer is not None:
            self._page_buffer.x = xL + xH * 256
            self._page_buffer.y = yL + yH * 256
            self._page_buffer.width = dxL + dxH * 256
            self._page_buffer.height = dyL + dyH * 256

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_lines(self, lines: List[_PrintLine]) -> RasterSet:
        """Convert a list of *PrintLine* objects into a :class:`RasterSet`."""
        images: List[Image.Image] = []
        for line in lines:
            img = self._render_line(line)
            if img is not None:
                images.append(img)
            if line.extra_feed_dots > 0:
                feed = Image.new(
                    "L",
                    (self.preset.print_width_dots, line.extra_feed_dots),
                    255,
                )
                images.append(feed)

        if not images:
            images.append(
                Image.new("L", (self.preset.print_width_dots, 1), 255)
            )

        total_h = sum(img.height for img in images)
        canvas = Image.new("L", (self.preset.print_width_dots, total_h), 255)
        y = 0
        for img in images:
            canvas.paste(img, (0, y))
            y += img.height

        rs = RasterSet()
        rs.add(RasterImage(canvas))
        return rs

    def _span_cell_width(self, span: _TextSpan) -> float:
        """Width in dots of one character cell for *span*."""
        preset = self.preset
        if span.font == 0:
            return (preset.print_width_dots / preset.font_a_chars_per_line) * span.char_size_w
        cpl = preset.font_b_chars_per_line or preset.font_a_chars_per_line
        return (preset.print_width_dots / cpl) * span.char_size_w

    def _break_spans_into_rows(self, spans: List[_TextSpan]) -> List[List[_TextSpan]]:
        """Split *spans* into rows that each fit within ``preset.print_width_dots``."""
        rows: List[List[_TextSpan]] = [[]]
        current_x: float = 0.0
        max_w: int = self.preset.print_width_dots

        for span in spans:
            cell_w = self._span_cell_width(span)
            remaining = span.text
            while remaining:
                available = max_w - current_x
                chars_fit = max(1, int(available / cell_w)) if cell_w > 0 else len(remaining)
                chunk = remaining[:chars_fit]
                remaining = remaining[chars_fit:]
                if chunk:
                    rows[-1].append(replace(span, text=chunk))
                    current_x += cell_w * len(chunk)
                if remaining:
                    rows.append([])
                    current_x = 0.0

        return rows

    def _render_line(self, line: _PrintLine) -> Optional[Image.Image]:
        """Render a single :class:`_PrintLine`; auto-wraps content wider than the paper."""
        # ── Embedded raster image (e.g. QR code rendered via GS v 0) ──────────
        if line.image is not None:
            preset = self.preset
            paper_w = preset.print_width_dots
            img = line.image
            img_w, img_h = img.size
            # Shrink if wider than paper; never upscale here
            if img_w > paper_w and img_w > 0:
                scale = paper_w / img_w
                img_w = paper_w
                img_h = max(1, round(img_h * scale))
                img = img.resize((img_w, img_h), Image.NEAREST)
            # Centre / align on paper-width canvas
            canvas = Image.new("L", (paper_w, img_h), 255)
            if line.align == 1:    # centre
                x = (paper_w - img_w) // 2
            elif line.align == 2:  # right
                x = paper_w - img_w
            else:                  # left
                x = 0
            canvas.paste(img, (max(0, x), 0))
            return canvas

        preset = self.preset
        line_h = self._effective_line_height(line)

        if not any(s.text for s in line.spans):
            return Image.new("L", (preset.print_width_dots, line_h), 255)

        rows = self._break_spans_into_rows(line.spans)
        if len(rows) > 1:
            logger.debug("line wrapped: %d char(s) → %d row(s)", sum(len(s.text) for s in line.spans), len(rows))

        row_images: List[Image.Image] = []
        for row_spans in rows:
            span_images: List[Image.Image] = [
                self._render_span(s, line_h) for s in row_spans if s.text
            ]

            row_canvas = Image.new("L", (preset.print_width_dots, line_h), 255)
            if span_images:
                total_span_w = sum(img.width for img in span_images)
                align = line.align
                if align == 1:   # centre
                    x = max(0, (preset.print_width_dots - total_span_w) // 2)
                elif align == 2: # right
                    x = max(0, preset.print_width_dots - total_span_w)
                else:            # left
                    x = 0
                for img in span_images:
                    paste_w = min(img.width, preset.print_width_dots - x)
                    if paste_w <= 0:
                        break
                    row_canvas.paste(img.crop((0, 0, paste_w, img.height)), (x, 0))
                    x += img.width
            row_images.append(row_canvas)

        if len(row_images) == 1:
            return row_images[0]

        total_h = sum(img.height for img in row_images)
        canvas = Image.new("L", (preset.print_width_dots, total_h), 255)
        y = 0
        for img in row_images:
            canvas.paste(img, (0, y))
            y += img.height
        return canvas

    def _render_span(self, span: _TextSpan, line_h: int) -> Image.Image:
        """Render a :class:`_TextSpan` to a grayscale PIL Image."""
        preset = self.preset

        if span.font == 0:
            base_char_h = preset.font_a_char_height
            base_chars_per_line = preset.font_a_chars_per_line
            font_name = preset.font_a_name
        else:
            base_char_h = preset.font_b_char_height
            base_chars_per_line = preset.font_b_chars_per_line
            font_name = preset.font_b_name or preset.font_a_name

        base_cell_w: float = preset.print_width_dots / base_chars_per_line

        eff_char_h = base_char_h * span.char_size_h
        eff_cell_w = base_cell_w * span.char_size_w

        font = self._get_font(font_name, eff_char_h)

        n_chars = len(span.text)
        span_w = max(1, round(eff_cell_w * n_chars))

        bg = 0   if span.invert else 255
        fg = 255 if span.invert else 0

        need_scale = span.char_size_w != 1 or span.char_size_h != 1
        if need_scale:
            base_span_w = max(1, round(base_cell_w * n_chars))
            base_line_h = self._get_line_height(span.font, 1)
            img = Image.new("L", (base_span_w, base_line_h), bg)
            draw = ImageDraw.Draw(img)
            base_font = self._get_font(font_name, base_char_h)
            try:
                bbox = base_font.getbbox("Ag")
                y_off = -bbox[1]
            except AttributeError:
                y_off = 0
            self._draw_chars(draw, span.text, base_cell_w, y_off, fg, base_font, span)
            img = img.resize((span_w, line_h), Image.NEAREST)
        else:
            img = Image.new("L", (span_w, line_h), bg)
            draw = ImageDraw.Draw(img)
            try:
                bbox = font.getbbox("Ag")
                y_off = -bbox[1]
            except AttributeError:
                y_off = 0
            self._draw_chars(draw, span.text, eff_cell_w, y_off, fg, font, span)

        return img

    @staticmethod
    def _draw_chars(
        draw: ImageDraw.ImageDraw,
        text: str,
        cell_w: float,
        y_off: int,
        fg: int,
        font: ImageFont.FreeTypeFont,
        span: "_TextSpan",
    ) -> None:
        """Draw characters at fixed cell-width intervals."""
        stroke = 1 if (span.bold or span.double_strike) else 0
        for i, ch in enumerate(text):
            x = round(i * cell_w)
            draw.text(
                (x, y_off),
                ch,
                fill=fg,
                font=font,
                stroke_width=stroke,
                stroke_fill=fg,
            )
        if span.underline > 0:
            try:
                ub = font.getbbox("A")
                ul_y = y_off + (ub[3] - ub[1]) + 1
            except AttributeError:
                ul_y = y_off + 16
            span_px_w = round(len(text) * cell_w)
            draw.rectangle(
                [0, ul_y, span_px_w - 1, ul_y + span.underline - 1],
                fill=fg,
            )

    # ------------------------------------------------------------------
    # Font helpers
    # ------------------------------------------------------------------

    def _get_font(
        self,
        font_name: Optional[str],
        char_height: int,
    ) -> ImageFont.FreeTypeFont:
        """Return a cached PIL font sized to render characters *char_height* dots tall."""
        font_path = self._resolve_font_path(font_name)
        key = (font_path, char_height)
        if key in self._font_cache:
            return self._font_cache[key]
        font = self._fit_font_height(font_path, char_height)
        self._font_cache[key] = font
        return font

    @staticmethod
    def _resolve_font_path(font_name: Optional[str]) -> str:
        """Resolve a font name/path to an absolute file path."""
        if font_name is None or font_name == "":
            if Path(_BUNDLED_FONT).is_file():
                return _BUNDLED_FONT
            font_name = None

        if font_name is not None and Path(font_name).is_file():
            return font_name

        try:
            from py_star_tsp.text import find_font
            found = find_font(font_name)
            if found:
                return found
        except Exception:
            pass

        if Path(_BUNDLED_FONT).is_file():
            return _BUNDLED_FONT

        raise FileNotFoundError(
            f"Could not resolve font {font_name!r} and bundled font is missing"
        )

    @staticmethod
    def _fit_font_height(font_path: str, target_h: int) -> ImageFont.FreeTypeFont:
        """Find the PIL font size where rendered characters are ≈ *target_h* pixels tall."""
        if not Path(font_path).is_file():
            logger.warning("Font file not found: %s — using Pillow default", font_path)
            return ImageFont.load_default()

        best_font = None
        for size in range(4, 200):
            try:
                font = ImageFont.truetype(font_path, size)
            except (OSError, IOError):
                break
            try:
                bbox = font.getbbox("Ag")
                h = bbox[3] - bbox[1]
            except AttributeError:
                h = size
            if h >= target_h:
                return font
            best_font = font

        if best_font is not None:
            return best_font
        try:
            return ImageFont.truetype(font_path, target_h)
        except (OSError, IOError):
            return ImageFont.load_default()

    # ------------------------------------------------------------------
    # Line-height helpers
    # ------------------------------------------------------------------

    def _effective_line_height(self, line: _PrintLine) -> int:
        """Compute the rendered pixel height for a *PrintLine*."""
        if line.line_spacing is not None:
            base = max(
                (self._get_line_height(s.font, s.char_size_h) for s in line.spans),
                default=self._get_line_height(0, 1),
            )
            return max(base, line.line_spacing)

        if not line.spans:
            return self._get_line_height(0, 1)

        return max(
            self._get_line_height(s.font, s.char_size_h) for s in line.spans
        )

    def _get_line_height(self, font: int, height_mag: int) -> int:
        """Line height in dots for the given *font* index and *height_mag*."""
        if font == 0:
            return self.preset.font_a_line_height * height_mag
        return self.preset.font_b_line_height * height_mag
