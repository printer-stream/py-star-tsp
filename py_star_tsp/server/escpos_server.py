"""TCP server that emulates a raw ESC/POS receipt printer.

Listens on port 9100 (the standard RAW/JetDirect port used by Epson
thermal printers) and forwards incoming print jobs through the
:class:`~py_star_tsp.escpos.EscposEmulator` to produce a
:class:`~py_star_tsp.raster.RasterSet` that can be sent to a physical
Star TSP100.

Quick-start
-----------
::

    import asyncio
    from py_star_tsp import StarTSP100
    from py_star_tsp.server import EscposServer

    def on_print(raster_set):
        with StarTSP100() as printer:
            for block in raster_set.blocks:
                printer.add_raster(block)
            printer.print()

    async def main():
        server = EscposServer(on_print=on_print)
        await server.start()

    asyncio.run(main())

The server uses :mod:`asyncio` so it is non-blocking and can handle
multiple concurrent connections from different print sources.  Each
connection gets its own :class:`~py_star_tsp.escpos.EscposEmulator`
instance; the emulator's content is flushed to ``on_print`` when a
*print trigger* command (``GS V``, ``FF``) is received **or** when the
TCP connection is closed.

The ``on_print`` callback is called synchronously from within the
connection handler coroutine.  If the callback blocks (e.g. USB write),
it will pause processing of that connection but will not block other
connections.  Pass an async-friendly wrapper (using
:func:`asyncio.get_event_loop().run_in_executor`) if you need truly
non-blocking behaviour.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional

from py_star_tsp.escpos import EscposEmulator, PrinterPreset, PRESET_EPSON_TM_T88
from py_star_tsp.raster import RasterSet

logger = logging.getLogger("py_star_tsp.server")


class EscposServer:
    """Asyncio TCP server that accepts raw ESC/POS data on port 9100.

    Args:
        host: IP address or hostname to bind to.  Defaults to
            ``"0.0.0.0"`` (all interfaces).
        port: TCP port to listen on.  Defaults to ``9100``.
        preset: :class:`~py_star_tsp.escpos.PrinterPreset` that
            controls rendering parameters.  Defaults to
            :data:`~py_star_tsp.escpos.PRESET_EPSON_TM_T88`.
        on_print: Callback invoked with a
            :class:`~py_star_tsp.raster.RasterSet` whenever a complete
            print job is ready (on cut/FF command or connection close).
            If ``None``, rendered jobs are discarded.
        read_chunk: Maximum bytes to read from each client per iteration.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 9100,
        preset: Optional[PrinterPreset] = None,
        on_print: Optional[Callable[[RasterSet], None]] = None,
        read_chunk: int = 4096,
    ) -> None:
        self.host = host
        self.port = port
        self.preset = preset or PRESET_EPSON_TM_T88
        self.on_print = on_print
        self.read_chunk = read_chunk
        self._server: Optional[asyncio.AbstractServer] = None

    # ------------------------------------------------------------------
    # Connection handler
    # ------------------------------------------------------------------

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        peer = writer.get_extra_info("peername", "<unknown>")
        logger.info("ESC/POS client connected: %s", peer)

        emulator = EscposEmulator(preset=self.preset, on_print=self.on_print)
        total_bytes = 0

        try:
            while True:
                data = await reader.read(self.read_chunk)
                if not data:
                    break
                total_bytes += len(data)
                logger.debug("Received %d bytes from %s (total: %d)", len(data), peer, total_bytes)
                emulator.feed(data)
        except asyncio.CancelledError:
            raise
        except ConnectionResetError:
            logger.debug("Connection reset by peer: %s", peer)
        except Exception as exc:
            logger.error(
                "Error handling ESC/POS client %s: %s", peer, exc, exc_info=True
            )
        finally:
            # Flush any content that arrived without an explicit cut command
            try:
                emulator.flush()
            except Exception as exc:
                logger.warning("Error flushing emulator for %s: %s", peer, exc)

            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            logger.info("ESC/POS client disconnected: %s — %d byte(s) processed", peer, total_bytes)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the TCP server and run until cancelled or :meth:`stop` is called.

        This coroutine blocks until the server is stopped.  Wrap it in
        :func:`asyncio.create_task` if you need to run other coroutines
        concurrently.
        """
        self._server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port,
        )
        addr = self._server.sockets[0].getsockname()
        logger.info("ESC/POS server listening on %s:%s", addr[0], addr[1])
        async with self._server:
            await self._server.serve_forever()

    async def stop(self) -> None:
        """Stop the server gracefully, closing all active connections."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
            logger.info("ESC/POS server stopped")

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "EscposServer":
        self._server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port,
        )
        addr = self._server.sockets[0].getsockname()
        logger.info("ESC/POS server listening on %s:%s", addr[0], addr[1])
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
