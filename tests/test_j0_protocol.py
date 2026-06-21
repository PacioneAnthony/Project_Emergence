import struct

import pytest

from j0.cli import _audio_device_candidates, _prepare_serial_port
from j0.protocol import (
    HELLO_PAYLOAD,
    IMU_PAYLOAD,
    RANGE_PAYLOAD,
    SERVO_STATE_PAYLOAD,
    SYNC_PAYLOAD,
    Packet,
    PacketType,
    ProtocolError,
    StreamDecoder,
    decode_frame,
    make_estop,
    make_set_servo,
    make_sync_request,
    unpack_payload,
)
from j0.sync import estimate_sync, summarize_sync


def test_packet_round_trip_and_payload_decode():
    payload = IMU_PAYLOAD.pack(1, -2, 3, -4, 5, -6, 9)
    packet = Packet(PacketType.IMU_SAMPLE, 42, 123456, payload, flags=3)

    decoded = decode_frame(packet.encode())

    assert decoded == packet
    assert unpack_payload(decoded) == {
        "accel_raw": [1, -2, 3],
        "gyro_raw": [-4, 5, -6],
        "status": 9,
    }


def test_payload_sizes_match_firmware_contract():
    assert HELLO_PAYLOAD.size == 18
    assert IMU_PAYLOAD.size == 14
    assert RANGE_PAYLOAD.size == 8
    assert SERVO_STATE_PAYLOAD.size == 10
    assert SYNC_PAYLOAD.size == 20


def test_stream_decoder_handles_fragmentation():
    first = Packet(PacketType.E_STOP, 1, 10).encode()
    second = Packet(PacketType.E_STOP, 2, 20).encode()
    decoder = StreamDecoder()

    assert decoder.feed(first[:5]) == []
    packets = decoder.feed(first[5:] + second[:3])
    assert [packet.sequence_id for packet in packets] == [1]
    packets = decoder.feed(second[3:])
    assert [packet.sequence_id for packet in packets] == [2]


def test_stream_decoder_rejects_corruption_and_recovers_next_frame():
    corrupt = bytearray(Packet(PacketType.E_STOP, 1, 10).encode())
    corrupt[8] ^= 0x40
    valid = Packet(PacketType.E_STOP, 2, 20).encode()
    decoder = StreamDecoder()

    packets = decoder.feed(b"noise" + corrupt + valid)

    assert [packet.sequence_id for packet in packets] == [2]
    assert decoder.stats.crc_errors == 1
    assert decoder.stats.discarded_bytes >= 6


def test_servo_command_enforces_confirmed_limits():
    assert unpack_payload(make_set_servo(0, 0, 10.0))["requested_cdeg"] == 1000
    assert unpack_payload(make_set_servo(0, 0, 170.0))["requested_cdeg"] == 17000
    with pytest.raises(ValueError):
        make_set_servo(0, 0, 9.99)
    with pytest.raises(ValueError):
        make_set_servo(0, 0, 170.01)


def test_command_builders_use_expected_payloads():
    sync = make_sync_request(7, 12, 99, 123456789)
    assert unpack_payload(sync) == {"token": 99, "host_send_ns": 123456789}
    assert unpack_payload(make_estop(8, 13)) == {}


def test_decode_rejects_wrong_crc():
    frame = bytearray(Packet(PacketType.E_STOP, 1, 10).encode())
    frame[-1] ^= 1
    with pytest.raises(ProtocolError, match="CRC mismatch"):
        decode_frame(frame)


def test_ntp_style_sync_estimate_and_summary():
    estimate = estimate_sync(
        token=1,
        host_send_ns=1_000_000,
        host_receive_ns=1_300_000,
        device_receive_us=100,
        device_send_us=150,
    )
    assert estimate.round_trip_ns == 250_000
    assert estimate.device_to_host_offset_ns == 1_025_000
    summary = summarize_sync([estimate])
    assert summary["count"] == 1
    assert summary["jitter_ns"] == 0


def test_brio_audio_candidates_prefer_directsound_then_mme():
    devices = [
        {"name": "BRIO 100", "max_input_channels": 1, "hostapi": 2, "default_samplerate": 48000},
        {"name": "BRIO 100", "max_input_channels": 1, "hostapi": 1, "default_samplerate": 44100},
        {"name": "BRIO 100", "max_input_channels": 1, "hostapi": 0, "default_samplerate": 44100},
        {"name": "BRIO 100", "max_input_channels": 1, "hostapi": 3, "default_samplerate": 48000},
    ]
    hostapis = [
        {"name": "MME"},
        {"name": "Windows DirectSound"},
        {"name": "Windows WASAPI"},
        {"name": "Windows WDM-KS"},
    ]

    candidates = _audio_device_candidates(devices, hostapis)

    assert [candidate["hostapi"] for candidate in candidates] == [
        "Windows DirectSound",
        "MME",
        "Windows WASAPI",
        "Windows WDM-KS",
    ]
    assert candidates[0]["sample_rate_hz"] == 44100


def test_prepare_serial_port_discards_arduino_boot_bytes(monkeypatch):
    calls = []

    class FakeSerial:
        def reset_input_buffer(self):
            calls.append("input")

        def reset_output_buffer(self):
            calls.append("output")

    monkeypatch.setattr("j0.cli.time.sleep", lambda duration: calls.append(("sleep", duration)))

    _prepare_serial_port(FakeSerial(), 2.5)

    assert calls == [("sleep", 2.5), "input", "output"]
