"""Minimal command-line interface; planned features are intentionally absent."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .contracts import validate_transcript
from .io_utils import read_json, write_json
from .srt import to_srt
from .transcribe import transcribe_media


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vtuber-shorts", description="VTuber Shorts Agent")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    transcribe = commands.add_parser("transcribe", help="Transcribe Japanese speech to JSON/SRT")
    transcribe.add_argument("--input", type=Path, required=True)
    transcribe.add_argument("--output", type=Path, required=True)
    transcribe.add_argument("--srt", type=Path, help="Optional SRT output path")
    transcribe.add_argument("--model", default="small", help="Whisper model (default: small)")
    transcribe.add_argument("--device", choices=("cpu", "cuda", "auto"), default="cpu")
    transcribe.add_argument("--compute-type", default="int8")
    transcribe.add_argument("--vad-filter", action="store_true")
    transcribe.add_argument("--no-word-timestamps", action="store_true")
    transcribe.add_argument("--overwrite", action="store_true")

    validate = commands.add_parser("validate-transcript", help="Validate transcript JSON")
    validate.add_argument("--input", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate-transcript":
            data = read_json(args.input)
            validate_transcript(data)
            print(f"Valid transcript: {len(data['segments'])} segments")
            return 0

        outputs = [args.output]
        if args.srt is not None:
            outputs.append(args.srt)
        if len(set(path.resolve() for path in outputs)) != len(outputs):
            raise ValueError("JSON and SRT output paths must be different")
        for output in outputs:
            if output.exists() and not args.overwrite:
                raise FileExistsError(f"Output exists: {output} (use --overwrite)")
        data = transcribe_media(
            args.input,
            model_name=args.model,
            device=args.device,
            compute_type=args.compute_type,
            vad_filter=args.vad_filter,
            word_timestamps=not args.no_word_timestamps,
        )
        write_json(args.output, data)
        if args.srt is not None:
            args.srt.parent.mkdir(parents=True, exist_ok=True)
            args.srt.write_text(to_srt(data["segments"]), encoding="utf-8-sig")
        print(f"Saved: {args.output} ({len(data['segments'])} segments)")
        if args.srt is not None:
            print(f"Saved: {args.srt}")
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
