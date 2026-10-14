"""Streaming physical audio measurements; no speech or emotion classifier."""

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .contracts import validate_audio_features

RATE = 16000


def window_features(samples, *, silence_dbfs=-40.0, pitch_enabled=True):
    import numpy as np

    rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
    dbfs = 20 * math.log10(rms) if rms > 0 else None
    frames = []
    pitches, periodicities = [], []
    for offset in range(0, len(samples), 640):
        frame = samples[offset:offset + 640].astype(np.float64)
        frame_rms = float(np.sqrt(np.mean(frame ** 2)))
        quiet = frame_rms < 10 ** (silence_dbfs / 20)
        frames.append((offset, len(frame), quiet))
        if not pitch_enabled or quiet or len(frame) < 640:
            continue
        frame -= frame.mean()
        spectrum = np.fft.rfft(frame, n=2048)
        correlation = np.fft.irfft(spectrum * spectrum.conj(), n=2048)[:len(frame)]
        energy = np.concatenate(([0.0], np.cumsum(frame ** 2)))
        lags = np.arange(27, 267)  # Approximate search range: 60–600 Hz.
        denominator = np.sqrt(energy[len(frame) - lags] * (energy[-1] - energy[lags]))
        scores = correlation[lags] / np.maximum(denominator, 1e-15)
        peaks = [i for i in range(1, len(scores) - 1)
                 if scores[i] >= scores[i - 1] and scores[i] > scores[i + 1]]
        if not peaks:
            continue
        best = max(float(scores[i]) for i in peaks)
        if best < 0.85:
            continue
        index = next(i for i in peaks if scores[i] >= best - 0.02)
        pitches.append(RATE / int(lags[index]))
        periodicities.append(min(1.0, float(scores[index])))
    voiced_fraction = len(pitches) / len(frames)
    reliable = pitch_enabled and voiced_fraction >= 0.5
    return {
        "rms": rms, "rms_dbfs": dbfs,
        "pitch_median_hz": float(np.median(pitches)) if reliable else None,
        "pitch_periodicity": float(np.median(periodicities)) if reliable else None,
        "voiced_fraction": voiced_fraction if pitch_enabled else None,
        "low_energy_fraction": sum(length for _, length, quiet in frames if quiet)
                               / len(samples),
        "speech_detected": None, "laughter_probability": None,
    }, frames


def media_windows(source: Path, *, window_seconds: float, max_seconds: float | None):
    """Yield bounded mono buffers with PTS-derived original-media timestamps."""
    import av
    import numpy as np

    with av.open(str(source)) as container:
        if not container.streams.audio:
            raise ValueError("Input has no audio stream")
        origin = (container.start_time or 0) / av.time_base
        resampler = av.AudioResampler(format="fltp", layout="mono", rate=RATE)
        pending = np.empty(0, dtype=np.float32)
        start = None
        size = round(window_seconds * RATE)

        def frames():
            for frame in container.decode(container.streams.audio[0]):
                yield from resampler.resample(frame)
            yield from resampler.resample(None)

        for frame in frames():
            if frame.pts is None or frame.time_base is None:
                raise ValueError("Audio timestamps unavailable; cannot preserve original timeline")
            timestamp = float(frame.pts * frame.time_base) - origin
            data = frame.to_ndarray().reshape(-1)
            if timestamp < 0:
                trim = min(len(data), round(-timestamp * RATE))
                data = data[trim:]
                timestamp = max(0, timestamp + trim / RATE)
            if max_seconds is not None:
                data = data[:max(0, round((max_seconds - timestamp) * RATE))]
            if not len(data):
                if max_seconds is not None and timestamp >= max_seconds:
                    break
                continue
            if start is None:
                start = timestamp
            expected = start + len(pending) / RATE
            if abs(timestamp - expected) > 2 / RATE:
                if timestamp < expected:
                    raise ValueError("Overlapping/backward audio timestamps are unsupported")
                if len(pending):
                    yield start, pending
                pending = np.empty(0, dtype=np.float32)
                start = timestamp
            pending = np.concatenate((pending, data))
            while len(pending) >= size:
                yield start, pending[:size]
                pending = pending[size:]
                start += size / RATE
        if len(pending):
            yield start, pending


def analyze_audio(
    source: Path, *, window_seconds: float = 1, silence_dbfs: float = -40,
    min_pause_seconds: float = 0.3, pitch_enabled: bool = True,
    max_seconds: float | None = None, progress: Callable[[float], None] | None = None,
) -> dict:
    if not source.is_file():
        raise FileNotFoundError(f"Input media not found: {source}")
    if (not all(math.isfinite(x) for x in (window_seconds, silence_dbfs, min_pause_seconds))
            or not 0.04 <= window_seconds <= 60 or not -120 <= silence_dbfs <= 0
            or min_pause_seconds <= 0
            or max_seconds is not None and (not math.isfinite(max_seconds) or max_seconds <= 0)):
        raise ValueError("Invalid audio settings (window: 0.04–60s, silence: -120–0 dBFS)")
    try:
        import av
        import numpy as np
    except ImportError as exc:
        raise RuntimeError('Install audio dependencies: pip install -e ".[audio]"') from exc
    windows, pauses = [], []
    quiet_start, quiet_end = None, None

    def finish_pause():
        nonlocal quiet_start, quiet_end
        if quiet_start is not None and quiet_end - quiet_start >= min_pause_seconds - 1e-8:
            pauses.append({"start": round(quiet_start, 6), "end": round(quiet_end, 6)})
        quiet_start, quiet_end = None, None

    next_report = 60
    try:
        for start, samples in media_windows(
                source, window_seconds=window_seconds, max_seconds=max_seconds):
            values, frames = window_features(
                samples, silence_dbfs=silence_dbfs, pitch_enabled=pitch_enabled)
            end = start + len(samples) / RATE
            windows.append({"start": round(start, 6), "end": round(end, 6), **values})
            for offset, length, quiet in frames:
                frame_start, frame_end = start + offset / RATE, start + (offset + length) / RATE
                if quiet_start is not None and abs(frame_start - quiet_end) > 2 / RATE:
                    finish_pause()
                if quiet:
                    if quiet_start is None:
                        quiet_start = frame_start
                    quiet_end = frame_end
                else:
                    finish_pause()
            if progress is not None and end >= next_report:
                progress(end)
                next_report = end + 60
    except av.error.FFmpegError as exc:
        raise RuntimeError(f"Audio decoding failed: {exc}") from exc
    finish_pause()
    if not windows:
        raise ValueError("Input has no decodable audio samples in the requested range")
    result = {
        "schema_version": "1.1", "source_media": source.name,
        "duration_seconds": windows[-1]["end"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "generated_by": "physical-audio-v1",
        "analysis": {"sample_rate_hz": RATE, "channels": 1, "audio_stream": 0,
                     "decoder": "PyAV", "decoder_version": av.__version__,
                     "numpy_version": np.__version__, "window_seconds": window_seconds,
                     "silence_dbfs": silence_dbfs, "min_pause_seconds": min_pause_seconds,
                     "pitch_enabled": pitch_enabled, "max_seconds": max_seconds,
                     "pitch_method": "normalized-autocorrelation-v1",
                     "pitch_range_hz": [60, 600], "frame_seconds": 0.04,
                     "periodicity_threshold": 0.85, "min_voiced_fraction": 0.5},
        "feature_definitions": {
            "rms": "linear full-scale amplitude of resampled mono audio; no loudness normalization",
            "rms_dbfs": "20*log10(rms), dBFS; null for digital zero",
            "pitch_median_hz": "periodic frame median, Hz; null if insufficient periodicity",
            "pitch_periodicity": "normalized autocorrelation; not speech confidence/probability",
            "voiced_fraction": "fraction of periodic frames; null when pitch disabled",
            "low_energy_fraction": "fraction of samples in frames below silence_dbfs",
            "pauses": "low-energy intervals, not verified speech pauses; music/noise may mask them",
        },
        "windows": windows, "pauses": pauses,
    }
    validate_audio_features(result)
    return result
