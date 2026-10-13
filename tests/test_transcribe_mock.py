"""Test the integration flow without downloading a speech model."""

from vtuber_shorts_agent import cli


def test_transcribe_command_writes_json_and_srt(monkeypatch, tmp_path):
    media = tmp_path / "local.mp4"
    media.write_bytes(b"dummy")
    output = tmp_path / "data" / "transcript.json"
    srt = tmp_path / "data" / "transcript.srt"

    def fake_transcribe(source, **kwargs):
        assert source == media
        return {
            "schema_version": "1.0",
            "source_media": media.name,
            "duration_seconds": 10.0,
            "language": "ja",
            "created_at_utc": "2026-10-13T00:00:00+00:00",
            "model": {"name": "mock"},
            "segments": [{"id": 1, "start": 0.0, "end": 2.0, "text": "こんにちは", "words": None}],
        }

    monkeypatch.setattr(cli, "transcribe_media", fake_transcribe)
    assert cli.main([
        "transcribe", "--input", str(media), "--output", str(output), "--srt", str(srt)
    ]) == 0
    assert output.exists()
    assert "こんにちは" in srt.read_text(encoding="utf-8-sig")
    assert cli.main(["transcribe", "--input", str(media), "--output", str(output)]) == 1
