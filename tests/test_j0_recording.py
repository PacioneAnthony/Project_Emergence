import json
from pathlib import Path
import time

import pytest

from j0.events import Event, MicrosUnwrapper, make_host_event
from j0.capture import SerialCapture
from j0.clap import _audio_impacts, _audio_impulse, analyze_clap
from j0.clock import host_clock_metadata
from j0.mechanics import analyze_mechanics
from j0.protocol import IMU_PAYLOAD, Packet, PacketType
from j0.quality import analyze_session
from j0.recorder import QuotaExceededError, QuotaPolicy, SessionRecorder
from j0.replay import SessionReplay


def event(session_id: str, sequence: int, timestamp_ns: int, *, event_type: str = "imu_sample") -> Event:
    return make_host_event(
        session_id=session_id,
        event_type=event_type,
        source_id=f"test.{event_type}",
        sequence_id=sequence,
        timestamp_ns=timestamp_ns,
        payload={"value": sequence},
    )


def test_recorder_replay_is_deterministic(tmp_path: Path):
    with SessionRecorder(tmp_path, session_id="session-a", fsync_every_events=0) as recorder:
        for sequence in range(3):
            recorder.append(event(recorder.session_id, sequence, 1_000_000_000 + sequence * 10_000_000))

    replay = SessionReplay(tmp_path / "sessions" / "session-a")
    direct = replay.stats()
    observed = []
    played = replay.play(observed.append, speed=0)

    assert [item.sequence_id for item in observed] == [0, 1, 2]
    assert played == direct
    manifest = replay.manifest()
    assert manifest["status"] == "complete"
    assert manifest["event_count"] == 3


def test_blob_stream_records_offsets_and_hashes(tmp_path: Path):
    with SessionRecorder(tmp_path, session_id="session-blob", fsync_every_events=0) as recorder:
        first = recorder.append_blob_stream(
            kind="audio",
            stream_name="audio.pcm",
            data=b"abcd",
            event=event(recorder.session_id, 0, 1, event_type="audio_chunk"),
        )
        second = recorder.append_blob_stream(
            kind="audio",
            stream_name="audio.pcm",
            data=b"ef",
            event=event(recorder.session_id, 1, 2, event_type="audio_chunk"),
        )

    assert first.payload["blob_offset"] == 0
    assert second.payload["blob_offset"] == 4
    assert (tmp_path / "sessions" / "session-blob" / "blobs" / "audio" / "audio.pcm").read_bytes() == b"abcdef"


def test_quality_detects_corrupted_blob(tmp_path: Path):
    with SessionRecorder(tmp_path, session_id="session-corrupt", fsync_every_events=0) as recorder:
        recorder.append_blob_stream(
            kind="audio",
            stream_name="audio.pcm",
            data=b"abcd",
            event=event(recorder.session_id, 0, 1, event_type="audio_chunk"),
        )
    blob = tmp_path / "sessions" / "session-corrupt" / "blobs" / "audio" / "audio.pcm"
    blob.write_bytes(b"abXd")

    report = analyze_session(blob.parents[2])

    assert report["blob_errors"][0]["error"] == "blob_hash_mismatch"
    assert report["passes_integrity_rules"] is False


def test_replay_ignores_only_truncated_final_line(tmp_path: Path):
    with SessionRecorder(tmp_path, session_id="session-tail", fsync_every_events=0) as recorder:
        recorder.append(event(recorder.session_id, 0, 1))
    events_path = tmp_path / "sessions" / "session-tail" / "events.jsonl"
    with events_path.open("ab") as stream:
        stream.write(b'{"incomplete":')

    stats = SessionReplay(events_path.parent).stats()

    assert stats.event_count == 1
    assert stats.ignored_trailing_bytes == len(b'{"incomplete":')


def test_quota_blocks_long_session_at_stop_threshold(tmp_path: Path):
    (tmp_path / "existing.bin").write_bytes(b"12345678")
    quota = QuotaPolicy(budget_bytes=10, warning_bytes=6, stop_long_session_bytes=8)

    with pytest.raises(QuotaExceededError):
        SessionRecorder(tmp_path, quota=quota, long_session=True)


def test_quality_detects_rate_and_sequence_gap(tmp_path: Path):
    with SessionRecorder(tmp_path, session_id="session-quality", fsync_every_events=0) as recorder:
        recorder.append(event(recorder.session_id, 0, 0))
        recorder.append(event(recorder.session_id, 2, 100_000_000))

    report = analyze_session(tmp_path / "sessions" / "session-quality")

    kinds = {item["kind"] for item in report["violations"]}
    assert {"low_rate", "large_gap", "sequence_gap"}.issubset(kinds)
    assert report["passes_integrity_rules"] is False


def test_micros_unwrapper_handles_uint32_rollover():
    clock = MicrosUnwrapper()
    before = clock.unwrap_ns(0xFFFFFFF0)
    after = clock.unwrap_ns(0x00000010)
    assert after > before
    assert after - before == 32_000


def test_serial_capture_records_decoded_packet(tmp_path: Path):
    class FakeSerial:
        def __init__(self, data: bytes):
            self.data = bytearray(data)
            self.written = bytearray()

        @property
        def in_waiting(self):
            return len(self.data)

        def read(self, size: int):
            if not self.data:
                time.sleep(0.001)
                return b""
            chunk = bytes(self.data[:size])
            del self.data[:size]
            return chunk

        def write(self, data: bytes):
            self.written.extend(data)
            return len(data)

    packet = Packet(
        PacketType.IMU_SAMPLE,
        3,
        1000,
        IMU_PAYLOAD.pack(1, 2, 3, 4, 5, 6, 9),
    )
    fake = FakeSerial(packet.encode())
    with SessionRecorder(tmp_path, session_id="session-serial", fsync_every_events=0) as recorder:
        capture = SerialCapture(fake, recorder)
        capture.start()
        deadline = time.monotonic() + 1
        while capture.decoder.stats.decoded_frames < 1 and time.monotonic() < deadline:
            time.sleep(0.005)
        capture.stop()

    events = list(SessionReplay(tmp_path / "sessions" / "session-serial").events())
    assert len(events) == 1
    assert events[0].source_id == "arduino.imu"
    assert events[0].payload["gyro_raw"] == [4, 5, 6]


def test_clap_analysis_aligns_audio_and_imu_peak(tmp_path: Path):
    with SessionRecorder(tmp_path, session_id="session-clap", fsync_every_events=0) as recorder:
        for sequence, (timestamp, sample) in enumerate([(900_000_000, 10), (1_000_000_000, 20000), (1_100_000_000, 10)]):
            audio_event = make_host_event(
                session_id=recorder.session_id,
                event_type="audio_chunk",
                source_id="microphone.test",
                sequence_id=sequence,
                timestamp_ns=timestamp,
                payload={"sample_format": "pcm_s16le"},
            )
            recorder.append_blob_stream(
                kind="audio",
                stream_name="audio.pcm",
                data=int(sample).to_bytes(2, "little", signed=True) * 100,
                event=audio_event,
            )
        for sequence, (timestamp, accel) in enumerate(
            [(900_000_000, [0, 0, 100]), (1_010_000_000, [1000, 0, 100]), (1_100_000_000, [0, 0, 100])]
        ):
            recorder.append(
                make_host_event(
                    session_id=recorder.session_id,
                    event_type="imu_sample",
                    source_id="arduino.imu",
                    sequence_id=sequence,
                    timestamp_ns=timestamp,
                    payload={"accel_raw": accel, "gyro_raw": [0, 0, 0]},
                )
            )

    report = analyze_clap(tmp_path / "sessions" / "session-clap")

    assert report["offsets_from_audio_ms"]["imu"] == pytest.approx(10.0)
    assert report["passes_20ms_target"] is True


def test_audio_impulse_uses_peak_sample_timestamp():
    samples = [1] * 100
    samples[25] = 20_000
    audio_event = make_host_event(
        session_id="session-audio-time",
        event_type="audio_chunk",
        source_id="microphone.test",
        sequence_id=0,
        timestamp_ns=1_000_000_000,
        payload={"sample_rate_hz": 1000},
        quality={"timestamp_source": "sample_count_anchored_to_portaudio_adc"},
    )
    data = b"".join(int(sample).to_bytes(2, "little", signed=True) for sample in samples)

    timestamp_ns, score = _audio_impulse(audio_event, data)

    assert timestamp_ns == 1_025_000_000
    assert score > 1000


def test_audio_impacts_preserve_multiple_distinct_taps():
    scores = [
        (0, 1.0),
        (100_000_000, 50.0),
        (150_000_000, 1.0),
        (300_000_000, 100.0),
        (350_000_000, 1.0),
        (500_000_000, 25.0),
        (550_000_000, 1.0),
    ]

    impacts = _audio_impacts(scores)

    assert [timestamp for timestamp, _ in impacts] == [100_000_000, 300_000_000, 500_000_000]


def test_j0_host_clock_is_high_resolution_and_monotonic():
    metadata = host_clock_metadata()

    assert metadata["name"] == "perf_counter"
    assert metadata["monotonic"] is True
    assert metadata["resolution_ns"] <= 1_000_000


def test_mechanics_report_detects_poor_settling(tmp_path: Path):
    with SessionRecorder(tmp_path, session_id="session-mechanics", fsync_every_events=0) as recorder:
        for sequence in range(700):
            timestamp_ns = sequence * 10_000_000
            gyro = [0, 0, 0]
            if 450 <= sequence < 550:
                gyro = [500, -500, 250]
            recorder.append(
                make_host_event(
                    session_id=recorder.session_id,
                    event_type="imu_sample",
                    source_id="arduino.imu",
                    sequence_id=sequence,
                    timestamp_ns=timestamp_ns,
                    payload={"accel_raw": [0, 0, 8192], "gyro_raw": gyro},
                )
            )
        recorder.append(
            make_host_event(
                session_id=recorder.session_id,
                event_type="servo_command",
                source_id="host.command",
                sequence_id=0,
                timestamp_ns=4_000_000_000,
                payload={"requested_angle_deg": 80.0},
            )
        )
        recorder.append(
            make_host_event(
                session_id=recorder.session_id,
                event_type="servo_command",
                source_id="host.command",
                sequence_id=1,
                timestamp_ns=4_100_000_000,
                payload={"requested_angle_deg": 100.0},
            )
        )

    report = analyze_mechanics(tmp_path / "sessions" / "session-mechanics")

    assert report["status"] == "complete"
    assert report["passes_provisional_stability_check"] is False
    assert report["commands"][1]["settling_gyro_ratio_to_baseline"] > 3.0
