from lcc_browser.can.connection import Connection, CanFrame
import wx
import serial.tools.list_ports
import serial
from time import sleep

baudrates = [1200, 2400, 4800, 9600, 19200, 28800, 38400, 57600, 115200, 230400, 460800]

class UsbcanZhouLigong(Connection):
    name = "USBCAN Dongle, Zhou-Ligong protocol"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.devices = []
        self.parameters_panel = None
        self.ser = None

    def create_parameters_panel(self, parent):
        """ generates a GUI for the user to select connection parameters """
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # choice of com port
        label_1 = wx.StaticText(panel, wx.ID_ANY, "Device")
        sizer.Add(label_1)
        com_ports = sorted(serial.tools.list_ports.comports())
        self.devices = [port.device for port in com_ports]
        descriptions = [f"{port.name} ({port.description})" for port in com_ports]
        self.device_selection = wx.Choice(panel, choices=descriptions)
        sizer.Add(self.device_selection)

        label_baudrate = wx.StaticText(panel, wx.ID_ANY, "UART Baudrate")
        sizer.Add(label_baudrate)
        self.baudrate = wx.Choice(panel, choices=list(map(str, baudrates)))
        sizer.Add(self.baudrate)

        panel.SetSizer(sizer)
        self.parameters_panel = panel
        return panel

    def get_parameters(self):
        idx_device = self.device_selection.GetSelection()
        if idx_device == wx.NOT_FOUND: return None
        idx_baud = self.baudrate.GetSelection()
        if idx_baud == wx.NOT_FOUND: return None
        return {
            'device': self.devices[idx_device],
            'uart_baudrate': baudrates[idx_baud],
        }

    def connect(self, parameters):
        self.ser = serial.Serial(parameters['device'], baudrate=9600, timeout=0)
        self.ser.dtr = 1 # enter config mode

        def send_command(command, expected_response):
            while 1:
                self.ser.write(command)
                sleep(.05)
                try:
                    buffer = self.ser.read(256)
                except serial.serialutil.SerialException as e:
                    print("Could not read from serial port:", e)
                    raise
                print("Dongle response:", buffer.decode(encoding='latin-1').replace('\r', ' ').replace('\n', ' '))
                if expected_response in buffer:
                    break
                sleep(1)

        send_command(b'can_b 125\n', b'real baud is 125') # set can baud rate
        send_command(b'mod 1\n', b'OK') # packet mode
        uart_b = parameters["uart_baudrate"]
        send_command(f'uart_b {uart_b}\n'.encode(), b'OK') # usb baudrate
        self.ser.dtr = 0 # exit config
        self.ser.flush()
        self.ser.baudrate = parameters["uart_baudrate"]

        #empty buffer for sync
        self.ser.read(4096)
        return True

    def disconnect(self):
        if self.ser:
            self.ser.close()
            self.ser = None

    def send(self, can_frame):
        super().send(can_frame)
        if can_frame.data is None: can_frame.data = bytes()
        assert len(can_frame.data) <= 8
        id = can_frame.id
        buffer = bytearray([
            0xaa, 0x01, 0x00, len(can_frame.data),
            (id >> 24) & 0b00011111, (id >> 16) & 0xff, (id >> 8) & 0xff, id & 0xff,
            *can_frame.data])
        buffer += bytes(16-len(buffer))
        self.ser.write(buffer)

    def receive(self):
        # tries to receive one can frame
        try:
            buffer = self.ser.read(16)
        except serial.serialutil.SerialException as e:
            print("Could not read from serial port:", e)
            return None
        if len(buffer) == 0: return None
        if buffer[0] != 0xaa:
            print('lost sync?', hex(buffer[0]))
            return None
        if len(buffer) < 16:
            # partial data: give data some more time to arrive, then give up
            sleep(.05)
            buffer += self.ser.read(16 - len(buffer))
            if len(buffer) < 16:
                print(f"CAN buffer length {len(buffer)} should be at least 16. Ignoring data")
                return None
        is_extended = buffer[1]
        is_remote = buffer[2]
        data_len = buffer[3]
        assert data_len <= 8
        id = int.from_bytes(buffer[4:8], byteorder='big')
        data = buffer[8:8+data_len]
        return CanFrame(id, data, is_extended, is_remote)
