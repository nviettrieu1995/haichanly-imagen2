#!/usr/bin/env python
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "ch08_auto_lane_batch.py"


def run(args):
    command = [sys.executable, "-u", str(RUNNER), *args]
    print("RUN", " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=str(ROOT))
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main():
    run([
        "--profile",
        "startend",
        "--batch-size",
        "1",
        "--missing-only",
        "--model",
        "gpt-5.5",
        "--timeout",
        "900",
        "--wait-on-rate-limit",
    ])
    run([
        "--profile",
        "full100",
        "--missing-only",
        "--model",
        "gpt-5.5",
        "--timeout",
        "900",
        "--wait-on-rate-limit",
    ])


if __name__ == "__main__":
    main()
