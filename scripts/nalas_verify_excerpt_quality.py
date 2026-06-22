#!/usr/bin/env python
import argparse
import json
import re
import sys
from pathlib import Path

try:
    from nalas_chapters_pipeline import PDF_SPACING_REPAIRS
    from nalas_verify_outputs import parse_chapter_list
except ModuleNotFoundError:
    from scripts.nalas_chapters_pipeline import PDF_SPACING_REPAIRS
    from scripts.nalas_verify_outputs import parse_chapter_list


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = ROOT / "nalas_chapters_08_86"
TEXT_DIR = PIPELINE_ROOT / "chapter_text"
GUIDE_DIR = PIPELINE_ROOT / "chapter_story_guides"
BRIEF_DIR = PIPELINE_ROOT / "chapter_visual_briefs"
PAIR_PROMPT_DIR = PIPELINE_ROOT / "lane_pair_prompts"

EXCERPT_BLOCK_RE = re.compile(
    r"Story beat excerpt to visualize:\n(?P<excerpt>.*?)(?:\n\nPair continuity:|\n\nTechnical output:|\Z)",
    flags=re.S,
)


def cid(chapter):
    return f"C{chapter:03d}"


def repo_rel(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_text(path):
    return path.read_text(encoding="utf-8", errors="replace")


def list_chapters(args):
    excluded = parse_chapter_list(args.exclude_chapters)
    chapters = [args.chapter] if args.chapter else list(range(args.start_chapter, args.end_chapter + 1))
    return [
        chapter
        for chapter in chapters
        if chapter not in excluded and (TEXT_DIR / f"{cid(chapter)}.txt").exists()
    ]


def artifact_patterns():
    patterns = []
    for bad, _good in PDF_SPACING_REPAIRS:
        escaped = re.escape(bad).replace(r"\ ", r"\s+")
        patterns.append((bad, re.compile(rf"\b{escaped}\b", flags=re.I)))
    return patterns


def first_line(value, limit=140):
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit]


def check_artifacts(label, text, issues, patterns):
    for bad, pattern in patterns:
        match = pattern.search(text)
        if match:
            issues.append(
                f"{label} pdf_spacing_artifact '{bad}': ...{first_line(text[max(0, match.start() - 60):match.end() + 60])}..."
            )


def check_guide_and_brief(chapter, issues, patterns):
    checked = 0
    for kind, folder in [("story_guide", GUIDE_DIR), ("visual_brief", BRIEF_DIR)]:
        path = folder / f"{cid(chapter)}.md"
        if not path.exists():
            issues.append(f"{cid(chapter)} missing_{kind}: {repo_rel(path)}")
            continue
        check_artifacts(f"{cid(chapter)} {kind}", read_text(path), issues, patterns)
        checked += 1
    return checked


def prompt_items(plan):
    for item in plan.get("items", []):
        prompt = item.get("prompt") or ""
        if prompt:
            yield item, prompt
    for batch in plan.get("batches", []):
        for item in batch.get("items", []):
            prompt = item.get("prompt") or ""
            if prompt:
                yield item, prompt


def check_prompt_cache(chapter, issues, patterns):
    plan_path = PAIR_PROMPT_DIR / cid(chapter) / "chapter_lane_pair_plan.json"
    if not plan_path.exists():
        issues.append(f"{cid(chapter)} missing_prompt_plan: {repo_rel(plan_path)}")
        return 0
    try:
        plan = json.loads(read_text(plan_path))
    except Exception as exc:
        issues.append(f"{cid(chapter)} invalid_prompt_plan_json: {exc}")
        return 0

    checked = 0
    for item, prompt in prompt_items(plan):
        lane = int(item.get("lane_index", -1))
        side = item.get("side", "unknown")
        label = f"{cid(chapter)} lane_{lane:03d}_{side}"
        match = EXCERPT_BLOCK_RE.search(prompt)
        if not match:
            issues.append(f"{label} missing_story_beat_excerpt_block")
            continue
        excerpt = match.group("excerpt").strip()
        if not excerpt:
            issues.append(f"{label} empty_story_beat_excerpt")
            continue
        check_artifacts(label, excerpt, issues, patterns)
        checked += 1
    return checked


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-chapter", type=int, default=8)
    parser.add_argument("--end-chapter", type=int, default=86)
    parser.add_argument("--chapter", type=int)
    parser.add_argument("--exclude-chapters", default="")
    parser.add_argument("--skip-prompts", action="store_true")
    args = parser.parse_args()

    chapters = list_chapters(args)
    patterns = artifact_patterns()
    issues = []
    checked_files = 0
    checked_prompt_items = 0

    for chapter in chapters:
        checked_files += check_guide_and_brief(chapter, issues, patterns)
        if not args.skip_prompts:
            checked_prompt_items += check_prompt_cache(chapter, issues, patterns)

    if issues:
        for issue in issues:
            print(issue)
        print(
            f"excerpt_quality_failed chapters={len(chapters)} files={checked_files} "
            f"prompt_items={checked_prompt_items} issues={len(issues)}"
        )
        return 1

    print(
        f"excerpt_quality_ok chapters={len(chapters)} files={checked_files} "
        f"prompt_items={checked_prompt_items}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
