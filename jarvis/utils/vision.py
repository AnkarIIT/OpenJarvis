from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def build_vision_report() -> dict[str, Any]:
    opencv = importlib.util.find_spec("cv2") is not None
    pillow = importlib.util.find_spec("PIL") is not None
    pypdf = importlib.util.find_spec("pypdf") is not None
    docx = importlib.util.find_spec("docx") is not None
    return {
        "opencv": opencv,
        "pillow": pillow,
        "pdf_text": pypdf,
        "docx_text": docx,
        "camera_analysis": opencv,
        "document_text_extraction": pypdf or docx,
        "llm_multimodal_input": False,
        "notes": [
            "Camera analysis uses local OpenCV skills when cv2 is installed.",
            "Screenshots are available through browser and desktop MCP tools.",
            "Direct image/document input to the LLM is not enabled yet.",
        ],
    }


def supported_document(path: str) -> bool:
    return Path(path).suffix.lower() in {".txt", ".md", ".pdf", ".docx"}
