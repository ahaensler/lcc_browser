import random
from lcc_browser.can.connection import CanFrame
from lcc_browser.lcc.message_format import LccFrame, DatagramProtocol, type_to_mti_map, type_to_cc_map, type_to_memory_config_map, response_filter, datagram_response_filter
from threading import Timer, Lock
import traceback
import math
from collections import defaultdict
import asyncio

def id_to_bytes(id):
    if type(id) == str:
        try:
            return bytearray.fromhex(id.replace(".", ""))
        except:
            return None
    else:
        return id

class MissingResponse(Exception):
    pass
class ProtocolError(Exception):
    pass
class CanError(Exception):
    pass

class LccProtocol:
    def __init__(self):
        self.node_id = bytes(6)
        self.node_alias = 0
        self.multipart_data = {} # buffer for addressed multipart data
        self.datagrams = {} # buffer for multipart datagrams
        self.alias_to_node_id = {}
        self.node_id_to_alias = {}
        self.node_locks = defaultdict(asyncio.Lock) # locks that provide exclusive access to a node (node_alias -> lock)
        self.handlers = {
            "AliasMapDefinitionFrame": self.handle_cc_alias_map_definition,
            "AliasMappingEnquiryFrame": self.handle_cc_alias_map_enquiry,
            "AliasMapResetFrame": self.handle_cc_alias_map_reset,
            "VerifiedNodeId": self.handle_mti_verified_node_id,
        }
        self.dynamic_handlers = defaultdict(dict) # one-time handlers waiting for replies, filter -> func
        self.dynamic_handler_lock = Lock()
        self.lcc_control_state = "inhibited"
        self.lcc_message_state = "ready" # we're always ready to accept events
        self.timer = None
        self.connection = None
        self.frame_callback = None

    def set_connection(self, connection):
        self.connection = connection

    def set_frame_callback(self, func):
        self.frame_callback = func

    def join(self):
        if self.timer: self.timer.cancel()
        self.lcc_control_state = "inhibited"
        self.lcc_message_state = "ready"

    def handle_cc_frame(self, frame):
        if frame.source_alias == self.node_alias:
            if self.lcc_control_state == "reserving":
                # third bullet point, or 6.2.1
                # The node shall restart the (reservation) process at the beginning if, before completion of the process, a frame is
                # received that carries a source Node ID alias value that is identical to the alias value being tested by this
                # procedure.
                print("Node alias collision detected while reserving")
                self.timer.cancel()
                self.timer = Timer(1, self.reserve_node_alias)
                self.timer.start()
            else:
                # see 6.2.5 Node ID Alias Collision Handling
                if frame.type == "CanControlCheckIDFrame":
                    # first bullet point
                    # CID frame
                    # reserve id alias
                    self.send_cc_frame("ReserveIDFrame")
                else:
                    if self.lcc_control_state == "permitted":
                        # second bullet point
                        # non CID frame
                        self.lcc_control_set_state("inhibited")
                        # send Alias Map Reset frame
                        self.send_cc_frame("AliasMapResetFrame", self.node_id)
                        # try to get a new alias reserved
                        print("Node alias collision")
                        self.timer.cancel()
                        self.timer = Timer(1, self.reserve_node_alias)
                        self.timer.start()

    def handle_cc_alias_map_definition(self, frame):
        # Alias Map Definition (AMD) frame
        # see 6.2.6 optional Duplicate Node ID Handling
        node_id = frame.inner.inner.node_id
        if self.lcc_control_state == "permitted" and node_id == self.node_id:
            # send Producer-Consumer Event Report
            # Duplicate Node ID Detected
            duplicate_node_id_evt = bytearray.fromhex("0101000000000201")
            can_frame = CanFrame(0x195b4000 | (self.node_alias & 0xfff), duplicate_node_id_evt, True, False)
            self.can_tx(can_frame)
            self.lcc_control_set_state("collision")
        self.add_alias(node_id, frame.source_alias)

    def handle_cc_alias_map_reset(self, frame):
        self.remove_alias(frame.inner.inner.node_id, frame.source_alias)

    def handle_mti_verified_node_id(self, frame):
        self.add_alias(frame.inner.inner.inner.node_id, frame.source_alias)

    def add_alias(self, node_id, alias):
        self.node_id_to_alias[node_id] = alias
        self.alias_to_node_id[alias] = node_id

    def remove_alias(self, node_id, alias):
        self.node_id_to_alias.pop(node_id, None)
        self.alias_to_node_id.pop(alias, None)

    def handle_cc_alias_map_enquiry(self, frame):
        # Alias Mapping Enquiry (AME) frame
        if self.lcc_control_state == "permitted" and \
            (frame.inner.inner.node_id is None or frame.inner.inner.node_id == self.node_id):
            # see 6.2.3
            # send alias map definition
            self.send_cc_frame("AliasMapDefinitionFrame", self.node_id);

    def update_node_id(self, node_id):
        node_id = id_to_bytes(node_id)
        random.seed(node_id)
        if node_id == self.node_id: return

        if self.lcc_control_state == "permitted":
            # release currently used alias
            self.send_cc_frame("AliasMapResetFrame", self.node_id)
        self.node_id = node_id
        if self.connection:
            self.reserve_node_alias()

    def send_cc_cid_frame(self, sequence_number, data, payload=None):
        if not self.connection: return 1
        can_frame = CanFrame((1 << 28) | (sequence_number << 24) | (data << 12) | self.node_alias, payload, True, False)
        self.can_tx(can_frame)

    def send_cc_frame(self, type, payload=None):
        if not self.connection: return 1
        sequence_number = 0
        data = type_to_cc_map.get(type)
        can_frame = CanFrame((1 << 28) | (sequence_number << 24) | (data << 12) | self.node_alias, payload, True, False)
        self.can_tx(can_frame)

    def send_lcc_frame(self, frame_type, data, payload=None):
        if not self.connection: return 1
        can_frame = CanFrame((0b11 << 27) | (frame_type << 24) | (data << 12) | self.node_alias, payload, True, False)
        self.can_tx(can_frame)

    def requires_initialization(func):
        def decorated(self, *args, **kwargs):
            if not self.connection: return 1
            if self.lcc_message_state != "initialized": return 1
            return func(self, *args, **kwargs)
        return decorated

    def send_mti_frame(self, type, payload=None, dst_alias=None):
        if not self.connection: return 1
        if self.lcc_message_state != "initialized" and not type.startswith("InitializationComplete"):
            return 1
        frame_type = 1
        mti = type_to_mti_map.get(type)
        assert mti
        is_addressed = mti & 0b1000
        if is_addressed:
            flag = 0 # TODO: support for multipart addressed messages
            assert dst_alias, f"MTI message {type} needs a destination alias"
            if payload is None: payload = bytes()
            payload = bytearray([(flag << 4) | (dst_alias >> 8), dst_alias & 0xff]) + payload
        can_frame = CanFrame((0b11 << 27) | (frame_type << 24) | (mti << 12) | self.node_alias, payload, True, False)
        self.can_tx(can_frame)

    async def protocol_support_inquiry(self, dst_alias):
        async with self.node_locks[dst_alias]:
            try:
                response_filter = lambda frame: frame.source_alias == dst_alias and frame.type == "ProtocolSupportReply"
                response_future = self.add_handler(response_filter)
                response_handler = datagram_response_filter(self.node_alias, dst_alias)
                self.send_mti_frame("ProtocolSupportInquiry", dst_alias=dst_alias)
                result = await asyncio.wait_for(response_future, timeout=2)
                return result.inner.inner.inner.inner
            finally:
                self.remove_handler(response_filter)

    async def simple_node_information(self, dst_alias):
        async with self.node_locks[dst_alias]:
            try:
                response_filter = lambda frame: frame.source_alias == dst_alias and frame.type == "SimpleNodeIdentInfoReply" and hasattr(frame, "multipart_data")
                response_future = self.add_handler(response_filter)
                response_handler = datagram_response_filter(self.node_alias, dst_alias)
                self.send_mti_frame("SimpleNodeIdentInfoRequest", dst_alias=dst_alias)
                result = await asyncio.wait_for(response_future, timeout=2)
                return result.inner.inner.inner.inner
            finally:
                self.remove_handler(response_filter)

    @requires_initialization
    async def send_datagram(self, payload, dst_alias, expected_response=None):
        """Sends a datagram and awaits its response."""
        async with self.node_locks[dst_alias]:
            # install handlers before sending datagram to avoid timing issues
            dg_filter = datagram_response_filter(self.node_alias, dst_alias)
            dg_future = self.add_handler(dg_filter)
            if expected_response:
                proto_future = self.add_handler(expected_response)

            try:
                num_frames = math.ceil(len(payload) / 8)
                for i in range(num_frames):
                    if num_frames <= 1:
                        frame_type = 2
                    elif i == 0:
                        frame_type = 3
                    elif i+1 < num_frames:
                        frame_type = 4
                    else:
                        frame_type = 5

                    data = payload[i*8:(i+1)*8]
                    can_frame = CanFrame((0b11 << 27) | (frame_type << 24) | (dst_alias << 12) | self.node_alias, data, True, False)
                    self.can_tx(can_frame)
                    # some delay helps avoid dropped frames by slow nodes (or drivers?)
                    await asyncio.sleep(0.001)

                dg_result = await asyncio.wait_for(dg_future, timeout=5)
                if dg_result.type == "DatagramRejected":
                    raise ProtocolError("Error: Datagram was rejected")
                if expected_response:
                    res = await asyncio.wait_for(proto_future, timeout=5)
                    return res
                else:
                    return True

            except asyncio.TimeoutError:
                print("Timeout while waiting for LCC response")
                raise MissingResponse()

            finally:
                self.remove_handler(dg_filter)
                if expected_response:
                    self.remove_handler(expected_response)

    async def read_memory_configuration_block(self, dst_alias, address_space, starting_address, size):
        assert size >= 1 and size <= 64, f"Invalid size {size}"
        assert address_space is not None, "Address space is None"
        command = type_to_memory_config_map.get("ReadMemoryConfiguration") & 0b11111100
        if address_space >= 0xfd:
            command += address_space - 0xfc
        data = bytearray([0x20, command, *starting_address.to_bytes(4, byteorder='big')])
        if address_space < 0xfd:
            data.append(address_space)
        data += size.to_bytes(1, byteorder='big')
        response = await self.send_datagram(data, dst_alias, response_filter(data, self.node_alias, dst_alias))

        if response and response.type == "ReadMemoryConfigurationReplyFailure":
                raise ProtocolError("Error: Memory read failed")
        return response.inner.inner.inner.inner.inner.data

    async def write_memory_configuration_block(self, dst_alias, address_space, starting_address, payload):
        size = len(payload)
        assert size >= 1 and size <= 64, f"Invalid size {size}"
        assert address_space is not None, "Address space is None"
        command = type_to_memory_config_map.get("WriteMemoryConfiguration") & 0b11111100
        if address_space >= 0xfd:
            command += address_space - 0xfc
        data = bytearray([0x20, command, *starting_address.to_bytes(4, byteorder='big')])
        if address_space < 0xfd:
            data.append(address_space)
        data += payload
        response = await self.send_datagram(data, dst_alias, response_filter(data, self.node_alias, dst_alias))
        
        if response and response.type == "WriteMemoryConfigurationReplyFailure":
                raise ProtocolError("Error: Memory write failed")

    def add_handler(self, filter):
        # returns a future that waits for an incoming frame
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        with self.dynamic_handler_lock:
            def func(frame):
                if loop.is_running() and not future.done():
                    loop.call_soon_threadsafe(future.set_result, frame)
            self.dynamic_handlers[filter] = func
        return future

    def remove_handler(self, filter):
        with self.dynamic_handler_lock:
            del self.dynamic_handlers[filter]

    async def wait_for_response(self, filter):
        # waits for an incoming message that matches the filter predicate function
        future = self.add_handler(filter)
        try:
            res = await asyncio.wait_for(future, timeout = 5)
        except asyncio.TimeoutError:
            print("Timeout while waiting for LCC response")
            raise MissingResponse()
        except asyncio.CancelledError:
            raise
        finally:
            self.remove_handler(filter)
        return res

    async def read_memory_options(self, dst_alias):
        command = type_to_memory_config_map.get("GetMemoryConfigurationOptions")
        data = bytearray([0x20, command])
        response = await self.send_datagram(data, dst_alias, response_filter(data, self.node_alias, dst_alias))
        return response.inner.inner.inner.inner.inner
        
    async def read_memory_configuration(self, dst_alias, address_space, address, size, progress_callback=None):
        # read memory configuration data in blocks of 64 bytes
        buffer = b""
        while 1:
            block_size = min(size, 64)
            try:
                data = await self.read_memory_configuration_block(dst_alias, address_space, address+len(buffer), block_size)
            except MissingResponse:
                raise MissingResponse("Node didn't answer request for memory config read")
            buffer += data
            size -= len(data)
            if progress_callback: progress_callback(len(buffer))
            if len(data) != 64 or size == 0: break
        return buffer

    async def write_memory_configuration(self, dst_alias, address_space, address, payload, progress_callback=None):
        # read memory configuration data in blocks of 64 bytes
        offset = 0
        while 1:
            block_size = min(len(payload), 64)
            block = payload[:block_size]
            try:
                data = await self.write_memory_configuration_block(dst_alias, address_space, address+offset, block)
            except MissingResponse:
                raise MissingResponse("Node didn't answer request for memory config write")
            offset += block_size
            payload = payload[block_size:]
            if progress_callback: progress_callback(offset)
            if len(payload) == 0: break

    async def read_cdi(self, dst_alias, progress_callback=None):
        await asyncio.sleep(.05) # allow some time for previous datagrams to settle, compensates bugs in some TCS nodes
        try:
            # check if CDI is present
            data = bytearray([0x20])
            command = type_to_memory_config_map.get("GetMemoryConfigurationAddressSpaceInfo")
            data.append(command)
            address_space = 0xff
            data.append(address_space)

            try:
                response = await self.send_datagram(data, dst_alias, response_filter(data, self.node_alias, dst_alias))
            except MissingResponse:
                raise MissingResponse("Node didn't answer request for memory address space information")
            if response.type == "DatagramRejected":
                raise ProtocolError("Datagram was rejected")
            assert response.inner.inner.inner.inner.inner.present
            return await self.read_memory_configuration(dst_alias, address_space, 0, 0xffffffff, progress_callback)
        except asyncio.CancelledError as e:
            return None

    def run_future(self, future):
        # runs an async function as future in the connection executor thread
        # may be canceled by calling the returned function
        if not self.connection or not self.connection.loop or not self.connection.loop.is_running():
            raise RuntimeError("No connection")
        future = asyncio.run_coroutine_threadsafe(future, self.connection.loop)
        def cancel_future(future=future):
            if not self.connection or not self.connection.loop or not self.connection.loop.is_running():
                return
            self.connection.loop.call_soon_threadsafe(future.cancel)
        return future, cancel_future
        
    def generate_node_alias(self):
        self.node_alias = random.randint(0, 0xfff)

    def reserve_node_alias(self):
        if self.timer: self.timer.cancel()
        # according to 6.2.1
        self.generate_node_alias()
        print(f"Reserving node alias {self.node_alias:X}")
        # send CID frames
        self.lcc_control_set_state("reserving")
        try:
            self.send_cc_cid_frame(7, (self.node_id[0]<<4) | ((self.node_id[1] & 0xf0) >> 4))
            self.send_cc_cid_frame(6, ((self.node_id[1] & 0xf)<<8) | self.node_id[2])
            self.send_cc_cid_frame(5, (self.node_id[3]<<4) | ((self.node_id[4] & 0xf0) >> 4))
            self.send_cc_cid_frame(4, ((self.node_id[4] & 0xf)<<8) | self.node_id[5])
        except:
            # backoff and repeat
            self.timer = Timer(2, self.reserve_node_alias)
            self.timer.start()
            return

        self.timer = Timer(0.2, self.reserve_node_alias_2, (self.node_alias,))
        self.timer.start()

    def reserve_node_alias_2(self, res_node_alias):
        # check if we still want to reserve
        if self.lcc_control_state != "reserving": return
        # check if this reservation was canceled
        if self.node_alias != res_node_alias: return

        # reserve id
        if self.send_cc_frame("ReserveIDFrame"):
            # backoff and repeat
            self.timer = Timer(0.5, self.reserve_node_alias, self.node_alias)
            self.timer.start()
        else:
            # send Alias Map Definition
            self.send_cc_frame("AliasMapDefinitionFrame", self.node_id);
            self.lcc_control_set_state("permitted")

    def lcc_control_set_state(self, state):
        print("CAN control status", state)
        self.lcc_control_state = state
        self.lcc_update_state()

    def lcc_update_state(self):
        if self.lcc_control_state == "permitted" and self.lcc_message_state == "ready":
            if not self.send_mti_frame("InitializationComplete", self.node_id):
                self.lcc_message_state = "initialized"
                self.advertise_events()
        elif self.lcc_control_state != "permitted" and self.lcc_message_state == "initialized":
            # any other link layer change resets initialization
            self.lcc_message_state = "ready"

    def advertise_events(self):
        pass

    def frame_to_human_readable(self, lcc_frame):
        # format construct parser output into human-readable columns
        # always include innermost fields
        inner = lcc_frame
        flattened = {}
        while hasattr(inner, 'inner'):
            flattened |= inner
            inner = inner.inner
        if "type" in lcc_frame:
            # always show type
            fields_to_show = {'type': lcc_frame["type"]}
        # always show innermost container
        if inner:
            fields_to_show |= dict(inner.copy())
        fields_to_show.pop('_io', None)
        if "destination_alias" in flattened:
            fields_to_show["destination_alias"] = flattened["destination_alias"]
        if "source_alias" in flattened:
            fields_to_show["source_alias"] = flattened["source_alias"]
        result = fields_to_show.pop('type', '')
        args = ", ".join([f'{key}={value}' for key, value in fields_to_show.items()])
        return ", ".join([result, args])

    def parse_frame(self, frame, sent_by_us = None):
        if not frame.is_extended: return None
        if frame.is_remote: return None
        parsing_input = frame.id.to_bytes(4, byteorder='big')
        if frame.data: parsing_input += frame.data
        try:
            lcc_frame = LccFrame.parse(parsing_input)
        except Exception as e:
            print('LCC construct parsing failed:', e)
            print(traceback.format_exc())
            print(frame)
            return None

        destination_address = getattr(lcc_frame.inner.inner, "destination_address", None)
        if destination_address:
            # assemble addressed multipart frames
            key = (lcc_frame.source_alias, lcc_frame.destination_alias)
            if destination_address.multipart_flag == "only_frame":
                lcc_frame.multipart_data = frame.data[2:]
            elif destination_address.multipart_flag == "first_frame":
                self.multipart_data[key] = frame.data[2:]
            elif destination_address.multipart_flag == "last_frame":
                self.multipart_data[key] += frame.data[2:]
                lcc_frame.multipart_data = self.multipart_data[key]
            elif destination_address.multipart_flag == "middle_frame":
                self.multipart_data[key] += frame.data[2:]

            if lcc_frame.inner.inner.inner:
                payload_parser = lcc_frame.inner.inner.inner.pop("inner", None)
                if destination_address.is_complete:
                    # parse multipart data
                    if payload_parser:
                        lcc_frame.inner.inner.inner.inner = payload_parser.parse(lcc_frame.multipart_data)

        if lcc_frame.type == "Datagram":
            # assemble datagrams
            key = (lcc_frame.source_alias, lcc_frame.destination_alias)
            multipart_flag = lcc_frame.inner.inner.multipart_flag
            if multipart_flag == "only_frame":
                lcc_frame.multipart_data = frame.data
            elif multipart_flag == "first_frame":
                self.datagrams[key] = frame.data
            elif multipart_flag == "last_frame":
                self.datagrams[key] += frame.data
                lcc_frame.multipart_data = self.datagrams[key]
            elif multipart_flag == "middle_frame":
                self.datagrams[key] += frame.data

            lcc_frame.inner.inner.inner = None
            if lcc_frame.inner.inner.is_complete:
                # parse datagram
                lcc_frame.inner.inner.inner = DatagramProtocol.parse(lcc_frame.multipart_data)

        if self.frame_callback: self.frame_callback(lcc_frame, sent_by_us)
        if lcc_frame.type == "Datagram" and lcc_frame.inner.inner.is_complete and not sent_by_us:
            # send confirmation message
            self.send_mti_frame("DatagramReceivedOk", dst_alias = lcc_frame.source_alias)

        if sent_by_us: return lcc_frame

        # call frame handlers if this is a received frame
        if not lcc_frame.is_openlcb_message:
            self.handle_cc_frame(lcc_frame)
        handler = self.handlers.get(getattr(lcc_frame, "type", None))
        if handler:
            if self.connection and self.connection.loop and self.connection.loop.is_running():
                self.connection.loop.call_soon_threadsafe(handler, lcc_frame)

        # dynamic handlers
        with self.dynamic_handler_lock:
            for filter, func in self.dynamic_handlers.items():
                if filter(lcc_frame): func(lcc_frame)
        return lcc_frame

    def simple_node_information_request(self, con, dst_alias):
        con.send_message((0b11<<27) |(1<<24) | (0xDE8 << 12) | 0x777, dst_alias.to_bytes(2, byteorder='big'))

    def emit_event(self, event_id):
        if not self.connection:
            print("Can't send CAN frame because no transmitter was provided")
            return
        can_frame = CanFrame((0b11<<27) |(1<<24) | (0x5B4 << 12) | self.node_alias, id_to_bytes(event_id), True, False)
        self.can_tx(can_frame)

    def can_tx(self, can_frame):
        if self.connection is None:
            print("Error: Cannot send LCC frame without CAN connection")
            return
        self.parse_frame(can_frame, sent_by_us=True)
        self.connection.send(can_frame)
