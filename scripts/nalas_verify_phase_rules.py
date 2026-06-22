#!/usr/bin/env python
import argparse
import json
import re
import sys
from pathlib import Path

from nalas_verify_outputs import parse_chapter_list


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = ROOT / "nalas_chapters_08_86"
TEXT_DIR = PIPELINE_ROOT / "chapter_text"
GUIDE_DIR = PIPELINE_ROOT / "chapter_story_guides"
BRIEF_DIR = PIPELINE_ROOT / "chapter_visual_briefs"
PAIR_PROMPT_DIR = PIPELINE_ROOT / "lane_pair_prompts"


EARLY_TEACHING_CHAPTERS = set(range(9, 16))
MODERN_ERA_CHAPTERS = set(range(16, 87))
INTERNATIONAL_TRAVEL_CHAPTERS = {
    38,
    39,
    42,
    43,
    44,
    45,
    46,
    47,
    48,
    49,
    50,
    53,
    56,
}
HEAVEN_DOMINANT_CHAPTERS = {21, 55, 56, 57, 58, 59, 60, 61, 62}


CHAPTER_MARKER_GROUPS = {
    8: [
        (
            "poor_modern_countryside",
            [
                "poor present-day vietnamese countryside",
                "poor modern vietnamese countryside",
                "poor peaceful countryside home",
            ],
        ),
        ("jade_dragon_event", ["huge jade-green dragon"]),
        ("two_male_messengers", ["two mature male messengers", "two adult men"]),
        ("old_disguise_sequence", ["old man", "old woman"]),
        ("not_city_apartment", ["city apartment", "apartment towers"]),
    ],
    16: [
        ("covid_origin", ["covid-era origin", "pandemic period"]),
        ("modern_classroom", ["led/fluorescent lights", "magnetic whiteboard", "marker pens"]),
        ("age_lock", ["32-35"]),
        ("three_male_students", ["three excellent male students"]),
    ],
    21: [
        ("earth_sleep_body", ["mortal teacher sleeps", "modern city room"]),
        ("heaven_transition", ["heavenly homeland", "heaven temple"]),
        ("father_style", ["sacred-heart-jesus", "jesus-like"]),
        ("no_duplicate_glasses", ["no duplicate glasses"]),
    ],
    39: [
        ("cebu_setting", ["cebu city", "philippines", "swimming pool"]),
        ("english_school", ["english school"]),
        ("not_vietnam_classroom", ["not vietnam classroom", "not countryside"]),
    ],
    42: [
        ("mahabodhi_bodhi_tree", ["gaya", "mahabodhi", "bodhi tree"]),
        ("real_pilgrimage_not_heaven", ["real indian pilgrimage site", "not heaven"]),
        ("inner_particle_journey", ["destructive brown space", "green wave-particles"]),
    ],
    43: [
        ("hotel_garden", ["hotel garden", "autumn dawn"]),
        ("vietnamese_tea_in_india", ["vietnamese tea", "indian relic"]),
        ("portable_whiteboard", ["whiteboard"]),
    ],
    44: [
        ("second_mahabodhi_evening", ["second evening", "mahabodhi", "bodhi tree"]),
        ("big_bang_embryo", ["big bang", "magical embryo"]),
        ("real_indian_night", ["real indian pilgrimage night"]),
    ],
    45: [
        ("nalanda_ruins", ["nalanda university ruins", "red-brick ruins"]),
        ("truong_duong_past_life", ["truong nalanda", "duong nalanda"]),
        ("not_modern_classroom", ["do not use modern classroom"]),
    ],
    46: [
        ("nalanda_ruins_continuation", ["nalanda university ruins", "pull grass"]),
        ("particle_diversity", ["yellow positive particles", "grey-white negative particles"]),
        ("not_scifi_lab", ["not make this a classroom", "sci-fi lab"]),
    ],
    47: [
        ("nepal_ancient_capital", ["nepal", "ancient capital"]),
        ("birthplace_relic", ["birthplace relic", "lake", "iron pillar"]),
        ("real_nepal_not_heaven", ["do not replace nepal relics with heaven"]),
    ],
    48: [
        ("patna_new_delhi_plane", ["plane from patna to new delhi", "airplane cabin"]),
        ("heaven_memory", ["central planet", "heaven"]),
        ("father_style", ["western sacred jesus-like father"]),
    ],
    49: [
        ("new_delhi_hotel", ["new delhi hotel", "hotel coffee bar"]),
        ("hot_cocoa_allergy", ["hot cocoa", "coffee can trigger his allergy"]),
        ("hotel_living_room", ["hotel living-room lecture", "hotel/coffee/sofa"]),
    ],
    50: [
        ("new_delhi_hotel_afternoon", ["new delhi hotel living room"]),
        ("rotation_lesson", ["spinning", "rotation mechanism"]),
        ("travel_teaching_anchor", ["hotel/travel teaching"]),
    ],
    51: [
        ("flight_back_hanoi", ["flight back to hanoi", "airplane cabin"]),
        ("body_memory_split", ["airplane-body frame", "cosmic memory"]),
        ("destructive_boundary", ["destructive energy and the universe"]),
    ],
    52: [
        ("sleeping_body_on_flight", ["mortal body sleeps on the flight", "airplane"]),
        ("information_system", ["information transceiver system", "pyramid-like information processing center"]),
        ("energy_wires", ["energy-wire", "bright energy strings"]),
        ("single_glasses", ["one pair of thin glasses", "no spare glasses"]),
    ],
    68: [
        ("hanoi_summer_coffee", ["hanoi", "summer", "iced coffee"]),
        ("coffee_allergy", ["allergic reaction", "runny nose"]),
        ("not_pure_space", ["avoid pure generic space art"]),
    ],
    74: [
        ("office_memory_opening", ["teacher's office", "meditating position"]),
        ("mother_child_case", ["mother and child", "murdered"]),
        ("transiting_planet", ["transiting planet"]),
        ("no_horror", ["no horror", "no gore"]),
    ],
    75: [
        ("modern_classroom_frame", ["modern classroom", "board/diagram", "classroom frame"]),
        ("ideology_particle", ["grey negative energy particle"]),
        ("classroom_frame", ["modern classroom", "particle mechanics are overlays"]),
    ],
    86: [
        ("regimen_summary", ["application/regimen summary", "mental-health-related illnesses"]),
        ("caregiver_home", ["modern vietnamese home", "caregiver"]),
        ("repeated_listening", ["repeated daily listening", "night and morning routines"]),
        ("no_horror_medical_caution", ["do not depict distress as horror", "do not imply instant miracle cure"]),
    ],
}


GLOBAL_MARKER_GROUPS = {
    "mortal_glasses": ["thin metal eyeglasses", "glasses are mandatory"],
    "no_chinese_visual_language": ["no hanfu", "xianxia", "chinese pagoda"],
}


def forbidden_groups_for_chapter(chapter):
    groups = {}
    if chapter < 16:
        groups["pre_covid_irrelevant_covid_style_note"] = [
            "covid/pandemic-era teaching scenes should look polished and modern",
        ]
    return groups


def cid(chapter):
    return f"C{chapter:03d}"


def read_text(path):
    return path.read_text(encoding="utf-8", errors="replace")


def normalize(value):
    value = value.lower().replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", value)


def has_marker(text, marker):
    return marker.lower() in text


def has_any_marker(text, markers):
    return any(has_marker(text, marker) for marker in markers)


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


def prompt_sample_text(chapter, max_files=3):
    plan_path = PAIR_PROMPT_DIR / cid(chapter) / "chapter_lane_pair_plan.json"
    if not plan_path.exists():
        return "", False
    texts = []
    try:
        plan = json.loads(read_text(plan_path))
    except Exception:
        plan = {}
    for item in plan.get("items", [])[:4]:
        prompt = item.get("prompt")
        if prompt:
            texts.append(prompt)
    for prompt_file in sorted((PAIR_PROMPT_DIR / cid(chapter)).glob("*_lane_batch_*.txt"))[:max_files]:
        texts.append(read_text(prompt_file))
    return normalize("\n".join(texts)), True


def expected_groups_for_chapter(chapter, scope):
    groups = dict(GLOBAL_MARKER_GROUPS)
    if chapter in EARLY_TEACHING_CHAPTERS:
        groups.update(
            {
                "early_teaching_phase": [
                    "after nalas has begun teaching",
                    "early teaching period",
                    "rented classroom",
                    "extraordinary class",
                    "one day a week",
                    "seven months",
                    "clean vietnamese learning room",
                ],
                "not_poor_countryside_after_teaching": [
                    "do not send earth scenes back to the poor countryside phase",
                    "do not show poor countryside",
                    "poor countryside is allowed only when the chapter phase requires it",
                    "not historical costume rural nostalgia",
                ],
            }
        )
    if chapter in MODERN_ERA_CHAPTERS and chapter not in INTERNATIONAL_TRAVEL_CHAPTERS:
        groups.update(
            {
                "modern_era_phase": [
                    "clearly modern 2020+",
                    "post-covid/modern-era",
                    "modern post-covid",
                    "modern office-classroom",
                    "covid/pandemic beats must look clearly modern",
                    "modern city office-classroom",
                    "modern class",
                    "modern classroom",
                    "modern hanoi office",
                    "works at the office",
                    "teacher's office",
                    "ordinary vietnamese city",
                    "normal vietnamese city districts",
                ],
            }
        )
        if scope != "story_guide" and chapter not in HEAVEN_DOMINANT_CHAPTERS:
            groups.update(
                {
                    "modern_room_props": [
                        "led/tube lights",
                        "led/fluorescent lights",
                        "led or fluorescent lights",
                        "led panels",
                        "fluorescent tube lights",
                        "office desks/chairs",
                        "proper tables/chairs",
                        "proper furniture",
                        "magnetic whiteboards",
                        "magnetic whiteboard",
                        "whiteboard when teaching",
                        "whiteboard or magnetic board",
                        "marker pens",
                    ],
                }
            )
    if chapter in INTERNATIONAL_TRAVEL_CHAPTERS:
        groups.update(
            {
                "international_travel_override": [
                    "international travel/pilgrimage",
                    "follow that real-world place literally",
                    "do not default back to vietnam",
                ],
            }
        )
    groups.update(CHAPTER_MARKER_GROUPS.get(chapter, {}))
    return groups


def check_marker_groups(chapter, label, text, groups, issues):
    for group_name, alternatives in groups.items():
        if not has_any_marker(text, alternatives):
            issues.append(
                f"{cid(chapter)} {label}_missing_phase_marker: "
                f"{group_name} expected one of {alternatives}"
            )


def check_forbidden_marker_groups(chapter, label, text, groups, issues):
    for group_name, forbidden_markers in groups.items():
        found = [marker for marker in forbidden_markers if has_marker(text, marker)]
        if found:
            issues.append(
                f"{cid(chapter)} {label}_forbidden_phase_marker: "
                f"{group_name} found {found}"
            )


def check_chapter(chapter, require_prompts):
    issues = []
    guide_path = GUIDE_DIR / f"{cid(chapter)}.md"
    brief_path = BRIEF_DIR / f"{cid(chapter)}.md"
    story_groups = expected_groups_for_chapter(chapter, "story_guide")
    brief_groups = expected_groups_for_chapter(chapter, "visual_brief")
    prompt_groups = expected_groups_for_chapter(chapter, "prompt_cache")
    forbidden_groups = forbidden_groups_for_chapter(chapter)

    if not guide_path.exists():
        issues.append(f"{cid(chapter)} missing_story_guide: {repo_rel(guide_path)}")
        guide_text = ""
    else:
        guide_text = normalize(read_text(guide_path))

    if not brief_path.exists():
        issues.append(f"{cid(chapter)} missing_visual_brief: {repo_rel(brief_path)}")
        brief_text = ""
    else:
        brief_text = normalize(read_text(brief_path))

    if guide_text:
        check_marker_groups(chapter, "story_guide", guide_text, story_groups, issues)
        check_forbidden_marker_groups(chapter, "story_guide", guide_text, forbidden_groups, issues)
    if brief_text:
        check_marker_groups(chapter, "visual_brief", brief_text, brief_groups, issues)
        check_forbidden_marker_groups(chapter, "visual_brief", brief_text, forbidden_groups, issues)

    prompt_checked = False
    if require_prompts:
        sample_text, prompt_checked = prompt_sample_text(chapter)
        if not prompt_checked:
            issues.append(
                f"{cid(chapter)} missing_prompt_cache_for_phase_rules: "
                f"{repo_rel(PAIR_PROMPT_DIR / cid(chapter))}"
            )
        elif sample_text:
            check_marker_groups(chapter, "prompt_cache", sample_text, prompt_groups, issues)
            check_forbidden_marker_groups(
                chapter,
                "prompt_cache",
                sample_text,
                forbidden_groups,
                issues,
            )

    return {
        "chapter": chapter,
        "groups_checked": len(set(story_groups) | set(brief_groups) | set(prompt_groups)),
        "prompt_checked": prompt_checked,
        "issues": issues,
        "ok": not issues,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Verify chapter phase and setting locks for Nalas lane-batch prompts."
    )
    parser.add_argument("--start-chapter", type=int, default=8)
    parser.add_argument("--end-chapter", type=int, default=86)
    parser.add_argument("--chapter", type=int)
    parser.add_argument("--exclude-chapters", default="")
    parser.add_argument(
        "--skip-prompts",
        action="store_true",
        help="Only check committed story guides and visual briefs; do not require generated prompt cache.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    chapters = list_chapters(args)
    results = [check_chapter(chapter, require_prompts=not args.skip_prompts) for chapter in chapters]
    issues = [issue for item in results for issue in item["issues"]]
    summary = {
        "chapters": len(results),
        "prompt_required": not args.skip_prompts,
        "prompt_checked": sum(1 for item in results if item["prompt_checked"]),
        "issues_count": len(issues),
        "first_issue": issues[0] if issues else None,
        "ok": not issues,
    }
    payload = {"summary": summary, "chapters": results}

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        prompt_summary = (
            f"prompt_checked={summary['prompt_checked']}/{summary['chapters']} "
            if not args.skip_prompts
            else "prompt_checked=skipped "
        )
        print(
            f"chapters={summary['chapters']} "
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
