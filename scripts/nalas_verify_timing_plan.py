#!/usr/bin/env python
import argparse
import json
import math
import sys
from pathlib import Path

from nalas_verify_outputs import parse_chapter_list


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = ROOT / "nalas_chapters_08_86"
CHAPTERS_MANIFEST = PIPELINE_ROOT / "chapters_manifest.json"
LANE_PAIRS_MANIFEST = PIPELINE_ROOT / "lane_pairs_manifest.json"
TEXT_DIR = PIPELINE_ROOT / "chapter_text"


def cid(chapter):
    return f"C{chapter:03d}"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def expected_image_count(duration_minutes, images_per_minute):
    return max(2, math.ceil(float(duration_minutes) * float(images_per_minute)))


def split_to_pairs(image_count):
    image_count = int(image_count)
    if image_count % 2:
        image_count += 1
    pair_count = max(1, image_count // 2)
    return pair_count, pair_count * 2


def chapter_filter(args):
    excluded = parse_chapter_list(args.exclude_chapters)
    chapters = [args.chapter] if args.chapter else list(range(args.start_chapter, args.end_chapter + 1))
    return [chapter for chapter in chapters if chapter not in excluded]


def index_by_chapter(manifest):
    return {int(item["chapter"]): item for item in manifest.get("chapters", [])}


def verify_chapter(chapter, chapter_item, pair_item, images_per_minute):
    issues = []
    if chapter_item is None:
        issues.append(f"{cid(chapter)} missing_from_chapters_manifest")
        return {"chapter": chapter, "issues": issues, "ok": False}
    if pair_item is None:
        issues.append(f"{cid(chapter)} missing_from_lane_pairs_manifest")

    text_path = TEXT_DIR / f"{cid(chapter)}.txt"
    if not text_path.exists():
        issues.append(f"{cid(chapter)} missing_chapter_text: {text_path}")

    duration = int(chapter_item.get("duration_minutes", 0))
    if duration <= 0:
        issues.append(f"{cid(chapter)} invalid_duration_minutes: {duration}")

    chapter_rate = float(chapter_item.get("images_per_minute", images_per_minute))
    if abs(chapter_rate - float(images_per_minute)) > 0.0001:
        issues.append(
            f"{cid(chapter)} chapter_rate_mismatch: {chapter_rate} expected {images_per_minute}"
        )

    expected_images = expected_image_count(duration, images_per_minute)
    expected_pairs, expected_even_images = split_to_pairs(expected_images)
    target_images = int(chapter_item.get("target_image_count", 0))

    if target_images != expected_images:
        issues.append(
            f"{cid(chapter)} target_image_count_mismatch: {target_images} expected {expected_images}"
        )
    if target_images % 2:
        issues.append(f"{cid(chapter)} target_image_count_not_even: {target_images}")

    if pair_item is not None:
        pair_duration = int(pair_item.get("duration_minutes", 0))
        target_lane_count = int(pair_item.get("target_lane_count", 0))
        target_pair_count = int(pair_item.get("target_pair_count", 0))
        pair_images = int(pair_item.get("target_image_count", 0))
        pairs_per_batch = int(pair_item.get("pairs_per_batch", 0))

        if pair_duration != duration:
            issues.append(
                f"{cid(chapter)} pair_duration_mismatch: {pair_duration} expected {duration}"
            )
        if pair_images != expected_even_images:
            issues.append(
                f"{cid(chapter)} pair_manifest_image_count_mismatch: "
                f"{pair_images} expected {expected_even_images}"
            )
        if target_lane_count != expected_pairs:
            issues.append(
                f"{cid(chapter)} target_lane_count_mismatch: {target_lane_count} expected {expected_pairs}"
            )
        if target_pair_count != expected_pairs:
            issues.append(
                f"{cid(chapter)} target_pair_count_mismatch: {target_pair_count} expected {expected_pairs}"
            )
        if pairs_per_batch < 1:
            issues.append(f"{cid(chapter)} invalid_pairs_per_batch: {pairs_per_batch}")

    return {
        "chapter": chapter,
        "title": chapter_item.get("title"),
        "duration_minutes": duration,
        "target_images": target_images,
        "target_lane_pairs": expected_pairs,
        "issues": issues,
        "ok": not issues,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Verify chapter timing, target image counts, and start/end lane-pair counts."
    )
    parser.add_argument("--start-chapter", type=int, default=8)
    parser.add_argument("--end-chapter", type=int, default=86)
    parser.add_argument("--chapter", type=int)
    parser.add_argument("--exclude-chapters", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not CHAPTERS_MANIFEST.exists():
        print(f"missing manifest: {CHAPTERS_MANIFEST}", file=sys.stderr)
        return 1
    if not LANE_PAIRS_MANIFEST.exists():
        print(f"missing manifest: {LANE_PAIRS_MANIFEST}", file=sys.stderr)
        return 1

    chapters_manifest = load_json(CHAPTERS_MANIFEST)
    pair_manifest = load_json(LANE_PAIRS_MANIFEST)
    images_per_minute = float(chapters_manifest.get("images_per_minute", 0))
    pair_images_per_minute = float(pair_manifest.get("images_per_minute", 0))
    pair_pairs_per_minute = float(pair_manifest.get("pairs_per_minute", 0))

    issues = []
    if images_per_minute <= 0:
        issues.append(f"invalid_images_per_minute: {images_per_minute}")
    if abs(pair_images_per_minute - images_per_minute) > 0.0001:
        issues.append(
            f"pair_manifest_images_per_minute_mismatch: {pair_images_per_minute} expected {images_per_minute}"
        )
    if abs(pair_pairs_per_minute - (images_per_minute / 2)) > 0.0001:
        issues.append(
            f"pair_manifest_pairs_per_minute_mismatch: {pair_pairs_per_minute} expected {images_per_minute / 2}"
        )

    chapter_items = index_by_chapter(chapters_manifest)
    pair_items = index_by_chapter(pair_manifest)
    chapters = chapter_filter(args)
    results = [
        verify_chapter(chapter, chapter_items.get(chapter), pair_items.get(chapter), images_per_minute)
        for chapter in chapters
    ]
    issues.extend(issue for item in results for issue in item["issues"])

    total_minutes = sum(item.get("duration_minutes", 0) for item in results)
    total_images = sum(item.get("target_images", 0) for item in results)
    total_pairs = sum(item.get("target_lane_pairs", 0) for item in results)

    if not args.chapter and not args.exclude_chapters and args.start_chapter == 8 and args.end_chapter == 86:
        manifest_total_minutes = int(chapters_manifest.get("total_minutes", 0))
        manifest_total_images = int(chapters_manifest.get("total_target_images", 0))
        pair_total_minutes = int(pair_manifest.get("total_minutes", 0))
        pair_total_images = int(pair_manifest.get("total_target_images", 0))
        pair_total_pairs = int(pair_manifest.get("total_lane_pairs", 0))
        if manifest_total_minutes != total_minutes:
            issues.append(
                f"chapters_manifest_total_minutes_mismatch: {manifest_total_minutes} expected {total_minutes}"
            )
        if manifest_total_images != total_images:
            issues.append(
                f"chapters_manifest_total_images_mismatch: {manifest_total_images} expected {total_images}"
            )
        if pair_total_minutes != total_minutes:
            issues.append(
                f"pair_manifest_total_minutes_mismatch: {pair_total_minutes} expected {total_minutes}"
            )
        if pair_total_images != total_images:
            issues.append(
                f"pair_manifest_total_images_mismatch: {pair_total_images} expected {total_images}"
            )
        if pair_total_pairs != total_pairs:
            issues.append(
                f"pair_manifest_total_pairs_mismatch: {pair_total_pairs} expected {total_pairs}"
            )

    summary = {
        "chapters": len(results),
        "images_per_minute": images_per_minute,
        "total_minutes": total_minutes,
        "total_lane_pairs": total_pairs,
        "total_target_images": total_images,
        "issues_count": len(issues),
        "first_issue": issues[0] if issues else None,
        "ok": not issues,
    }
    payload = {"summary": summary, "chapters": results, "issues": issues}

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"chapters={summary['chapters']} "
            f"minutes={summary['total_minutes']} "
            f"images_per_minute={summary['images_per_minute']} "
            f"lane_pairs={summary['total_lane_pairs']} "
            f"images={summary['total_target_images']} "
            f"issues={summary['issues_count']}"
        )
        if issues:
            print(f"first_issue={issues[0]}")
            for issue in issues[:20]:
                print(f"- {issue}")
            if len(issues) > 20:
                print(f"... {len(issues) - 20} more issues")

    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
