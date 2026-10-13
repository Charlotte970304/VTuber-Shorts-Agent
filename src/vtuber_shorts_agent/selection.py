"""Reproducible, local transcript-only event discovery (no LLM calls)."""

import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import validate_transcript
from .io_utils import read_json

STRATEGY = "text-cues-v1"
CUES = {
    "question": ("?", "？"),
    "surprise_word": ("えっ", "まさか", "びっくり", "嘘", "うそ"),
    "story_word": ("面白", "実は", "そういえば", "昨日", "この前"),
    "turn_word": ("でも", "ところが", "なのに", "結局"),
    "laughter_text": ("笑", "はは", "ふふ"),
}


def load_transcript(path: Path) -> dict[str, Any]:
    if path.suffix.lower() != ".srt":
        data = read_json(path)
        validate_transcript(data)
        ordered_segments(data)
        return data
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()
    rows = []
    timestamp = r"(\d{2,}):(\d{2}):(\d{2}),(\d{3})"
    pattern = re.compile(rf"^{timestamp}\s+-->\s+{timestamp}$")
    for index, block in enumerate(re.split(r"\n\s*\n", text)):
        lines = block.splitlines()
        if len(lines) < 3 or not lines[0].strip().isdigit():
            raise ValueError(f"Invalid SRT block {index + 1}")
        match = pattern.fullmatch(lines[1].strip())
        if not match:
            raise ValueError(f"Invalid SRT timestamp in block {index + 1}")
        values = list(map(int, match.groups()))
        times = []
        for offset in (0, 4):
            h, m, s, ms = values[offset:offset + 4]
            if m >= 60 or s >= 60:
                raise ValueError(f"Invalid SRT clock in block {index + 1}")
            times.append(h * 3600 + m * 60 + s + ms / 1000)
        rows.append({"id": index + 1, "start": times[0], "end": times[1],
                     "text": "\n".join(lines[2:]), "words": None})
    data = {
        "schema_version": "1.0", "source_media": path.name,
        "duration_seconds": max((row["end"] for row in rows), default=0),
        "language": "ja", "model": {"backend": "srt-import"},
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "segments": rows,
    }
    validate_transcript(data)
    ordered_segments(data)
    return data


def ordered_segments(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    rows = sorted(transcript["segments"], key=lambda row: (row["start"], row["end"]))
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Transcript segment IDs must be unique for selection")
    return rows


def discover_events(
    transcript: dict[str, Any], *, gap_seconds: float = 3,
    max_event_seconds: float = 90, context_seconds: float = 15,
    max_events: int = 20,
) -> dict[str, Any]:
    validate_transcript(transcript)
    if (not all(math.isfinite(value) for value in (
            gap_seconds, context_seconds, max_event_seconds))
            or gap_seconds < 0 or context_seconds < 0 or max_event_seconds <= 0
            or max_events < 1):
        raise ValueError("Invalid discovery settings")
    groups: list[list[dict[str, Any]]] = []
    for row in ordered_segments(transcript):
        if not row["text"].strip():
            continue
        if (not groups or row["start"] - max(r["end"] for r in groups[-1]) > gap_seconds
                or row["end"] - groups[-1][0]["start"] > max_event_seconds):
            groups.append([])
        groups[-1].append(row)
    events = []
    for group in groups:
        evidence = []
        for row in group:
            for label, cues in CUES.items():
                if any(cue in row["text"] for cue in cues):
                    evidence.append({"segment_id": row["id"], "cue": label})
        # No invented semantic summaries or emotion predictions.
        if not evidence:
            continue
        start, end = group[0]["start"], max(row["end"] for row in group)
        events.append({
            "id": f"event-{len(events) + 1:04d}", "start": start, "end": end,
            "context_start": max(0, start - context_seconds),
            "context_end": min(transcript["duration_seconds"], end + context_seconds),
            "summary": " ".join(row["text"] for row in group)[:200],
            "interesting_reason": "Text cues: " + ", ".join(sorted(
                {item["cue"] for item in evidence})),
            "evidence_segment_ids": [row["id"] for row in group],
            "text_cues": evidence, "needs_more_context": True,
            "priority": len({item["cue"] for item in evidence}),
        })
    events.sort(key=lambda event: (-event["priority"], event["start"]))
    return {
        "schema_version": "1.0", "source_media": transcript["source_media"],
        "duration_seconds": transcript["duration_seconds"],
        "selection_strategy": STRATEGY,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "settings": {"gap_seconds": gap_seconds, "max_event_seconds": max_event_seconds,
                     "context_seconds": context_seconds, "max_events": max_events},
        "events": events[:max_events],
    }


def transcript_chunks(
    transcript: dict[str, Any], *, chunk_seconds: float = 600,
    overlap_seconds: float = 60,
) -> list[dict[str, Any]]:
    if (not math.isfinite(chunk_seconds) or not math.isfinite(overlap_seconds)
            or chunk_seconds <= 0 or not 0 <= overlap_seconds < chunk_seconds):
        raise ValueError("Require chunk_seconds > overlap_seconds >= 0")
    rows = ordered_segments(transcript)
    chunks = []
    start = 0.0
    while start < transcript["duration_seconds"]:
        end = min(start + chunk_seconds, transcript["duration_seconds"])
        selected = [row for row in rows if row["start"] < end and row["end"] > start]
        if selected:
            chunks.append({"chunk_id": len(chunks) + 1, "start": start, "end": end,
                           "segments": selected})
        if end == transcript["duration_seconds"]:
            break
        start += chunk_seconds - overlap_seconds
    return chunks
