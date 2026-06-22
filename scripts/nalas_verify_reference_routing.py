#!/usr/bin/env python
import argparse
import json
import re
import sys
from pathlib import Path

from nalas_verify_outputs import parse_chapter_list


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = ROOT / "nalas_chapters_08_86"
PAIR_PROMPT_DIR = PIPELINE_ROOT / "lane_pair_prompts"
TEXT_DIR = PIPELINE_ROOT / "chapter_text"


INTERNAL_FATHER_ONLY = re.compile(
    r"\b(awaken Father|awaken the connection between father and his body|"
    r"father and his body|father in his body|father within him|"
    r"awakened the father in his body|body general)\b",
    flags=re.I,
)

VISIBLE_FATHER = re.compile(
    r"\b(Father (?:said|asked|replied|answered|taught|teaches|lectured|"
    r"appeared|sat|stood|showed|summoned)|Father Nalas|Cha Nalas|my children|"
    r"temple in heaven|lake in heaven|returned to heaven|"
    r"teacher's place of work and teaching in heaven|temple of Nalas Nalanda|"
    r"returning to visit your homeland|sparkling golden energy space|"
    r"tour around the universe|Giac immediately said to him.*Fathe\s*r|"
    r"greeted,\s*[\"“]?Fathe\s*r)\b",
    flags=re.I | re.S,
)

MESSENGER_TERMS = re.compile(
    r"\b(Giac|Chap|two messengers|five messengers|several messengers|"
    r"the messengers|male messengers|adult men|two adult men)\b",
    flags=re.I,
)

VISIBLE_DREAM_MORTAL = re.compile(
    r"\b(when he sleeps|starting to go to sleep|fall into a deep sleep|fell into a deep sleep|"
    r"waking him up|woke up|sat up|couldn't sleep|middle of the house|inside the house|"
    r"glass windows|moonlight|courtyard|yard|opened the door|stepped out|walked to the garden|"
    r"left side of the house|staring intently at him|looking at him|ran straight into the house|"
    r"closed the door|look through the window|standing in front of them|step out and approach|"
    r"rooster crowed|lead him to meet a woman|old man came to his house|older woman came to him)\b",
    flags=re.I | re.S,
)


EXPECTED_C008_FLAGS = {
    (1, "start"): (True, False),
    (1, "end"): (False, False),
    (2, "start"): (False, False),
    (2, "end"): (False, False),
    (3, "start"): (False, False),
    (3, "end"): (False, False),
    (4, "end"): (False, False),
    (5, "end"): (True, False),
    (6, "start"): (True, False),
    (6, "end"): (True, False),
}


def cid(chapter):
    return f"C{chapter:03d}"


def read_text(path):
    return path.read_text(encoding="utf-8", errors="replace")


def extract_excerpt(prompt):
    marker = "Story beat excerpt to visualize:"
    if marker not in prompt:
        return ""
    tail = prompt.split(marker, 1)[1]
    return tail.split("Pair continuity:", 1)[0].strip()


def normalize(value):
    return re.sub(r"\s+", " ", value.strip())


def list_chapters(args):
    excluded = parse_chapter_list(args.exclude_chapters)
    chapters = [args.chapter] if args.chapter else list(range(args.start_chapter, args.end_chapter + 1))
    return [
        chapter
        for chapter in chapters
        if chapter not in excluded and (TEXT_DIR / f"{cid(chapter)}.txt").exists()
    ]


def load_plan(chapter, issues):
    plan_path = PAIR_PROMPT_DIR / cid(chapter) / "chapter_lane_pair_plan.json"
    if not plan_path.exists():
        issues.append(f"{cid(chapter)} missing_lane_pair_plan: {plan_path}")
        return None
    try:
        return json.loads(read_text(plan_path))
    except Exception as exc:
        issues.append(f"{cid(chapter)} invalid_lane_pair_plan_json: {exc}")
        return None


def check_common_item(chapter, item, issues):
    lane = int(item.get("lane_index", -1))
    side = item.get("side", "")
    prompt = item.get("prompt", "")
    excerpt = extract_excerpt(prompt)
    key = f"{cid(chapter)} lane_{lane:03d}_{side}"
    use_pham = item.get("use_pham_tran_ref")
    use_divine = item.get("use_divine_nalas_ref")

    if use_divine and INTERNAL_FATHER_ONLY.search(excerpt) and not VISIBLE_FATHER.search(excerpt):
        issues.append(f"{key} divine_ref_on_internal_father_only_excerpt")

    if MESSENGER_TERMS.search(excerpt):
        lowered = prompt.lower()
        for required in [
            "mature adult man",
            "not one man and one woman",
            "not children",
            "not father nalas clones",
        ]:
            if required not in lowered:
                issues.append(f"{key} messenger_prompt_missing_lock: {required}")

    messenger_two_men_scene = re.search(
        r"\b(two adult men|adult men)\b", excerpt, flags=re.I
    ) or (
        int(chapter) == 8
        and MESSENGER_TERMS.search(excerpt)
        and re.search(r"\btwo men\b", excerpt, flags=re.I)
    )
    if messenger_two_men_scene:
        lowered = prompt.lower()
        if "two adult men" not in lowered or "male/female pair" not in lowered:
            issues.append(f"{key} two_adult_men_scene_missing_gender_guard")

    return excerpt, use_pham, use_divine


def check_chapter_8(plan, issues):
    item_by_key = {
        (int(item.get("lane_index", -1)), item.get("side", "")): item
        for item in plan.get("items", [])
    }
    for key, (expected_pham, expected_divine) in EXPECTED_C008_FLAGS.items():
        item = item_by_key.get(key)
        if not item:
            issues.append(f"C008 missing_expected_item: lane={key[0]} side={key[1]}")
            continue
        lane_label = f"C008 lane_{key[0]:03d}_{key[1]}"
        if item.get("use_pham_tran_ref") is not expected_pham:
            issues.append(
                f"{lane_label} pham_ref_expected_{expected_pham}: got={item.get('use_pham_tran_ref')}"
            )
        if item.get("use_divine_nalas_ref") is not expected_divine:
            issues.append(
                f"{lane_label} divine_ref_expected_{expected_divine}: got={item.get('use_divine_nalas_ref')}"
            )

    for item in plan.get("items", []):
        lane = int(item.get("lane_index", -1))
        side = item.get("side", "")
        excerpt = extract_excerpt(item.get("prompt", ""))
        key = f"C008 lane_{lane:03d}_{side}"
        if VISIBLE_DREAM_MORTAL.search(excerpt) and item.get("use_pham_tran_ref") is not True:
            issues.append(f"{key} visible_dream_mortal_missing_pham_ref")
        if re.search(r"\b(two adult men|adult men)\b", excerpt, flags=re.I) and item.get("use_divine_nalas_ref"):
            issues.append(f"{key} two_male_messenger_scene_should_not_use_divine_father_ref")


def check_plan(chapter, plan, issues):
    for item in plan.get("items", []):
        check_common_item(chapter, item, issues)
    if int(chapter) == 8:
        check_chapter_8(plan, issues)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapter", type=int)
    parser.add_argument("--start-chapter", type=int, default=8)
    parser.add_argument("--end-chapter", type=int, default=86)
    parser.add_argument("--exclude-chapters", default="")
    args = parser.parse_args()

    issues = []
    checked = 0
    for chapter in list_chapters(args):
        plan = load_plan(chapter, issues)
        if plan is None:
            continue
        check_plan(chapter, plan, issues)
        checked += 1

    if issues:
        print("REFERENCE ROUTING QA FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print(f"reference routing QA passed for {checked} chapter(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
