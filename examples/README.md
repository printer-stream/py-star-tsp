# Examples

## Quickstart

Source: [quickstart.py](https://github.com/printer-stream/py-star-tsp/blob/master/examples/quickstart.py)

## Reference print

Source: [demo_reference.py](https://github.com/printer-stream/py-star-tsp/blob/master/examples/demo_reference.py)

Scan: [reference print](/doc/reference_print_v1.6.3.jpg)

![py-star-tsp reference print gif](/doc/reference_print_v1.6.3.gif)

## Print server

Source: [print_server.py](https://github.com/printer-stream/py-star-tsp/blob/master/examples/print_server.py)

Listens on port 9100 for raw ESC/POS data and forwards completed jobs to a
physical Star TSP100 via USB.

## python-escpos client

Source: [python_escpos_client.py](https://github.com/printer-stream/py-star-tsp/blob/master/examples/python_escpos_client.py)

Shows how to use the [`python-escpos`](https://python-escpos.readthedocs.io/)
library as the content-generation layer while printing to a Star TSP100.
Because Star TSP100 printers don't support native ESC/POS, `python-escpos`
targets our `EscposServer` (localhost:9100) instead of the physical printer
directly — the server translates the byte stream to raster and sends it on.

```
pip install python-escpos
python examples/print_server.py    # terminal 1
python examples/python_escpos_client.py  # terminal 2
```

| [![escpos_emulation_epson_tm_t88.jpg](https://gh.printer.stream/static/sm/escpos_emulation_epson_tm_t88.jpg)](https://gh.printer.stream/static/escpos_emulation_epson_tm_t88.jpg) | [![escpos_emulation_star_tsp100.jpg](https://gh.printer.stream/static/sm/escpos_emulation_star_tsp100.jpg)](https://gh.printer.stream/static/escpos_emulation_star_tsp100.jpg) |
| :--: | :--: |
