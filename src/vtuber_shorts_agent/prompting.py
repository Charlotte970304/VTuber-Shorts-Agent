"""Export versioned manual LLM experiments without sending any data."""

import json
from importlib.resources import files
from typing import Any

from .contracts import validate_transcript
from .selection import transcript_chunks


def prepare_prompts(
    transcript: dict[str, Any], *, chunk_seconds: float = 600, overlap_seconds: float = 60,
) -> dict[str, Any]:
    validate_transcript(transcript)
    resources = files("vtuber_shorts_agent").joinpath("resources")
    prompts = {f"round_{number}": resources.joinpath(f"round{number}.md").read_text(
        encoding="utf-8") for number in (1, 2, 3)}
    return {
        "schema_version": "1.0", "prompt_version": "three-round-v1",
        "source_media": transcript["source_media"], "duration_seconds": transcript[
            "duration_seconds"],
        "settings": {"chunk_seconds": chunk_seconds, "overlap_seconds": overlap_seconds},
        "prompts": prompts,
        "schemas": {kind: json.loads(resources.joinpath(f"{kind}.schema.json").read_text(
            encoding="utf-8")) for kind in ("events", "candidates")},
        "round_1_inputs": transcript_chunks(
            transcript, chunk_seconds=chunk_seconds, overlap_seconds=overlap_seconds),
        "instructions": "Run round 1 for each chunk; merge duplicate events by source time "
                        "and evidence. Round 2 needs surrounding original segments. Round 3 "
                        "needs round-2 results. This bundle has not run any model.",
    }
