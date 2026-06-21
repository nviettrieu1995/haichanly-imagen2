#!/usr/bin/env python
import argparse
import json
from pathlib import Path

from nalas_verify_outputs import check_png, load_plan, parse_chapter_list


ROOT = Path(__file__).resolve().parents[1]
FINAL_DIR = ROOT / "nalas_chapters_08_86" / "final_image_video"


def verify_chapter(chapter):
    plan = load_plan(chapter)
    chapter_dir = FINAL_DIR / f"C{chapter:03d}"
    expected_names = set()
    complete_pairs = 0
    complete_images = 0
    invalid_images = []
    missing_lanes = []

    for lane in plan["lanes"]:
        lane_index = int(lane["lane_index"])
        start_name = f"C{chapter:03d}_lane_{lane_index:03d}_start.png"
        end_name = f"C{chapter:03d}_lane_{lane_index:03d}_end.png"
        expected_names.update([start_name, end_name])
        start_path = chapter_dir / start_name
        end_path = chapter_dir / end_name
        start = check_png(start_path)
        end = check_png(end_path)
        start_ok = start["exists"] and start["valid_png"] and start["ratio_ok"]
        end_ok = end["exists"] and end["valid_png"] and end["ratio_ok"]
        complete_images += int(start_ok) + int(end_ok)
        complete_pairs += int(start_ok and end_ok)
        if not (start_ok and end_ok):
            missing_lanes.append(lane_index)
        for side, result, path in [("start", start, start_path), ("end", end, end_path)]:
            if result["exists"] and not (result["valid_png"] and result["ratio_ok"]):
                invalid_images.append({"lane": lane_index, "side": side, "path": str(path), "result": result})

    actual_names = set()
    if chapter_dir.exists():
        actual_names = {path.name for path in chapter_dir.glob("*.png")}
    extras = sorted(actual_names - expected_names)
    return {
        "chapter": chapter,
        "complete_pairs": complete_pairs,
        "target_pairs": len(plan["lanes"]),
        "complete_images": complete_images,
        "target_images": len(plan["lanes"]) * 2,
        "missing_lanes_count": len(missing_lanes),
        "missing_lanes_preview": missing_lanes[:50],
        "invalid_images_count": len(invalid_images),
        "invalid_images_preview": invalid_images[:20],
        "extra_png_count": len(extras),
        "extra_png_preview": extras[:20],
        "ok": complete_pairs == len(plan["lanes"]) and not invalid_images and not extras,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-chapter", type=int, default=8)
    parser.add_argument("--end-chapter", type=int, default=86)
    parser.add_argument("--chapter", type=int)
    parser.add_argument("--exclude-chapters", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    excluded = parse_chapter_list(args.exclude_chapters)
    chapters = [args.chapter] if args.chapter else list(range(args.start_chapter, args.end_chapter + 1))
    chapters = [chapter for chapter in chapters if chapter not in excluded]
    results = [verify_chapter(chapter) for chapter in chapters]
    summary = {
        "chapters": len(results),
        "complete_pairs": sum(item["complete_pairs"] for item in results),
        "target_pairs": sum(item["target_pairs"] for item in results),
        "complete_images": sum(item["complete_images"] for item in results),
        "target_images": sum(item["target_images"] for item in results),
        "invalid_images_count": sum(item["invalid_images_count"] for item in results),
        "extra_png_count": sum(item["extra_png_count"] for item in results),
        "first_incomplete": next((item for item in results if not item["ok"]), None),
    }
    payload = {"final_dir": str(FINAL_DIR), "summary": summary, "chapters": results}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(
        f"final_dir={FINAL_DIR} "
        f"chapters={summary['chapters']} "
        f"pairs={summary['complete_pairs']}/{summary['target_pairs']} "
        f"images={summary['complete_images']}/{summary['target_images']} "
        f"invalid={summary['invalid_images_count']} extras={summary['extra_png_count']}"
    )
    if summary["first_incomplete"]:
        item = summary["first_incomplete"]
        print(
            f"first_incomplete=C{item['chapter']:03d} "
            f"pairs={item['complete_pairs']}/{item['target_pairs']} "
            f"images={item['complete_images']}/{item['target_images']} "
            f"missing_lanes={item['missing_lanes_count']} "
            f"invalid={item['invalid_images_count']} extras={item['extra_png_count']}"
        )


if __name__ == "__main__":
    main()
