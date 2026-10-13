"""Local Japanese transcription using the optional faster-whisper dependency."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import SCHEMA_VERSION, validate_transcript


def transcribe_media(
    source: Path,
    *,
    model_name: str = "small",
    device: str = "cpu",
    compute_type: str = "int8",
    vad_filter: bool = False,
    word_timestamps: bool = True,
) -> dict[str, Any]:
    """Transcribe one local file and return the versioned JSON payload."""
    if not source.is_file():
        raise FileNotFoundError(f"Input media not found: {source}")
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError('Install transcription extras: pip install -e ".[transcribe]"') from exc

    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments_iter, info = model.transcribe(
        str(source),
        language="ja",
        word_timestamps=word_timestamps,
        vad_filter=vad_filter,
        beam_size=5,
    )
    rows = []
    # Iterating is essential: faster-whisper transcription runs lazily.
    for segment in segments_iter:
        words = None
        if segment.words is not None:
            words = [
                {
                    "start": round(float(word.start), 3),
                    "end": round(float(word.end), 3),
                    "word": word.word,
                }
                for word in segment.words
            ]
        rows.append(
            {
                "id": int(segment.id),
                "start": round(float(segment.start), 3),
                "end": round(float(segment.end), 3),
                "text": segment.text.strip(),
                "words": words,
            }
        )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "source_media": source.name,  # Avoid leaking an absolute local path.
        "duration_seconds": round(float(info.duration), 3),
        "language": info.language,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": {
            "name": model_name,
            "backend": "faster-whisper",
            "device": device,
            "compute_type": compute_type,
            "vad_filter": vad_filter,
            "word_timestamps": word_timestamps,
        },
        "segments": rows,
    }
    validate_transcript(payload)
    return payload
