#!/usr/bin/env python
import argparse
import json
import re
import sys
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = ROOT / "nalas_chapters_08_86"
TEXT_DIR = PIPELINE_ROOT / "chapter_text"
GUIDE_DIR = PIPELINE_ROOT / "chapter_story_guides"
BRIEF_DIR = PIPELINE_ROOT / "chapter_visual_briefs"


STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "because",
    "before",
    "between",
    "chapter",
    "class",
    "classroom",
    "course",
    "earth",
    "energy",
    "excerpt",
    "focus",
    "from",
    "generic",
    "human",
    "humans",
    "image",
    "images",
    "information",
    "lane",
    "local",
    "nalanda",
    "nalas",
    "particle",
    "particles",
    "people",
    "scene",
    "scenes",
    "setting",
    "show",
    "student",
    "students",
    "teacher",
    "teaching",
    "that",
    "their",
    "there",
    "these",
    "this",
    "through",
    "tuelinh",
    "tuelinhs",
    "universe",
    "visual",
    "when",
    "where",
    "which",
    "with",
    "world",
}


CONCRETE_ANCHORS = [
    "airplane",
    "airport",
    "bihar",
    "big bang",
    "bodhi",
    "bus",
    "cebu",
    "chap",
    "coffee",
    "covid",
    "dragon",
    "duong",
    "father",
    "flight",
    "gaya",
    "giac",
    "hanoi",
    "heaven",
    "hotel",
    "india",
    "loi",
    "mahabodhi",
    "mother",
    "nalanda university",
    "nepal",
    "new delhi",
    "office",
    "pandemic",
    "patient",
    "patients",
    "philippines",
    "pyramid",
    "ruins",
    "teacher's office",
    "tea",
    "transiting planet",
    "truong",
    "whiteboard",
]


def cid(chapter):
    return f"C{chapter:03d}"


def read_text(path):
    return path.read_text(encoding="utf-8", errors="replace")


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


def list_chapters(args):
    excluded = parse_chapter_list(args.exclude_chapters)
    chapters = [args.chapter] if args.chapter else list(range(args.start_chapter, args.end_chapter + 1))
    return [
        chapter
        for chapter in chapters
        if chapter not in excluded and (TEXT_DIR / f"{cid(chapter)}.txt").exists()
    ]


def repo_rel(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def extract_flow_lock(text, chapter):
    match = re.search(
        rf"(Chapter {chapter} step-by-step lock:\n.*?)(?=\n- Story focus priority:|\n\nVisual direction:|\Z)",
        text,
        flags=re.S,
    )
    return match.group(1).strip() if match else ""


def lock_bullets(flow_lock):
    return [line.strip() for line in flow_lock.splitlines() if line.strip().startswith("- ")]


def normalize_text(value):
    value = value.lower()
    value = re.sub(r"\bchapter\s+\d+\b", " ", value)
    value = re.sub(r"\bc\d{3}\b", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def content_tokens(value):
    normalized = normalize_text(value)
    return {
        token
        for token in re.findall(r"[a-z][a-z'-]{2,}", normalized)
        if token not in STOPWORDS and len(token) >= 4
    }


def concrete_anchor_hits(flow_lock):
    normalized = normalize_text(flow_lock)
    hits = []
    for anchor in CONCRETE_ANCHORS:
        pieces = [re.escape(piece) for piece in anchor.split()]
        pattern = r"\b" + r"\s+".join(pieces) + r"\b"
        if re.search(pattern, normalized):
            hits.append(anchor)
    return sorted(hits)


def jaccard(left, right):
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def check_chapter(chapter, args):
    issues = []
    guide_path = GUIDE_DIR / f"{cid(chapter)}.md"
    brief_path = BRIEF_DIR / f"{cid(chapter)}.md"

    if not guide_path.exists():
        issues.append(f"{cid(chapter)} missing_story_guide: {repo_rel(guide_path)}")
        guide_text = ""
    else:
        guide_text = read_text(guide_path)

    if not brief_path.exists():
        issues.append(f"{cid(chapter)} missing_visual_brief: {repo_rel(brief_path)}")
        brief_text = ""
    else:
        brief_text = read_text(brief_path)

    guide_lock = extract_flow_lock(guide_text, chapter)
    brief_lock = extract_flow_lock(brief_text, chapter)
    if not guide_lock:
        issues.append(f"{cid(chapter)} missing_story_guide_step_lock")
    if not brief_lock:
        issues.append(f"{cid(chapter)} missing_visual_brief_step_lock")
    if guide_lock and brief_lock and guide_lock != brief_lock:
        issues.append(f"{cid(chapter)} brief_step_lock_mismatch")

    bullets = lock_bullets(guide_lock)
    if guide_lock and len(bullets) < args.min_bullets:
        issues.append(
            f"{cid(chapter)} weak_step_lock_bullet_count: "
            f"bullets={len(bullets)} expected>={args.min_bullets}"
        )

    tokens = content_tokens(guide_lock)
    if guide_lock and len(tokens) < args.min_unique_tokens:
        issues.append(
            f"{cid(chapter)} weak_step_lock_unique_tokens: "
            f"tokens={len(tokens)} expected>={args.min_unique_tokens}"
        )

    anchors = concrete_anchor_hits(guide_lock)
    if guide_lock and len(anchors) < args.min_concrete_anchors:
        issues.append(
            f"{cid(chapter)} weak_step_lock_concrete_anchors: "
            f"anchors={len(anchors)} expected>={args.min_concrete_anchors}"
        )

    return {
        "chapter": chapter,
        "guide_lock": guide_lock,
        "brief_lock": brief_lock,
        "bullet_count": len(bullets),
        "unique_token_count": len(tokens),
        "concrete_anchors": anchors,
        "issues": issues,
        "ok": not issues,
    }


def check_similarity(results, threshold):
    issues = []
    token_sets = {
        item["chapter"]: content_tokens(item["guide_lock"])
        for item in results
        if item.get("guide_lock")
    }
    max_pair = None
    max_score = 0.0
    for left, right in combinations(sorted(token_sets), 2):
        score = jaccard(token_sets[left], token_sets[right])
        if score > max_score:
            max_score = score
            max_pair = (left, right)
        if score >= threshold:
            issues.append(
                f"{cid(left)}_{cid(right)} step_lock_too_similar: similarity={score:.3f}"
            )
    return issues, max_pair, max_score


def main():
    parser = argparse.ArgumentParser(
        description="Verify that Nalas chapter guides keep distinct step-by-step story locks."
    )
    parser.add_argument("--start-chapter", type=int, default=8)
    parser.add_argument("--end-chapter", type=int, default=86)
    parser.add_argument("--chapter", type=int)
    parser.add_argument("--exclude-chapters", default="")
    parser.add_argument("--min-bullets", type=int, default=5)
    parser.add_argument("--min-unique-tokens", type=int, default=22)
    parser.add_argument("--min-concrete-anchors", type=int, default=0)
    parser.add_argument("--similarity-threshold", type=float, default=0.9)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    chapters = list_chapters(args)
    results = [check_chapter(chapter, args) for chapter in chapters]
    similarity_issues, max_pair, max_similarity = check_similarity(
        results,
        args.similarity_threshold,
    )
    issues = [issue for item in results for issue in item["issues"]] + similarity_issues
    summary = {
        "chapters": len(results),
        "guide_locks": sum(1 for item in results if item["guide_lock"]),
        "brief_locks": sum(1 for item in results if item["brief_lock"]),
        "max_similarity_pair": [cid(max_pair[0]), cid(max_pair[1])] if max_pair else None,
        "max_similarity": round(max_similarity, 3),
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
            f"guide_locks={summary['guide_locks']}/{summary['chapters']} "
            f"brief_locks={summary['brief_locks']}/{summary['chapters']} "
            f"max_similarity={summary['max_similarity']} "
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
