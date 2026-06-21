"""Command-line entry points for J0 capture, replay, and quality checks."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import signal
import sys
import time
from typing import Any

from j0.capture import AudioCapture, SerialCapture, VideoCapture
from j0.clap import analyze_clap
from j0.clock import host_clock_metadata, host_time_ns
from j0.events import make_host_event
from j0.mechanics import analyze_mechanics
from j0.quality import analyze_session
from j0.recorder import SessionRecorder
from j0.replay import SessionReplay
from j0.sync import summarize_sync


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _audio_device_candidates(
    devices: list[dict[str, Any]], hostapis: list[dict[str, Any]], *, name_filter: str = "brio 100"
) -> list[dict[str, Any]]:
    hostapi_priority = {
        "windows directsound": 0,
        "mme": 1,
        "windows wasapi": 2,
        "windows wdm-ks": 3,
    }
    candidates: list[dict[str, Any]] = []
    for index, device in enumerate(devices):
        if device["max_input_channels"] < 1 or name_filter.lower() not in device["name"].lower():
            continue
        hostapi_name = str(hostapis[device["hostapi"]]["name"])
        candidates.append(
            {
                "index": index,
                "name": str(device["name"]),
                "hostapi": hostapi_name,
                "sample_rate_hz": int(round(float(device["default_samplerate"]))),
            }
        )
    return sorted(
        candidates,
        key=lambda candidate: (hostapi_priority.get(candidate["hostapi"].lower(), 99), candidate["index"]),
    )


def _resolve_audio_devices(requested: int | str | None) -> list[dict[str, Any]]:
    import sounddevice as sd

    if requested is not None:
        try:
            requested_index = int(requested)
        except (TypeError, ValueError):
            requested_index = None
        if requested_index is not None:
            device = sd.query_devices(requested_index)
            hostapi = sd.query_hostapis(device["hostapi"])
            return [
                {
                    "index": requested_index,
                    "name": str(device["name"]),
                    "hostapi": str(hostapi["name"]),
                    "sample_rate_hz": int(round(float(device["default_samplerate"]))),
                }
            ]

    devices = list(sd.query_devices())
    hostapis = list(sd.query_hostapis())
    candidates = _audio_device_candidates(
        devices,
        hostapis,
        name_filter=str(requested) if requested is not None else "brio 100",
    )
    if not candidates:
        requested_name = str(requested) if requested is not None else "BRIO 100"
        raise RuntimeError(f"the {requested_name} microphone is not visible to PortAudio")
    return candidates


def _prepare_serial_port(serial_port: Any, boot_wait_s: float) -> None:
    if boot_wait_s > 0:
        time.sleep(boot_wait_s)
    serial_port.reset_input_buffer()
    serial_port.reset_output_buffer()


def command_capture(args: argparse.Namespace) -> int:
    if args.audio and importlib.util.find_spec("sounddevice") is None:
        raise RuntimeError("audio capture requires the optional 'sounddevice' package")

    audio_devices = _resolve_audio_devices(args.audio_device) if args.audio else []

    import serial

    metadata = {
        "protocol": "EMG1",
        "protocol_version": 1,
        "serial_port": args.port,
        "baud_rate": args.baud,
        "camera_index": args.camera_index if args.video else None,
        "audio_device_candidates": audio_devices,
        "serial_boot_wait_s": args.serial_boot_wait,
        "host_clock": host_clock_metadata(),
        "requested_duration_s": args.duration,
        "servo_limits_deg": [10, 170],
        "servo_test_enabled": args.servo_test,
    }
    stop = False

    def request_stop(signum: int, frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    serial_port = serial.Serial(args.port, args.baud, timeout=0.1)
    _prepare_serial_port(serial_port, args.serial_boot_wait)
    recorder = SessionRecorder(
        args.output,
        metadata=metadata,
        long_session=args.duration >= 1800,
        fsync_every_events=100,
    )
    serial_capture = SerialCapture(serial_port, recorder)
    video_capture = VideoCapture(recorder, device_index=args.camera_index) if args.video else None
    audio_capture = AudioCapture(recorder, device_candidates=audio_devices) if args.audio else None

    servo_schedule = [(10.0, 90.0), (12.0, 80.0), (14.0, 100.0), (16.0, 90.0)] if args.servo_test else []
    servo_step = 0
    failure: BaseException | None = None
    try:
        serial_capture.start()
        if video_capture:
            video_capture.start()
        if audio_capture:
            audio_capture.start()

        readiness_deadline = time.perf_counter() + args.capture_start_timeout
        captures = [capture for capture in (video_capture, audio_capture) if capture is not None]
        while captures and not all(capture.ready.is_set() for capture in captures):
            for capture in captures:
                if capture.error:
                    raise RuntimeError(f"capture startup failed: {capture.error}")
            if time.perf_counter() >= readiness_deadline:
                raise RuntimeError("capture startup timed out")
            time.sleep(0.05)
        for capture in captures:
            if capture.error:
                raise RuntimeError(f"capture startup failed: {capture.error}")

        started = time.perf_counter()
        next_sync = started

        while not stop and time.perf_counter() - started < args.duration:
            if serial_capture.error:
                raise RuntimeError(f"serial capture failed: {serial_capture.error}")
            if video_capture and video_capture.error:
                raise RuntimeError(f"video capture failed: {video_capture.error}")
            if audio_capture and audio_capture.error:
                raise RuntimeError(f"audio capture failed: {audio_capture.error}")
            now = time.perf_counter()
            elapsed = now - started
            if servo_step < len(servo_schedule) and elapsed >= servo_schedule[servo_step][0]:
                serial_capture.set_servo(servo_schedule[servo_step][1])
                servo_step += 1
            if now >= next_sync:
                serial_capture.request_sync()
                next_sync = now + args.sync_interval
            time.sleep(0.05)
    except BaseException as error:
        failure = error
    finally:
        try:
            serial_capture.emergency_stop()
        except BaseException:
            pass
        try:
            if audio_capture:
                audio_capture.stop()
        except BaseException as error:
            failure = failure or error
        try:
            if video_capture:
                video_capture.stop()
        except BaseException as error:
            failure = failure or error
        serial_capture.stop()
        decoder_stats = serial_capture.decoder.stats
        serial_duration_s = (
            (host_time_ns() - serial_capture.started_ns) / 1_000_000_000
            if serial_capture.started_ns is not None
            else 0.0
        )
        recorder.append(
            make_host_event(
                session_id=recorder.session_id,
                event_type="source_status",
                source_id="arduino.serial.status",
                sequence_id=0,
                timestamp_ns=host_time_ns(),
                payload={
                    "decoded_frames": decoder_stats.decoded_frames,
                    "crc_errors": decoder_stats.crc_errors,
                    "version_errors": decoder_stats.version_errors,
                    "length_errors": decoder_stats.length_errors,
                    "discarded_bytes": decoder_stats.discarded_bytes,
                    "bytes_received": serial_capture.bytes_received,
                    "bytes_sent": serial_capture.bytes_sent,
                    "duration_s": serial_duration_s,
                    "receive_bytes_per_second": (
                        serial_capture.bytes_received / serial_duration_s if serial_duration_s > 0 else 0.0
                    ),
                    "estimated_wire_utilization": (
                        serial_capture.bytes_received * 10 / serial_duration_s / args.baud
                        if serial_duration_s > 0
                        else 0.0
                    ),
                },
            )
        )
        serial_port.close()

    sync_report = summarize_sync(serial_capture.sync_estimates)
    _write_json(recorder.session_dir / "reports" / "sync.json", sync_report)
    if failure:
        recorder.abort(f"capture failed: {type(failure).__name__}: {failure}")
    else:
        recorder.close(status="complete")
    report = analyze_session(recorder.session_dir)
    print(recorder.session_dir)
    print(json.dumps({"sync": sync_report, "quality": report}, ensure_ascii=False, indent=2))
    if failure:
        raise failure
    return 0


def command_demo(args: argparse.Namespace) -> int:
    """Generate a deterministic no-hardware session for recorder/replay smoke tests."""

    start_ns = 1_000_000_000
    with SessionRecorder(
        args.output,
        metadata={"synthetic": True, "requested_duration_s": args.duration},
        fsync_every_events=0,
    ) as recorder:
        sequence = {"imu": 0, "range": 0, "video": 0, "audio": 0, "servo": 0}
        steps = round(args.duration * 100)
        for step in range(steps):
            timestamp_ns = start_ns + step * 10_000_000
            if step == 0:
                recorder.append(
                    make_host_event(
                        session_id=recorder.session_id,
                        event_type="servo_state",
                        source_id="synthetic.servo",
                        sequence_id=sequence["servo"],
                        timestamp_ns=timestamp_ns,
                        payload={"requested_cdeg": 9000, "applied_cdeg": 9000, "status": 1},
                    )
                )
                sequence["servo"] += 1
            recorder.append(
                make_host_event(
                    session_id=recorder.session_id,
                    event_type="imu_sample",
                    source_id="synthetic.imu",
                    sequence_id=sequence["imu"],
                    timestamp_ns=timestamp_ns,
                    payload={"accel_raw": [0, 0, 8192], "gyro_raw": [0, 0, 0], "status": 1},
                )
            )
            sequence["imu"] += 1
            if step % 5 == 0:
                recorder.append(
                    make_host_event(
                        session_id=recorder.session_id,
                        event_type="range_sample",
                        source_id="synthetic.range",
                        sequence_id=sequence["range"],
                        timestamp_ns=timestamp_ns,
                        payload={"distance_mm": 500, "piezo_raw": 0, "servo_target_cdeg": 9000},
                    )
                )
                sequence["range"] += 1
            if step % 3 == 0:
                event = make_host_event(
                    session_id=recorder.session_id,
                    event_type="video_frame",
                    source_id="synthetic.video",
                    sequence_id=sequence["video"],
                    timestamp_ns=timestamp_ns,
                    payload={"encoding": "synthetic"},
                )
                recorder.append_blob_stream(kind="video", stream_name="frames.bin", data=b"FRAME", event=event)
                sequence["video"] += 1
            if step % 5 == 0:
                event = make_host_event(
                    session_id=recorder.session_id,
                    event_type="audio_chunk",
                    source_id="synthetic.audio",
                    sequence_id=sequence["audio"],
                    timestamp_ns=timestamp_ns,
                    payload={"sample_rate_hz": 48000, "channels": 1, "sample_format": "pcm_s16le"},
                )
                recorder.append_blob_stream(kind="audio", stream_name="audio.pcm", data=b"\x00\x00" * 2400, event=event)
                sequence["audio"] += 1

        session_dir = recorder.session_dir

    report = analyze_session(session_dir)
    print(session_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def command_quality(args: argparse.Namespace) -> int:
    report = analyze_session(args.session)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    passed = (
        report["passes_integrity_rules"] and not report["ignored_trailing_bytes"]
        if args.allow_short
        else report["passes_j0_automatic_checks"]
    )
    return 0 if passed else 2


def command_replay(args: argparse.Namespace) -> int:
    replay = SessionReplay(args.session)
    stats = replay.play(lambda event: None, speed=args.speed)
    print(json.dumps(stats.__dict__, indent=2))
    return 0


def command_clap(args: argparse.Namespace) -> int:
    report = analyze_clap(args.session)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passes_20ms_target"] else 2


def command_mechanics(args: argparse.Namespace) -> int:
    report = analyze_mechanics(args.session)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("passes_provisional_stability_check") else 2


def command_devices(args: argparse.Namespace) -> int:
    result = {"audio": [], "serial": []}
    if importlib.util.find_spec("sounddevice") is not None:
        import sounddevice as sd

        hostapis = sd.query_hostapis()
        for index, device in enumerate(sd.query_devices()):
            if device["max_input_channels"]:
                result["audio"].append(
                    {
                        "index": index,
                        "name": device["name"],
                        "hostapi": hostapis[device["hostapi"]]["name"],
                        "input_channels": device["max_input_channels"],
                        "default_samplerate": device["default_samplerate"],
                    }
                )
    try:
        import serial.tools.list_ports

        result["serial"] = [
            {"device": port.device, "description": port.description, "hwid": port.hwid}
            for port in serial.tools.list_ports.comports()
        ]
    except ImportError:
        pass
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Emergence J0 instrumentation tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture = subparsers.add_parser("capture", help="capture a physical Windows session")
    capture.add_argument("--port", required=True)
    capture.add_argument("--baud", type=int, default=115200)
    capture.add_argument("--serial-boot-wait", type=float, default=2.5)
    capture.add_argument("--capture-start-timeout", type=float, default=10.0)
    capture.add_argument("--duration", type=float, default=60.0)
    capture.add_argument("--output", type=Path, default=Path("data/j0"))
    capture.add_argument("--sync-interval", type=float, default=0.5)
    capture.add_argument("--camera-index", type=int, default=0)
    capture.add_argument("--audio-device", default=None)
    capture.add_argument(
        "--servo-test",
        action="store_true",
        help="run one explicit 90-80-100-90 degree qualification sequence",
    )
    capture.add_argument("--no-video", dest="video", action="store_false")
    capture.add_argument("--no-audio", dest="audio", action="store_false")
    capture.set_defaults(video=True, audio=True, function=command_capture)

    demo = subparsers.add_parser("demo-record", help="write a deterministic synthetic session")
    demo.add_argument("--duration", type=float, default=2.0)
    demo.add_argument("--output", type=Path, default=Path("data/j0-demo"))
    demo.set_defaults(function=command_demo)

    quality = subparsers.add_parser("quality", help="analyze one session")
    quality.add_argument("session", type=Path)
    quality.add_argument("--allow-short", action="store_true", help="check integrity without requiring 30 minutes")
    quality.set_defaults(function=command_quality)

    replay = subparsers.add_parser("replay", help="replay one session")
    replay.add_argument("session", type=Path)
    replay.add_argument("--speed", type=float, default=0.0)
    replay.set_defaults(function=command_replay)

    clap = subparsers.add_parser("clap-sync", help="estimate audio/video/IMU offsets from a sync gesture")
    clap.add_argument("session", type=Path)
    clap.set_defaults(function=command_clap)

    mechanics = subparsers.add_parser("mechanics", help="compare servo settling against the IMU baseline")
    mechanics.add_argument("session", type=Path)
    mechanics.set_defaults(function=command_mechanics)

    devices = subparsers.add_parser("devices", help="list audio input and serial devices without recording")
    devices.set_defaults(function=command_devices)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.function(args))
    except RuntimeError as error:
        parser.error(str(error))
        return 2


if __name__ == "__main__":
    sys.exit(main())
