from threading import Thread
import asyncio
from abc import ABC

class Connection(Thread, ABC):
    """Runs a dedicated thread and asyncio event loop that handles all CAN & LCC related traffic."""
    """This is subclassed by CAN drivers."""
    name = ''

    def __init__(self, protocol=None):
        super().__init__()
        self.loop = None
        self.protocol = protocol
        self.frame_callback = None

    def set_protocol(self, protocol):
        self.protocol = protocol

    def create_parameters_panel(self, parent):
        pass

    def get_parameters(self):
        pass

    def connect(self, parameters):
        pass

    def send(self, can_frame):
        if self.frame_callback:
            self.frame_callback(can_frame, True)

    def receive(self):
        pass

    def disconnect(self):
        pass

    def set_frame_callback(self, func):
        self.frame_callback = func

    async def receive_can_task(self):
        while 1:
            frame = self.receive()
            if frame:
                if self.frame_callback:
                    self.frame_callback(frame, False)
                self.protocol.parse_frame(frame)
            else:
                try:
                    await asyncio.sleep(.01)
                except asyncio.CancelledError:
                    return

    async def run_async(self):
        self.loop = asyncio.get_running_loop()
        await asyncio.create_task(self.receive_can_task())
        
    def run(self):
        asyncio.run(self.run_async())

    def join(self, timeout=None):
        if self.loop:
            for task in asyncio.all_tasks(self.loop):
                task.cancel()
        if self.is_alive():
            super().join(timeout)

    def run_future(self, future):
        # runs an async function as future in the connection executor thread
        # may be canceled by calling the returned function
        if not self.connection.loop or not self.connection.loop.is_running():
            raise RuntimeError("No connection")
        future = asyncio.run_coroutine_threadsafe(future, self.loop)
        def cancel_future(future=future):
            if not self.connection.loop or not self.connection.loop.is_running():
                return
            self.loop.call_soon_threadsafe(future.cancel)
        return future, cancel_future

class CanFrame:
    def __init__(self, id, data, is_extended, is_remote):
        self.id = id
        self.data = data
        self.is_extended = is_extended
        self.is_remote = is_remote

    def __repr__(self):
        id = hex(self.id)
        id_type = "ext_id" if self.is_extended else "id"
        remote = " remote," if self.is_remote else ""
        data = self.data.hex() if self.data else '""'
        res = f"CAN frame, {id_type}={id},{remote} data={data}"
        return res
