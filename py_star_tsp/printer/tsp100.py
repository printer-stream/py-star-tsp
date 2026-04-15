from __future__ import annotations
import logging
from typing import Optional

from .printer import StarTSP

logger = logging.getLogger("py_star_tsp")


class StarTSP100(StarTSP):
    """
        Printer class for the Star TSP100 series.
        
        1. DPI: 203
        2. Paper width: 80mm
        3. USB interface
        4. Supported commands: StarPRNT
        
        USB_VID = 0x0519
        USB_PID = 0x0001

        Bus 001 Device 016: ID 0519:0003 Star Micronics Co., Ltd TSP100ECO/TSP100II

        usb 1-5.1: USB disconnect, device number 16
        usb 1-5.1: new full-speed USB device number 17 using xhci_hcd
        usb 1-5.1: New USB device found, idVendor=0519, idProduct=0003, bcdDevice= 0.01
        usb 1-5.1: New USB device strings: Mfr=1, Product=2, SerialNumber=0
        usb 1-5.1: Product: Star TSP143
        usb 1-5.1: Manufacturer: STAR
        usblp 1-5.1:1.0: usblp0: USB Bidirectional printer dev 17 if 0 alt 0 proto 2 vid 0x0519 pid 0x0003

    """

    def __init__(self, 
                product_id: Optional[int] = None,
                timeout: int = 5000,
                *args, **kwargs) -> None:

        self.vendor_id = 0x0519
        self.product_id = product_id
        self.timeout = timeout

        self.paper_width_mm = 80
        self.raster_dpi = 203
        self.raster_width = 576  # 576 pixels (80mm at 203 DPI)

        super().__init__(vendor_id=self.vendor_id, product_id=self.product_id, timeout=self.timeout, *args, **kwargs)

    def __enter__(self) -> "StarTSP100":
        logger.info("Opening printer connection")
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        logger.info("Closing printer connection")
        self.close()

