#!/usr/bin/env python
import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = ROOT / "nalas_chapters_08_86"
TEXT_DIR = PIPELINE_ROOT / "chapter_text"
BRIEF_DIR = PIPELINE_ROOT / "chapter_visual_briefs"
EARLY_TEACHING_START_CHAPTER = 9
MODERN_ERA_START_CHAPTER = 16


def chapter_is_early_teaching(chapter):
    return EARLY_TEACHING_START_CHAPTER <= int(chapter) < MODERN_ERA_START_CHAPTER


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
    return re.sub(r"\s+", " ", text).strip()


def excerpt_at(words, start_ratio, word_count=90):
    if not words:
        return ""
    start = int(max(0, min(1, start_ratio)) * max(0, len(words) - word_count))
    return " ".join(words[start : start + word_count])


def chapter_title(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 2 and lines[0].lower().startswith("chapter"):
        return f"{lines[0]} - {lines[1]}"
    return lines[0] if lines else "Untitled chapter"


def build_brief(chapter):
    text_path = TEXT_DIR / f"C{chapter:03d}.txt"
    text = text_path.read_text(encoding="utf-8")
    words = re.findall(r"\S+", text)
    title = chapter_title(text)
    opening = compact(excerpt_at(words, 0.0))
    modern_era_note = ""
    if chapter >= MODERN_ERA_START_CHAPTER:
        modern_era_note = (
            "- From Chapter 16 onward, Earth/pham-tran scenes belong to the clearly modern 2020+ "
            "Covid/post-Covid era. During Covid, Nalas is about 32-35 years old: mid-30s, calm, compassionate, "
            "knowledgeable, physically similar to the approved pham-tran reference, not elderly, "
            "not 45+, not grey-haired, and not frail. Dress him cleanly and more formally: white "
            "button-down shirt or light dress shirt, optionally a dark blazer in class. Use normal "
            "Vietnamese city districts in 2020-2026: ordinary wards/districts, townhouses, apartments, rented classrooms, "
            "offices, training rooms, paved streets, alleys, shopfronts, streetlights, scooters/cars "
            "when natural, LED panels or fluorescent tube lights, office desks/chairs, magnetic "
            "whiteboards, marker pens and erasers, shelves, notebooks, tea/coffee, phones/laptops/"
            "projectors when natural, and visible signs that the era has moved forward. For generic "
            "emotional Earth scenes, choose city homes, apartment rooms, paved ward alleys, shopfronts, "
            "office-classrooms, or training rooms rather than scenic landscapes. Avoid oil-lamp "
            "poverty, floor mats, low tables, bamboo blinds, old wooden tea rooms, rural hut staging, "
            "countryside riverbanks, rice fields, fishing boats, muddy canals, riverside villages, "
            "rural lotus ponds, river-delta nostalgia, floating markets, rural water villages, and "
            "mien que song nuoc. If water is unavoidable, make it a modern "
            "urban canal, city lake, or riverfront promenade with concrete paths, railings, "
            "streetlights, apartment/townhouse background, traffic, and unmistakable city context.\n"
        )
    early_teaching_note = ""
    if chapter_is_early_teaching(chapter):
        early_teaching_note = (
            "- Phase lock for Chapters 9-15: Nalas has already begun teaching and gathering "
            "students. Default Earth/pham-tran scenes to early teaching rooms, rented classrooms, "
            "or clean learning rooms with students/disciples, desks/chairs, notebooks, tea, shelves, "
            "and improved electric lighting. Do not show poor countryside, village poverty, rural "
            "water scenery, or pre-teaching home life unless the local excerpt explicitly says "
            "flashback, past life, old village, or early awakening. Chapter 15 may show ancient "
            "South Asian past-life flashbacks only when the excerpt moves to crown prince / "
            "ascetic practice memories; its present-class scenes remain modern early-teaching rooms.\n"
        )
    c008_flow_note = ""
    if chapter == 8:
        c008_flow_note = (
            "- Chapter 8 flow lock: before Nalas has returned wisdom and before he teaches, keep "
            "Earth scenes in a poor peaceful Vietnamese countryside/village home, not a city apartment. "
            "Nalas looks modern and clean, always with thin glasses, but the house/yard/window view is "
            "moc mac: low houses, sparse night lights, simple electric bulb or fluorescent tube light, "
            "cement/tile floor, worn plaster/brick wall, simple furniture. Follow the exact sequence: "
            "two mature male messengers Giac/Chap watch him; he sleeps on a cold New Year night; he "
            "dreams inside the moonlit house; a huge jade-green dragon appears with head low, tail up, "
            "long whiskers/beard, and body curved into six sections; the dragon transforms into two adult "
            "men; later an adult male guide leads him toward a woman teacher; then a messenger appears as "
            "an old man, next night as an old woman, and only after he meets the woman teacher do old man "
            "and old woman appear together. Do not replace these beats with generic teacher portraits.\n"
        )
    return f"""# C{chapter:03d} Visual Brief

Title: {title}

Source reading rule:
This brief is derived from the chapter text, and every image lane must still obey its local story excerpt. Do not let the general Nalas DNA override the chapter scene.

Opening anchor:
{opening}

Visual direction:
- Prefer concrete scenes, people, settings, actions, and emotional states named in the local excerpt.
- Story focus priority: character identity, relationship, chapter phase, setting, and local action/emotion matter more than small decorative details. Secondary props, particles, diagrams, and symbolic overlays should support the beat, not crowd it.
- If the local excerpt is an Earth/pham-tran lecture, show the Teacher as a human teacher with students, tea or coffee when supported, illness/suffering reactions, attentive faces, and a clean modern teaching space. Use whiteboards/magnetic boards, marker pens, desks/chairs, shelves, notebooks, LED/fluorescent lighting when natural, and no fake legible text; boards may be blank or contain simple non-readable marker strokes/diagrams. If the lecture happens in heaven, a temple in heaven, paradise, tuelinh homeland, or celestial space, show Cha Nalas Nalanda in his stable divine Father manifestation instead: traditional Chua/Sacred-Heart-Jesus compassion, one fixed traditional Jesus-like portrait in every lane, apparent age 40-42, fatherly rather than boyish or elderly, center-parted shoulder-length wavy dark chestnut-brown hair, full neat brown beard and moustache, warm olive/light-tan Mediterranean/Semitic features, pure white flowing robe, no wings, inner warm golden light, outer sapphire-blue/lucy-blue cosmic aura, golden particles and blue cosmic energy particles, sacred-heart style gentle inner radiance, open-handed teaching authority, surrounded by tuelinhs/angels/light messengers in a cathedral-like heavenly setting. Keep him close to the heaven-Father canonical reference and immediately readable as familiar sacred Jesus-like imagery. Only Father may carry the full Jesus-like hair+beard+ivory robe+radiant heart signature; other male tuelinhs/attendants must have distinct faces, lower glow, shorter or tied-back hair, clean-shaven/light-stubble faces, distinct robe accents, and absolutely no Sacred Heart, heart-shaped chest light, glowing heart icon, or radiant chest emblem. Do not make him an elderly white-bearded God-Father, a model-like youthful savior, a youthful 30s actor-Jesus, a 45+ older Father, a modern-actor Jesus, winged, dark/aggressive/evil/horror-like, or a young clean-shaven messenger.
- If the chapter enters dream, heaven, temple, memory, tuelinh, energy, dragon, Giac, Chap, or cosmic travel, show that spiritual layer only for that excerpt.
- If a mortal Earth excerpt only mentions heaven, paradise, or spirits inside a thought, complaint, memory, or spoken idea, keep the scene Vietnamese and human; do not add Jesus, angels, or heavenly figures to the Earth room.
- Keep Nalas Nalanda's human mission and form-body continuity in pham-tran scenes only. In Earth scenes, preserve the approved mortal father-teacher identity: adult Vietnamese man, rounded-square gentle face, thin metal eyeglasses worn on his face, solid grounded body, calm scholarly compassion. The glasses are mandatory whenever the mortal/teacher body is visible, including sleep; do not show a bare-faced mortal Nalas and do not place spare glasses on a bed/table/desk. Update clothes and settings by phase: Chapter 8 before wisdom returns uses clean T-shirt/polo/casual shirt in a poor present-day countryside home; Chapters 9-15 use cleaner early-teaching/rented-classroom clothes and rooms unless a local excerpt is a flashback; Chapter 16+ Covid/post-Covid uses white button-down or light dress shirt, optionally blazer, and modern office-classroom settings. Around the Covid chapter he should read as 32-35, not elderly or grey-haired. In true heaven/celestial scenes, do not use the mortal Vietnamese teacher as the main figure; use Cha Nalas Nalanda's stable divine Father / traditional Chua-Sacred-Heart-Jesus form: one fixed traditional Jesus-like portrait in every lane, apparent age 40-42, fatherly rather than boyish or elderly, center-parted shoulder-length wavy dark chestnut-brown hair, full neat brown beard and moustache, warm olive/light-tan Mediterranean/Semitic features, pure white flowing robe, no wings, sacred-heart style radiant inner warm golden light plus outer sapphire-blue cosmic aura, close to the canonical reference, never elderly white-bearded, never model-like youthful or modern-actor handsome, never youthful 30s actor-Jesus, never 45+ old Father, and never young clean-shaven.
- Do not import images from another part of the chapter into the current lane; the lane excerpt decides the scene.
- Avoid generic deity posters and unrelated cosmic portals. In pham tran / Earth scenes, also avoid Jesus/God-Father styling, white-robed savior poses, angel wings, and church iconography. In heaven or celestial scenes, Western sacred/Jesus/angel visual language is allowed.
- Use an international modern cinematic/editorial look: premium lensing, controlled natural light, restrained color grade, tactile realism, mature composition. Modernity comes from camera grammar and polish, not from adding modern props unless the excerpt requires them.
- Keep the cultural ground clearly Vietnam through Vietnamese faces and body language, warm family/classroom atmosphere, books, notebooks, tea/coffee, plants, and ordinary contemporary details. Split the pham-tran timeline by phase: Chapter 8 before wisdom returns / before formal teaching uses poor present-day Vietnamese countryside/village settings with low houses, sparse lights, simple electric lighting, cement/tile floors, worn plaster/brick walls, simple furniture, and clean modern clothing; after Nalas starts teaching classes and disciples gather, especially Chapters 9-15, the Earth setting becomes cleaner, brighter, more modern, and more spacious because disciples support the class: proper tables/chairs, shelves, books, notebooks, whiteboard or magnetic board when natural, marker pens, modest tea or coffee service, organized students, and a khang trang Vietnamese teaching room in an ordinary city district; Chapter 16+ moves to clearly modern Covid/post-Covid office-classrooms. Do not put high-rise buildings, city skyline, apartment towers, busy traffic, or polished city interiors into the Chapter 8 countryside phase.
- Covid/pandemic-era teaching scenes should look polished and modern: LED ceiling panels or fluorescent tube lights, office-style desks and chairs, a proper magnetic whiteboard or whiteboard on wheels, visible marker pens and eraser, organized notebooks, bookshelves, tea/coffee, and a serious modern Vietnamese training-room/office-classroom feel. It can be more xịn xò than before, but keep it warm and human, not corporate luxury, hotel styling, old wooden tea room, sci-fi lab, hospital drama unless explicitly medical, or ancient classroom.
{c008_flow_note.rstrip()}
{early_teaching_note.rstrip()}
{modern_era_note.rstrip()}
- Pham tran / Earth / ordinary life: clearly Vietnamese, grounded, modern-cinematic, humble, no Jesus/church/angel styling, no halo or luminous ring/crown/corona above any human head.
- Thien duong / thien gioi / heaven / dream / tuelinh / cosmic memory / golden spiritual space: show Cha Nalas Nalanda in his stable divine Father manifestation, not the pham-tran Vietnamese teacher. Use Western sacred/heavenly visual language instead of Asian fantasy: Renaissance/Baroque-inspired heaven, white-gold clouds, cathedral-like depth, marble/ivory/gold atmosphere, traditional Sacred-Heart-Jesus compassion, saintly calm, pure white flowing robe with subtle fabric texture, no wings, inner warm golden light, outer sapphire-blue/lucy-blue cosmic aura, golden particles and blue cosmic energy particles floating softly, volumetric light rays, and angelic or light-messenger presence when supported by the excerpt. His heavenly face/age must be consistent and close to the canonical reference: one fixed traditional Jesus-like portrait in every lane, apparent age 40-42, center-parted shoulder-length wavy dark chestnut-brown hair, full neat brown beard and moustache, warm olive/light-tan Mediterranean/Semitic features, compassionate wise eyes, calm loving expression, slight gentle smile. Do not let attendants share the full Father signature; keep male attendants shorter-haired or tied-back, clean-shaven/light-stubble, lower-glow, and non-radiant-heart. Do not switch him between young angel, mortal teacher, model-like youthful savior, youthful 30s actor-Jesus, 45+ old Father, modern-actor Jesus, and elderly white-bearded God-Father.
- If Giac and Chap appear in heaven, they are not generic identical angels, not Father Nalas clones, and not the same white-haired man repeated twice. Giac is insight/discernment: slightly older, leaner oval face, high cheekbones, calm analytical eyes, restrained gold-white aura, precise still posture, with a small gold-white geometry or clear-light thread near the hands/chest. Chap is compassion/attachment-testing: slightly younger or softer face, warmer eyes, rose-gold or amber-white aura, humble protective posture, with a rose-gold sash or warm rose light held in the palm. If Father Nalas is present, Giac, Chap, and all messengers must have no Sacred Heart, no glowing heart icon, no heart-shaped chest light, and no radiant chest emblem; only Father has chest-heart radiance. If all five messengers appear, use a coherent five-member celestial working group: Giac, Chap, a blue-white order/law messenger with grid/archive/tablet markers, a green-gold healing/transformation messenger clearing toxins or carrying clean botanical light, and a silver-violet transmission/transit messenger with a gateway/path/arc marker. Give each one a distinct aura color, face type, posture, gesture, and role marker. If they appear in Earth teaching scenes, keep them ordinary and Vietnamese.
- Children in heaven may sit, play, or learn in a Western heavenly garden or cloud-lit sacred space; do not stage them in a Chinese fantasy temple academy.
- When Chapter 8 or the local excerpt mentions the jade-green dragon or a dragon vision, render it as a major dream event: a huge jade-green sacred dragon with a large head low near the ground, tail rising up toward the sky, a long powerful body bending in six visible sweeping curves, and long whiskers/beard flowing through strange breath. Keep it sacred and Vietnamese/Lac Viet dreamlike, but not imperial Chinese palace style: no pearl-chasing pose, no Chinese pagoda/palace, no red lanterns, no xianxia costume, no ornate court setting. Outside Chapter 8, only show a dragon when the local excerpt explicitly requires one.
- When the excerpt mentions Yin Yang or a yin-yang energy embryo, avoid a literal Taoist/Taijitu emblem, black-white yin-yang icon, or Chinese philosophical symbol as the main image. Prefer abstract balanced dual forces: interwoven gold-blue light, twin currents, a luminous dual energy filter, or a subtle non-cultural equilibrium sphere grounded in the Vietnamese/Western-heaven scene context.
- Avoid Chinese, Japanese, Korean, or generic pan-Asian visual language everywhere: no hanfu, tang suit, Chinese imperial robes, topknots, high hair buns, wuxia, xianxia, Chinese pagoda, Chinese palace garden, Chinese stone temple courtyard, giant circular stone relief, ornate round gate, hanging bells, red lanterns, calligraphy scrolls, kimono, hanbok, samurai, shoji, torii, or k-drama palace styling.
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-chapter", type=int, default=8)
    parser.add_argument("--end-chapter", type=int, default=86)
    parser.add_argument("--exclude-chapters", default="")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    excluded = parse_chapter_list(args.exclude_chapters)
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for chapter in range(args.start_chapter, args.end_chapter + 1):
        if chapter in excluded:
            continue
        brief_path = BRIEF_DIR / f"C{chapter:03d}.md"
        if brief_path.exists() and not args.force:
            continue
        brief_path.write_text(build_brief(chapter), encoding="utf-8")
        count += 1
        print(f"wrote {brief_path}")
    print(f"briefs_written={count}")


if __name__ == "__main__":
    main()
