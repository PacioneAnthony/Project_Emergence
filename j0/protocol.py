"""Versioned binary serial protocol shared by J0 host tools and firmware."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import struct
from typing import Iterable, Iterator


MAGIC = b"\xA5\x5A"
PROTOCOL_VERSION = 1
HEADER = struct.Struct("<2sBBBBHII")
CRC = struct.Struct("<H")
MAX_PAYLOAD_SIZE = 512


class ProtocolError(ValueError):
    """Raised when a complete frame violates the EMG1 contract."""


class PacketType(IntEnum):
    DEVICE_HELLO = 0x01
    IMU_SAMPLE = 0x10
    RANGE_SAMPLE = 0x11
    SERVO_STATE = 0x12
    SYNC_REPLY = 0x20
    ERROR = 0x7F
    SET_SERVO = 0x80
    SYNC_REQUEST = 0x81
    E_STOP = 0x82


class Capability(IntEnum):
    IMU = 1 << 0
    ULTRASONIC = 1 << 1
    PIEZO = 1 << 2
    SERVO = 1 << 3
    TIME_SYNC = 1 << 4


class StatusFlag(IntEnum):
    VALID = 1 << 0
    TIMEOUT = 1 << 1
    SATURATED = 1 << 2
    IMU_PRESENT = 1 << 3
    FAILSAFE = 1 << 4


@dataclass(frozen=True)
class Packet:
    packet_type: int
    sequence_id: int
    source_time_us: int
    payload: bytes = b""
    flags: int = 0
    version: int = PROTOCOL_VERSION

    def encode(self) -> bytes:
        return encode_packet(self)


@dataclass(frozen=True)
class DecoderStats:
    decoded_frames: int
    crc_errors: int
    version_errors: int
    length_errors: int
    discarded_bytes: int


def crc16_ccitt(data: bytes, initial: int = 0xFFFF) -> int:
    """CRC-16/CCITT-FALSE, polynomial 0x1021."""

    crc = initial
    for value in data:
        crc ^= value << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def encode_packet(packet: Packet) -> bytes:
    payload = bytes(packet.payload)
    if len(payload) > MAX_PAYLOAD_SIZE:
        raise ProtocolError(f"payload too large: {len(payload)} > {MAX_PAYLOAD_SIZE}")
    if not 0 <= packet.packet_type <= 0xFF:
        raise ProtocolError("packet type must fit in one byte")

    header = HEADER.pack(
        MAGIC,
        packet.version,
        packet.packet_type,
        packet.flags,
        0,
        len(payload),
        packet.sequence_id & 0xFFFFFFFF,
        packet.source_time_us & 0xFFFFFFFF,
    )
    protected = header[2:] + payload
    return header + payload + CRC.pack(crc16_ccitt(protected))


def decode_frame(frame: bytes) -> Packet:
    if len(frame) < HEADER.size + CRC.size:
        raise ProtocolError("frame shorter than fixed header and CRC")

    magic, version, packet_type, flags, reserved, payload_length, sequence_id, source_time_us = HEADER.unpack_from(frame)
    if magic != MAGIC:
        raise ProtocolError("invalid magic")
    if version != PROTOCOL_VERSION:
        raise ProtocolError(f"unsupported protocol version: {version}")
    if reserved != 0:
        raise ProtocolError("reserved header byte must be zero")
    if payload_length > MAX_PAYLOAD_SIZE:
        raise ProtocolError(f"payload length exceeds limit: {payload_length}")

    expected_size = HEADER.size + payload_length + CRC.size
    if len(frame) != expected_size:
        raise ProtocolError(f"frame size mismatch: {len(frame)} != {expected_size}")

    expected_crc = CRC.unpack_from(frame, expected_size - CRC.size)[0]
    actual_crc = crc16_ccitt(frame[2 : expected_size - CRC.size])
    if actual_crc != expected_crc:
        raise ProtocolError(f"CRC mismatch: {actual_crc:#06x} != {expected_crc:#06x}")

    payload = frame[HEADER.size : expected_size - CRC.size]
    return Packet(packet_type, sequence_id, source_time_us, payload, flags, version)


class StreamDecoder:
    """Incremental decoder that recovers after noise, truncation, or bad CRC."""

    def __init__(self, max_payload_size: int = MAX_PAYLOAD_SIZE):
        self.max_payload_size = max_payload_size
        self._buffer = bytearray()
        self._decoded_frames = 0
        self._crc_errors = 0
        self._version_errors = 0
        self._length_errors = 0
        self._discarded_bytes = 0

    @property
    def stats(self) -> DecoderStats:
        return DecoderStats(
            self._decoded_frames,
            self._crc_errors,
            self._version_errors,
            self._length_errors,
            self._discarded_bytes,
        )

    def feed(self, data: bytes | bytearray | memoryview) -> list[Packet]:
        self._buffer.extend(data)
        packets: list[Packet] = []

        while True:
            magic_index = self._buffer.find(MAGIC)
            if magic_index < 0:
                keep = 1 if self._buffer.endswith(MAGIC[:1]) else 0
                discard = len(self._buffer) - keep
                if discard:
                    del self._buffer[:discard]
                    self._discarded_bytes += discard
                break
            if magic_index:
                del self._buffer[:magic_index]
                self._discarded_bytes += magic_index
            if len(self._buffer) < HEADER.size:
                break

            version = self._buffer[2]
            if version != PROTOCOL_VERSION:
                del self._buffer[0]
                self._version_errors += 1
                self._discarded_bytes += 1
                continue

            payload_length = struct.unpack_from("<H", self._buffer, 6)[0]
            if payload_length > self.max_payload_size:
                del self._buffer[0]
                self._length_errors += 1
                self._discarded_bytes += 1
                continue

            frame_size = HEADER.size + payload_length + CRC.size
            if len(self._buffer) < frame_size:
                break

            frame = bytes(self._buffer[:frame_size])
            try:
                packet = decode_frame(frame)
            except ProtocolError as error:
                if "CRC mismatch" in str(error):
                    self._crc_errors += 1
                else:
                    self._length_errors += 1
                del self._buffer[0]
                self._discarded_bytes += 1
                continue

            del self._buffer[:frame_size]
            self._decoded_frames += 1
            packets.append(packet)

        return packets


def decode_chunks(chunks: Iterable[bytes]) -> Iterator[Packet]:
    decoder = StreamDecoder()
    for chunk in chunks:
        yield from decoder.feed(chunk)


HELLO_PAYLOAD = struct.Struct("<IIHHHHBB")
IMU_PAYLOAD = struct.Struct("<hhhhhhH")
RANGE_PAYLOAD = struct.Struct("<HHHH")
SERVO_STATE_PAYLOAD = struct.Struct("<IHHH")
SYNC_PAYLOAD = struct.Struct("<IQII")
SET_SERVO_PAYLOAD = struct.Struct("<H")
SYNC_REQUEST_PAYLOAD = struct.Struct("<IQ")
ERROR_PAYLOAD = struct.Struct("<HH")


def unpack_payload(packet: Packet) -> dict[str, int | list[int]]:
    """Decode known payloads into JSON-compatible values."""

    try:
        packet_type = PacketType(packet.packet_type)
    except ValueError:
        return {"raw_hex": packet.payload.hex()}

    if packet_type == PacketType.DEVICE_HELLO:
        values = HELLO_PAYLOAD.unpack(packet.payload)
        return dict(
            device_id=values[0],
            capabilities=values[1],
            imu_rate_hz=values[2],
            range_rate_hz=values[3],
            servo_min_cdeg=values[4],
            servo_max_cdeg=values[5],
            imu_who_am_i=values[6],
            firmware_patch=values[7],
        )
    if packet_type == PacketType.IMU_SAMPLE:
        ax, ay, az, gx, gy, gz, status = IMU_PAYLOAD.unpack(packet.payload)
        return {"accel_raw": [ax, ay, az], "gyro_raw": [gx, gy, gz], "status": status}
    if packet_type == PacketType.RANGE_SAMPLE:
        distance_mm, piezo_raw, target_cdeg, status = RANGE_PAYLOAD.unpack(packet.payload)
        return {
            "distance_mm": distance_mm,
            "piezo_raw": piezo_raw,
            "servo_target_cdeg": target_cdeg,
            "status": status,
        }
    if packet_type == PacketType.SERVO_STATE:
        command_sequence, requested_cdeg, applied_cdeg, status = SERVO_STATE_PAYLOAD.unpack(packet.payload)
        return {
            "command_sequence": command_sequence,
            "requested_cdeg": requested_cdeg,
            "applied_cdeg": applied_cdeg,
            "status": status,
        }
    if packet_type == PacketType.SYNC_REPLY:
        token, host_send_ns, device_receive_us, device_send_us = SYNC_PAYLOAD.unpack(packet.payload)
        return {
            "token": token,
            "host_send_ns": host_send_ns,
            "device_receive_us": device_receive_us,
            "device_send_us": device_send_us,
        }
    if packet_type == PacketType.SET_SERVO:
        return {"requested_cdeg": SET_SERVO_PAYLOAD.unpack(packet.payload)[0]}
    if packet_type == PacketType.SYNC_REQUEST:
        token, host_send_ns = SYNC_REQUEST_PAYLOAD.unpack(packet.payload)
        return {"token": token, "host_send_ns": host_send_ns}
    if packet_type == PacketType.E_STOP:
        if packet.payload:
            raise ProtocolError("E_STOP payload must be empty")
        return {}
    if packet_type == PacketType.ERROR:
        code, context = ERROR_PAYLOAD.unpack(packet.payload)
        return {"code": code, "context": context}
    return {"raw_hex": packet.payload.hex()}


def make_set_servo(sequence_id: int, source_time_us: int, angle_deg: float) -> Packet:
    angle_cdeg = round(angle_deg * 100)
    if not 1000 <= angle_cdeg <= 17000:
        raise ValueError("servo angle must be within 10 to 170 degrees")
    return Packet(PacketType.SET_SERVO, sequence_id, source_time_us, SET_SERVO_PAYLOAD.pack(angle_cdeg))


def make_sync_request(sequence_id: int, source_time_us: int, token: int, host_send_ns: int) -> Packet:
    return Packet(
        PacketType.SYNC_REQUEST,
        sequence_id,
        source_time_us,
        SYNC_REQUEST_PAYLOAD.pack(token & 0xFFFFFFFF, host_send_ns & 0xFFFFFFFFFFFFFFFF),
    )


def make_estop(sequence_id: int, source_time_us: int) -> Packet:
    return Packet(PacketType.E_STOP, sequence_id, source_time_us)
