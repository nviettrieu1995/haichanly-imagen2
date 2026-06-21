#!/usr/bin/env python
import argparse
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PAIR_PROMPT_DIR = ROOT / "nalas_chapters_08_86" / "lane_pair_prompts"
PAIR_IMAGE_DIR = ROOT / "nalas_chapters_08_86" / "generated_lane_pairs"


def is_16x9(size, tolerance=0.03):
    width, height = size
    if not width or not height:
        return False
    return abs((width / height) - (16 / 9)) <= tolerance


def check_png(path):
    if not path.exists():
        return {"exists": False, "valid_png": False, "size": None, "ratio_ok": False}
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            size = image.size
        return {
            "exists": True,
            "valid_png": True,
            "size": list(size),
            "ratio_ok": is_16x9(size),
            "bytes": path.stat().st_size,
        }
    except Exception as exc:
        return {
            "exists": True,
            "valid_png": False,
            "size": None,
            "ratio_ok": False,
            "error": str(exc),
            "bytes": path.stat().st_size if path.exists() else 0,
        }


def load_plan(chapter):
    plan_path = PAIR_PROMPT_DIR / f"C{chapter:03d}" / "chapter_lane_pair_plan.json"
    if not plan_path.exists():
        raise FileNotFoundError(plan_path)
    return json.loads(plan_path.read_text(encoding="utf-8"))


def verify_chapter(chapter):
    plan = load_plan(chapter)
    complete_pairs = 0
    complete_images = 0
    invalid_images = []
    missing_lanes = []
    for lane in plan["lanes"]:
        lane_index = lane["lane_index"]
        start = check_png(Path(lane["start_target"]))
        end = check_png(Path(lane["end_target"]))
        start_ok = start["exists"] and start["valid_png"] and start["ratio_ok"]
        end_ok = end["exists"] and end["valid_png"] and end["ratio_ok"]
        complete_images += int(start_ok) + int(end_ok)
        complete_pairs += int(start_ok and end_ok)
        if not (start_ok and end_ok):
            missing_lanes.append(lane_index)
        for side, result in [("start", start), ("end", end)]:
            if result["exists"] and not (result["valid_png"] and result["ratio_ok"]):
                invalid_images.append(
                    {
                        "lane": lane_index,
                        "side": side,
                        "path": lane[f"{side}_target"],
                        "result": result,
                    }
                )
    target_pairs = len(plan["lanes"])
    target_images = target_pairs * 2
    extras = sorted(
        path.name
        for path in (PAIR_IMAGE_DIR / f"C{chapter:03d}").glob("*.png")
        if not path.name.startswith(f"C{chapter:03d}_lane_")
    )
    return {
        "chapter": chapter,
        "complete_pairs": complete_pairs,
        "target_pairs": target_pairs,
        "complete_images": complete_images,
        "target_images": target_images,
        "missing_lanes_count": len(missing_lanes),
        "missing_lanes_preview": missing_lanes[:50],
        "invalid_images_count": len(invalid_images),
        "invalid_images_preview": invalid_images[:20],
        "extra_png_count": len(extras),
        "extra_png_preview": extras[:20],
        "ok": complete_pairs == target_pairs and not invalid_images,
    }


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
    payload = {"summary": summary, "chapters": results}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(
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
            f"invalid={item['invalid_images_count']}"
        )


if __name__ == "__main__":
    main()
