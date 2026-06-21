"""Canonical asynchronous event contract for J0 sessions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any, Mapping

from j0.protocol import Packet, PacketType, ProtocolError, unpack_payload


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Event:
    session_id: str
    event_type: str
    source_id: str
    sequence_id: int
    source_timestamp_ns: int
    host_receive_timestamp_ns: int
    payload: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)
    calibration_version: str = "unversioned"
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("session_id is required")
        if not self.event_type or not self.source_id:
            raise ValueError("event_type and source_id are required")
        if self.sequence_id < 0:
            raise ValueError("sequence_id must be non-negative")
        if self.source_timestamp_ns < 0 or self.host_receive_timestamp_ns < 0:
            raise ValueError("timestamps must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Event":
        return cls(
            session_id=str(data["session_id"]),
            event_type=str(data["event_type"]),
            source_id=str(data["source_id"]),
            sequence_id=int(data["sequence_id"]),
            source_timestamp_ns=int(data["source_timestamp_ns"]),
            host_receive_timestamp_ns=int(data["host_receive_timestamp_ns"]),
            payload=dict(data.get("payload", {})),
            quality=dict(data.get("quality", {})),
            calibration_version=str(data.get("calibration_version", "unversioned")),
            schema_version=int(data.get("schema_version", SCHEMA_VERSION)),
        )

    @classmethod
    def from_json(cls, line: str) -> "Event":
        return cls.from_dict(json.loads(line))


class MicrosUnwrapper:
    """Extend Arduino's wrapping uint32 micros clock to a monotone integer."""

    WRAP = 1 << 32

    def __init__(self) -> None:
        self._last_raw: int | None = None
        self._epoch = 0

    def unwrap_ns(self, raw_us: int) -> int:
        raw_us &= 0xFFFFFFFF
        if self._last_raw is not None and raw_us < self._last_raw and self._last_raw - raw_us > self.WRAP // 2:
            self._epoch += self.WRAP
        self._last_raw = raw_us
        return (self._epoch + raw_us) * 1000


_EVENT_NAMES = {
    PacketType.DEVICE_HELLO: "device_hello",
    PacketType.IMU_SAMPLE: "imu_sample",
    PacketType.RANGE_SAMPLE: "range_sample",
    PacketType.SERVO_STATE: "servo_state",
    PacketType.SYNC_REPLY: "sync_reply",
    PacketType.ERROR: "device_error",
    PacketType.SET_SERVO: "servo_command",
    PacketType.SYNC_REQUEST: "sync_request",
    PacketType.E_STOP: "emergency_stop",
}


def event_from_packet(
    packet: Packet,
    *,
    session_id: str,
    source_id: str,
    host_receive_timestamp_ns: int,
    source_clock: MicrosUnwrapper,
    calibration_version: str,
    decoder_quality: Mapping[str, Any] | None = None,
) -> Event:
    try:
        packet_type = PacketType(packet.packet_type)
        event_type = _EVENT_NAMES[packet_type]
    except ValueError:
        event_type = f"unknown_packet_{packet.packet_type:02x}"

    try:
        payload = unpack_payload(packet)
        payload_valid = True
    except (ProtocolError, ValueError) as error:
        payload = {"raw_hex": packet.payload.hex(), "decode_error": str(error)}
        payload_valid = False

    quality = {"payload_valid": payload_valid, "protocol_version": packet.version, "flags": packet.flags}
    if decoder_quality:
        quality.update(decoder_quality)

    return Event(
        session_id=session_id,
        event_type=event_type,
        source_id=source_id,
        sequence_id=packet.sequence_id,
        source_timestamp_ns=source_clock.unwrap_ns(packet.source_time_us),
        host_receive_timestamp_ns=host_receive_timestamp_ns,
        payload=payload,
        quality=quality,
        calibration_version=calibration_version,
    )


def make_host_event(
    *,
    session_id: str,
    event_type: str,
    source_id: str,
    sequence_id: int,
    timestamp_ns: int,
    payload: Mapping[str, Any] | None = None,
    quality: Mapping[str, Any] | None = None,
    calibration_version: str = "host-v1",
) -> Event:
    return Event(
        session_id=session_id,
        event_type=event_type,
        source_id=source_id,
        sequence_id=sequence_id,
        source_timestamp_ns=timestamp_ns,
        host_receive_timestamp_ns=timestamp_ns,
        payload=dict(payload or {}),
        quality=dict(quality or {}),
        calibration_version=calibration_version,
    )
