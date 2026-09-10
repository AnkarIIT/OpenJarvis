from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class TrafficCameraSkill:
    name: str = "traffic_camera"
    description: str = "Monitor traffic cameras: list cameras, detect motion, read traffic flow, snapshot."
    version: str = "1.0.0"
    author: str = "OpenJarvis"

    def __init__(self, settings=None):
        self.settings = settings
        self.cameras: dict[str, dict] = {}
        self._cap = None

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="cam_list",
                description="List all available cameras (webcam, RTSP, file).",
                handler=self._list,
                skill_name=self.name,
            ),
            SkillCommand(
                name="cam_snapshot",
                description="Take a snapshot from a camera. Usage: cam_snapshot --source 0 or cam_snapshot --source rtsp_url",
                handler=self._snapshot,
                skill_name=self.name,
            ),
            SkillCommand(
                name="cam_detect_motion",
                description="Detect motion in camera feed. Usage: cam_detect_motion --source 0 --duration 10",
                handler=self._detect_motion,
                skill_name=self.name,
            ),
            SkillCommand(
                name="cam_traffic_flow",
                description="Estimate traffic flow (objects moving in frame).",
                handler=self._traffic_flow,
                skill_name=self.name,
            ),
            SkillCommand(
                name="cam_status",
                description="Check camera feed status and quality.",
                handler=self._status,
                skill_name=self.name,
            ),
        ]

    async def initialize(self, settings) -> None:
        self.settings = settings

    async def _list(self) -> str:
        lines = ["Available Cameras:"]
        # Webcam
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                lines.append(f"  [Webcam {i}] {width}x{height}")
                cap.release()
        cap.release()

        # Check for RTSP cameras
        lines.append("  [RTSP] Check your config for RTSP URLs")
        return "\n".join(lines)

    async def _snapshot(self, source: str = "0") -> str:
        try:
            src = int(source)
        except ValueError:
            src = source  # RTSP URL or file path

        try:
            cap = cv2.VideoCapture(src)
            if not cap.isOpened():
                return f"Error: Cannot open camera/source: {source}"

            ret, frame = cap.read()
            if not ret:
                return f"Error: Failed to read frame from {source}"

            # Save snapshot
            out_dir = Path.home() / ".jarvis" / "camera_snapshots"
            out_dir.mkdir(parents=True, exist_ok=True)
            idx = len(list(out_dir.glob("*.jpg"))) + 1
            out_path = out_dir / f"snapshot_{idx}.jpg"
            cv2.imwrite(str(out_path), frame)
            cap.release()

            # Also get metadata
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

            return (
                f"Snapshot saved: {out_path}\n"
                f"Resolution: {width}x{height}\n"
                f"Timestamp: {__import__('datetime').datetime.now().isoformat()}"
            )
        except Exception as e:
            return f"Camera error: {e}"

    async def _detect_motion(self, source: str = "0", duration: int = 10) -> str:
        try:
            src = int(source)
        except ValueError:
            src = source

        try:
            cap = cv2.VideoCapture(src)
            if not cap.isOpened():
                return f"Error: Cannot open camera: {source}"

            ret, prev_frame = cap.read()
            if not ret:
                return f"Error: Failed to read frame"

            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
            prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)

            motion_frames = 0
            total_frames = 0
            start = __import__('datetime').datetime.now()

            while (
                __import__('datetime').datetime.now() - start
            ).total_seconds() < duration and total_frames < 300:
                ret, frame = cap.read()
                if not ret:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)

                frame_diff = cv2.absdiff(prev_gray, gray)
                _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
                thresh = cv2.dilate(thresh, None, iterations=2)

                contours, _ = cv2.findContours(
                    thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                motion_pixels = sum(cv2.contourArea(c) for c in contours if cv2.contourArea(c) > 500)

                if motion_pixels > 5000:
                    motion_frames += 1

                prev_gray = gray
                total_frames += 1

            cap.release()
            motion_pct = (motion_frames / max(total_frames, 1)) * 100

            return (
                f"Motion detection complete ({duration}s):\n"
                f"  Frames analyzed: {total_frames}\n"
                f"  Frames with motion: {motion_frames}\n"
                f"  Motion rate: {motion_pct:.1f}%"
            )
        except Exception as e:
            return f"Motion detection error: {e}"

    async def _traffic_flow(self, source: str = "0") -> str:
        try:
            src = int(source)
        except ValueError:
            src = source

        try:
            cap = cv2.VideoCapture(src)
            if not cap.isOpened():
                return f"Error: Cannot open camera: {source}"

            # Simple background subtraction for object counting
            ret, first_frame = cap.read()
            if not ret:
                return f"Error: Failed to read frame"

            bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=50, varThreshold=50, detectShadows=False
            )

            objects_detected = 0
            frames_counted = 0

            for _ in range(30):  # Count for 30 frames
                ret, frame = cap.read()
                if not ret:
                    break

                mask = bg_subtractor.apply(frame)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
                contours, _ = cv2.findContours(
                    mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                for c in contours:
                    if cv2.contourArea(c) > 1000:
                        objects_detected += 1

                frames_counted += 1

            cap.release()
            return (
                f"Traffic flow estimate ({source}):\n"
                f"  Frames analyzed: {frames_counted}\n"
                f"  Objects detected: {objects_detected}\n"
                f"  Average objects/frame: {objects_detected/max(frames_counted,1):.1f}"
            )
        except Exception as e:
            return f"Traffic flow error: {e}"

    async def _status(self) -> str:
        lines = ["Camera Status:"]
        # Check webcams
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                lines.append(f"  Webcam {i}: OK ({width}x{height}, {fps:.0f}fps)")
                cap.release()
            else:
                cap.release()

        # Check for OpenCV
        lines.append(f"  OpenCV: {cv2.__version__}")
        lines.append(f"  Snapshots directory: {Path.home() / '.jarvis' / 'camera_snapshots'}")
        return "\n".join(lines)
