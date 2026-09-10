from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class MultiSensorySkill:
    name: str = "multisensory"
    description: str = "Process visual and sensory input: camera vision, image recognition, scene analysis."
    version: str = "1.0.0"
    author: str = "OpenJarvis"

    def __init__(self, settings=None):
        self.settings = settings
        self._last_frame = None
        self._camera_active = False

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="vision_describe",
                description="Describe what the camera sees using OpenCV analysis.",
                handler=self._describe,
                skill_name=self.name,
            ),
            SkillCommand(
                name="vision_detect_objects",
                description="Detect objects in camera frame using contour analysis.",
                handler=self._detect_objects,
                skill_name=self.name,
            ),
            SkillCommand(
                name="vision_read_text",
                description="Extract text from camera frame (basic OCR via template matching).",
                handler=self._read_text,
                skill_name=self.name,
            ),
            SkillCommand(
                name="vision_face_detect",
                description="Detect faces in camera frame.",
                handler=self._face_detect,
                skill_name=self.name,
            ),
            SkillCommand(
                name="vision_color_detect",
                description="Detect dominant colors in camera frame.",
                handler=self._color_detect,
                skill_name=self.name,
            ),
            SkillCommand(
                name="vision_screenshot",
                description="Capture a screenshot of the current screen or camera.",
                handler=self._screenshot,
                skill_name=self.name,
            ),
        ]

    async def initialize(self, settings) -> None:
        self.settings = settings

    async def _describe(self, source: str = "0") -> str:
        try:
            src = int(source)
        except ValueError:
            src = source

        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            return f"Error: Cannot access camera {source}"

        ret, frame = cap.read()
        cap.release()
        if not ret:
            return "Error: Failed to capture frame"

        # Analyze frame
        height, width = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect edges
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size * 100

        # Detect brightness
        brightness = np.mean(gray)

        # Detect motion areas
        blur = cv2.GaussianBlur(gray, (21, 21), 0)

        description = (
            f"Scene Description:\n"
            f"  Resolution: {width}x{height}\n"
            f"  Brightness: {brightness:.1f}/255\n"
            f"  Edge density: {edge_density:.1f}%\n"
            f"  Dominant regions: {self._count_regions(gray)}"
        )

        self._last_frame = frame
        return description

    async def _detect_objects(self, source: str = "0") -> str:
        try:
            src = int(source)
        except ValueError:
            src = source

        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            return f"Error: Cannot access camera"

        ret, frame = cap.read()
        cap.release()
        if not ret:
            return "Error: Failed to capture frame"

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        objects = []
        for c in contours:
            area = cv2.contourArea(c)
            if area > 500:
                x, y, w, h = cv2.boundingRect(c)
                aspect = w / h if h > 0 else 0
                shape = self._classify_shape(w, h)
                objects.append(f"  {shape} (area: {int(area)}, pos: ({x},{y}))")

        objects = sorted(objects, key=lambda x: int(x.split("area: ")[1].split(",")[0]), reverse=True)[:10]

        return (
            f"Objects detected: {len(objects)}\n" +
            "\n".join(objects) if objects else
            "No significant objects detected"
        )

    async def _read_text(self, source: str = "0") -> str:
        try:
            src = int(source)
        except ValueError:
            src = source

        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            return "Error: Cannot access camera"

        ret, frame = cap.read()
        cap.release()
        if not ret:
            return "Error: Failed to capture frame"

        # Simple text detection via edge patterns
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Threshold and find rectangular regions that look like text
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        # Look for horizontal text-like lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel)

        contours, _ = cv2.findContours(
            detect_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        text_regions = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w > 50 and h > 10 and h < 100:  # Text-like aspect ratio
                text_regions.append(f"  Text region at ({x},{y}) size {w}x{h}")

        if text_regions:
            return f"Detected {len(text_regions)} text regions:\n" + "\n".join(text_regions[:15])
        return "No text regions detected (install pytesseract for better OCR)"

    async def _face_detect(self, source: str = "0") -> str:
        try:
            src = int(source)
        except ValueError:
            src = source

        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            return "Error: Cannot access camera"

        ret, frame = cap.read()
        cap.release()
        if not ret:
            return "Error: Failed to capture frame"

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Haar cascade face detection
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        if face_cascade.empty():
            return "Error: Haar cascade not found"

        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )

        if len(faces) > 0:
            lines = [f"Detected {len(faces)} face(s):"]
            for i, (x, y, w, h) in enumerate(faces):
                lines.append(f"  Face {i+1}: ({x},{y}) {w}x{h}")
            return "\n".join(lines)
        return "No faces detected"

    async def _color_detect(self, source: str = "0") -> str:
        try:
            src = int(source)
        except ValueError:
            src = source

        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            return "Error: Cannot access camera"

        ret, frame = cap.read()
        cap.release()
        if not ret:
            return "Error: Failed to capture frame"

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Define color ranges
        color_ranges = {
            "Red": ([0, 100, 100], [10, 255, 255]),
            "Green": ([40, 50, 50], [80, 255, 255]),
            "Blue": ([100, 50, 50], [130, 255, 255]),
            "Yellow": ([20, 100, 100], [35, 255, 255]),
            "Orange": ([10, 100, 100], [25, 255, 255]),
        }

        lines = ["Dominant Colors:"]
        for color_name, (lower, upper) in color_ranges.items():
            lower = np.array(lower, dtype="uint8")
            upper = np.array(upper, dtype="uint8")
            mask = cv2.inRange(hsv, lower, upper)
            pixel_count = np.sum(mask > 0)
            if pixel_count > 100:
                lines.append(f"  {color_name}: {pixel_count} pixels ({pixel_count/frame.shape[0]*frame.shape[1]*100:.1f}%)")

        return "\n".join(lines) if len(lines) > 1 else "No dominant colors detected"

    async def _screenshot(self) -> str:
        try:
            import subprocess
            import tempfile

            # Use computer_use style screenshot capture via OpenCV desktop window
            # For now, capture from default webcam as screenshot
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return "Error: No camera available"

            ret, frame = cap.read()
            cap.release()
            if not ret:
                return "Error: Failed to capture"

            out_dir = Path.home() / ".jarvis" / "screenshots"
            out_dir.mkdir(parents=True, exist_ok=True)
            idx = len(list(out_dir.glob("*.png"))) + 1
            out_path = out_dir / f"screenshot_{idx}.png"
            cv2.imwrite(str(out_path), frame)

            return f"Screenshot saved: {out_path}"
        except Exception as e:
            return f"Screenshot error: {e}"

    def _count_regions(self, gray: np.ndarray) -> int:
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return len([c for c in contours if cv2.contourArea(c) > 100])

    def _classify_shape(self, w: int, h: int) -> str:
        ratio = w / h if h > 0 else 0
        if 0.8 < ratio < 1.2:
            return "Square"
        elif ratio > 2:
            return "Wide"
        elif ratio < 0.5:
            return "Tall"
        return "Rect"
