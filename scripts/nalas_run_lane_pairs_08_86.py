#!/usr/bin/env python
import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "scripts" / "nalas_lane_pair_pipeline.py"


def run(args):
    command = [sys.executable, "-u", str(PIPELINE), *args]
    print("RUN", " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=str(ROOT))
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-chapter", type=int, default=8)
    parser.add_argument("--end-chapter", type=int, default=86)
    parser.add_argument("--pairs-per-batch", type=int, default=2)
    parser.add_argument("--images-per-minute", type=float, default=4.0)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--limit-chapters", type=int, default=0)
    args = parser.parse_args()

    run(
        [
            "--build-manifest",
            "--extract-text",
            "--images-per-minute",
            str(args.images_per_minute),
            "--pairs-per-batch",
            str(args.pairs_per_batch),
        ]
    )
    chapters = list(range(args.start_chapter, args.end_chapter + 1))
    if args.limit_chapters:
        chapters = chapters[: args.limit_chapters]
    for chapter in chapters:
        run(["--prepare-chapter", str(chapter), "--pairs-per-batch", str(args.pairs_per_batch)])
        run(
            [
                "--run-chapter",
                str(chapter),
                "--pairs-per-batch",
                str(args.pairs_per_batch),
                "--model",
                args.model,
                "--timeout",
                str(args.timeout),
                "--wait-on-rate-limit",
            ]
        )


if __name__ == "__main__":
    main()
