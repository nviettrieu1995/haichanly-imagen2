#!/usr/bin/env python
import argparse
import json
import subprocess
import sys
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
    PAIR_PROMPT_DIR,
    plan_paths_match_current_root,
    prepare_chapter_lane_pairs,
    reference_paths_for_batch,
    verify_chapter_pairs,
    write_pair_manifest,
)


FRAME_LOG_DIR = LOG_DIR / "frame_jobs"
PRINT_LOCK = threading.Lock()


def say(message):
    with PRINT_LOCK:
        log(message)


def frame_prompt_path(item):
    chapter = int(item["chapter"])
    lane = int(item["lane_index"])
    side = item["side"]
    directory = PAIR_PROMPT_DIR / f"C{chapter:03d}" / "frame_prompts"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"C{chapter:03d}_lane_{lane:03d}_{side}.txt"


def write_frame_prompt(item):
    path = frame_prompt_path(item)
    text = "\n".join(
        [
            "Generate exactly one separate standalone cinematic 16:9 image.",
            "Do not create a collage, grid, poster, contact sheet, or multi-panel image.",
            "No text, no subtitles, no watermark, no logo.",
            "",
            item["prompt"],
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")
    return path


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


def collect_missing_frame_jobs(plans, max_jobs):
    jobs = []
    for plan in plans:
        for item in plan["items"]:
            target = Path(item["target"])
            if target.exists():
                continue
            prompt_path = write_frame_prompt(item)
            jobs.append(
                {
                    "chapter": int(item["chapter"]),
                    "lane_index": int(item["lane_index"]),
                    "side": item["side"],
                    "target": target,
                    "prompt_file": prompt_path,
                    "use_pham_tran_ref": bool(item.get("use_pham_tran_ref", True)),
                    "use_divine_nalas_ref": bool(item.get("use_divine_nalas_ref", False)),
                    "visual_dna_tags": list(item.get("visual_dna_tags", [])),
                }
            )
            if max_jobs and len(jobs) >= max_jobs:
                return jobs
    return jobs


def write_all_frame_prompts(plans):
    count = 0
    for plan in plans:
        for item in plan["items"]:
            write_frame_prompt(item)
            count += 1
    say(f"rewrote {count} frame prompts from current lane-pair plans")
    return count


def save_output_from_json(stdout, target):
    if target.exists():
        return True
    result = parse_json(stdout)
    images = result.get("images") or []
    if not images:
        return False
    source = Path(images[0]["path"])
    if source.resolve() != target.resolve():
        source.replace(target)
    return target.exists()


def run_frame_job(job, model, timeout, wait_on_rate_limit, force):
    target = Path(job["target"])
    if target.exists() and not force:
        return "skip"
    if target.exists() and force:
        target.unlink()
    label = f"C{job['chapter']:03d}_lane_{job['lane_index']:03d}_{job['side']}"
    FRAME_LOG_DIR.mkdir(parents=True, exist_ok=True)
    stdout_log = FRAME_LOG_DIR / f"{label}.stdout.log"
    stderr_log = FRAME_LOG_DIR / f"{label}.stderr.log"
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
        str(target),
        "--prompt-file",
        str(job["prompt_file"]),
    ]
    for ref_path in reference_paths_for_batch(
        job["chapter"],
        job.get("use_pham_tran_ref", True),
        job.get("use_divine_nalas_ref", False),
        job.get("visual_dna_tags", []),
    ):
        command.extend(["--input-ref", str(ref_path), "--image-detail", "high"])
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
            if save_output_from_json(completed.stdout, target):
                say(f"{label}: saved {target.name}")
                return "done"
            raise RuntimeError(f"{label}: completed without image path")
        if target.exists() and target.stat().st_size > 100000:
            say(f"{label}: saved after nonzero return")
            return "done"
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
    done = 0
    total = len(jobs)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        pending = {
            executor.submit(run_frame_job, job, model, timeout, wait_on_rate_limit, force): job
            for job in jobs
        }
        while pending:
            completed, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in completed:
                job = pending.pop(future)
                try:
                    future.result()
                    done += 1
                    say(
                        f"frame progress: {done}/{total} "
                        f"(last C{job['chapter']:03d} lane {job['lane_index']:03d} {job['side']})"
                    )
                except Exception as exc:
                    failures = int(job.get("failures", 0)) + 1
                    job["failures"] = failures
                    label = f"C{job['chapter']:03d} lane {job['lane_index']:03d} {job['side']}"
                    if failures <= job_retries:
                        say(f"frame failed, requeue {failures}/{job_retries}: {label}: {exc}")
                        pending[
                            executor.submit(
                                run_frame_job,
                                job,
                                model,
                                timeout,
                                wait_on_rate_limit,
                                force,
                            )
                        ] = job
                        continue
                    say(f"frame failed permanently: {label}: {exc}")
                    for remaining in pending:
                        remaining.cancel()
                    raise


def verify_all(plans):
    chapters = []
    total_pairs = 0
    complete_pairs = 0
    total_images = 0
    complete_images = 0
    for plan in plans:
        chapter = int(plan["chapter"])
        lanes = plan["lanes"]
        chapter_total_pairs = len(lanes)
        chapter_complete_pairs = 0
        chapter_complete_images = 0
        for lane in lanes:
            has_start = Path(lane["start_target"]).exists()
            has_end = Path(lane["end_target"]).exists()
            chapter_complete_images += int(has_start) + int(has_end)
            chapter_complete_pairs += int(has_start and has_end)
        total_pairs += chapter_total_pairs
        complete_pairs += chapter_complete_pairs
        total_images += chapter_total_pairs * 2
        complete_images += chapter_complete_images
        chapters.append(
            {
                "chapter": chapter,
                "complete_pairs": chapter_complete_pairs,
                "target_pairs": chapter_total_pairs,
                "complete_images": chapter_complete_images,
                "target_images": chapter_total_pairs * 2,
            }
        )
    status = {
        "complete_pairs": complete_pairs,
        "target_pairs": total_pairs,
        "complete_images": complete_images,
        "target_images": total_images,
        "chapters": chapters,
    }
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return status


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-chapter", type=int, default=8)
    parser.add_argument("--end-chapter", type=int, default=86)
    parser.add_argument("--exclude-chapters", default="")
    parser.add_argument("--pairs-per-batch", type=int, default=2)
    parser.add_argument("--images-per-minute", type=float, default=4.0)
    parser.add_argument("--max-workers", type=int, default=3)
    parser.add_argument("--max-jobs", type=int, default=0)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--job-retries", type=int, default=3)
    parser.add_argument("--wait-on-rate-limit", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-extract", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--write-frame-prompts-only", action="store_true")
    parser.add_argument("--verify-chapter", type=int)
    args = parser.parse_args()

    excluded = parse_chapter_list(args.exclude_chapters)
    plans = ensure_plans(
        args.start_chapter,
        args.end_chapter,
        args.images_per_minute,
        args.pairs_per_batch,
        args.skip_extract,
        excluded,
    )
    if excluded:
        say(f"excluded chapters: {','.join(str(chapter) for chapter in sorted(excluded))}")
    if args.verify_chapter:
        verify_chapter_pairs(args.verify_chapter)
        return
    if args.write_frame_prompts_only:
        write_all_frame_prompts(plans)
        return
    if args.verify_only:
        verify_all(plans)
        return
    jobs = collect_missing_frame_jobs(plans, args.max_jobs)
    say(
        f"parallel frame runner: {len(jobs)} missing frames, "
        f"{args.max_workers} workers, chapters {args.start_chapter}-{args.end_chapter}"
    )
    if not jobs:
        verify_all(plans)
        return
    run_jobs(
        jobs,
        args.max_workers,
        args.model,
        args.timeout,
        args.wait_on_rate_limit,
        args.force,
        args.job_retries,
    )
    verify_all(plans)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130)
