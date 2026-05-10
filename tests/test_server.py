"""
Unit tests for py_star_tsp.server — ESC/POS TCP server.

Tests use asyncio and mock the EscposEmulator to avoid real USB/PIL
dependencies.  Integration-level "real server" tests are included but
require asyncio.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, call

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

if HAS_PIL:
    from py_star_tsp.server import EscposServer
    from py_star_tsp.escpos import PRESET_EPSON_TM_T88, PRESET_58MM, PrinterPreset
    from py_star_tsp.raster import RasterSet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ===========================================================================
# EscposServer — construction
# ===========================================================================

@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEscposServerConstruction(unittest.TestCase):

    def test_default_host_port(self):
        s = EscposServer()
        self.assertEqual(s.host, "0.0.0.0")
        self.assertEqual(s.port, 9100)

    def test_custom_host_port(self):
        s = EscposServer(host="127.0.0.1", port=9200)
        self.assertEqual(s.host, "127.0.0.1")
        self.assertEqual(s.port, 9200)

    def test_default_preset(self):
        s = EscposServer()
        self.assertEqual(s.preset.name, PRESET_EPSON_TM_T88.name)

    def test_custom_preset(self):
        s = EscposServer(preset=PRESET_58MM)
        self.assertEqual(s.preset.name, PRESET_58MM.name)

    def test_on_print_callback_stored(self):
        cb = MagicMock()
        s = EscposServer(on_print=cb)
        self.assertIs(s.on_print, cb)

    def test_no_callback_by_default(self):
        s = EscposServer()
        self.assertIsNone(s.on_print)

    def test_server_not_running_initially(self):
        s = EscposServer()
        self.assertIsNone(s._server)


# ===========================================================================
# EscposServer — handle_client
# ===========================================================================

@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEscposServerHandleClient(unittest.TestCase):
    """Tests for _handle_client via asyncio.run()."""

    def _make_reader(self, chunks):
        """Create a mock StreamReader that yields chunks then EOF."""
        reader = AsyncMock()
        side_effects = list(chunks) + [b""]
        reader.read = AsyncMock(side_effect=side_effects)
        return reader

    def _make_writer(self):
        writer = MagicMock()
        writer.get_extra_info = MagicMock(return_value=("127.0.0.1", 12345))
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()
        return writer

    def test_data_forwarded_to_emulator(self):
        """Data received over TCP is fed to the emulator."""
        data_received = []

        class CapturingEmulator:
            def __init__(self, **kwargs):
                self.on_print = kwargs.get("on_print")
                self.preset = kwargs.get("preset")

            def feed(self, data):
                data_received.append(data)

            def flush(self):
                pass

        reader = self._make_reader([b"Hello\n", b"World\n"])
        writer = self._make_writer()

        async def run():
            server = EscposServer()
            with patch("py_star_tsp.server.escpos_server.EscposEmulator", CapturingEmulator):
                await server._handle_client(reader, writer)

        _run(run())
        self.assertIn(b"Hello\n", data_received)
        self.assertIn(b"World\n", data_received)

    def test_flush_called_on_connection_close(self):
        """flush() is called when the client disconnects."""
        flushed = []

        class RecordFlushEmulator:
            def __init__(self, **kwargs):
                self.on_print = kwargs.get("on_print")
                self.preset = kwargs.get("preset")

            def feed(self, data):
                pass

            def flush(self):
                flushed.append(True)

        reader = self._make_reader([b"Data\n"])
        writer = self._make_writer()

        async def run():
            server = EscposServer()
            with patch("py_star_tsp.server.escpos_server.EscposEmulator", RecordFlushEmulator):
                await server._handle_client(reader, writer)

        _run(run())
        self.assertEqual(len(flushed), 1)

    def test_on_print_passed_to_emulator(self):
        """The server's on_print callback is passed to each emulator."""
        cb = MagicMock()
        preset_used = []
        cb_used = []

        class InspectingEmulator:
            def __init__(self, **kwargs):
                preset_used.append(kwargs.get("preset"))
                cb_used.append(kwargs.get("on_print"))

            def feed(self, data):
                pass

            def flush(self):
                pass

        reader = self._make_reader([b""])
        writer = self._make_writer()

        async def run():
            server = EscposServer(preset=PRESET_58MM, on_print=cb)
            with patch("py_star_tsp.server.escpos_server.EscposEmulator", InspectingEmulator):
                await server._handle_client(reader, writer)

        _run(run())
        self.assertIs(cb_used[0], cb)
        self.assertIs(preset_used[0], PRESET_58MM)

    def test_writer_closed_after_disconnect(self):
        reader = self._make_reader([b""])
        writer = self._make_writer()

        async def run():
            server = EscposServer()
            await server._handle_client(reader, writer)

        _run(run())
        writer.close.assert_called_once()

    def test_flush_error_does_not_raise(self):
        """An exception in flush() is logged but does not propagate."""
        class BrokenFlushEmulator:
            def __init__(self, **kwargs):
                self.on_print = kwargs.get("on_print")
                self.preset = kwargs.get("preset")

            def feed(self, data):
                pass

            def flush(self):
                raise RuntimeError("Flush failed")

        reader = self._make_reader([b""])
        writer = self._make_writer()

        async def run():
            server = EscposServer()
            with patch("py_star_tsp.server.escpos_server.EscposEmulator", BrokenFlushEmulator):
                # Should complete without raising
                await server._handle_client(reader, writer)

        _run(run())  # no assertion needed — must not raise


# ===========================================================================
# EscposServer — start / stop (mocked asyncio.start_server)
# ===========================================================================

@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestEscposServerLifecycle(unittest.TestCase):

    def test_stop_when_not_started(self):
        """stop() on an unstarted server must not raise."""
        async def run():
            s = EscposServer()
            await s.stop()

        _run(run())  # must not raise

    def test_stop_clears_server_ref(self):
        mock_server = MagicMock()
        mock_server.close = MagicMock()
        mock_server.wait_closed = AsyncMock()

        async def run():
            s = EscposServer()
            s._server = mock_server
            await s.stop()
            return s

        result = _run(run())
        mock_server.close.assert_called_once()
        self.assertIsNone(result._server)

    def test_read_chunk_passed_correctly(self):
        """Custom read_chunk is stored on the server."""
        s = EscposServer(read_chunk=1024)
        self.assertEqual(s.read_chunk, 1024)

    def test_context_manager_sets_server(self):
        """__aenter__ creates the server socket."""
        mock_asyncio_server = MagicMock()
        mock_asyncio_server.sockets = [MagicMock()]
        mock_asyncio_server.sockets[0].getsockname.return_value = ("0.0.0.0", 9100)
        mock_asyncio_server.close = MagicMock()
        mock_asyncio_server.wait_closed = AsyncMock()

        async def run():
            s = EscposServer(port=9100)
            with patch("asyncio.start_server", return_value=mock_asyncio_server) as m:
                result = await s.__aenter__()
                self.assertIs(result, s)
                self.assertIs(s._server, mock_asyncio_server)
                await s.__aexit__(None, None, None)

        _run(run())


# ===========================================================================
# Integration-level: real emulator + server round-trip (no real socket)
# ===========================================================================

@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class TestServerRoundTrip(unittest.TestCase):
    """End-to-end test using a real EscposEmulator through the server handler."""

    def _make_reader_from_bytes(self, data: bytes):
        reader = AsyncMock()
        chunk = 512
        chunks = [data[i:i+chunk] for i in range(0, len(data), chunk)] + [b""]
        reader.read = AsyncMock(side_effect=chunks)
        return reader

    def _make_writer(self):
        writer = MagicMock()
        writer.get_extra_info = MagicMock(return_value=("127.0.0.1", 9999))
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()
        return writer

    def test_text_line_produces_raster_output(self):
        """A simple ESC/POS text job produces a non-empty RasterSet."""
        ESC = b"\x1b"
        GS  = b"\x1d"
        job = b"Hello, World!\n" + GS + b"V\x00"

        printed = []
        server = EscposServer(on_print=printed.append)

        async def run():
            reader = self._make_reader_from_bytes(job)
            writer = self._make_writer()
            await server._handle_client(reader, writer)

        _run(run())
        self.assertEqual(len(printed), 1)
        self.assertIsInstance(printed[0], RasterSet)
        img = printed[0].to_image()
        self.assertEqual(img.width, PRESET_EPSON_TM_T88.print_width_dots)
        self.assertGreater(img.height, 0)

    def test_multi_line_job(self):
        ESC = b"\x1b"
        GS  = b"\x1d"
        job = (
            b"Line 1\n"
            b"Line 2\n"
            b"Line 3\n"
            + GS + b"V\x00"
        )
        printed = []
        server = EscposServer(on_print=printed.append)

        async def run():
            reader = self._make_reader_from_bytes(job)
            writer = self._make_writer()
            await server._handle_client(reader, writer)

        _run(run())
        self.assertEqual(len(printed), 1)
        img = printed[0].to_image()
        # Three lines should be taller than one
        single_printed = []
        server2 = EscposServer(on_print=single_printed.append)

        async def run2():
            reader = self._make_reader_from_bytes(b"Line 1\n" + GS + b"V\x00")
            writer = self._make_writer()
            await server2._handle_client(reader, writer)

        _run(run2())
        self.assertGreater(img.height, single_printed[0].to_image().height)


if __name__ == "__main__":
    unittest.main()
