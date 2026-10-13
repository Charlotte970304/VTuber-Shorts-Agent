"""Transcription, offline event discovery and manual experiment CLI."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .contracts import validate_selection, validate_transcript
from .io_utils import read_json, write_json
from .prompting import prepare_prompts
from .selection import discover_events, load_transcript
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
    discover = commands.add_parser("discover-events", help="Local JSON/SRT text-cue baseline")
    discover.add_argument("--input", type=Path, required=True)
    discover.add_argument("--output", type=Path, required=True)
    discover.add_argument("--gap-seconds", type=float, default=3)
    discover.add_argument("--max-event-seconds", type=float, default=90)
    discover.add_argument("--context-seconds", type=float, default=15)
    discover.add_argument("--max-events", type=int, default=20)
    discover.add_argument("--overwrite", action="store_true")
    prompts = commands.add_parser("prepare-prompts", help="Export three-round experiment inputs")
    prompts.add_argument("--input", type=Path, required=True)
    prompts.add_argument("--output", type=Path, required=True)
    prompts.add_argument("--chunk-seconds", type=float, default=600)
    prompts.add_argument("--overlap-seconds", type=float, default=60)
    prompts.add_argument("--overwrite", action="store_true")
    selection = commands.add_parser("validate-selection", help="Validate events/candidates JSON")
    selection.add_argument("--input", type=Path, required=True)
    selection.add_argument("--kind", choices=("events", "candidates"), default="candidates")
    selection.add_argument("--transcript", type=Path, help="Optional JSON/SRT evidence source")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate-transcript":
            data = read_json(args.input)
            validate_transcript(data)
            print(f"Valid transcript: {len(data['segments'])} segments")
            return 0

        if args.command == "validate-selection":
            data = read_json(args.input)
            source = load_transcript(args.transcript) if args.transcript else None
            validate_selection(data, kind=args.kind, transcript=source)
            print(f"Valid {args.kind}: {len(data[args.kind])} items")
            return 0

        if args.command in ("discover-events", "prepare-prompts"):
            if args.input.resolve() == args.output.resolve():
                raise ValueError("Input and output paths must be different")
            if args.output.exists() and not args.overwrite:
                raise FileExistsError(f"Output exists: {args.output} (use --overwrite)")
            transcript = load_transcript(args.input)
            if args.command == "discover-events":
                data = discover_events(
                    transcript, gap_seconds=args.gap_seconds,
                    max_event_seconds=args.max_event_seconds,
                    context_seconds=args.context_seconds, max_events=args.max_events,
                )
                validate_selection(data, kind="events", transcript=transcript)
            else:
                data = prepare_prompts(transcript, chunk_seconds=args.chunk_seconds,
                                       overlap_seconds=args.overlap_seconds)
            write_json(args.output, data)
            print(f"Saved: {args.output}")
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
