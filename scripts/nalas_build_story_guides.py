#!/usr/bin/env python
import argparse
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = ROOT / "nalas_chapters_08_86"
TEXT_DIR = PIPELINE_ROOT / "chapter_text"
GUIDE_DIR = PIPELINE_ROOT / "chapter_story_guides"
MANIFEST_PATH = PIPELINE_ROOT / "chapters_manifest.json"


KEY_TERM_PATTERNS = [
    "body, soul and wisdom therapy course",
    "smallest energy particle",
    "positive energy particle",
    "negative energy particle",
    "yin and yang energy embryo",
    "yin and yang embryos",
    "single energy filter",
    "dual energy filter",
    "intellectual wave code fibre",
    "intellectual wave code",
    "sustainable transformation mechanism",
    "destructive transformation mechanism",
    "destructive transmutation",
    "sustainable transmutation",
    "information entanglement",
    "changing nature of information",
    "Mind Dharma",
    "dharma within dharma",
    "dharma outside dharma",
    "dharma unites dharma",
    "dharma denies dharma",
    "Unified Tao of the Universe",
    "truth of the universe",
    "truth of enlightenment",
    "two truths",
    "enlightened wisdom",
    "ignorant wisdom",
    "enlightened mind",
    "ignorant soul",
    "methods of liberation",
    "destructive power",
    "eliminate toxins",
    "destroying toxins",
    "love between men and women",
    "ancestral particles",
    "mental health",
    "depression",
    "insomnia",
    "anxiety disorders",
    "hallucinations",
    "postpartum",
    "pilgrimage",
    "children",
    "family",
    "Father",
    "Giac",
    "Chap",
    "tuelinh",
    "tuelinhs",
    "heaven",
    "temple",
    "human world",
    "Covid",
    "pandemic",
    "classroom",
    "students",
    "teacher's office",
    "raining",
    "winter",
    "coffee",
    "tea",
]


STOPWORDS = {
    "chapter", "teacher", "students", "student", "people", "things", "human",
    "humans", "world", "universe", "knowledge", "energy", "particle", "particles",
    "information", "truth", "wisdom", "tuelinh", "tuelinhs", "nalas", "nalanda",
    "because", "therefore", "however", "through", "within", "outside", "between",
    "their", "about", "which", "where", "when", "what", "this", "that", "with",
    "from", "they", "them", "will", "have", "been", "were", "your", "into",
    "body", "soul", "mind", "form", "life", "value", "values", "many",
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


def compact(text):
    text = text.replace("\ufffd", "'")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def words_of(text):
    return re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text)


def excerpt_at(words, ratio, count=130):
    if not words:
        return ""
    start = int(max(0, min(1, ratio)) * max(0, len(words) - count))
    return compact(" ".join(words[start : start + count]))


def chapter_title(text, manifest_item=None):
    if manifest_item and manifest_item.get("title"):
        return manifest_item["title"]
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 2 and lines[0].lower().startswith("chapter"):
        return lines[1]
    return lines[0] if lines else "Untitled"


def find_key_terms(text):
    lower = text.lower()
    found = []
    for term in KEY_TERM_PATTERNS:
        if term.lower() in lower:
            found.append(term)
    counts = Counter(
        token.lower()
        for token in words_of(text)
        if len(token) >= 5 and token.lower() not in STOPWORDS
    )
    for token, _count in counts.most_common(12):
        if token not in {item.lower() for item in found}:
            found.append(token)
        if len(found) >= 18:
            break
    return found[:18]


def detect_profiles(chapter, text):
    lower = text.lower()
    profiles = []
    if re.search(r"\b(covid|pandemic|coronavirus|lockdown|quarantine|epidemic)\b", lower):
        profiles.append("covid_or_pandemic")
    if re.search(r"\b(classroom|class|students|lecture|course|teacher's office|office|whiteboard|tea|coffee)\b", lower):
        profiles.append("earth_modern_teaching")
    if re.search(r"\b(heaven|temple|paradise|tuelinh|tuelinhs|giac|chap|father)\b", lower):
        profiles.append("heaven_or_tuelinh")
    if re.search(r"\b(rain|raining|winter|streetlights|roads in the city|capital)\b", lower):
        profiles.append("urban_weather_or_city")
    if re.search(r"\b(family|children|father|mother|wife|husband|men and women|love)\b", lower):
        profiles.append("family_or_relationship")
    if chapter >= 16 and "modern_era" not in profiles:
        profiles.append("modern_era")
    return profiles


def profile_rules(chapter, profiles):
    lines = []
    if "covid_or_pandemic" in profiles:
        lines.append(
            "- Covid/pandemic beats must look clearly modern: Nalas about 32-35 during Covid, neat hair, thin glasses, white/light shirt or blazer, LED/tube lights, magnetic whiteboard, marker pens, desks/chairs, shelves, notebooks, tea/coffee, city office-classroom. Do not use huts, oil lamps, floor mats, or old village rooms."
        )
    elif chapter >= 16:
        lines.append(
            "- Earth/pham-tran beats are post-Covid/modern-era by visual baseline: ordinary Vietnamese city districts, apartments, townhouses, offices, training rooms, paved alleys, scooters/cars, LED or fluorescent lights, proper furniture, whiteboard when teaching."
        )
    else:
        lines.append(
            "- Earth/pham-tran beats before Covid are still modern Vietnamese urban life, not old rural poverty: clean T-shirt/polo/casual shirt, modest city home or rented room, painted walls, tiled floors, glass/aluminum windows, ceiling fan, LED/tube lights."
        )
    if "earth_modern_teaching" in profiles:
        lines.append(
            "- Teaching/class/course beats should not all use the same composition. Vary teacher at board, student reaction, desk/table discussion, tea/coffee pause, notebook close-up, office/classroom wide shot, and abstract lesson visualization only when the excerpt supports it."
        )
    if "heaven_or_tuelinh" in profiles:
        lines.append(
            "- Heaven/temple/tuelinh beats use Western sacred heavenly grammar. When Cha Nalas/Father/Teacher is present in heaven, show him as stable divine Father Nalas in traditional Chua/Sacred-Heart-Jesus form: one fixed traditional Jesus-like portrait in every lane, apparent age 40-42, fatherly rather than boyish or elderly, center-parted shoulder-length wavy dark chestnut-brown hair, full neat brown beard and moustache, warm olive/light-tan Mediterranean/Semitic features, luminous ivory-white robe with subtle gold trim, sacred-heart style radiant heart/inner light, and calm compassionate authority. Keep him close to the heaven-Father canonical reference, immediately readable as familiar sacred Jesus-like imagery, and do not drift into a younger/older face. Only Father may carry the full Jesus-like hair+beard+ivory robe+radiant heart signature; other male tuelinhs/attendants must have distinct faces, lower glow, shorter or tied-back hair, clean-shaven/light-stubble faces, distinct robe accents, and absolutely no Sacred Heart, glowing heart icon, heart-shaped chest light, or radiant chest emblem. Do not make him a young clean-shaven messenger, a baby-faced or model-like youthful savior, a youthful 30s actor-Jesus, a 45+ older Father, a modern-actor Jesus, a short-haired pham-tran teacher, or an elderly white-bearded God-Father. When the excerpt only mentions a sleeping/waking Earth body, keep the mortal Vietnamese body as the anchor and do not invent a giant divine poster."
        )
    if "urban_weather_or_city" in profiles:
        lines.append(
            "- City/weather beats should show modern urban Vietnam: streetlights, wet paved roads, traffic, apartments/townhouses, office windows, rain reflections, winter clothes when supported. Do not turn rain/water into countryside river scenery."
        )
    if "family_or_relationship" in profiles:
        lines.append(
            "- Family/relationship beats should be human, contemporary, and emotionally specific: ordinary homes, table conversations, parents/children/students, respectful distance, practical modern rooms, not costume drama or nostalgic village tableau."
        )
    return lines


def build_guide(chapter, manifest_item=None):
    text_path = TEXT_DIR / f"C{chapter:03d}.txt"
    text = text_path.read_text(encoding="utf-8", errors="replace")
    title = chapter_title(text, manifest_item)
    word_list = re.findall(r"\S+", text)
    key_terms = find_key_terms(text)
    profiles = detect_profiles(chapter, text)
    samples = [
        ("Opening", excerpt_at(word_list, 0.00)),
        ("Early turn", excerpt_at(word_list, 0.18)),
        ("Middle", excerpt_at(word_list, 0.45)),
        ("Late turn", excerpt_at(word_list, 0.72)),
        ("Closing", excerpt_at(word_list, 0.92)),
    ]
    key_terms_text = "\n".join(f"- {term}" for term in key_terms) if key_terms else "- Use the exact local lane excerpt as the main subject."
    sample_text = "\n".join(f"- {label}: {excerpt}" for label, excerpt in samples if excerpt)
    profile_text = "\n".join(profile_rules(chapter, profiles))
    profile_names = ", ".join(profiles) if profiles else "literal_excerpt_only"
    return f"""# C{chapter:03d} Story Guide - {title}

Chapter identity:
- Title/subject: {title}
- This guide is built from the chapter text and must be read before batching this chapter.
- Do not make this chapter look like every other chapter. The title, local excerpt, and motifs below must drive the image choices.
- Visual profile tags: {profile_names}.

Chapter-specific motifs and terms:
{key_terms_text}

Story arc samples to keep the chapter distinct:
{sample_text}

Mandatory visual rules for this chapter:
{profile_text}
- Always obey the local lane excerpt first. If the excerpt is a classroom conversation, show that exact class beat. If it is a technical doctrine, visualize it through the named mechanism rather than a generic glowing circle. If it is heaven, temple, tuelinh, Giac, Chap, or Father, use the correct heaven/Earth split.
- Whenever the mortal/pham-tran Nalas or Earth teacher body is visible, keep the approved identity: Vietnamese father-teacher, rounded-square gentle face, solid grounded build, calm scholarly compassion, and thin metal eyeglasses worn on his face. The glasses are mandatory even when he sleeps; do not show a bare-faced mortal Nalas and do not create a spare pair of glasses on a bed/table/desk.
- If Giac, Chap, two messengers, or five messengers appear, keep them role-distinct and non-cloned. Giac is insight/discernment: restrained gold-white, slightly older, leaner oval face, high cheekbones, calm analytical gaze, precise still posture, with a small gold-white geometry or clear-light thread near the hands/chest. Chap is compassion/attachment-testing: warmer rose-gold, slightly younger or softer face, warmer eyes, humble protective posture, rose-gold sash or warm rose light held in the palm. If Father Nalas is present, Giac, Chap, and all messengers must have no Sacred Heart, no glowing heart icon, no heart-shaped chest light, and no radiant chest emblem; only Father has chest-heart radiance. The other three messengers, when present, are blue-white order/law with grid/archive/tablet markers, green-gold healing/transformation clearing toxins or carrying clean botanical light, and silver-violet transmission/transit with a gateway/path/arc marker. Do not render Giac and Chap as identical generic angels, identical white-haired men, or Father Nalas lookalikes.
- Do not use rural river/countryside-water beauty, rice fields, muddy canals, old wooden tea houses, oil lamps, dirt floors, patched peasant clothes, Chinese costume drama, pagodas, hanfu, xianxia, or generic Asian fantasy.
- No fake readable text on boards/books. Boards may be blank or have simple non-readable marker strokes only.

Composition variety:
- Across lanes, alternate wide establishing frames, teacher/student mid-shots, reaction shots, object/details, city/weather frames, heavenly temple frames, and abstract doctrine visualizations according to the excerpt.
- Avoid repeating the same front-facing teacher-with-students layout unless the local excerpt genuinely needs it.
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-chapter", type=int, default=8)
    parser.add_argument("--end-chapter", type=int, default=86)
    parser.add_argument("--exclude-chapters", default="")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    excluded = parse_chapter_list(args.exclude_chapters)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {"chapters": []}
    by_chapter = {int(item["chapter"]): item for item in manifest.get("chapters", [])}
    GUIDE_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for chapter in range(args.start_chapter, args.end_chapter + 1):
        if chapter in excluded:
            continue
        guide_path = GUIDE_DIR / f"C{chapter:03d}.md"
        if guide_path.exists() and not args.force:
            continue
        guide_path.write_text(build_guide(chapter, by_chapter.get(chapter)), encoding="utf-8")
        count += 1
        print(f"wrote {guide_path}")
    print(f"guides_written={count}")


if __name__ == "__main__":
    main()
