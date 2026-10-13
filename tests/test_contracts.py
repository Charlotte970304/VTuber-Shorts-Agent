import copy
import json
from pathlib import Path

import pytest

from vtuber_shorts_agent.contracts import validate_transcript

EXAMPLE_PATH = Path(__file__).parents[1] / "examples" / "transcript.example.json"


def example():
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_example_is_valid():
    validate_transcript(example())


def test_invalid_time_range_is_rejected():
    payload = copy.deepcopy(example())
    payload["segments"][0]["end"] = payload["segments"][0]["start"]
    with pytest.raises(ValueError, match="invalid time range"):
        validate_transcript(payload)


def test_missing_schema_is_rejected():
    payload = example()
    del payload["schema_version"]
    with pytest.raises(ValueError, match="schema_version"):
        validate_transcript(payload)
