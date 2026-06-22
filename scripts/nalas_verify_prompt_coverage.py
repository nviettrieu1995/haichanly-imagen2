#!/usr/bin/env python
import argparse
import json
import sys
from pathlib import Path

from nalas_verify_outputs import parse_chapter_list


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = ROOT / "nalas_chapters_08_86"
TEXT_DIR = PIPELINE_ROOT / "chapter_text"
STORY_GUIDE_DIR = PIPELINE_ROOT / "chapter_story_guides"
VISUAL_BRIEF_DIR = PIPELINE_ROOT / "chapter_visual_briefs"
PAIR_PROMPT_DIR = PIPELINE_ROOT / "lane_pair_prompts"


PROMPT_GUARDS = [
    "Chapter-specific story guide, mandatory:",
    "Chapter flow lock:",
    "Story beat excerpt to visualize:",
    "Do not render written words",
    "No subtitles, no labels, no watermark, no logo",
    "Negative prompt:",
]


def cid(chapter):
    return f"C{chapter:03d}"


def read_text(path):
    return path.read_text(encoding="utf-8")


def has_any(text, patterns):
    return any(pattern in text for pattern in patterns)


def flow_markers(chapter):
    return [
        f"Chapter {chapter} step-by-step lock:",
        f"{cid(chapter)} step-by-step story flow lock:",
    ]


def prompt_flow_markers(chapter):
    return [
        f"{cid(chapter)} flow lock:",
        f"{cid(chapter)} step-by-step story flow lock:",
    ]


def normalize_repo_path(value):
    if value is None or str(value).strip() == "":
        return ROOT / "__missing_path__"
    path = Path(value)
    if path.exists():
        return path
    normalized = str(value).replace("\\", "/")
    marker = "nalas_chapters_08_86/"
    if marker in normalized:
        return ROOT / marker / normalized.split(marker, 1)[1]
    return path


def repo_rel(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def list_chapters(args):
    excluded = parse_chapter_list(args.exclude_chapters)
    chapters = [args.chapter] if args.chapter else list(range(args.start_chapter, args.end_chapter + 1))
    return [
        chapter
        for chapter in chapters
        if chapter not in excluded and (TEXT_DIR / f"{cid(chapter)}.txt").exists()
    ]


def check_text_file(chapter, kind, path, issues):
    if not path.exists():
        issues.append(f"{cid(chapter)} missing_{kind}: {repo_rel(path)}")
        return False
    text = read_text(path)
    markers = flow_markers(chapter)
    ok = has_any(text, markers)
    if not ok:
        issues.append(
            f"{cid(chapter)} {kind}_missing_flow_lock_marker: expected one of {markers}"
        )
    if kind == "visual_brief" and "Chapter flow lock from story guide:" not in text:
        issues.append(f"{cid(chapter)} visual_brief_missing_embedded_story_flow_lock")
        ok = False
    return ok


def check_lane_targets(chapter, plan, issues):
    expected_lanes = int(plan.get("target_lane_count", 0))
    expected_images = int(plan.get("target_image_count", 0))
    lanes = plan.get("lanes", [])
    items = plan.get("items", [])

    if len(lanes) != expected_lanes:
        issues.append(
            f"{cid(chapter)} lane_count_mismatch: lanes={len(lanes)} target={expected_lanes}"
        )
    if expected_images != expected_lanes * 2:
        issues.append(
            f"{cid(chapter)} image_count_mismatch: images={expected_images} expected={expected_lanes * 2}"
        )
    if len(items) != expected_images:
        issues.append(
            f"{cid(chapter)} item_count_mismatch: items={len(items)} target_images={expected_images}"
        )

    expected_indices = list(range(1, expected_lanes + 1))
    actual_indices = [int(lane.get("lane_index", -1)) for lane in lanes]
    if actual_indices != expected_indices:
        issues.append(f"{cid(chapter)} lane_indices_not_sequential")

    target_names = set()
    for lane in lanes:
        lane_index = int(lane.get("lane_index", -1))
        expected_start = f"{cid(chapter)}_lane_{lane_index:03d}_start.png"
        expected_end = f"{cid(chapter)}_lane_{lane_index:03d}_end.png"
        for side, expected_name in [("start", expected_start), ("end", expected_end)]:
            target_value = lane.get(f"{side}_target", "")
            target_path = normalize_repo_path(target_value)
            target_names.add(target_path.name)
            if target_path.name != expected_name:
                issues.append(
                    f"{cid(chapter)} lane_{lane_index:03d}_{side}_target_name_mismatch: "
                    f"{target_path.name} expected {expected_name}"
                )
        lane_items = lane.get("items", [])
        sides = sorted(item.get("side") for item in lane_items)
        if sides != ["end", "start"]:
            issues.append(f"{cid(chapter)} lane_{lane_index:03d}_items_missing_start_end: {sides}")

    if len(target_names) != expected_images:
        issues.append(
            f"{cid(chapter)} duplicate_target_names: unique={len(target_names)} expected={expected_images}"
        )


def check_prompt_text(chapter, prompt_text, issues, context, expected_lanes=None):
    for guard in PROMPT_GUARDS:
        if guard not in prompt_text:
            issues.append(f"{cid(chapter)} {context}_missing_guard: {guard}")
    if not has_any(prompt_text, prompt_flow_markers(chapter)):
        issues.append(f"{cid(chapter)} {context}_missing_chapter_prompt_flow_lock")
    if "16:9" not in prompt_text:
        issues.append(f"{cid(chapter)} {context}_missing_16x9")
    if expected_lanes:
        for lane_index in expected_lanes:
            for side in ["START", "END"]:
                label = f"Lane {int(lane_index):03d} {side} image:"
                if label not in prompt_text:
                    issues.append(f"{cid(chapter)} {context}_missing_lane_label: {label}")


def check_prompt_plan(chapter, issues):
    plan_path = PAIR_PROMPT_DIR / cid(chapter) / "chapter_lane_pair_plan.json"
    if not plan_path.exists():
        issues.append(f"{cid(chapter)} missing_prompt_plan: {repo_rel(plan_path)}")
        return {
            "plan": False,
            "batches": 0,
            "target_batches": 0,
            "lane_pairs": 0,
            "images": 0,
        }

    try:
        plan = json.loads(read_text(plan_path))
    except Exception as exc:
        issues.append(f"{cid(chapter)} invalid_prompt_plan_json: {exc}")
        return {
            "plan": False,
            "batches": 0,
            "target_batches": 0,
            "lane_pairs": 0,
            "images": 0,
        }

    if int(plan.get("chapter", -1)) != chapter:
        issues.append(f"{cid(chapter)} plan_chapter_mismatch: {plan.get('chapter')}")

    check_lane_targets(chapter, plan, issues)

    batches = plan.get("batches", [])
    pairs_per_batch = max(1, int(plan.get("pairs_per_batch", 1)))
    target_lanes = int(plan.get("target_lane_count", 0))
    target_batches = (target_lanes + pairs_per_batch - 1) // pairs_per_batch
    if len(batches) != target_batches:
        issues.append(
            f"{cid(chapter)} batch_count_mismatch: batches={len(batches)} expected={target_batches}"
        )

    seen_lanes = []
    for batch in batches:
        prompt_file = normalize_repo_path(batch.get("prompt_file", ""))
        batch_no = int(batch.get("batch", 0))
        batch_lanes = [int(lane) for lane in batch.get("lanes", [])]
        seen_lanes.extend(batch_lanes)
        targets = batch.get("targets", [])
        if len(targets) != len(batch_lanes) * 2:
            issues.append(
                f"{cid(chapter)} batch_{batch_no:03d}_target_count_mismatch: "
                f"targets={len(targets)} lanes={len(batch_lanes)}"
            )
        if not prompt_file.exists():
            issues.append(f"{cid(chapter)} missing_prompt_file: {repo_rel(prompt_file)}")
            continue
        prompt_text = read_text(prompt_file)
        check_prompt_text(
            chapter,
            prompt_text,
            issues,
            context=f"batch_{batch_no:03d}",
            expected_lanes=batch_lanes,
        )

    if sorted(seen_lanes) != list(range(1, target_lanes + 1)):
        issues.append(f"{cid(chapter)} batch_lane_coverage_mismatch")

    item_preview_count = 0
    for item in plan.get("items", []):
        prompt = item.get("prompt", "")
        if item_preview_count < 4:
            check_prompt_text(
                chapter,
                prompt,
                issues,
                context=f"plan_item_lane_{int(item.get('lane_index', 0)):03d}_{item.get('side', 'unknown')}",
            )
            item_preview_count += 1
        if item.get("side") not in {"start", "end"}:
            issues.append(
                f"{cid(chapter)} invalid_item_side: lane={item.get('lane_index')} side={item.get('side')}"
            )

    return {
        "plan": True,
        "batches": len(batches),
        "target_batches": target_batches,
        "lane_pairs": target_lanes,
        "images": int(plan.get("target_image_count", 0)),
    }


def verify_chapter(chapter, require_prompts):
    issues = []
    guide_ok = check_text_file(
        chapter,
        "story_guide",
        STORY_GUIDE_DIR / f"{cid(chapter)}.md",
        issues,
    )
    brief_ok = check_text_file(
        chapter,
        "visual_brief",
        VISUAL_BRIEF_DIR / f"{cid(chapter)}.md",
        issues,
    )
    prompt_result = {
        "plan": None,
        "batches": 0,
        "target_batches": 0,
        "lane_pairs": 0,
        "images": 0,
    }
    if require_prompts:
        prompt_result = check_prompt_plan(chapter, issues)
    return {
        "chapter": chapter,
        "story_guide_ok": guide_ok,
        "visual_brief_ok": brief_ok,
        "prompt_plan_ok": prompt_result["plan"],
        "prompt_batches": prompt_result["batches"],
        "target_prompt_batches": prompt_result["target_batches"],
        "lane_pairs": prompt_result["lane_pairs"],
        "images": prompt_result["images"],
        "issues": issues,
        "ok": not issues,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Verify Nalas chapter flow locks, visual briefs, and lane prompt cache coverage."
    )
    parser.add_argument("--start-chapter", type=int, default=8)
    parser.add_argument("--end-chapter", type=int, default=86)
    parser.add_argument("--chapter", type=int)
    parser.add_argument("--exclude-chapters", default="")
    parser.add_argument(
        "--skip-prompts",
        action="store_true",
        help="Only verify committed chapter text guides/briefs; do not require generated prompt cache.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    chapters = list_chapters(args)
    results = [verify_chapter(chapter, require_prompts=not args.skip_prompts) for chapter in chapters]
    issues = [issue for item in results for issue in item["issues"]]
    prompts_required = not args.skip_prompts
    summary = {
        "chapters": len(results),
        "story_guides_ok": sum(1 for item in results if item["story_guide_ok"]),
        "visual_briefs_ok": sum(1 for item in results if item["visual_brief_ok"]),
        "prompts_required": prompts_required,
        "prompt_plans_ok": sum(1 for item in results if item["prompt_plan_ok"]) if prompts_required else None,
        "prompt_batches": sum(item["prompt_batches"] for item in results) if prompts_required else None,
        "target_prompt_batches": sum(item["target_prompt_batches"] for item in results) if prompts_required else None,
        "lane_pairs": sum(item["lane_pairs"] for item in results) if prompts_required else None,
        "images": sum(item["images"] for item in results) if prompts_required else None,
        "issues_count": len(issues),
        "first_issue": issues[0] if issues else None,
        "ok": not issues,
    }
    payload = {"summary": summary, "chapters": results}

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if prompts_required:
            prompt_summary = (
                f"prompt_plans={summary['prompt_plans_ok']}/{summary['chapters']} "
                f"prompt_batches={summary['prompt_batches']}/{summary['target_prompt_batches']} "
                f"lane_pairs={summary['lane_pairs']} images={summary['images']} "
            )
        else:
            prompt_summary = (
                "prompt_plans=skipped prompt_batches=skipped "
                "lane_pairs=skipped images=skipped "
            )
        print(
            f"chapters={summary['chapters']} "
            f"story_guides={summary['story_guides_ok']}/{summary['chapters']} "
            f"visual_briefs={summary['visual_briefs_ok']}/{summary['chapters']} "
            f"{prompt_summary}"
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
