"""Versioned data contract and validators for the transcript MVP."""

import math
from typing import Any

SCHEMA_VERSION = "1.0"


def validate_audio_features(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != "1.1":
        raise ValueError("Unsupported audio schema_version (expected '1.1')")
    for field in ("source_media", "generated_by", "created_at_utc"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    for field in ("analysis", "feature_definitions"):
        if not isinstance(payload.get(field), dict) or not payload[field]:
            raise ValueError(f"{field} must be a non-empty object")
    duration = _finite_number(payload.get("duration_seconds"), "duration_seconds")
    if duration <= 0:
        raise ValueError("duration_seconds must be positive")
    for collection in ("windows", "pauses"):
        rows = payload.get(collection)
        if not isinstance(rows, list) or collection == "windows" and not rows:
            raise ValueError(f"Invalid {collection} array")
        previous_end = 0
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"{collection} entries must be objects")
            start = _finite_number(row.get("start"), "start")
            end = _finite_number(row.get("end"), "end")
            if not previous_end <= start < end <= duration:
                raise ValueError(f"Invalid {collection} time range")
            previous_end = end
            if collection == "pauses":
                continue
            rms = _finite_number(row.get("rms"), "rms")
            if rms < 0:
                raise ValueError("rms must be nonnegative")
            for field in ("rms_dbfs", "pitch_median_hz", "pitch_periodicity", "voiced_fraction",
                          "low_energy_fraction", "speech_detected", "laughter_probability"):
                if field not in row:
                    raise ValueError(f"Missing {field}")
                value = row[field]
                if field in ("speech_detected", "laughter_probability"):
                    if value is not None:
                        raise ValueError(f"{field} is unmeasured and must be null")
                elif value is not None:
                    number = _finite_number(value, field)
                    if field == "pitch_median_hz" and not 60 <= number <= 600:
                        raise ValueError("Pitch must be within 60–600 Hz")
                    if field in ("pitch_periodicity", "voiced_fraction", "low_energy_fraction"):
                        if not 0 <= number <= 1:
                            raise ValueError(f"{field} must be within 0–1")
            if row["low_energy_fraction"] is None:
                raise ValueError("low_energy_fraction cannot be null")
            if (rms == 0) != (row["rms_dbfs"] is None):
                raise ValueError("rms_dbfs must be null only for zero RMS")
            if (row["pitch_median_hz"] is None) != (row["pitch_periodicity"] is None):
                raise ValueError("Pitch and periodicity must both be measured or null")


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


def validate_selection(
    payload: dict[str, Any], *, kind: str = "candidates",
    transcript: dict[str, Any] | None = None,
) -> None:
    """Validate event/candidate artifacts, optionally checking source evidence."""
    if kind not in ("events", "candidates"):
        raise ValueError("Unknown selection kind")
    if payload.get("schema_version") != "1.0":
        raise ValueError("Unsupported schema_version (expected '1.0')")
    for field in ("source_media", "selection_strategy"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    if not isinstance(payload.get(kind), list):
        raise ValueError(f"{kind} must be an array")
    duration = None
    if "duration_seconds" in payload:
        duration = _finite_number(payload["duration_seconds"], "duration_seconds")
        if duration <= 0:
            raise ValueError("duration_seconds must be positive")
    source_rows = None
    if transcript is not None:
        validate_transcript(transcript)
        if transcript["source_media"] != payload["source_media"]:
            raise ValueError("Selection and transcript source_media must match")
        if duration is not None and duration != transcript["duration_seconds"]:
            raise ValueError("Selection and transcript duration_seconds must match")
        duration = transcript["duration_seconds"]
        source_rows = {row["id"]: row for row in transcript["segments"]}
        if len(source_rows) != len(transcript["segments"]):
            raise ValueError("Transcript segment IDs must be unique")
    ids = set()
    for index, row in enumerate(payload[kind]):
        if not isinstance(row, dict):
            raise ValueError(f"{kind}[{index}] must be an object")
        identifier = row.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in ids:
            raise ValueError("Selection IDs must be unique non-empty strings")
        ids.add(identifier)
        start, end, context_start, context_end = (
            _finite_number(row.get(field), field)
            for field in ("start", "end", "context_start", "context_end")
        )
        if not 0 <= context_start <= start < end <= context_end:
            raise ValueError(f"Invalid selection time range at {identifier}")
        if duration is not None and context_end > duration:
            raise ValueError(f"Selection exceeds source duration at {identifier}")
        fields = ("summary", "interesting_reason") if kind == "events" else (
            "reason", "hook_suggestion")
        for field in fields:
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"{field} must be a non-empty string")
        evidence = row.get("evidence_segment_ids")
        if (not isinstance(evidence, list) or not evidence
                or any(isinstance(item, bool) or not isinstance(item, int) for item in evidence)
                or len(evidence) != len(set(evidence))):
            raise ValueError("evidence_segment_ids must contain unique integer IDs")
        if source_rows is not None:
            for segment_id in evidence:
                if segment_id not in source_rows:
                    raise ValueError(f"Unknown evidence segment ID: {segment_id}")
                segment = source_rows[segment_id]
                if segment["end"] <= context_start or segment["start"] >= context_end:
                    raise ValueError("Evidence must overlap the context range")
        if kind == "events":
            if not isinstance(row.get("needs_more_context"), bool):
                raise ValueError("needs_more_context must be a boolean")
        else:
            if row.get("review_status") not in ("pending", "approved", "rejected"):
                raise ValueError("Invalid review_status")
            if "scores" not in row:
                raise ValueError("scores is required (use null when unscored)")
            scores = row.get("scores")
            if scores is not None:
                if not isinstance(scores, dict):
                    raise ValueError("scores must be an object or null")
                for field in ("hook", "understandability", "personality", "payoff", "clipability"):
                    score = _finite_number(scores.get(field), f"scores.{field}")
                    if not 1 <= score <= 5:
                        raise ValueError("Scores must be between 1 and 5")
                if (not isinstance(row.get("score_rubric_version"), str)
                        or not row["score_rubric_version"].strip()):
                    raise ValueError("Scored candidates require score_rubric_version")
