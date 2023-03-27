from construct import *

class NodeIdAdapter(Adapter):
    def _decode(self, obj, context, path):
        return ".".join([f"{x:02X}" for x in obj])

    def _encode(self, obj, context, path):
        return bytearray.fromhex(obj.replace(".",""))

class EventIdAdapter(Adapter):
    def _decode(self, obj, context, path):
        res = obj.hex().upper()
        return res[:12] + '.' + res[12:]

    def _encode(self, obj, context, path):
        return bytearray.fromhex(obj.replace(".",""))

NodeId = NodeIdAdapter(Bytewise(Bytes(6)))
EventId = EventIdAdapter(Bytewise(Bytes(8)))

class Type(Subconstruct):
    # adds frame type to root context
    def __init__(self, type):
        self.name = None
        self.type = type
        self.flagbuildnone = True
        self.parsed = None

    def _parse(self, stream, context, path):
        context._root["type"] = self.type

class EmbedInRoot(Subconstruct):
    # adds the field to root context after parsing
    def __init__(self, name, type):
        super().__init__(type)
        self.name = name

    def _parse(self, stream, context, path):
        res = self.subcon._parse(stream, context, path)
        context._root[self.name] = res
        return res

    def _build(self, obj, stream, context, path):
        return self.subcon._build(self._encode(obj, context, path), stream, context, path)

MtiMultipartType = lambda type, payload_parser: Struct(
    Type(type),
    "inner" / Computed(payload_parser), # parsed after payload is reassembled
)

CanControlCheckIDFrame = Struct(
    Type("CanControlCheckIDFrame"),
    "frame_sequence_number" / Computed(this._.frame_sequence_number),
    "partial_node_id" / Computed(this._.cc_variable_field),
)

ReserveIDFrame = Struct(
    Type("ReserveIDFrame"),
)

AliasMapDefinitionFrame = Struct(
    Type("AliasMapDefinitionFrame"),
    "node_id" / NodeId,
)

AliasMappingEnquiryFrame = Struct(
    Type("AliasMappingEnquiryFrame"),
    "node_id" / Optional(NodeId)
)

AliasMapResetFrame = Struct(
    Type("AliasMapResetFrame"),
    "node_id" / NodeId,
)

ErrorInformationReport = Struct(
    Type("ErrorInformationReport"),
    "code" / Computed(this._.cc_variable_field & 0b11)
)

CanControlFrame = Struct(
    "is_check_id_frame" / Flag,
    "frame_sequence_number" / BitsInteger(2),
    "cc_variable_field" / Hex(BitsInteger(12)),
    "source_alias" / EmbedInRoot("source_alias", Hex(BitsInteger(12))),
    "inner" / Switch(this.is_check_id_frame, {
        True : CanControlCheckIDFrame,
        False: Switch(this.cc_variable_field, {
            0x700: ReserveIDFrame,
            0x701: AliasMapDefinitionFrame,
            0x702: AliasMappingEnquiryFrame,
            0x703: AliasMapResetFrame,
            0x710: ErrorInformationReport,
            0x711: ErrorInformationReport,
            0x712: ErrorInformationReport,
            0x713: ErrorInformationReport,
        })
    }),
)

InitializationComplete = Struct(
    Type("InitializationComplete"),
    "node_id" / NodeId
)

InitializationCompleteSimple = Struct(
    Type("InitializationCompleteSimple"),
    "node_id" / NodeId
)

VerifyNodeIdAddressed = Struct(
    Type("VerifyNodeIdAddressed"),
    "node_id" / Optional(NodeId)
)

VerifyNodeIdGlobal= Struct(
    Type("VerifyNodeIdGlobal"),
    "node_id" / Optional(NodeId)
)

VerifiedNodeId = Struct(
    Type("VerifiedNodeId"),
    "simple_set_sufficient" / Computed(this._.mti & 1),
    "node_id" / NodeId
)

OptionalInteractionRejected = Struct(
    Type("OptionalInteractionRejected"),
    "error_code" / BitsInteger(16)
)

TerminateDueToError = Struct(
    Type("TerminateDueToError"),
    "error_code" / BitsInteger(16)
)

ProtocolSupport = BitStruct(
    "SimpleProtocolSubset" / Optional(Flag),
    "DatagramProtocol" / Optional(Flag),
    "StreamProtocol" / Optional(Flag),
    "MemoryConfigurationProtocol" / Optional(Flag),
    "ReservationProtocol" / Optional(Flag),
    "EventExchangeProtocol" / Optional(Flag),
    "Identification Protocol" / Optional(Flag),
    "TeachingLearningConfigurationProtocol" / Optional(Flag),
    "RemoteButtonProtocol" / Optional(Flag),
    "AbbreviatedDefaultCDIProtocol" / Optional(Flag),
    "DisplayProtocol" / Optional(Flag),
    "SimpleNodeInformationProtocol" / Optional(Flag),
    "ConfigurationDescriptionInformation" / Optional(Flag),
    "TractionControlProtocol" / Optional(Flag),
    "FunctionDescriptionInformation" / Optional(Flag),
    "DccCommandStationProtocol" / Optional(Flag),
    "SimpleTrainNodeInformationProtocol" / Optional(Flag),
    "FunctionConfiguration" / Optional(Flag),
    "FirmwareUpgradeProtocol" / Optional(Flag),
    "FirmwareUpgradeActive" / Optional(Flag),
    Optional(Padding(4)),
    Bytewise(GreedyBytes),
)

ProducerConsumerReport = Struct(
    Type("ProducerConsumerReport"),
    "event_id" / EventId,
)

IdentifyConsumer = Struct(
    Type("IdentifyConsumer"),
    "event_id" / EventId,
)

ConsumerIdentified = Struct(
    Type("ConsumerIdentified"),
    "status" / Enum(Computed(this._.mti & 0b11), valid=0, invalid=1, unknown=3),
    "event_id" / EventId,
)

class EventIdRangeAdapter(Adapter):
    def _decode(self, obj, context, path):
        mask_count = 1
        while (obj >> mask_count) & 1 == obj & 1:
            mask_count += 1
        mask = (1 << mask_count) - 1
        lower_range = obj & (~mask)
        upper_range = obj | mask
        return f"{hex(lower_range)} - {hex(upper_range)}"

    def _encode(self, obj, context, path):
        # TODO
        return None

EventIdRange = EventIdRangeAdapter(BitsInteger(64))

ConsumerRangeIdentified = Struct(
    Type("ConsumerRangeIdentified"),
    "event_id_range" / EventIdRange,
)

IdentifyProducer = Struct(
    Type("IdentifyProducer"),
    "event_id_range" / EventIdRange,
)

ProducerIdentified = Struct(
    Type("ProducerIdentified"),
    "status" / Enum(Computed(this._.mti & 0b11), valid=0, invalid=1, unknown=3),
    "event_id" / EventId,
)

ProducerRangeIdentified = Struct(
    Type("ProducerRangeIdentified"),
    "event_id_range" / EventIdRange,
)

IdentifyEvents = Struct(
    Type("IdentifyEvents"),
    "destination_node_id" / Optional(NodeId),
)

LearnEvent = Struct(
    Type("LearnEvent"),
    "event_id" / EventId
)

SimpleNodeInformation = Struct(
    "version_fixed_fields" / Byte,
    "fixed_fields" / Switch(this.version_fixed_fields, {
        1: Struct(
            "manufacturer_name" / CString("utf8"),
        ),
        4: Struct(
            "manufacturer_name" / CString("utf8"),
            "model_name" / CString("utf8"),
            "hardware_version" / CString("utf8"),
            "software_version" / CString("utf8"),
        ),
    }),
    "version_user_fields" / Byte,
    "user_fields" / Switch(this.version_user_fields, {
        1: Struct(
            "node_name" / CString("utf8"),
        ),
        2: Struct(
            "node_name" / CString("utf8"),
            "node_description" / CString("utf8"),
        ),
    }),
)

MtiMessage = Struct(
    "mti" / Hex(Computed(this._.variable_field)),
    "destination_address" / If(this._.variable_field & 0b1000, Struct(
        "multipart_flag" / Enum(BitsInteger(4), only_frame=0, first_frame=1, last_frame=2, middle_frame=3),
        "is_complete" / Computed(lambda this: this.multipart_flag in ["only_frame", "last_frame"]),
        "destination_alias" / EmbedInRoot("destination_alias", BitsInteger(12)),
        "payload" / Bytewise(GreedyBytes), # potential multipart payload
    )),
    "inner" / Switch(this.mti, {
        # basic messages
        0x100: InitializationComplete,
        0x101: InitializationCompleteSimple,
        0x488: VerifyNodeIdAddressed,
        0x490: VerifyNodeIdGlobal,
        0x170: VerifiedNodeId,
        0x171: VerifiedNodeId,
         0x68: OptionalInteractionRejected,
         0xA8: TerminateDueToError,
        0x828: Type("ProtocolSupportInquiry"),
        0x668: MtiMultipartType("ProtocolSupportReply", ProtocolSupport),

        # events
        0x5B4: ProducerConsumerReport,
        0x8F4: IdentifyConsumer,
        0x4C4: ConsumerIdentified,
        0x4C5: ConsumerIdentified,
        0x4C7: ConsumerIdentified,
        0x4A4: ConsumerRangeIdentified,
        0x914: IdentifyProducer,
        0x544: ProducerIdentified,
        0x545: ProducerIdentified,
        0x547: ProducerIdentified,
        0x524: ProducerRangeIdentified,
        0x970: IdentifyEvents,
        0x968: IdentifyEvents,
        0x594: LearnEvent,

        # traction control
        0x5EB: Type("MTI_TRACTION_CONTROL_COMMAND"),
        0x1e9: Type("MTI_TRACTION_CONTROL_REPLY"),
        0x5ea: Type("MTI_TRACTION_PROXY_COMMAND"),
        0x1e8: Type("MTI_TRACTION_PROXY_REPLY"),

        # Other
        0x820: Type("MTI_XPRESSNET"),

        # Remote button
        0x948: Type("MTI_REMOTE_BUTTON_REQUEST"),
        0x549: Type("MTI_REMOTE_BUTTON_REPLY"),

        # Traction ident
        0xDA8: Type("MTI_SIMPLE_TRAIN_NODE_IDENT_INFO_REQUEST"),
        0x9C8: Type("MTI_SIMPLE_TRAIN_NODE_IDENT_INFO_REPLY"),

        # Simple Node ident
        0xDE8: Type("SimpleNodeIdentInfoRequest"),
        0xA08: MtiMultipartType("SimpleNodeIdentInfoReply", SimpleNodeInformation),

        # Datagram
        0xA28: Type("DatagramReceivedOk"),
        0xA48: Type("DatagramRejected"),

        # Stream
        0xcc8: Type("MTI_STREAM_INITIATE_REQUEST"),
        0x868: Type("MTI_STREAM_INITIATE_REPLY"),
        0x888: Type("MTI_STREAM_DATA_PROCEED"),
        0x8a8: Type("MTI_STREAM_DATA_COMPLETE"),
        },
        default = Type("UnknownMtiMessage"),
    ),
)

Datagram = Struct(
    Type("Datagram"),
    "destination_alias" / EmbedInRoot("destination_alias", Computed(this._.variable_field)),
    "inner" / Bytewise(GreedyBytes),
    "multipart_flag" / Enum(Computed(this._.frame_type), only_frame=2, first_frame=3, middle_frame=4, last_frame=5),
    "is_complete" / Computed(lambda this: this.multipart_flag in ["only_frame", "last_frame"]),
)

Stream = Struct(
    Type("Stream")
)

OpenLcbMessage = Struct(
    "frame_type" / BitsInteger(3),
    "variable_field" / Hex(BitsInteger(12)),
    "source_alias" / EmbedInRoot("source_alias", Hex(BitsInteger(12))),
    "inner" / Switch(this.frame_type, {
        1: MtiMessage,
        2: Datagram, # single
        3: Datagram, # first
        4: Datagram, # middle
        5: Datagram, # final
        7: Stream
        },
        default=Type("InvalidFrame")
    ),
)

# can frame is formatted as 4 bytes of ext_id, 0-8 bytes of data
LccFrame = BitStruct(
    Padding(3),
    "priority" / Flag,
    "is_openlcb_message" / Flag,
    "inner"
    / Switch(this.is_openlcb_message, {
        True: OpenLcbMessage,
        False: CanControlFrame,
    }),
    "extra_data" / Bytewise(GreedyBytes),

    # embedded fields
    "type" / Computed(this.type),
    "source_alias" / Computed(lambda this: getattr(this, "source_alias", None)),
    "destination_alias" / Computed(lambda this: getattr(this, "destination_alias", None)),
)

# Memory Configuration Protocol
ReadMemoryConfiguration = Struct(
    Type("ReadMemoryConfiguration"),
    "starting_address" / Int32ub,
    "address_space" / IfThenElse(
        this._.command & 0b11 == 0, 
        Byte,
        Computed(0xFC + (this._.command & 0b11))
    ),
    "read_count" / Byte
)

ReadMemoryConfigurationReply = Struct(
    Type("ReadMemoryConfigurationReply"),
    "starting_address" / Int32ub,
    "address_space" / IfThenElse(
        this._.command & 0b11 == 0, 
        Byte,
        Computed(0xFC + (this._.command & 0b11))
    ),
    "data" / GreedyBytes
)

ReadMemoryConfigurationReplyFailure = Struct(
    Type("ReadMemoryConfigurationReplyFailure"),
    "starting_address" / Int32ub,
    "address_space" / IfThenElse(
        this._.command & 0b11 == 0, 
        Byte,
        Computed(0xFC + (this._.command & 0b11))
    ),
    "error_code" / Int16ub,
    "data" / GreedyBytes
)

WriteMemoryConfiguration = Struct(
    Type("WriteMemoryConfiguration"),
    "starting_address" / Int32ub,
    "address_space" / IfThenElse(
        this._.command & 0b11 == 0, 
        Byte,
        Computed(0xFC + (this._.command & 0b11))
    ),
    "data" / GreedyBytes
)

WriteMemoryConfigurationReply = Struct(
    Type("WriteMemoryConfigurationReply"),
    "starting_address" / Int32ub,
    "address_space" / IfThenElse(
        this._.command & 0b11 == 0, 
        Byte,
        Computed(0xFC + (this._.command & 0b11))
    )
)

WriteMemoryConfigurationReplyFailure = Struct(
    Type("WriteMemoryConfigurationReplyFailure"),
    "starting_address" / Int32ub,
    "address_space" / IfThenElse(
        this._.command & 0b11 == 0, 
        Byte,
        Computed(0xFC + (this._.command & 0b11))
    ),
    "error_code" / Int16ub,
    "data" / GreedyBytes
)

GetMemoryConfigurationOptionsReply = Struct(
    Type("GetMemoryConfigurationOptionsReply"),
    "available_commands" / BitStruct(
        "write_under_mask" / Flag,
        "unaligned_read" / Flag,
        "unaligned_write" / Flag,
        Padding(5),
        "read_space_fc" / Flag,
        "read_space_fb" / Flag,
        "write_space_fb" / Flag,
        Padding(5),
    ),
    "write_lengths" / BitStruct(
        "1_byte" / Flag,
        "2_byte" / Flag,
        "4_byte" / Flag,
        "64_byte" / Flag,
        Padding(2),
        "arbitrary" / Flag,
        "stream_support" / Flag,
    ),
    "highest_address_space" / Byte,
    "lowest_address_space" / Optional(Byte),
    "name" / Optional(CString("utf8")),
)

GetMemoryConfigurationAddressSpaceInfo = Struct(
    Type("GetMemoryConfigurationAddressSpaceInfo"),
    "address_space" / Byte
)

GetMemoryConfigurationAddressSpaceInfoReply = Struct(
    Type("GetMemoryConfigurationAddressSpaceInfoReply"),
    "present" / Computed(this._.command & 1),
    "address_space" / Byte,
    "inner" / Optional(Struct(
        "highest_address" / Int32ub,
        "flags" / Byte,
        "read_only" / Computed(this.flags & 1),
        "lowest_address" / IfThenElse(this.flags & 0b10, Int32ub, Computed(0)),
        "description" / CString("utf8"),
    )),
)

MemoryConfiguration = Struct(
    "command" / Byte,
    "inner" / Switch(this.command, {
        0x40: ReadMemoryConfiguration,
        0x41: ReadMemoryConfiguration,
        0x42: ReadMemoryConfiguration,
        0x43: ReadMemoryConfiguration,
        0x50: ReadMemoryConfigurationReply,
        0x51: ReadMemoryConfigurationReply,
        0x52: ReadMemoryConfigurationReply,
        0x53: ReadMemoryConfigurationReply,
        0x58: ReadMemoryConfigurationReplyFailure,
        0x59: ReadMemoryConfigurationReplyFailure,
        0x5A: ReadMemoryConfigurationReplyFailure,
        0x5B: ReadMemoryConfigurationReplyFailure,

        0x00: WriteMemoryConfiguration,
        0x01: WriteMemoryConfiguration,
        0x02: WriteMemoryConfiguration,
        0x03: WriteMemoryConfiguration,
        0x10: WriteMemoryConfigurationReply,
        0x11: WriteMemoryConfigurationReply,
        0x12: WriteMemoryConfigurationReply,
        0x13: WriteMemoryConfigurationReply,
        0x18: WriteMemoryConfigurationReplyFailure,
        0x19: WriteMemoryConfigurationReplyFailure,
        0x1A: WriteMemoryConfigurationReplyFailure,
        0x1B: WriteMemoryConfigurationReplyFailure,

        0x80: Type("GetMemoryConfigurationOptions"),
        0x82: GetMemoryConfigurationOptionsReply,

        0x84: GetMemoryConfigurationAddressSpaceInfo,
        0x86: GetMemoryConfigurationAddressSpaceInfoReply,
        0x87: GetMemoryConfigurationAddressSpaceInfoReply,
    }),
)

DatagramProtocol = Struct(
    "protocol_type" / Byte,
    "inner" / Switch(this.protocol_type, {
        0x20: MemoryConfiguration,
    }),
    "type" / Computed(this.type),
)


### utilities for generating LCC can frames

def traverse_subcons(sc, keyfunc, number, save_types=None):
    # traverses message definitions and saves a map of {type_name: number} pairs
    result = {}
    for child in getattr(sc, "subcons", []):
        result |= traverse_subcons(child, keyfunc, number, save_types)
    if hasattr(sc, "subcon"): 
        result |= traverse_subcons(sc.subcon, keyfunc, number, save_types)
    if isinstance(sc, Switch):
        if sc.keyfunc._Path__field == keyfunc:
            save_types=1
        for key, child in sc.cases.items():
            result |= traverse_subcons(child, keyfunc, key, save_types)
    if isinstance(sc, Type):
        if number and save_types:
            result |= {sc.type: number}
    return result

type_to_mti_map = traverse_subcons(LccFrame.subcon, "mti", None)
type_to_cc_map = traverse_subcons(LccFrame.subcon, "cc_variable_field", None)
type_to_memory_config_map = traverse_subcons(DatagramProtocol, "command", None)


### utilities for waiting on expected responses

def get_memory_config_reply_command(request_command):
    # returns value and mask of response code
    if request_command < 0x80:
        return request_command + 0x10, 0xf0
    elif request_command == 0x80: return 0x82, 0xff
    elif request_command == 0x84: return 0x86, 0xfe
    elif request_command == 0x88: return 0x8a, 0xff
    elif request_command == 0x8c: return 0x8d, 0xff
    return None # no reply is expected

def datagram_response_filter(requestor_alias, responder_alias):
    def response_filter(frame):
        return frame.destination_alias == requestor_alias and frame.source_alias == responder_alias \
            and frame.type in ["DatagramReceivedOk", "DatagramRejected"]
    return response_filter

def response_filter(request_datagram, requestor_alias, responder_alias):
    # returns a filter function that matches valid response frames for a given request
    if request_datagram[0] != 0x20:
        print("Unsupported datagram protocol", request_datagram[0])
        return lambda: False

    command = request_datagram[1]
    response_command, response_mask = get_memory_config_reply_command(command)
    def response_filter(frame):
        if frame.destination_alias != requestor_alias or frame.source_alias != responder_alias: return False
        if frame.type != "Datagram": return False
        datagram = frame.inner.inner.inner
        if not datagram: return False # incomplete
        return datagram.protocol_type == 0x20 and datagram.inner.command & response_mask == response_command & response_mask
    return response_filter
