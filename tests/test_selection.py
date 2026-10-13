import copy
import json
from pathlib import Path

import pytest

from vtuber_shorts_agent.cli import main
from vtuber_shorts_agent.contracts import validate_selection
from vtuber_shorts_agent.prompting import prepare_prompts
from vtuber_shorts_agent.selection import discover_events, load_transcript, transcript_chunks

ROOT = Path(__file__).parents[1]


def source():
    return load_transcript(ROOT / "examples/transcript.example.json")


def test_baseline_evidence_and_original_time():
    transcript = source()
    result = discover_events(transcript)
    validate_selection(result, kind="events", transcript=transcript)
    event = result["events"][0]
    assert (event["start"], event["end"]) == (2, 8.6)
    assert event["evidence_segment_ids"] == [1, 2]
    assert event["needs_more_context"] is True
    assert event["context_start"] == 0
    assert event["context_end"] == 20
    assert result["selection_strategy"] == "text-cues-v1"


def test_silence_separates_events_and_priority_limits():
    transcript = source()
    transcript["duration_seconds"] = 100
    transcript["segments"].append(
        {"id": 3, "start": 80, "end": 84, "text": "実はまさか、でも嘘？", "words": None})
    result = discover_events(transcript, max_events=1)
    assert len(result["events"]) == 1
    assert result["events"][0]["start"] == 80


def test_no_cues_returns_empty_not_fabricated_events():
    transcript = source()
    for row in transcript["segments"]:
        row["text"] = "こんにちは"
    assert discover_events(transcript)["events"] == []


def test_duplicates_rejected_and_unsorted_segments_sorted():
    transcript = source()
    transcript["segments"].reverse()
    assert discover_events(transcript)["events"][0]["evidence_segment_ids"] == [1, 2]
    transcript["segments"][0]["id"] = 1
    with pytest.raises(ValueError, match="unique"):
        discover_events(transcript)


def test_overlapping_chunks_keep_boundary_evidence():
    transcript = source()
    chunks = transcript_chunks(transcript, chunk_seconds=6, overlap_seconds=2)
    assert chunks[0]["segments"][1]["id"] == 2
    assert chunks[1]["segments"][1]["id"] == 2
    ids = {row["id"] for chunk in chunks for row in chunk["segments"]}
    assert ids == {1, 2}
    assert chunks[-1]["end"] <= 20
    assert chunks[1]["segments"][1]["start"] == 5.2


@pytest.mark.parametrize("settings", [
    {"gap_seconds": -1}, {"max_event_seconds": 0}, {"context_seconds": float("nan")},
    {"max_events": 0}, {"gap_seconds": float("inf")},
])
def test_invalid_discovery_settings(settings):
    with pytest.raises(ValueError):
        discover_events(source(), **settings)


@pytest.mark.parametrize("chunk,overlap", [(0, 0), (60, 60), (60, -1), (float("inf"), 0)])
def test_invalid_chunk_settings(chunk, overlap):
    with pytest.raises(ValueError):
        transcript_chunks(source(), chunk_seconds=chunk, overlap_seconds=overlap)


def test_srt_import_bom_multiline_and_long_timestamp(tmp_path):
    path = tmp_path / "stream.srt"
    path.write_text("10\n04:00:00,250 --> 04:00:02,500\nえっ？\n実は\n", encoding="utf-8-sig")
    transcript = load_transcript(path)
    assert transcript["segments"][0]["start"] == 14400.25
    assert transcript["segments"][0]["text"] == "えっ？\n実は"
    assert transcript["duration_seconds"] == 14402.5
    validate_selection(discover_events(transcript), kind="events", transcript=transcript)


@pytest.mark.parametrize("content", ["", "1\n00:60:00,000 --> 01:00:02,000\nx",
                                      "1\n00:00:03,000 --> 00:00:02,000\nx"])
def test_malformed_srt_rejected(tmp_path, content):
    path = tmp_path / "bad.srt"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        load_transcript(path)


def test_prompt_bundle_has_three_rounds_and_schemas():
    bundle = prepare_prompts(source())
    assert set(bundle["prompts"]) == {"round_1", "round_2", "round_3"}
    assert set(bundle["schemas"]) == {"events", "candidates"}
    assert bundle["prompt_version"] == "three-round-v1"
    assert bundle["round_1_inputs"][0]["segments"] == source()["segments"]


def test_cli_discovery_validation_and_overwrite(tmp_path):
    path = tmp_path / "events.json"
    transcript = ROOT / "examples/transcript.example.json"
    args = ["discover-events", "--input", str(transcript), "--output", str(path)]
    assert main(args) == 0
    assert main(["validate-selection", "--kind", "events", "--input", str(path),
                 "--transcript", str(transcript)]) == 0
    content = path.read_bytes()
    assert main(args) == 1
    assert path.read_bytes() == content
    assert main(args + ["--overwrite"]) == 0


def test_cli_prompt_export_and_input_protection(tmp_path):
    path = tmp_path / "source.json"
    path.write_text(json.dumps(source()), encoding="utf-8")
    original = path.read_bytes()
    assert main(["prepare-prompts", "--input", str(path), "--output", str(path),
                 "--overwrite"]) == 1
    assert path.read_bytes() == original
    output = tmp_path / "prompts.json"
    assert main(["prepare-prompts", "--input", str(path), "--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["prompt_version"] == "three-round-v1"


def candidate():
    return json.loads((ROOT / "examples/candidates.example.json").read_text(encoding="utf-8"))


def test_existing_candidate_example_is_compatible():
    validate_selection(candidate(), transcript=source())


@pytest.mark.parametrize("field,value", [
    ("start", -1), ("end", 30), ("context_start", 3), ("context_end", 21),
    ("evidence_segment_ids", [999]), ("evidence_segment_ids", [True]),
    ("evidence_segment_ids", []), ("review_status", "published"), ("scores", {"hook": 8}),
])
def test_invalid_candidates_rejected(field, value):
    payload = candidate()
    payload["candidates"][0][field] = value
    with pytest.raises(ValueError):
        validate_selection(payload, transcript=source())


def test_duplicate_candidates_and_wrong_source_rejected():
    payload = candidate()
    payload["candidates"].append(copy.deepcopy(payload["candidates"][0]))
    with pytest.raises(ValueError, match="unique"):
        validate_selection(payload)
    payload = candidate()
    payload["source_media"] = "other.mp4"
    with pytest.raises(ValueError, match="source_media"):
        validate_selection(payload, transcript=source())


def test_scored_candidates_require_rubric():
    payload = candidate()
    row = payload["candidates"][0]
    row["scores"] = dict.fromkeys(
        ("hook", "understandability", "personality", "payoff", "clipability"), 3)
    with pytest.raises(ValueError, match="rubric"):
        validate_selection(payload)
    row["score_rubric_version"] = "new-viewer-v1"
    validate_selection(payload)
