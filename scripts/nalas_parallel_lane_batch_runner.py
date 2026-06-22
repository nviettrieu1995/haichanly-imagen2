#!/usr/bin/env python
import argparse
from collections import deque
import json
import subprocess
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

from nalas_chapters_pipeline import (
    CODEX_IMAGEN,
    LOG_DIR,
    MANIFEST_PATH,
    ROOT,
    build_manifest,
    extract_chapter_texts,
    is_transient,
    load_manifest,
    log,
    parse_json,
    parse_rate_limit,
)
from nalas_lane_pair_pipeline import (
    CANONICAL_HEAVEN_FATHER_REF,
    CANONICAL_PHAM_TRAN_REF,
    C008_YOUNG_PHAM_TRAN_REF,
    PAIR_PROMPT_DIR,
    plan_paths_match_current_root,
    prepare_chapter_lane_pairs,
    write_pair_manifest,
)


BATCH_LOG_DIR = LOG_DIR / "lane_batch_jobs"
PRINT_LOCK = threading.Lock()


def say(message):
    with PRINT_LOCK:
        log(message)


def parse_chapter_list(value):
    chapters = set()
    if not value:
        return chapters
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = [int(piece.strip()) for piece in part.split("-", 1)]
            chapters.update(range(start, end + 1))
        else:
            chapters.add(int(part))
    return chapters


def ensure_plans(start_chapter, end_chapter, images_per_minute, pairs_per_batch, skip_extract, excluded=None):
    excluded = excluded or set()
    if not MANIFEST_PATH.exists():
        manifest = build_manifest(images_per_minute)
        say(
            f"manifest: {len(manifest['chapters'])} chapters, "
            f"{manifest['total_minutes']} minutes, {manifest['total_target_images']} images"
        )
    else:
        manifest = load_manifest()
    write_pair_manifest(manifest, pairs_per_batch)
    if not skip_extract:
        extract_chapter_texts(manifest)

    plans = []
    for chapter_number in range(start_chapter, end_chapter + 1):
        if chapter_number in excluded:
            continue
        plan_path = PAIR_PROMPT_DIR / f"C{chapter_number:03d}" / "chapter_lane_pair_plan.json"
        if plan_path.exists():
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            if not plan_paths_match_current_root(plan):
                say(f"C{chapter_number:03d}: cached lane plan points outside this repo, regenerating")
                plan = prepare_chapter_lane_pairs(manifest, chapter_number, pairs_per_batch)
        else:
            plan = prepare_chapter_lane_pairs(manifest, chapter_number, pairs_per_batch)
        plans.append(plan)
    return plans


def collect_missing_batch_jobs(plans, max_batches, force=False, only_divine_ref=False, exclude_divine_ref=False):
    jobs = []
    for plan in plans:
        for batch in plan["batches"]:
            if only_divine_ref and not batch.get("use_divine_nalas_ref", False):
                continue
            if exclude_divine_ref and batch.get("use_divine_nalas_ref", False):
                continue
            targets = [Path(path) for path in batch["targets"]]
            if all(path.exists() for path in targets) and not force:
                continue
            jobs.append(
                {
                    "chapter": int(plan["chapter"]),
                    "batch": int(batch["batch"]),
                    "prompt_file": Path(batch["prompt_file"]),
                    "output_stem": Path(batch["output_stem"]),
                    "targets": targets,
                    "use_pham_tran_ref": bool(batch.get("use_pham_tran_ref", True)),
                    "use_divine_nalas_ref": bool(batch.get("use_divine_nalas_ref", False)),
                }
            )
            if max_batches and len(jobs) >= max_batches:
                return jobs
    return jobs


def remove_source_if_extra(source, targets):
    try:
        source_path = Path(source)
        if source_path.exists() and source_path not in targets:
            source_path.unlink()
    except OSError:
        pass


def save_images_from_json(stdout, targets, force):
    result = parse_json(stdout)
    images = result.get("images") or []
    saved = 0
    targets = [Path(path) for path in targets]
    for image, target in zip(images, targets):
        source = Path(image["path"])
        if target.exists() and force:
            target.unlink()
        if target.exists():
            remove_source_if_extra(source, targets)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() == target.resolve():
            saved += int(target.exists())
            continue
        source.replace(target)
        saved += 1
    return saved, len(images), all(path.exists() for path in targets)


def run_batch_job(job, model, timeout, wait_on_rate_limit, force):
    targets = [Path(path) for path in job["targets"]]
    if all(path.exists() for path in targets) and not force:
        return True
    if force:
        for target in targets:
            if target.exists():
                target.unlink()

    label = f"C{job['chapter']:03d}_lane_batch_{job['batch']:03d}"
    BATCH_LOG_DIR.mkdir(parents=True, exist_ok=True)
    stdout_log = BATCH_LOG_DIR / f"{label}.stdout.log"
    stderr_log = BATCH_LOG_DIR / f"{label}.stderr.log"
    command = [
        "node",
        str(CODEX_IMAGEN),
        "--json",
        "--model",
        model,
        "--timeout",
        str(timeout),
        "--retries",
        "4",
        "--output",
        str(job["output_stem"]),
        "--prompt-file",
        str(job["prompt_file"]),
    ]
    pham_tran_ref = CANONICAL_PHAM_TRAN_REF
    if int(job["chapter"]) == 8 and C008_YOUNG_PHAM_TRAN_REF.exists():
        pham_tran_ref = C008_YOUNG_PHAM_TRAN_REF
    if pham_tran_ref.exists() and job.get("use_pham_tran_ref", True):
        command.extend(["--input-ref", str(pham_tran_ref), "--image-detail", "high"])
    if CANONICAL_HEAVEN_FATHER_REF.exists() and job.get("use_divine_nalas_ref", False):
        command.extend(["--input-ref", str(CANONICAL_HEAVEN_FATHER_REF), "--image-detail", "high"])

    attempt = 1
    while True:
        say(f"{label}: start attempt {attempt}")
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout_log.write_text(completed.stdout, encoding="utf-8")
        stderr_log.write_text(completed.stderr, encoding="utf-8")
        if completed.returncode == 0:
            saved, returned, complete = save_images_from_json(completed.stdout, targets, force)
            say(
                f"{label}: returned={returned} saved={saved} "
                f"complete={'yes' if complete else 'no'}"
            )
            return complete

        rate = parse_rate_limit(completed.stderr)
        if wait_on_rate_limit and rate:
            wait_seconds, reset_at = rate
            say(f"{label}: rate limited, wait {wait_seconds}s reset={reset_at}")
            time.sleep(wait_seconds)
            attempt += 1
            continue
        if wait_on_rate_limit and is_transient(completed.stderr):
            wait_seconds = min(900, 60 * attempt)
            say(f"{label}: transient failure, wait {wait_seconds}s")
            time.sleep(wait_seconds)
            attempt += 1
            continue
        raise RuntimeError(completed.stderr[-1500:] or completed.stdout[-1500:])


def run_jobs(jobs, max_workers, model, timeout, wait_on_rate_limit, force, job_retries):
    completed_count = 0
    total = len(jobs)
    queued = deque(jobs)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        pending = {}

        def submit_next_jobs():
            while queued and len(pending) < max_workers:
                job = queued.popleft()
                pending[
                    executor.submit(
                        run_batch_job,
                        job,
                        model,
                        timeout,
                        wait_on_rate_limit,
                        force,
                    )
                ] = job

        submit_next_jobs()
        while pending:
            completed, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in completed:
                job = pending.pop(future)
                label = f"C{job['chapter']:03d} batch {job['batch']:03d}"
                try:
                    complete = future.result()
                    if not complete:
                        failures = int(job.get("failures", 0)) + 1
                        job["failures"] = failures
                        if failures <= job_retries:
                            say(f"{label}: partial batch, requeue {failures}/{job_retries}")
                            queued.appendleft(job)
                            continue
                        say(
                            f"{label}: partial batch still incomplete after "
                            f"{job_retries} retries; requeue later"
                        )
                        job["failures"] = 0
                        queued.append(job)
                        continue
                    completed_count += 1
                    say(f"lane-batch progress: {completed_count}/{total} (last {label})")
                except Exception as exc:
                    failures = int(job.get("failures", 0)) + 1
                    job["failures"] = failures
                    if failures <= job_retries:
                        say(f"{label}: failed, requeue {failures}/{job_retries}: {exc}")
                        queued.appendleft(job)
                        continue
                    say(f"{label}: failed permanently, leave frames for fallback: {exc}")
                    completed_count += 1
            submit_next_jobs()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-chapter", type=int, default=10)
    parser.add_argument("--end-chapter", type=int, default=86)
    parser.add_argument("--exclude-chapters", default="")
    parser.add_argument("--pairs-per-batch", type=int, default=2)
    parser.add_argument("--images-per-minute", type=float, default=4.0)
    parser.add_argument("--max-workers", type=int, default=2)
    parser.add_argument("--max-batches", type=int, default=0)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--job-retries", type=int, default=1)
    parser.add_argument("--wait-on-rate-limit", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--only-divine-ref", action="store_true")
    parser.add_argument("--exclude-divine-ref", action="store_true")
    parser.add_argument("--skip-extract", action="store_true")
    args = parser.parse_args()
    if args.only_divine_ref and args.exclude_divine_ref:
        raise SystemExit("--only-divine-ref and --exclude-divine-ref cannot be used together")

    excluded = parse_chapter_list(args.exclude_chapters)
    plans = ensure_plans(
        args.start_chapter,
        args.end_chapter,
        args.images_per_minute,
        args.pairs_per_batch,
        args.skip_extract,
        excluded,
    )
    jobs = collect_missing_batch_jobs(
        plans,
        args.max_batches,
        force=args.force,
        only_divine_ref=args.only_divine_ref,
        exclude_divine_ref=args.exclude_divine_ref,
    )
    say(
        f"parallel lane-batch runner: {len(jobs)} missing batches, "
        f"{args.max_workers} workers, chapters {args.start_chapter}-{args.end_chapter}"
    )
    if jobs:
        run_jobs(
            jobs,
            args.max_workers,
            args.model,
            args.timeout,
            args.wait_on_rate_limit,
            args.force,
            args.job_retries,
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130)
