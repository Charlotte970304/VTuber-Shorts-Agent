from pathlib import Path

from vtuber_shorts_agent.cli import main


def test_validate_example(capsys):
    example = Path(__file__).parents[1] / "examples" / "transcript.example.json"
    assert main(["validate-transcript", "--input", str(example)]) == 0
    assert "Valid transcript" in capsys.readouterr().out


def test_missing_file_returns_error(capsys, tmp_path):
    assert main(["validate-transcript", "--input", str(tmp_path / "missing.json")]) == 1
    assert "Error" in capsys.readouterr().err
