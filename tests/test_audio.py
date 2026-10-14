import copy
import json
import wave
from pathlib import Path

import av
import numpy as np
import pytest

from vtuber_shorts_agent.audio import RATE, analyze_audio, window_features
from vtuber_shorts_agent.cli import main
from vtuber_shorts_agent.contracts import validate_audio_features


def tone(seconds=1, frequency=200):
    return (0.2 * np.sin(2 * np.pi * frequency * np.arange(round(seconds * RATE)) / RATE)
            ).astype(np.float32)


def wav(path, samples):
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes((samples * 32767).astype("<i2").tobytes())
    return path


def test_tone_rms_pitch_and_periodicity():
    values, _ = window_features(tone())
    assert values["rms"] == pytest.approx(0.2 / np.sqrt(2), rel=1e-5)
    assert values["rms_dbfs"] == pytest.approx(-16.9897, abs=0.001)
    assert values["pitch_median_hz"] == pytest.approx(200, abs=2)
    assert values["pitch_periodicity"] > 0.99


def test_silence_and_noise_do_not_fabricate_pitch():
    values, _ = window_features(np.zeros(RATE, dtype=np.float32))
    assert values["rms"] == 0
    assert values["rms_dbfs"] is None
    assert values["pitch_median_hz"] is None
    assert values["low_energy_fraction"] == 1
    values, _ = window_features(np.random.default_rng(123).normal(0, 0.1, RATE))
    assert values["pitch_median_hz"] is None


def test_real_decode_partial_window_and_pause_across_windows(tmp_path):
    samples = np.concatenate((tone(0.8), np.zeros(round(0.8 * RATE)), tone(0.65)))
    data = analyze_audio(wav(tmp_path / "sample.wav", samples))
    validate_audio_features(data)
    assert len(data["windows"]) == 3
    assert data["duration_seconds"] == 2.25
    assert data["pauses"] == [{"start": 0.8, "end": 1.6}]
    assert data["windows"][-1]["end"] == 2.25
    assert data["source_media"] == "sample.wav"
    assert data["analysis"]["decoder_version"] == av.__version__


def test_preview_and_no_pitch(tmp_path):
    path = wav(tmp_path / "sample.wav", tone(3))
    data = analyze_audio(path, max_seconds=1.25, pitch_enabled=False)
    assert data["duration_seconds"] == 1.25
    assert all(row["pitch_median_hz"] is None for row in data["windows"])
    assert all(row["voiced_fraction"] is None for row in data["windows"])


def test_pts_offset_preserved_in_media(tmp_path):
    path = tmp_path / "offset.mkv"
    with av.open(str(path), "w") as container:
        video = container.add_stream("mpeg4", rate=25)
        video.width = video.height = 16
        video.pix_fmt = "yuv420p"
        audio = container.add_stream("pcm_s16le", rate=RATE)
        audio.layout = "mono"
        image = av.VideoFrame.from_ndarray(np.zeros((16, 16, 3), dtype=np.uint8), format="rgb24")
        image.pts = 0
        for packet in video.encode(image):
            container.mux(packet)
        for packet in video.encode(None):
            container.mux(packet)
        from fractions import Fraction

        frame = av.AudioFrame.from_ndarray((tone() * 32767).astype(np.int16).reshape(1, -1),
                                          format="s16", layout="mono")
        frame.sample_rate = RATE
        frame.time_base = Fraction(1, RATE)
        frame.pts = 2 * RATE
        for packet in audio.encode(frame):
            container.mux(packet)
        for packet in audio.encode(None):
            container.mux(packet)
    data = analyze_audio(path)
    assert data["windows"][0]["start"] == pytest.approx(2, abs=0.001)
    assert data["duration_seconds"] == pytest.approx(3, abs=0.001)
    assert data["pauses"] == []


@pytest.mark.parametrize("settings", [
    {"window_seconds": 0}, {"window_seconds": float("nan")}, {"silence_dbfs": 1},
    {"max_seconds": float("inf")}, {"min_pause_seconds": -1},
])
def test_invalid_settings(tmp_path, settings):
    path = wav(tmp_path / "sample.wav", tone())
    with pytest.raises(ValueError):
        analyze_audio(path, **settings)


def test_corrupt_media_returns_cli_error(tmp_path):
    path = tmp_path / "bad.mp4"
    path.write_bytes(b"not media")
    assert main(["analyze-audio", "--input", str(path),
                 "--output", str(tmp_path / "out.json")]) == 1


def test_cli_analysis_validation_and_output_protection(tmp_path):
    path = wav(tmp_path / "sample.wav", tone())
    out = tmp_path / "features.json"
    args = ["analyze-audio", "--input", str(path), "--output", str(out)]
    assert main(args) == 0
    assert main(["validate-audio", "--input", str(out)]) == 0
    before = out.read_bytes()
    assert main(args) == 1
    assert out.read_bytes() == before
    original = path.read_bytes()
    assert main(["analyze-audio", "--input", str(path), "--output", str(path),
                 "--overwrite"]) == 1
    assert path.read_bytes() == original


@pytest.mark.parametrize("field,value", [
    ("rms", -1), ("pitch_median_hz", 900), ("pitch_periodicity", 1.1),
    ("low_energy_fraction", float("nan")), ("speech_detected", True),
])
def test_invalid_measurements(tmp_path, field, value):
    data = analyze_audio(wav(tmp_path / "sample.wav", tone()))
    data["windows"][0][field] = value
    with pytest.raises(ValueError):
        validate_audio_features(data)


def test_overlapping_windows_rejected(tmp_path):
    data = analyze_audio(wav(tmp_path / "sample.wav", tone(2)))
    data["windows"][1]["start"] = 0.5
    with pytest.raises(ValueError):
        validate_audio_features(data)


def test_example_contract():
    path = Path(__file__).parents[1] / "examples/audio_features.example.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_audio_features(copy.deepcopy(data))
