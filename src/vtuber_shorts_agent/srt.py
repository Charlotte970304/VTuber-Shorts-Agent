"""Render transcript segments to SRT text."""

from typing import Any


def format_srt_time(seconds: float) -> str:
    if seconds < 0:
        raise ValueError("SRT time cannot be negative")
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def to_srt(segments: list[dict[str, Any]]) -> str:
    parts = []
    for segment in segments:
        text = str(segment["text"]).strip()
        if not text:
            continue
        start = format_srt_time(float(segment["start"]))
        end = format_srt_time(float(segment["end"]))
        parts.append(f"{len(parts) + 1}\n{start} --> {end}\n{text}\n")
    return "\n".join(parts)
