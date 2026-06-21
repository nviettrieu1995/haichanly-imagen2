#!/usr/bin/env python
import argparse
import json
import shutil
import time
from pathlib import Path

from nalas_verify_outputs import check_png, load_plan, parse_chapter_list


ROOT = Path(__file__).resolve().parents[1]
FINAL_DIR = ROOT / "nalas_chapters_08_86" / "final_image_video"
STATUS_PATH = FINAL_DIR / "_sync_status.json"


def copy_if_needed(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        source_stat = source.stat()
        target_stat = target.stat()
        if target_stat.st_size == source_stat.st_size and target_stat.st_mtime >= source_stat.st_mtime:
            return False
    shutil.copy2(source, target)
    return True


def valid_image(path):
    result = check_png(path)
    return result["exists"] and result["valid_png"] and result["ratio_ok"]


def sync_once(chapters):
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    mirrored_images = 0
    mirrored_pairs = 0
    pending_pairs = 0
    chapters_status = []

    for chapter in chapters:
        plan = load_plan(chapter)
        chapter_dir = FINAL_DIR / f"C{chapter:03d}"
        chapter_pairs = 0
        chapter_images = 0
        chapter_copied = 0
        chapter_pending = 0

        for lane in plan["lanes"]:
            start_source = Path(lane["start_target"])
            end_source = Path(lane["end_target"])
            if not (valid_image(start_source) and valid_image(end_source)):
                chapter_pending += 1
                continue

            for source in [start_source, end_source]:
                target = chapter_dir / source.name
                if copy_if_needed(source, target):
                    copied += 1
                    chapter_copied += 1
                chapter_images += 1

            chapter_pairs += 1

        mirrored_pairs += chapter_pairs
        mirrored_images += chapter_images
        pending_pairs += chapter_pending
        chapters_status.append(
            {
                "chapter": chapter,
                "mirrored_pairs": chapter_pairs,
                "target_pairs": len(plan["lanes"]),
                "mirrored_images": chapter_images,
                "target_images": len(plan["lanes"]) * 2,
                "pending_pairs": chapter_pending,
                "copied_this_run": chapter_copied,
            }
        )

    status = {
        "final_dir": str(FINAL_DIR),
        "mirrored_pairs": mirrored_pairs,
        "mirrored_images": mirrored_images,
        "pending_pairs": pending_pairs,
        "copied_this_run": copied,
        "chapters": chapters_status,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-chapter", type=int, default=8)
    parser.add_argument("--end-chapter", type=int, default=86)
    parser.add_argument("--chapter", type=int)
    parser.add_argument("--exclude-chapters", default="")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()

    excluded = parse_chapter_list(args.exclude_chapters)
    chapters = [args.chapter] if args.chapter else list(range(args.start_chapter, args.end_chapter + 1))
    chapters = [chapter for chapter in chapters if chapter not in excluded]

    while True:
        status = sync_once(chapters)
        print(
            f"final_sync pairs={status['mirrored_pairs']} images={status['mirrored_images']} "
            f"pending_pairs={status['pending_pairs']} copied={status['copied_this_run']}",
            flush=True,
        )
        if not args.watch:
            break
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    main()
