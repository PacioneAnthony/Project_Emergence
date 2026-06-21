"""Hardware capture orchestration for a J0 session on Windows."""

from __future__ import annotations

import queue
import threading
from typing import Any

from j0.clock import host_time_ns
from j0.events import MicrosUnwrapper, event_from_packet, make_host_event
from j0.protocol import Packet, PacketType, StreamDecoder, make_estop, make_set_servo, make_sync_request
from j0.recorder import SessionRecorder
from j0.sync import estimate_sync


def _packet_source_id(packet_type: int) -> str:
    mapping = {
        PacketType.DEVICE_HELLO: "arduino.control",
        PacketType.IMU_SAMPLE: "arduino.imu",
        PacketType.RANGE_SAMPLE: "arduino.range",
        PacketType.SERVO_STATE: "arduino.servo",
        PacketType.SYNC_REPLY: "arduino.sync",
        PacketType.ERROR: "arduino.control",
    }
    try:
        return mapping.get(PacketType(packet_type), "arduino.unknown")
    except ValueError:
        return "arduino.unknown"


class SerialCapture:
    def __init__(self, serial_port: Any, recorder: SessionRecorder, *, calibration_version: str = "imu-raw-v1"):
        self.serial_port = serial_port
        self.recorder = recorder
        self.calibration_version = calibration_version
        self.decoder = StreamDecoder()
        self._source_clocks: dict[str, MicrosUnwrapper] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._command_sequence = 0
        self._token = 0
        self._pending_sync: dict[int, int] = {}
        self.sync_estimates = []
        self.bytes_received = 0
        self.bytes_sent = 0
        self.started_ns: int | None = None
        self.error: BaseException | None = None

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("serial capture already started")
        self.started_ns = host_time_ns()
        self._thread = threading.Thread(target=self._run, name="j0-serial", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                data = self.serial_port.read(self.serial_port.in_waiting or 1)
                if not data:
                    continue
                self.bytes_received += len(data)
                receive_ns = host_time_ns()
                for packet in self.decoder.feed(data):
                    source_id = _packet_source_id(packet.packet_type)
                    clock = self._source_clocks.setdefault(source_id, MicrosUnwrapper())
                    stats = self.decoder.stats
                    event = event_from_packet(
                        packet,
                        session_id=self.recorder.session_id,
                        source_id=source_id,
                        host_receive_timestamp_ns=receive_ns,
                        source_clock=clock,
                        calibration_version=self.calibration_version,
                        decoder_quality={
                            "decoder_crc_errors": stats.crc_errors,
                            "decoder_discarded_bytes": stats.discarded_bytes,
                        },
                    )
                    self.recorder.append(event)
                    if packet.packet_type == PacketType.SYNC_REPLY and event.quality.get("payload_valid"):
                        payload = event.payload
                        host_send_ns = self._pending_sync.pop(int(payload["token"]), int(payload["host_send_ns"]))
                        estimate = estimate_sync(
                            token=int(payload["token"]),
                            host_send_ns=host_send_ns,
                            host_receive_ns=receive_ns,
                            device_receive_us=int(payload["device_receive_us"]),
                            device_send_us=int(payload["device_send_us"]),
                        )
                        self.sync_estimates.append(estimate)
        except BaseException as error:
            self.error = error

    def _send(self, packet: Packet, event_type: str, payload: dict) -> None:
        encoded = packet.encode()
        self.serial_port.write(encoded)
        self.bytes_sent += len(encoded)
        now_ns = host_time_ns()
        self.recorder.append(
            make_host_event(
                session_id=self.recorder.session_id,
                event_type=event_type,
                source_id="host.command",
                sequence_id=packet.sequence_id,
                timestamp_ns=now_ns,
                payload=payload,
            )
        )

    def set_servo(self, angle_deg: float) -> None:
        now_ns = host_time_ns()
        packet = make_set_servo(self._command_sequence, now_ns // 1000, angle_deg)
        self._send(packet, "servo_command", {"requested_angle_deg": angle_deg})
        self._command_sequence += 1

    def request_sync(self) -> int:
        now_ns = host_time_ns()
        token = self._token
        self._token += 1
        self._pending_sync[token] = now_ns
        packet = make_sync_request(self._command_sequence, now_ns // 1000, token, now_ns)
        self._send(packet, "sync_request", {"token": token, "host_send_ns": now_ns})
        self._command_sequence += 1
        return token

    def emergency_stop(self) -> None:
        now_ns = host_time_ns()
        packet = make_estop(self._command_sequence, now_ns // 1000)
        self._send(packet, "emergency_stop", {})
        self._command_sequence += 1


class VideoCapture:
    def __init__(
        self,
        recorder: SessionRecorder,
        *,
        device_index: int = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        jpeg_quality: int = 80,
    ) -> None:
        self.recorder = recorder
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps = fps
        self.jpeg_quality = jpeg_quality
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.ready = threading.Event()
        self.error: BaseException | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="j0-video", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        if self.error:
            raise RuntimeError(f"video capture failed: {self.error}") from self.error

    def _run(self) -> None:
        try:
            import cv2

            camera = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            camera.set(cv2.CAP_PROP_FPS, self.fps)
            if not camera.isOpened():
                raise RuntimeError(f"cannot open camera index {self.device_index}")
            self.ready.set()
            sequence = 0
            failure_sequence = 0
            try:
                while not self._stop.is_set():
                    ok, frame = camera.read()
                    receive_ns = host_time_ns()
                    if not ok:
                        self.recorder.append(
                            make_host_event(
                                session_id=self.recorder.session_id,
                                event_type="drop_notice",
                                source_id="camera.brio100.status",
                                sequence_id=failure_sequence,
                                timestamp_ns=receive_ns,
                                payload={"source": "camera.brio100", "reason": "read_failed", "count": 1},
                            )
                        )
                        failure_sequence += 1
                        continue
                    encoded, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
                    if not encoded:
                        continue
                    event = make_host_event(
                        session_id=self.recorder.session_id,
                        event_type="video_frame",
                        source_id="camera.brio100",
                        sequence_id=sequence,
                        timestamp_ns=receive_ns,
                        payload={
                            "width": int(frame.shape[1]),
                            "height": int(frame.shape[0]),
                            "encoding": "jpeg",
                            "capture_timestamp_source": "host_after_read",
                        },
                        quality={"hardware_capture_timestamp_available": False},
                        calibration_version="brio100-video-v1",
                    )
                    self.recorder.append_blob_stream(
                        kind="video", stream_name="frames.mjpeg", data=buffer.tobytes(), event=event
                    )
                    sequence += 1
            finally:
                camera.release()
        except BaseException as error:
            self.error = error
            self.ready.set()


class AudioCapture:
    def __init__(
        self,
        recorder: SessionRecorder,
        *,
        device_candidates: list[dict[str, Any]],
        channels: int = 1,
        chunk_ms: int = 50,
    ) -> None:
        self.recorder = recorder
        if not device_candidates:
            raise ValueError("at least one audio device candidate is required")
        self.device_candidates = device_candidates
        self.channels = channels
        self.chunk_ms = chunk_ms
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.ready = threading.Event()
        self.selected_device: dict[str, Any] | None = None
        self.error: BaseException | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="j0-audio", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        if self.error:
            raise RuntimeError(f"audio capture failed: {self.error}") from self.error

    def _run(self) -> None:
        try:
            import sounddevice as sd

            capture_sequence = 0
            expected_sequence = 0
            notice_sequence = 0
            failures: list[str] = []

            for candidate in self.device_candidates:
                if self._stop.is_set():
                    return
                sample_rate_hz = int(candidate["sample_rate_hz"])
                frames_per_chunk = round(sample_rate_hz * self.chunk_ms / 1000)
                chunks: queue.Queue[tuple[int, int, bytes, bool, str]] = queue.Queue(maxsize=100)
                stream_origin_ns: int | None = None
                stream_frame_offset = 0

                def callback(indata: bytes, frames: int, time_info: Any, status: Any) -> None:
                    nonlocal capture_sequence, stream_frame_offset, stream_origin_ns
                    callback_ns = host_time_ns()
                    observed_first_sample_ns = callback_ns - round(frames / sample_rate_hz * 1_000_000_000)
                    timestamp_source = "sample_count_anchored_to_host_callback"
                    try:
                        adc_time = float(time_info.inputBufferAdcTime)
                        current_time = float(time_info.currentTime)
                        if adc_time > 0 and current_time > 0:
                            observed_first_sample_ns = callback_ns + round((adc_time - current_time) * 1_000_000_000)
                            timestamp_source = "sample_count_anchored_to_portaudio_adc"
                    except (AttributeError, TypeError, ValueError):
                        pass
                    if stream_origin_ns is None:
                        stream_origin_ns = observed_first_sample_ns
                    timestamp_ns = stream_origin_ns + round(stream_frame_offset / sample_rate_hz * 1_000_000_000)
                    stream_frame_offset += frames
                    sequence = capture_sequence
                    capture_sequence += 1
                    try:
                        chunks.put_nowait(
                            (sequence, timestamp_ns, bytes(indata), bool(status), timestamp_source)
                        )
                    except queue.Full:
                        pass

                try:
                    with sd.RawInputStream(
                        samplerate=sample_rate_hz,
                        blocksize=frames_per_chunk,
                        device=candidate["index"],
                        channels=self.channels,
                        dtype="int16",
                        callback=callback,
                    ):
                        self.selected_device = candidate
                        self.recorder.append(
                            make_host_event(
                                session_id=self.recorder.session_id,
                                event_type="source_status",
                                source_id="microphone.brio100.status",
                                sequence_id=notice_sequence,
                                timestamp_ns=host_time_ns(),
                                payload={
                                    "source": "microphone.brio100",
                                    "status": "audio_device_selected",
                                    "device_index": candidate["index"],
                                    "device_name": candidate["name"],
                                    "hostapi": candidate["hostapi"],
                                    "sample_rate_hz": sample_rate_hz,
                                },
                            )
                        )
                        notice_sequence += 1
                        self.ready.set()
                        while not self._stop.is_set():
                            try:
                                sequence, timestamp_ns, data, had_status, timestamp_source = chunks.get(timeout=0.2)
                            except queue.Empty:
                                continue
                            if sequence > expected_sequence:
                                self.recorder.append(
                                    make_host_event(
                                        session_id=self.recorder.session_id,
                                        event_type="drop_notice",
                                        source_id="microphone.brio100.status",
                                        sequence_id=notice_sequence,
                                        timestamp_ns=timestamp_ns,
                                        payload={
                                            "source": "microphone.brio100",
                                            "reason": "capture_queue_full",
                                            "count": sequence - expected_sequence,
                                        },
                                    )
                                )
                                notice_sequence += 1
                            event = make_host_event(
                                session_id=self.recorder.session_id,
                                event_type="audio_chunk",
                                source_id="microphone.brio100",
                                sequence_id=sequence,
                                timestamp_ns=timestamp_ns,
                                payload={
                                    "sample_rate_hz": sample_rate_hz,
                                    "channels": self.channels,
                                    "sample_format": "pcm_s16le",
                                    "frames": len(data) // (2 * self.channels),
                                },
                                quality={"driver_status": had_status, "timestamp_source": timestamp_source},
                                calibration_version="brio100-audio-v1",
                            )
                            self.recorder.append_blob_stream(
                                kind="audio", stream_name="audio.pcm", data=data, event=event
                            )
                            expected_sequence = sequence + 1
                    return
                except BaseException as error:
                    failures.append(
                        f"{candidate['name']} ({candidate['hostapi']}, index {candidate['index']}): {error}"
                    )

            raise RuntimeError("no audio backend could start: " + "; ".join(failures))
        except BaseException as error:
            self.error = error
            self.ready.set()
