#!/bin/python
from lcc_browser.can.drivers.usbcan_zhou_ligong import UsbcanZhouLigong
from lcc_browser.lcc.lcc_protocol import LccProtocol
import time

# callback that logs received frames
def log_frame(frame, sent_by_us):
    print(f"Received a frame, sent_by_us={sent_by_us}")
    print(frame)

# create a lcc protocol and can bus connection
con = UsbcanZhouLigong()
lcc = LccProtocol()
con.set_protocol(lcc)
lcc.set_connection(con)

# connect can bus
con.connect({"device": "/dev/ttyUSB0", "uart_baudrate": 9600})

# start receiving data in a background thread
con.start()

# supply callbacks for can and lcc frames
# it will be called from the background thread
lcc.set_frame_callback(log_frame)
con.set_frame_callback(log_frame)

# add your application here
# for example
lcc.update_node_id("02.01.0D.00.00.00")
lcc.reserve_node_alias()
lcc.emit_event(bytes.fromhex("0123456789abcdef"))
time.sleep(5)

# stop the background thread and close the connection (and associated protocol)
con.join()
