"""Versioned data contract and validators for the transcript MVP."""

import math
from typing import Any

SCHEMA_VERSION = "1.0"


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return float(value)


def validate_transcript(payload: dict[str, Any]) -> None:
    """Raise ValueError when the transcript does not match our v0.1 contract."""
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported schema_version (expected '1.0')")
    if not isinstance(payload.get("source_media"), str) or not payload["source_media"]:
        raise ValueError("source_media must be a non-empty filename")
    if not isinstance(payload.get("language"), str) or not payload["language"]:
        raise ValueError("language must be non-empty")
    duration = _finite_number(payload.get("duration_seconds"), "duration_seconds")
    if duration <= 0:
        raise ValueError("duration_seconds must be greater than zero")
    if not isinstance(payload.get("model"), dict):
        raise ValueError("model must be an object")
    if not isinstance(payload.get("segments"), list):
        raise ValueError("segments must be an array")
    for index, segment in enumerate(payload["segments"]):
        if not isinstance(segment, dict):
            raise ValueError(f"segments[{index}] must be an object")
        if not isinstance(segment.get("id"), int) or isinstance(segment["id"], bool):
            raise ValueError(f"segments[{index}].id must be an integer")
        start = _finite_number(segment.get("start"), f"segments[{index}].start")
        end = _finite_number(segment.get("end"), f"segments[{index}].end")
        if start < 0 or end <= start or end > duration + 1.0:
            raise ValueError(f"segments[{index}] has invalid time range")
        if not isinstance(segment.get("text"), str):
            raise ValueError(f"segments[{index}].text must be a string")
        words = segment.get("words")
        if words is not None:
            if not isinstance(words, list):
                raise ValueError(f"segments[{index}].words must be an array or null")
            for word_index, word in enumerate(words):
                if not isinstance(word, dict) or not isinstance(word.get("word"), str):
                    raise ValueError(f"Invalid word at segments[{index}].words[{word_index}]")
                word_start = _finite_number(word.get("start"), "word.start")
                word_end = _finite_number(word.get("end"), "word.end")
                if word_start < 0 or word_end < word_start:
                    raise ValueError(f"Invalid word timestamps at segment {index}")
