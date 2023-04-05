# LCC Browser 1.0

[LCC](https://www.nmra.org/lcc) is a bus for model railroad control. The LCC browser application provides a user interface for LCC systems. At the center is an embedded web browser that shows your custom-designed control panel. Also included are loggers for CAN and LCC traffic, and an LCC configuration tool.

![alt text](https://github.com/ahaensler/lcc_browser/blob/master/screenshot.png "Screenshot Linux")

## Installation
[Download the executable](https://github.com/ahaensler/lcc_browser/releases) for your operating system. It is a standalone build and doesn't need an installer. Connect the CAN bus `(Connection - Establish...)` and see if LCC nodes are found `(View - LCC Nodes)`. Create an HTML file with your layout controls (see index.html for an example).

## Drivers
| Name        | Description | Supported devices  |
| ----------- | ----------- | ------------------ |
| USBCAN Dongle, Zhou-Ligong protocol | CAN frames are sent through a USB serial protocol in packets of 16 bytes `(0xAA...)` | https://www.aliexpress.com/item/2255800739172034.html |

More drivers can easily be added as plugins. Create a file in `lcc_browser/can/drivers` and add the required functions for connecting, sending and receiving. The code will import the file automatically and make the driver available to the user. Optionally, add a GUI panel for configuring the driver.

## Outlook
This version provides the minimum functionality to get started with LCC. I have tested it successfully with a [TCS](www.tcsdcc.com) node and a CAN USB dongle. It would be nice to make the interface more user friendly and
- add dedicated user interfaces for LCC nodes. Current LCC software permits raw CDI configuration. This is too low-level for the typical user by today's standards. Adding graphical frontends for individual manufacturers/models as plugins would fix this.
- add abstraction around events. The goal is to remove any hexidecimal representation of event ids from the user interface and instead have a graphical representation, or at least human-readable identifiers.

The code can also be used as a Python library. There's a small example included ([lcc_example.py](https://github.com/ahaensler/lcc_browser/blob/master/bin/lcc_example.py)).
