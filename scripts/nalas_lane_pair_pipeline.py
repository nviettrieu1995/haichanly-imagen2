#!/usr/bin/env python
import argparse
import json
import math
import os
import re
import subprocess
import time
from pathlib import Path

from nalas_chapters_pipeline import (
    CH8_PROMPT_DNA_PATH,
    CODEX_IMAGEN,
    LOG_DIR,
    MANIFEST_PATH,
    PIPELINE_ROOT,
    ROOT,
    build_manifest,
    excerpt_segments,
    extract_chapter_texts,
    is_transient,
    load_manifest,
    log,
    parse_json,
    parse_rate_limit,
    read_dna as read_base_dna,
)


PAIR_PROMPT_DIR = PIPELINE_ROOT / "lane_pair_prompts"
PAIR_IMAGE_DIR = PIPELINE_ROOT / "generated_lane_pairs"
PAIR_MANIFEST_PATH = PIPELINE_ROOT / "lane_pairs_manifest.json"
BRIEF_DIR = PIPELINE_ROOT / "chapter_visual_briefs"
STORY_GUIDE_DIR = PIPELINE_ROOT / "chapter_story_guides"
CANONICAL_PHAM_TRAN_REF = PIPELINE_ROOT / "character_refs" / "pham_tran_canonical" / "pham_tran_canonical.png"
CANONICAL_HEAVEN_FATHER_REF = (
    PIPELINE_ROOT / "character_refs" / "heaven_father_canonical" / "heaven_father_canonical.png"
)
MODERN_ERA_START_CHAPTER = 16
EARLY_TEACHING_START_CHAPTER = 9


CHAPTER8_DNA_LEAK_MARKERS = [
    "Chapter 8 step-by-step lock:",
    "C008 is the return-to-wisdom journey",
    "huge jade-green dragon with large head low near the ground",
    "adult male person announced in the dream",
    "old man and old woman appear together",
]


def strip_chapter8_specific_dna(dna):
    """Keep reusable character DNA, but remove C008-only plot beats for other chapters."""
    dna = dna.replace("Core truth established in Chapter 8:", "Core incarnation truth:")
    dna = re.sub(
        r"\nChapter 8 step-by-step lock:\n.*?(?=\nEarth and teaching scenes:)",
        "\n",
        dna,
        flags=re.S,
    )
    dna = re.sub(
        r"\n- If the Chapter 8 dragon appears,.*?(?=\n- If a temple appears)",
        "\n",
        dna,
        flags=re.S,
    )
    return re.sub(r"\n{3,}", "\n\n", dna).strip()


def read_dna_for_chapter(chapter_number):
    dna = read_base_dna()
    if int(chapter_number) == 8:
        return dna
    return strip_chapter8_specific_dna(dna)


def path_points_inside_root(value):
    if not value:
        return True
    path = Path(value)
    if not path.is_absolute():
        return True
    try:
        return path.resolve().is_relative_to(ROOT.resolve())
    except OSError:
        return False


def plan_paths_match_current_root(plan):
    values = [
        plan.get("book_path"),
        plan.get("prompt_dir"),
        plan.get("output_dir"),
        plan.get("text_path"),
    ]
    for lane in plan.get("lanes", [])[:5]:
        values.extend([lane.get("start_target"), lane.get("end_target")])
        for item in lane.get("items", []):
            values.append(item.get("target"))
    for batch in plan.get("batches", [])[:5]:
        values.extend([batch.get("prompt_file"), batch.get("output_stem")])
        values.extend(batch.get("targets", []))
        for item in batch.get("items", []):
            values.append(item.get("target"))
    return all(path_points_inside_root(value) for value in values)


def atomic_write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        tmp_path.write_text(text, encoding="utf-8")
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


PHAM_TRAN_CHARACTER_DNA = """Canonical pham-tran Nalas reference:
Use the approved pham-tran canonical reference image when it is attached by the runner. It defines the mortal Vietnamese form of Cha Nalas Nalanda in Earth scenes: an adult Vietnamese father-teacher with a rounded-square face, gentle fullness, short dark hair, thin metal eyeglasses, solid grounded body, calm scholarly expression, and compassionate teacher energy. Keep the face/body continuity, but update clothing and setting by timeline: before teaching he can wear a clean T-shirt, polo, or casual shirt in a poor but present-day Vietnamese countryside home, with sparse village lights, low modest houses, simple electric bulbs or fluorescent tube light, cement/tile floor, simple wooden furniture, and no city skyline or high-rise apartment view. He must look modern and clean, not like an old scholar, monk, thầy đồ, historical peasant, or costume-drama figure. By the Covid chapter he should read as 32-35 rather than elderly, neater and more formal in a white button-down shirt or light dress shirt, optionally a dark blazer in class. No obvious grey hair, no frailty, no 45+ styling. Keep him human, kind, learned, and ordinary; do not turn him into a warrior, monk, Chinese ancient scholar, Western Jesus figure, or slim heroic fantasy character.
Extra phase lock for the mortal body: Chapter 8 / before wisdom returns uses the poor present-day countryside home. Chapters 9-15 / after classes begin use rented classrooms or cleaner learning rooms with students, notebooks, tea, shelves, proper tables/chairs, and improved electric lighting; do not send him back to a poor pre-teaching home unless the local excerpt is explicitly a flashback. Chapter 16+ / Covid and post-Covid uses modern office-classrooms or training rooms, with Nalas about 32-35 around Covid in a white button-down or light dress shirt, optionally a blazer.
The canonical reference is only for pham tran / Earth / mortal scenes. In true heaven, dream, tuelinh, or celestial scenes, do not use the mortal Vietnamese teacher as the primary divine figure. Use the mortal reference only if the sleeping or waking earthly body is explicitly visible."""


DIVINE_NALAS_CHARACTER_DNA = """Divine/heaven Nalas identity:
In true heaven, thien duong, thien gioi, tuelinh homeland, celestial temple, or paradise scenes, Cha Nalas Nalanda must appear in one stable divine Father form, not as the pham-tran Vietnamese schoolteacher and not as a generic changing deity. When the approved heaven-Father canonical reference image is attached by the runner, treat it as the portrait lock: preserve the same face identity, exact age read, hair length, beard density, robe language, shoulder build, and sacred presence. Use a Western sacred / traditional Christian Sacred-Heart Jesus visual register with a consistent Chua-like identity that reads immediately as a familiar sacred Jesus figure: one fixed traditional Jesus-like portrait in every lane, apparent age 40-42, fatherly and compassionate rather than boyish or elderly, with subtle forehead texture, mature smile lines, and calm gravity in the eyes but no grey/white age markers. He has classic Jesus iconography: shoulder-length wavy dark chestnut-brown hair with a natural center part, full neat brown beard and moustache, warm olive/light-tan Mediterranean/Semitic features, deep calm eyes, gentle strength, luminous ivory-white robe with subtle gold trim, open hands, a sacred-heart style radiant heart or gentle inner light, surrounded by tuelinhs/angels/light messengers in cathedral-like white-gold space. This is Nalas Nalanda's heavenly manifestation in a Chua/Jesus-like form; do not drift away from the reference into a generic fantasy angel, handsome young savior, modern actor/model Jesus, vague deity, or elderly God-Father. Keep this exact heavenly face, hair, beard, apparent age, robe language, and emotional presence across all heaven lanes and across both images in a start/end pair. When messengers, tuelinhs, or students share the heaven frame, Father Nalas must remain uniquely recognizable as the central sacred Father anchor: most authoritative, warmest white-gold heart light, most classic Jesus-like robe/hair/beard silhouette, and closest to the reference. Only Father Nalas may have the full signature combination of center-parted shoulder-length chestnut hair, full neat brown beard, ivory-gold robe, and radiant heart.
Heaven-Father sample style lock: for every true heaven/celestial Father Nalas frame, use the style of a close-up divine father portrait inspired by the God Father Jesus archetype: pure white flowing robe, no wings, long soft hair, gentle beard, compassionate wise eyes, calm loving expression, slight gentle smile, ultra-detailed skin and fabric texture, soft cinematic lighting, volumetric light rays, sacred atmosphere, ethereal glow, depth of field, and ultra-realistic 16:9 cinematic detail. Surround him with dual aura layers: inner warm golden light and outer sapphire-blue / lucy-blue cosmic aura, both glowing softly. Add golden particles and blue cosmic energy particles floating around him in slow motion. Keep the older white-gold Sacred-Heart language as a soft inner radiance, but avoid making it aggressive, dark, horror-like, or winged.
Other male tuelinhs, attendants, or messengers must have distinct faces, lower light intensity, different robe accents, and absolutely no Sacred Heart, heart-shaped chest light, radiant chest emblem, or glowing heart icon. Default them to short hair or tied-back hair, clean-shaven faces, light stubble at most, and cooler or softer aura markers. If one attendant has longer hair, he must not also have a full beard, ivory-gold Father robe, or any chest-heart radiance. Messengers must not copy his full Jesus-like beard, exact robe, face, age, or radiant-heart identity. Do not make him an elderly God-Father with grey/white hair or a long white beard. Do not make him a younger clean-shaven man, teenage angel, slim student, baby-faced 20s/early-30s savior, youthful 30s actor-Jesus, 45+ older Father, 50s/60s old Father, short-haired mortal teacher, or one of the messengers. Do not attach the pham-tran face/body reference to pure heaven lanes. If the sleeping or waking Earth body also appears, keep it as a separate modern Vietnamese mortal body layer, visually secondary to the heavenly manifestation."""


PHAM_TRAN_GLASSES_RULE = """Mortal Nalas glasses lock:
Whenever the pham-tran / Earth / mortal teacher body of Nalas Nalanda is visible, he must wear his thin metal eyeglasses on his face. This includes sleeping, resting, studying, teaching, walking, drinking tea/coffee, Covid-era classes, and any modern Vietnamese room scene. The glasses are a core identity marker, not an optional prop. Make the thin metal rims or a small lens glint visibly readable even in mid-shots; do not merely imply glasses with a bare-looking face. Do not show a bare-faced mortal Nalas. Do not place a spare pair of glasses on the bed, table, floor, notebook, or bedside if he is visible; exactly one pair exists, and it is worn on his face. This rule applies to the mortal Vietnamese body only; the pure divine Father manifestation in heaven remains a separate sacred form unless the lane also shows the mortal Earth body."""


PHAM_TRAN_AGE_CONTINUITY_LOCK = """Mortal Nalas age continuity lock:
Keep the pham-tran / Earth Nalas as one continuous person across all lanes in a chapter and across both images in a start/end pair. The approved reference controls face shape, glasses, body type, calm scholarly compassion, and grounded build; the local chapter controls age stage. Do not let lighting, sleep, dream glow, camera angle, or emotion turn him into a different younger or older man.
- Chapter 8 / before wisdom returns: apparent age 30-32 but still before the Covid teaching era, same rounded-square Vietnamese face with gentle fullness, same solid grounded adult body, short dark hair, thin glasses, clean T-shirt/polo/casual shirt. He may look tired, humble, or thoughtful, but not elderly, 40+, grey-haired, deeply wrinkled, frail, receding-haired, or like a middle-aged senior teacher. He also must not become a baby-faced college student, slim youthful actor, narrow-faced handsome youth, thin-necked model, or a different younger man. Keep the mature father-teacher identity even when subtly de-aged.
- Chapters 9-15 / early teaching: the same person, only slightly more established and teacher-like, about early-30s unless the excerpt says otherwise. Do not jump between boyish youth and old master.
- Covid chapter / Chapter 16: about 32-35, neat and formal, same face/body continuity with thin glasses. Later chapters can mature gradually, but age must progress smoothly, not randomly within one chapter.
If the canonical reference appears older than the current chapter stage, borrow identity, glasses, rounded-square face proportions, gentle fullness, and solid body silhouette from it, then only subtly de-age for Chapter 8 rather than copying older skin or grey hair. If the local excerpt shows sleep, keep the same age as the awake frame; sleep must not make him look older."""


FIVE_MESSENGERS_DNA = """Five messengers visual DNA:
When the text mentions Giac, Chap, the two messengers, several messengers, or the five messengers of the first tuelinh, do not make them generic identical angels, identical white-haired men, Father Nalas clones, children, women, or random students. Their true forms are five mature male messengers. Keep them as a coherent five-member celestial working group: mature calm male faces, white-ivory Western sacred garments, early-Christian / Greco-Roman-inspired simple tunics and mantles, role-colored sashes or light seams, restrained sacred posture, no wings unless the excerpt strongly needs symbolic angelic language, and no Chinese/xianxia styling. Avoid East Asian wrap robes, cross-collar hanfu shapes, kimono-like overlapping collars, monk robes, topknots, and court-sage styling for true messenger forms. Messenger hair must be short or neatly tied back; no shoulder-length loose waves, no full Jesus beard, no Father-like face, and no chest-centered holy glow. Giac and Chap appearing in dreams before the disguise sequence are both adult men, never one male and one female. Only when the local excerpt explicitly says a messenger disguises himself as an old man or old woman should the image show that temporary disguise; the underlying messenger identity remains male.
- Giac: insight / discernment messenger. Slightly older than Chap, leaner oval face, higher cheekbones, calm analytical eyes, precise upright posture, almost still. Restrained gold-white aura. Gesture: one hand lightly tracing a small gold-white geometry or clear-light thread near the hands/chest. Position: often nearest Father, watching, measuring, asking. Never use a halo, crown, beard-heavy Jesus face, or warm rose color.
- Chap: compassion / attachment-testing messenger. Slightly younger or softer than Giac, fuller kinder face, warmer eyes, humble protective posture, emotionally responsive but not weak. Rose-gold or amber-white aura. Gesture: open palm near the heart line or a protective hand lowered toward suffering people, with the glow clearly in the palm and away from the center of his chest. Visual marker: rose-gold sash, warm light held in the palm, or a soft rose aura around the hands. Never give Chap a Sacred Heart, heart-shaped chest light, radiant chest emblem, central chest glow between both hands, or the Father's chest glow when Father Nalas is present. Never clone Giac's lean analytical face or gold-white geometry marker.
- Messenger Three: order / law / causal record. Upright and symmetrical, quiet judge-like composure, blue-white aura. Visual marker: blue-white luminous grid, archive table, or orderly light tablets with no readable text. Gesture: holding the structure steady, not comforting.
- Messenger Four: healing / transformation / toxin removal. Gentle guardian presence, green-gold aura, softer grounded stance. Visual marker: clean botanical light, green-gold healing current, or particles clearing black toxins. Never demonic, horror, plague doctor, or frightening.
- Messenger Five: transmission / transit / path between realms. Slender quiet guide, silver-violet aura, slightly turned body as if opening a route. Visual marker: silver-violet gateway, path, arc, or transit ribbon when supported by the excerpt. Never make this figure another gold-white Giac.
If Giac and Chap appear together, compose them as two clearly different roles: Giac is restrained gold-white, lean, precise, and analytical; Chap is warmer rose-gold, softer, compassionate, and protective. Do not give them the same face, same hair, same beard, same aura color, same robe silhouette, or the Jesus-like divine Father look. If Father Nalas appears in the same frame, Giac/Chap/five messengers should read as attendants or emissaries, not alternate versions of Father: less central, no radiant heart lock, no Sacred Heart or heart-shaped glow on the chest, no identical shoulder-length hair plus full Jesus beard combination, and no exact ivory-gold Father robe. If the excerpt says the messengers pretend to be Buddha or God as a test, show the deception as an ambiguous spiritual apparition or testing vision, not as the real Buddha/God and not as Cha Nalas. Keep their mission clear: exposing greed, attachment, intellectual arrogance, toxins, and activating goodness. Avoid halos over heads, ornate crowns, Chinese immortal robes, Buddhist monk costume, literal church iconography, or horror-demon staging."""


EARTH_STAGE_RULE = """Pham-tran timeline / setting rule:
- Early/pre-teaching ordinary life, especially Chapter 8: the setting is a poor, modest Vietnamese countryside/village home, not a city apartment or urban district. Keep the period modern enough for 2014-2019: clean T-shirt/polo/casual shirt, simple trousers, thin glasses, electric bulb or fluorescent tube light, fan when natural, cement or plain tile floor, painted or worn plaster/brick walls, simple wooden bed/table/chairs, notebooks/books, and low rural houses or a dark quiet village outside the window. The village may feel poor and mộc mạc, but never ancient, costume-drama, thầy đồ, monk, or old dynastic China. Avoid high-rise buildings, city skyline, many urban lights, glass office towers, apartment blocks, busy traffic, and polished city interiors in this early quê period.
- Later teaching/classroom period: when the excerpt shows Nalas teaching classes, students/disciples, lectures, tea/coffee, rented classrooms, improved learning rooms, or organized study groups, move the Earth setting into a clean, bright, modern Vietnamese learning room in an ordinary city district. He has traveled, gathered disciples, and the disciples contribute to the class, so the room can be khang trang: proper tables and chairs, orderly shelves, books, notebooks, tea or coffee cups, potted plants, modest wall lights, and an organized serious classroom feel. Do not make it a rustic tea house, antique wooden room, ancient classroom, corporate luxury office, hotel, temple fantasy, or historical costume room.
- Covid / pandemic teaching period, around 2020: when the excerpt enters Covid-19, pandemic, lockdown, quarantine, infectious disease, or post-pandemic mental-health class material, raise the production value clearly above earlier scenes. Nalas is about 32-35, neat and formal: white button-down shirt or light dress shirt, optionally a dark blazer, tidy hair, thin glasses, compassionate and knowledgeable. Use a proper modern Vietnamese office-classroom or training room: LED ceiling panels or fluorescent tube lights, office-style desks and chairs, a real magnetic whiteboard or whiteboard on wheels, visible marker pens and eraser, organized notes, bookshelves, tea/coffee, and students seated like a serious modern class. The whiteboard may be clean or contain simple non-readable marker strokes/diagrams; avoid fake legible text. Avoid hospital drama unless the excerpt is medical; avoid sci-fi lab, corporate luxury, hotel styling, old wooden tea room, and ancient classroom.
- Post-Covid modern era: from Chapter 16 onward, Earth/pham-tran scenes are never the old oil-lamp poverty look and must not become rural river/countryside scenes. Nalas is about 32-35 during Covid and gradually older after that. Keep the approved face/body continuity, but make him more mature, established, and teacher-like. Default to normal Vietnamese city districts in 2020-2026: ordinary wards, urban neighborhoods, modern homes, apartments, townhouses, offices, classrooms, rented training rooms, paved streets, alleys, shopfronts, streetlights, scooters/cars when natural, electric lights, whiteboards, office desks/chairs, shelves, notebooks, tea/coffee, phones or laptops only when natural, and a world that has visibly moved forward. If water is explicitly necessary, make it an urban canal/lake/riverfront promenade with concrete paths, railings, streetlights, buildings, apartments/townhouses, traffic, and city context; never scenic countryside-water.
- International travel/pilgrimage exception: when the excerpt names Cebu/Philippines, India, Nepal, Bihar, Gaya, Mahabodhi, Bodhi tree, Nalanda University, New Delhi, Patna, airport, plane, bus, hotel, relic, ruins, or pilgrimage, follow that named place literally. Keep Nalas as the same Vietnamese pham-tran teacher with thin glasses and modern travel clothes, but do not force the setting back into Vietnam or a generic office-classroom."""


PHAM_TRAN_PHASE_TIMELINE = """Phase timeline lock:
1. Before wisdom returns / before formal teaching: Nalas is the same modern Vietnamese man, always wearing thin glasses, but he lives in a poor countryside/village environment. Use low modest houses, a quiet yard, simple rural lane, sparse night lights, electric bulb or tube light, cement/tile floor, worn plaster/brick wall, simple furniture, books/notebooks, clean T-shirt/polo/casual shirt. Do not show city skyline, high-rise buildings, apartment towers, crowded urban lights, luxury rooms, or thầy đồ/old-scholar clothing.
2. Guided study / meeting the spiritual teacher: still grounded and modest, with travel/visits and skeptical human emotion. If a male guide leads him to a woman teacher, show a real adult male guide and the woman teacher as concrete story characters, not vague symbols. Keep the setting rural/modest or transitional unless the excerpt clearly moves elsewhere.
3. After he begins teaching / gathering disciples: the environment improves. Use cleaner, brighter Vietnamese learning rooms, proper tables/chairs, bookshelves, notebooks, tea/coffee, organized students, and a room that feels supported by disciples. This can look modern and khang trang, but not corporate luxury or a hotel.
4. Covid and post-Covid: clearly modern 2020+ office-classroom/training-room language. Use LED/tube lights, magnetic whiteboard or whiteboard on wheels, markers/eraser, desks/chairs, shelves, notebooks, tea/coffee, and a neat formal Nalas around age 32-35 during Covid.
Chapter mapping: C008 belongs to phases 1-2, C009-C015 belong to phase 3 unless the local excerpt explicitly says flashback/past life, and C016+ belongs to phase 4. International travel/pilgrimage chapters still follow their named real-world location instead of defaulting to Vietnam."""


EARLY_RURAL_MATERIAL_LOCK = """Early rural material lock:
When Chapter 8 or any pre-teaching pham-tran frame shows Nalas's poor countryside home, poverty must read as modest present-day rural Vietnam, not an ancient hut. Use a concrete/cement or brick house with painted, peeling, or worn plaster walls; cement or ceramic tile floor; aluminum/glass window frames; ordinary modern door; visible electric wiring, LED/fluorescent tube, simple bulb, or ceiling fan. The room can be old, damp, cracked, and poor, but it must not be nha tranh/vach dat: no mud wall, clay wall, earthen wall, woven bamboo wall, straw/thatch hut, exposed bamboo rafters, exposed thatch roof, dirt floor, oil lamp nostalgia, or patched historical peasant interior."""


STORY_FOCUS_PRIORITY_RULE = """Story focus hierarchy:
1. Character identity and relationship are the first priority: Nalas's correct mortal/divine form, Giac/Chap/five messengers, students, mothers, patients, named examples, and whether the scene is Earth, dream, or heaven.
2. Setting and timeline are the second priority: C008 poor modern countryside, C009-C015 early teaching rooms, C016+ modern/Covid/post-Covid office-classrooms, named international travel/pilgrimage locations when the excerpt says Cebu/India/Nepal/New Delhi, and Western sacred heaven for true celestial scenes.
3. The local action/emotion is the third priority: a question, tea pause, class reaction, rain outside the office, sleeping body, mother waiting, pandemic memory, group practice, or heavenly teaching.
4. Secondary props, energy particles, diagrams, symbolic overlays, and doctrine visuals are optional support. Use them only when they clarify the beat; do not overload a frame with every doctrine term or tiny detail."""


C008_STORY_FLOW_LOCK = """C008 step-by-step story flow lock:
Chapter 8 is not generic teacher-at-desk imagery. It is the journey of Nalas Nalanda's mortal body gradually returning to wisdom while being accompanied and protected by the messengers.
Required flow anchors:
1. Heaven remains Western sacred, not Chinese/xianxia. Giac and Chap are two mature male messengers watching the 29-year-old mortal body.
2. The Earth body is sleeping in a poor, peaceful countryside home on a cold early-spring New Year night. He is modern and clean, always wearing thin glasses; the room is poor/moc mac, not city/apartment.
3. In the dream he stands inside the house, moonlight through glass windows, unsure dream vs reality.
4. He hears a strange breath, opens the door, steps to the left garden, and sees a huge jade-green dragon: large head low near the ground, tail up toward the sky, long whiskers/beard, body bent into six sweeping sections. It must be large and frightening/sacred, not a tiny snake.
5. The dragon passes the front door and transforms into two adult men. These two are male messengers in human form. Never show one male and one female, children, or two little girls here.
6. The two men tell him time is running out, they cannot teach him, and they will direct him to someone to study.
7. Months later he meets the notified adult male person, who leads/directs him to a woman teacher with spiritual abilities. Include the adult male guide and the woman teacher when this beat appears.
8. Before meeting the woman teacher, a messenger first disguises himself as an old man in a dream and urges him to study quickly; Nalas remains skeptical and does not answer.
9. The next night a messenger disguises himself as an old woman and repeats the message; Nalas still does not answer.
10. After Nalas meets the woman teacher, the two disguised figures appear together as an old man and an old woman, repeat that they cannot teach him and he must study with that woman for one year. This old-man/old-woman pair appears only at this later step, not at the initial two-male-messenger step.
11. He studies, becomes disappointed, burns his notes, and questions the heaven/paradise people. Show this as human frustration in the modest Earth setting, not as a generic mystical poster.
12. Later dreams reveal the temple/heaven/lake/homeland and the gradual return of memory and wisdom. Heaven remains Western sacred; if Father Nalas appears, use the canonical Sacred-Heart-Jesus-like Father form.
13. He later teaches many classes and students; only then should the Earth setting improve into cleaner, better-funded rooms."""


EARLY_TEACHING_FLOW_LOCKS = {
    9: """C009 flow lock:
Four Commandments / Gathering of Humanity. Start from Giac proudly following Nalas's human teaching over years and seeing many sick/suffering people recover through the two truths. Key Earth beat: nearly one hundred students in a cramped rented classroom inside a house; Giac blends into the classroom atmosphere to listen. Then move to Nalas explaining his name and the first tuelinh identity, and to Western sacred Father/heaven scenes for creation/four-commandment material. Show family, society, nation, and teacher-student life as concrete human practice forms. Avoid generic teacher portraits.""",
    10: """C010 flow lock:
Congress of Unifying the Practising Path of the Tuelinhs. Opening Earth beat: students arrive before the Teacher, a previous lecture recording plays, Nalas sips hot tea, and a young student asks why tuelinhs become humans and animal souls incarnate. Cosmic beats: destructive energy storms, yin-yang energy embryo growing into a giant sphere, explosion into a mature tuelinh, creation of plants/animals/insects with five particle groups, Father holding a small glass jar of white powder, and tuelinhs becoming enthusiastic to incarnate. No generic glowing-circle filler.""",
    11: """C011 flow lock:
Ignorant Wisdom. Ground the chapter in class reactions: attentive tearful students, illness and suffering relief, students asking about warmth, sweating, drowsiness, headaches, nausea, itching, and bone pain while listening. Nalas explains negative/positive information reactions and healing; students bring hot tea to his table. Keep the emphasis on believable class healing reactions plus restrained information-energy visuals.""",
    12: """C012 flow lock:
Enlightened Wisdom. A student asks for a clear standard between ignorant and enlightened wisdom; Nalas answers through the two truths and smallest energy particle knowledge. Vary seated tea, standing lecture, student question, board/diagram, and reflective class frames. Doctrine beats can show understanding information in people/animals/events/destructive energy and activating positive information, but Earth classroom excerpts stay grounded.""",
    13: """C013 flow lock:
State of Ignorant Soul. Show the scale and humanity of the course: one class a week, six-hour lectures, seven months, students from under ten to over sixty, serious illnesses, families accompanying patients, people flying/driving/renting near the classroom, students arriving early and seeing the classroom as a second home. Nalas records illness/recovery and checks patients weekly. Do not collapse it into one repeated teacher-at-board frame.""",
    14: """C014 flow lock:
State of Enlightened Mind. Teaching-room baseline with doctrine visualizations only when useful: intellectual wave code fibres, yin-yang root embryo, positive energy controlling negative energy, compassion, delight, and peace. Use concrete moral scenes for compassion around possession/non-possession, love/hatred, wisdom/lack of knowledge, success/failure, action/inaction. Alternate classroom explanation, student reflection, human examples, and restrained mechanism visuals.""",
    15: """C015 flow lock:
Suffering and Methods of Liberation. Present-class scenes: Nalas sipping hot tea, students asking about past lives, and Nalas sharing memories to support the lesson. Past-life flashbacks are allowed only when the excerpt moves there: ancient South Asian crown prince, king and queen, wife/children, high-walled capital, temple study, escape southeast, teachers, meditation, asceticism, and three metal-tool sounds. Past-life scenes are South Asian/princely/ascetic, not Chinese fantasy; present class stays modern early-teaching."""
}


MODERN_CHAPTER_FLOW_LOCKS = {
    16: """C016 flow lock:
Covid-era origin of the smallest energy particle teaching. Open with modern pandemic lockdown, death/economic loss/mental-health suffering, toxins erupting, fraud/corruption/fake medicine, and also doctors/scientists/donors/helpers. Classes close for a year; when blockade lifts, Nalas returns to a modern city office-classroom with LED/tube lights, magnetic whiteboard, markers, desks/chairs, shelves, notebooks, tea/coffee, and three excellent male students. He transforms sublime smallest-particle knowledge into simple lessons, treats mentally ill patients respectfully, observes reactions, then teaches particle structure and student body reactions. Nalas is 32-35, glasses always, white/light shirt or blazer. No old rural room, hospital horror, fake readable diagrams, or sci-fi lab.""",
    17: """C017 flow lock:
Truth of the Universe with smallest energy particle knowledge. Modern post-Covid class/training room; students arrive early and look forward to the new lesson. Focus on Nalas giving a practical standard for the truth of the universe, including parent-child/soul-not-property examples. Visualize smallest positive/negative energy particles only as restrained support for classroom explanation of humans, animals, tuelinhs, events, interactions, information acquisition, toxins, and suffering.""",
    18: """C018 flow lock:
Truth of Enlightenment. Modern classroom dialogue with students who have studied for years but once misunderstood enlightened knowledge because memorization did not become practice. Focus on correction of pride/disobedience, suffering lessons, origin/nature/humanity/tuelinh mission, and liberation from suffering. Intellectual fibres, vibrational wave code, and positive/negative energy particles should support the teacher-student explanation, not replace it.""",
    19: """C019 flow lock:
Love Story and destructive transformation. Begin with cold rain, autumn-to-winter transition, wet modern city/office atmosphere, and Nalas making hot tea after walking in freezing rain. Focus on the teacher reflecting on sick students and discussing a girl's mental illness, parental misunderstanding, medicine suppression, false information, relationship confusion, wrong-body/confused-soul explanation, and decay. Keep it compassionate, modern, and non-sensational.""",
    20: """C020 flow lock:
Symbol of Sustainable Transformation. Winter office warmth after rain, hot fragrant tea, teacher with two students. Key character Loi Nalanda, over sixty, as a fulfilled older Vietnamese man whose family, business, social relationships, and spreading of the two truths demonstrate sustainable transmutation. Use his life and Nalas's office discussion to anchor positive/neutral/harmful particle doctrine and balanced tuelinh structure.""",
    21: """C021 flow lock:
Mind Dharma. Strong split: mortal Nalas sleeps in a modern bright capital/city night with streetlights and roads outside, while his tuelinh leaves the body and returns to heavenly homeland. The Earth body wears glasses and sleeps naturally. Heaven stays Western sacred with divine Father Nalas teaching mature tuelinhs about dharma within dharma, dharma outside dharma, dharma unites dharma, and dharma denies dharma. Do not turn heavenly teaching into an Earth classroom.""",
    22: """C022 flow lock:
Information entanglement. Weekend body-soul-wisdom therapy course in a modern classroom; students arrive early; an older mother waits quietly in the teacher's office; a student makes tea for Nalas. Key human question: why her mentally ill child is normal in class but abnormal at home. Focus on devoted mother, family environment, sincere love, positive environments, relatives helping patients, and information changing nature in different environments.""",
    23: """C023 flow lock:
Destructive power of decaying tuelinh. Pandemic-era memory, second year of a terrible epidemic near New Year, with deaths and economic collapse. Modern Covid/post-Covid Vietnam, not old rooms. Show social/moral examples as compassionate consequence scenes: family suffering, impure love, prostitution/adultery, hunting/fishing cruelty, corrupt professions, harmful teachers, arrogant students. Use heaven/Giac/Chap only when the excerpt reaches rescue/rebuilding humanity.""",
    24: """C024 flow lock:
Unified Tao of the Universe. Modern class about four forms of human life. Student asks difference between Tao of the universe and transforming the yin-yang embryo into an energy filter. Use concrete examples of family Tao, social Tao, national Tao, and teacher-student Tao: father/mother/son/daughter, spouses, siblings, community, nation, and classroom practice. Keep doctrine anchored in human forms.""",
    25: """C025 flow lock:
Destroying Toxins in Learners. Open with Nalas's tuelinh returning to heaven to speak with two male messengers about toxins; then move to modern healing course/classroom. Students with illness, mental illness, and suffering share experiences. Focus on the learner role, laziness/arrogance/hurting teachers and classmates, frozen toxin clusters, group practice, forgiveness, gratitude, and uniting with Nalas to squeeze out toxins. No horror staging.""",
    26: """C026 flow lock:
Eliminating toxins in wisdom spreaders. After a short rest and cup of tea, modern classroom continues from learner toxins to wisdom-spreader toxins. Show teacher with tea and students after intense inner conflict. Human examples: religious conflict/slander, school teachers abusing scores or power, harmful liberation teachings, spells/method sellers. Inner images of Buddha/God/devil are toxin-movie imagery in the mind, not true deities. End with body-wisdom-soul practice and helping friends.""",
    27: """C027 flow lock:
Destroying toxins of meditation and worship rituals. Modern weekly classroom, quiet students, teacher asks about experiences breaking toxic ice in learner and wisdom-spreader groups. Key student reports nearly twenty years of demon/ancestor possession phenomena. Teaching explains why meditation/worship rituals do not complete enlightenment and can relate to harmful ritual teachers, animal killing, sudden death, reincarnation with possession/mental illness. Tone is compassionate and healing, not horror.""",
    28: """C028 flow lock:
Eliminating toxins as a national leader. Modern therapy classroom; Nalas enters, students report strong reactions and improved illness, then hot tea before teaching. Key student: depressed male with fear/anxiety/fast heartbeat/medication history and repeated dreams of being a general ordering killings. Show leader toxins as civic consequence scenes: arrogance, exploiting people, unfair taxes, disaster/epidemic profiteering, oppression, hatred, invasion. No graphic war spectacle.""",
    29: """C029 flow lock:
Destroying toxins as citizens for the nation. After lunch break, same modern classroom; silence when Nalas enters, first cup of tea, student reports breathing difficulty/headache/fear/sweating from leader toxin practice. Focus on citizen role: leader is not master, every leader is also a citizen, law/rights/obligations, work/study, poverty, deception, theft, prohibited trade, social unity. Avoid generic flags or patriotic poster imagery.""",
    30: """C030 flow lock:
Eliminate toxins in love between men and women. Serious modern classroom discussion, not romance poster. Student asks about same-sex love in different countries/religions; Nalas explains through smallest particles, family model, male/female yin-yang simulation. Human examples include betrayal, fear, mental illness, loss of self-control, coercive/exploitative behavior, suicide pressure, and teaching young people genuine love. Adult, clothed, non-explicit, compassionate.""",
    31: """C031 flow lock:
Destroying toxins in the spouse relationship. Sunday afternoon continuation. Opening Q&A about gender reassignment and positive-energy practice, treated respectfully. Key woman shares gambling-addicted husband, debts, parents paying debts, children, divorce pressure. Spouse examples include divorce, incompatibility, greed through relatives, bribery via spouse, pressure/compression in marriage. Use modern homes/offices/classroom; compassionate, not melodrama.""",
    32: """C032 flow lock:
Parent-child toxins. Modern classroom and modern family scenes. Nalas asks whether parents may decide children's education/career/future/life; students answer each person has an independent soul. Examples: academic pressure and suicide-note aftermath, abortion from fear/economics, parents failing to educate children, wealthy family property discrimination, children neglecting sick parents. Doctrine: parents as yin-yang embryo, children as smallest particles, mirror of wisdom/toxins. No graphic scenes.""",
    33: """C033 flow lock:
Sibling relationship toxins. Nalas asks students to guess the sibling symbol, then explains synthetic positive/neutral/negative energy particles in tuelinh structure. Show modern classroom plus family/property/competition examples. Buddha/Devadatta is only a restrained historical teaching reference when the excerpt reaches it, not the default setting. Focus on blocked information causing hallucination/depression/anxiety and competition over wealth, land, position, throne, or knowledge.""",
    34: """C034 flow lock:
Employer-employee toxins. Opens with course-comparison Q&A: this body-wisdom-mind healing course is stronger because Nalas researched during a pandemic-year break and transformed smallest-particle knowledge into lectures. Modern Covid/post-Covid classroom with hot tea, LED/tube lights, board/markers. Then social Tao employer/employee roles, cause/effect of boss/employee/rich/poor, mutual benefit, non-exploitation, and healing through two truths.""",
    35: """C035 flow lock:
Researcher and inventor toxins. Nalas reframes suffering as practice material; student says life from birth to sickness/old age/death is harsh; teacher uses high-mountain practice metaphor. Research/invention examples: agriculture/tools/medicine/body-world-space knowledge/enlightened knowledge, and harmful inventions such as poisons, stimulants, weapons, animal-harming methods, destructive products. Modern classroom with restrained lab/tool/notebook details, no sci-fi clutter.""",
    36: """C036 flow lock:
Businessman and producer toxins. Full modern class; students say repeated toxin lessons are valuable because reactions and illnesses decrease. Key beat: student says Nalas is not a businessperson because no tuition; Nalas laughs and explains energy filter as factory, enlightened knowledge as goods, super-energy particles as products, teaching as distribution/technology transfer. Student case: wealth-ritual visions of demons/God/Buddha, redirected toward ethical small business and family care.""",
    37: """C037 flow lock:
Animals and all species. Opening recalls taming animals so their souls may become humans. Key woman: family bought a mountain for stone exploitation, mental health problems, snake/tiger hallucinations, then sold the mountain and changed business. Include animal/tree/rock/soil souls, destroyed mountain habitat, dog-slaughter neighborhood examples, and toxin images as a short film. Keep environmental and compassionate; no graphic slaughter or horror.""",
    38: """C038 flow lock:
Final toxin-removal lecture: treating yourself and others. Opening testimony: woman reports stage III breast cancer markers/bone scan improved, with sharp bone pain from toxin elimination; show unreadable medical papers and hopeful class emotion. Course evidence: cancer and mental illness patients recover, class shares joy, farewell/oath memory, Nalas vows to spread the two truths worldwide after success and no future Vietnam classes. Last lecture covers self/others, not killing self/others, not provoking toxins, children, everyone as teacher, and humble helping.""",
    39: """C039 flow lock:
Cebu City, Philippines frame plus August/October 2018 cosmic memory. Open beside an English-school swimming pool after dinner with Truong and Duong discussing English study and book writing. Then show Nalas's tuelinh leaving the sleeping mortal body to teach young tuelinhs on a vast planet about destructive energy, decay, universe collapse, dual energy filter, and lapis lazuli blue super-energy. Closing milestone: October 12, 2018 dual-filter enlightenment and students seeing lapis lazuli particles while meditating. Keep mortal body with glasses; true Father/tuelinh scenes use Western sacred Jesus-like Father Nalas, no wings.""",
    40: """C040 flow lock:
Modern teacher-office/classroom morning with mentally ill patients and students. Patients feel sleepy/headaches; a woman asks about direct lectures versus social network videos; Nalas explains super-energy transmission, ancestral/source particles, green young-banana-leaf wave-particles, singularity doors, spiral movement, and transformations in heatless/positive/negative heat environments. Keep office/classroom, tea, patients, students, and restrained particle diagrams; not heaven, not pilgrimage.""",
    41: """C041 flow lock:
After lunch break and tea in a modern office/classroom, Nalas teaches destructive energy particles and their intelligence. He draws on a board with a pen: oval brown destructive particle, green intellectual wave-code fibre, three points, vibration/intellect segments. Focus on destructive particles from heatless wave-particles, no rotation/bonding, excess brown heat, positive/negative values, and mental illness/information disorder application. Avoid pure cosmic battle as default.""",
    42: """C042 flow lock:
First day of India/Nepal pilgrimage at Mahabodhi temple and Bodhi tree in Gaya/Bihar under full moon. Real Indian temple grounds, monks/pilgrims/visitors, chanting, moonlight, students sitting around Nalas under the Bodhi tree. Guided inner journey: become smallest particles, witness brown destructive space, green wave-particles, red explosions, first positive/negative particles, repeated appearance/erasure of yin-yang particles. Return to moonlit Bodhi tree. This temple is real-world pilgrimage, not heaven.""",
    43: """C043 flow lock:
Autumn dawn hotel garden near Buddha's enlightenment land, then breakfast and hotel living room with Vietnamese tea utensils. Nalas and students share Vietnamese tea, then bring a whiteboard closer for the lesson. Focus on positive/negative particles from wave-particles, three-part particle structure, internal/external environment, heat as information, and the difficulty of forming yin-yang particles. Hotel garden/living room, tea, and portable board anchor the chapter; not formal classroom or pure abstract space.""",
    44: """C044 flow lock:
Second evening at Mahabodhi temple/Bodhi tree: sunset, temple lights, moonlight, security gate, worship, walking around the tree, pilgrims/monks/Western visitors. After the crowd thins, students gather under the tree for the lesson on miraculous yin-yang energy embryo and Big Bang. Inner journey: colorful particles seek each other; one bright-yellow positive particle and one grey-white negative particle bond, survive destructive attacks, mature into a giant sphere, reveal the first tuelinh, then Big Bang releases particles. Return to Bodhi tree.""",
    45: """C045 flow lock:
Bus from Mahabodhi to ancient Nalanda University ruins in Bihar; bad roads, lunch/rest, red-brick walls/foundations, moss, vast lawns, autumn afternoon, regret for the destroyed Buddhist university. Truong remembers a past life; Duong was his sister; Nalas says he was once king here and used the first tuelinh name to save her. Students meditate/rest on grass, then Nalas teaches particle production of the yin-yang embryo. Keep Nalanda ruins/lawn visible, not a generic class.""",
    46: """C046 flow lock:
Continuation at Nalanda University ruins under large trees and cool autumn breeze. Students are confused after difficult lectures, some pulling grass unconsciously. Nalas guides them to become positive particles inside the universe's yin-yang embryo and observe production stages: embryo, mature embryo, adult tuelinh, pre-Big Bang, yellow/grey-white/fire-red/green/black/blood-red/ivory particles, destructive attacks, first tuelinh selecting particles. Return to fading afternoon and hotel.""",
    47: """C047 flow lock:
Day nine in Nepal: ancient capital where Prince Siddhartha grew up, high brick walls, rice fields, palace foundations, southeast exit; then bus to birthplace relic at sunset with huge house, lake, tall iron pillar, lawn. Students ask about the first tuelinh; Nalas explains production/linking, yin-yang embryo bonding, synthetic particle bonding, marriage example and teacher-student mission example. He identifies first tuelinh as God/Father/Buddha. Keep real Nepal relics unless excerpt moves inward.""",
    48: """C048 flow lock:
Plane from Patna to New Delhi after pilgrimage. Students sleep from exhaustion; Nalas stays awake by the airplane window, then closes eyes and recalls wisdom/past lives. Inner memory shows the central heavenly planet/House of Tuelinhs after Big Bang: divine Father/first tuelinh, crystal caves for baby tuelinhs, gold and precious-stone architecture, calm lapis-lazuli seas/lakes, glowing grass/trees/hills, golden super-energy. End with plane landing New Delhi and students waking. Keep plane-memory frame clear.""",
    49: """C049 flow lock:
New Delhi hotel day before flying back to Vietnam. After breakfast, students choose coffee at hotel coffee bar; Duong brings Nalas hot cocoa; Loi asks him to share pilgrimage wisdom. Hotel living room lecture on current universe: central magical planet, pyramid gemstone, solar systems/galaxies/layers, rotating cosmic sphere, energy beams, fire particles, one universe outside destructive energy, three matter groups, eight particle colors/types, tuelinh babies, souls of rocks/trees/animals, transformation mechanisms. Students rest on sofas afterward.""",
    50: """C050 flow lock:
Final pilgrimage afternoon in a New Delhi hotel living room after lunch, not a Vietnam classroom. Nalas asks students for questions because they are Nalandas who must teach clearly. Student asks about spinning/rotation; Nalas tests whether spinning exists in humans/tuelinhs through happy, sad, neutral emotions. Focus on two spinning forms: physical rotation while moving and internal circulation of information waves. Keep hotel/travel sofas, students, tea/water/notebooks and restrained rotation/particle overlays; do not make it pure space art.""",
    51: """C051 flow lock:
Flight back to Hanoi after pilgrimage. Earth anchor: airplane cabin, runway/airport view, tired students, Nalas with thin glasses closing eyes as plane takes off. He enters tuelinh memory. Cosmic memory: first tuelinh after Big Bang surveys the central magical planet, embryos in crystal rocks, heat from explosion, outer universe with rotating particles/yin-yang embryos, boundary with destructive energy, and heat being consumed. Keep airplane-body frame clear; Father/Jesus-like form only inside memory.""",
    52: """C052 flow lock:
Continues the memory journey while the mortal body sleeps on the flight. First tuelinh builds the universe information transceiver: central-planet pyramid processing center, synthetic particle clusters/stations, neutral-particle wires, negative particles receiving signals, positive particles pushing data, and energy strings connecting suns/galaxies to the central planet. The system is like a giant tuelinh/soul spread through the universe. Closing returns to the airplane one hour before Hanoi landing; sleeping Nalas wears one pair of glasses, no spare glasses.""",
    53: """C053 flow lock:
Modern Hanoi office on a cold autumn morning. Nalas sits on a sofa with hot Vietnamese tea before students unexpectedly arrive with a sad older woman whose mother is gravely ill in hospital. Nalas explains life completion, the mother's soul, devotion, illness, death, and information instead of miracle-cure spectacle. Then he draws the intellectual wave-code fibre on a whiteboard beside the coffee table and teaches Everything Is Information. Keep sofa/tea/whiteboard/students/older woman; no literal heaven unless excerpt leaves office.""",
    54: """C054 flow lock:
Modern Hanoi office after lunch. Students nap in chairs, wash faces, drink tea/water, then gather when a male student asks what first tuelinh did before creating human practice. Heaven-memory beats: baby tuelinhs born from crystal rocks in a giant cave, gold/precious-stone homes and temple, Father teaching, children secretly practicing near destructive energy, many injured/disintegrated, Father suffering and healing survivors, then deciding Earth/human life must be a harsh school. Keep office frame distinct from Western sacred/cosmic memory.""",
    55: """C055 flow lock:
First spring after dual energy filter. Earth setup: cold rainy night, mortal body sleeps after children sleep. Heaven: Nalas returns to private working space on central planet; messenger opens door; golden super-energy particles and magical heart-pulsing pyramid. Pyramid replays congresses and shows Nalas with five eldest male tuelinh children who will incarnate, lead humanity, operate cause/effect tree, and become five messengers. Then past-life montage: forest tribe survivor, soldier avoiding killing, trader, teacher, stay-at-home mother/father, other Tao lives. No female/child messengers or clones.""",
    56: """C056 flow lock:
Heaven lecture to children/tuelinhs. Earth setup only: Nalas returns home early after a tuelinh signal and sleeps after his children. Main scene: Father Nalas sits in his central-planet temple before thousands of tuelinh children. He explains recent human-world therapy teaching, India-pilgrimage knowledge upgrades, two truths, energy particles, intellectual wave-code secrets, and successful transformation of his yin-yang embryo into a dual energy filter. Use stable Jesus-like Father in Western sacred heaven; not an Earth classroom.""",
    57: """C057 flow lock:
Same heavenly temple lecture. A child asks whether speaking ill of harmful people is ignorant wisdom in action. Father answers with the toxin/poisonous-snake metaphor and warns that attacking another person's toxins provokes more toxins. Doctrine: black negative particles with very strong electric waves bond with ivory-white, green, fire-red, or yellow positive particles and corrupt their sustainable information. Keep child/Father dialogue in heavenly temple; no horror snake staging.""",
    58: """C058 flow lock:
Same heavenly temple lecture about ignorant wisdom in spreading false knowledge. Father compares war between countries with creating/spreading false knowledge about origin and mission. Children debate; Father says false knowledge is more poisonous long-term because everything is information and wrong information creates blood-red negative particles with super-strong electric waves. Use restrained lesson visions for war/false teachers/religious or ideological misinformation, but main frame stays heaven with stable Father.""",
    59: """C059 flow lock:
Same heavenly temple lecture. A child asks how Father can save tuelinhs whose wisdom is easily manipulated and rejects true knowledge. Father reassures them he abandons no tuelinh; five messengers, transit planet, and information transmission/reception system support rescue. Solutions: four Tao interaction scenarios force out toxins over lifetimes; accurate-information environments teach origin, mission, and liberation. Human-world suffering/mental illness may appear as soft vision windows only.""",
    60: """C060 flow lock:
Same heavenly temple lesson on sustainable-development intelligence. Children discuss environment changing intelligence and fear human incarnation. Father shows vision windows: poor people who study hard, farmers improving crops, workers/engineers building useful projects, scientists making medicines/vaccines/transport/machines, businesspeople overcoming hardship, and teachers creating useful knowledge. Alternate Father/children temple shots with human-world vignettes inside luminous visions; not a random modern classroom montage.""",
    61: """C061 flow lock:
Same heavenly temple sermon, not Earth. Tuelinh children are excited that many have miraculous embryos and can accompany humans; Father introduces the more miraculous grey-white weak negative plus fire-red very-strong positive embryo that spreads sustainable development values. Use stable Western sacred Jesus-like Father, children/tuelinhs, and restrained non-Chinese particle diagrams.""",
    62: """C062 flow lock:
Closing heavenly sermon before the physical body wakes. Father says the sermon is nearly over because the mortal body is about to wake, then explains the transformation from different wisdom embryos into energy filters by reducing negative waves/toxins and increasing positive particles. Stay in Western sacred heaven unless the excerpt explicitly shows modern mortal Nalas waking with glasses.""",
    63: """C063 flow lock:
Modern Vietnamese winter classroom in freezing rain; the room becomes warm from Nalas's lecture. Key testimony: former restaurant/slaughter family, depression, recovery, stopping animal killing. Teaching moves into animal souls, plants/rocks/soil, wave-particles, destructive energy, yin-yang embryo, and first tuelinh. Anchor with classroom, student testimony, tea, warmth/sweat; no graphic slaughter or standalone space poster.""",
    64: """C064 flow lock:
Modern class on the Tuelinh transformation journey. Students discuss animal souls becoming tuelinhs/humans; Nalas warns against killing animals and destroying forests/mountains/minerals. Cover ignorant ideology/action/false knowledge versus helping life, spreading sustainable values, and solidarity. Use classroom Q&A, board diagrams, and restrained particle-path overlays, not generic mystic posters.""",
    65: """C065 flow lock:
Modern office visit: Duong, Truong Nalanda, and students arrive from provinces with fruit, candies, tea, and questions about healing and the transiting planet. Lesson shows transit-planet resting places, cause-and-effect tree, Return of Tao/Executive/Administrative councils, and five adult male messengers. Hell/prison gates are symbolic particle illusions, no gore, no Chinese bureaucracy.""",
    66: """C066 flow lock:
Modern Vietnamese home near Tet: Nalas waters orchids on the balcony beside kumquat/peach plants, then drinks hot tea with Ms. Phuong, Dzung, Nga, cakes/fruit. Discuss US dorm/campus trapped souls, forensic/autopsy souls following Ms. Phuong, particle copying/bombardment, pain, and overuse of meditation powers. Warm family-like scene with restrained translucent soul-energy, not horror.""",
    67: """C067 flow lock:
Modern office with students and a worn-looking man confused by many religious/spiritual practices: tantra, meditation, pure land, rituals, spirit/demon/ancestor voices, third eye/chakra loss of control. Nalas compassionately explains origin/mission and why rituals/spells/supernatural powers do not create sustainable energy. Buddha/God/devil visions are mental toxin-movie imagery, not true room visitors.""",
    68: """C068 flow lock:
Hot Hanoi summer office/classroom. Truong, Duong, and students bring iced coffee, fruit, and cakes; Nalas drinks coffee despite allergy, sneezes, then clarifies cause and effect as universal transformation, not religious punishment. Inner journey: students become smallest particles guided by shiny yellow Nalas-particle through wave-particles, destructive particles, yin-yang embryo, first tuelinh, galaxies, energy wiring, and baby tuelinhs. Keep coffee/tea/student frame visible.""",
    69: """C069 flow lock:
Modern class on cause and effect for tuelinhs/souls in human practice. First tuelinh designs incarnation milestones, family, marriage, illness, death, and environment into practice plans. Cause-effect system: protected space, giant pyramid twenty times adult height, five adult male messengers working on a plane at the top, stored causal particles, and four Tao rule sets. Alternate classroom and celestial-system views; no female/child messengers or Chinese court styling.""",
    70: """C070 flow lock:
Unified Tao through Family Tao in a modern course memory. Nalas drinks hot tea; students ask how four Tao forms produce particles and unite with the universe. Cover marriage, husband-wife fidelity/conflict/forgiveness, spouse death with or without children, spouse with social status, parent-child, siblings, ancestors/dead family. Use contemporary classroom plus restrained family vignettes; no explicit sexuality, no melodrama, no generic teacher-only repetition.""",
    71: """C071 flow lock:
Unified Tao through Social Tao after the long Family Tao lecture. Modern classroom anchor. Content groups: animals, natural resources, employee-employer/employer-employee, products/livelihood/production, love/social/work relationships, human trafficking rescue/reporting, age/race/religion respect, helping people in danger. Show modern animal protection, environmental protection, ethical workplace, civic rescue, and people helping each other; no graphic violence or propaganda poster.""",
    72: """C072 flow lock:
Unified Tao through National Tao, not generic patriotic poster. Modern classroom with hot tea. Cover head of state/territory/people, leaders/managers, ordinary citizens, laws/obligations/resources. Negative civic vignettes: war, invasion, corruption, epidemic mishandling, poverty, exploitation, nepotism, superstition, destructive policies. Positive vignettes: peace, anti-corruption, disaster response, education, resource protection, unity across ethnicities/religions/countries. No violent spectacle.""",
    73: """C073 flow lock:
Unified Tao through Teacher-Student Tao after National Tao lunch break. Modern class about the power of knowledge. Cover teacher treats student, student treats teacher, students treat each other, and value of knowledge. Show caring teachers, respectful students, peers helping each other, and accurate enlightened knowledge; harmful teaching/abuse/superstition/false knowledge only as restrained lesson vignettes. No sensational abuse imagery.""",
    74: """C074 flow lock:
Journey after human life. Modern office opening: students quietly enter while Nalas sits eyes closed in memory, one refreshes tea. Human case: murdered mother/child and depressed husband influenced by trapped soul, told compassionately with no graphic crime. Teaching: transiting planet, suicide/accident/sudden death/being killed, trapped souls, Executive Council, enlightened preaching versus empty rituals. Use office, subtle death-location soul overlay, and symbolic transit reception; no horror.""",
    75: """C075 flow lock:
Ignorance in ideology: grey negative particles with strong electric waves. Modern technical lecture with excited students after hard particle lessons. Structure is four environments plus five stages: desire, decoding/encoding, ideology, action, causal wave-code fibre. Example is adultery: adult attraction, faithful wife/family positive information, denial, hidden self-satisfaction. Keep adult, non-explicit, restrained; classroom/board and grey overlays anchor the scene.""",
    76: """C076 flow lock:
Ignorance in action: black negative particles with very strong electric waves. Opens with lunch-break students discussing Nalas teaching all day and crowded class. Example is pig slaughter business: a man starts a slaughterhouse, becomes wealthy, denies positive information, and each slaughter creates black particles. Show business/decision/ethical consequence only, no visible killing/gore/slaughter close-ups. Modern classroom plus subdued black-particle overlays.""",
    77: """C077 flow lock:
Ignorance in spreading false knowledge: blood-red negative particles with super-strong electric waves. Modern class after student chatter. Include poisonous-snake/toxin method, false knowledge about origin/mission/practice, superstition/ritual misinformation, and Devadatta-Buddha only when excerpt reaches that historical teaching example. Use lesson windows and blood-red wave-code overlays; no demon horror, attack spectacle, Chinese temple fantasy, or fake religious poster.""",
    78: """C078 flow lock:
Destructive energy detonation method starts from hot tea. Nalas asks how to boil water and brew tea; students mention kettle/pot/fire/electricity/teapot/tea quality/time. Use tea setup as analogy for tools, heat, pressure, body/soul/tuelinh, ideology, action, four Tao forms and two truths. Method steps: negative thoughts after Tao interaction, truth of universe to avoid sinking, truth of enlightenment to create positive thought. No generic cosmic explosion or self-harm imagery.""",
    79: """C079 flow lock:
Practice producing green positive particles. Modern classroom/training room, polished Covid/post-Covid if cues appear. Green particles with strong electric waves, positive particle controls negative particle, five stages, positive/negative environments, origin/mission/liberation thought, causal-tree collection. Use classroom, board, calm practice, concrete helping/development vignettes, and green overlays; avoid pure abstract particle wallpaper or all-green palette.""",
    80: """C080 flow lock:
Practice producing fire-red positive particles. Distinct from C079 by spreading sustainable development values. Students analyze the morning example; Nalas explains desire/action to spread useful values, teaching/research/sharing, five stages, very-strong fire-red waves, causal-tree collection. Modern classroom anchor with warm fire-red overlays and value-spreading vignettes; avoid aggressive flames, war, or red fantasy magic.""",
    81: """C081 flow lock:
Practice producing yellow positive particles: solidarity/unified positive energy. Opening asks why yellow is most valuable. Key metaphor: solid house of ignorance, cool lake, green forest, sun of spreading values, united people on the porch who see inside and share outside truths without entering. Use modern classroom plus clear house/porch/sun/forest/lake visualization, yellow overlays, and causal-tree thread; no flat infographic, flags, or religious symbols.""",
    82: """C082 flow lock:
Energy Filter - Unified Tao culmination. Opening emotion: Nalas and students drink hot tea with happiness and regret after mental-health research course succeeds; he regrets not opening class earlier and leaving Vietnam soon to spread knowledge worldwide. Then explain single energy filter conditions and dual energy filter with shiny yellow and lapis-lazuli blue superparticles. Alternate tea/classroom emotion and refined gold/blue filter visualizations; divine Father only if excerpt truly shifts celestial.""",
    83: """C083 flow lock:
Hymn / Great Mantra Nalas Nalanda. Sacred textless hymn atmosphere, not normal classroom. Show practitioners or tuelinhs uniting with Father Nalas's root power, peace, healing, and return to homeland through golden and sapphire-blue light. Father, if present, is stable Western sacred Jesus-like. Do not render lyrics, readable text, calligraphy, subtitles, scrolls, or occult spell poster.""",
    84: """C084 flow lock:
Symbol of Unified Tao. Use a textless four-wing golden emblem inspired by the word Tao: Family, Social, National, Teacher-Student Tao branches intersect at central mind/soul point. Clockwise/upward/golden for positive, inverted/dim only if excerpt discusses negative, shiny golden upgrade for single filter, outward emblems for superparticles. Avoid readable letters, fake calligraphy, Taijitu, talisman, logo/UI, or flat infographic.""",
    85: """C085 flow lock:
Method of saving trapped tuelinhs/souls to the transiting planet. Trapped souls at death locations due to killing, suicide, accident, disaster, war, epidemic, sudden death. Helper must study Nalas knowledge, stay fearless/compassionate, preach origin/mission/four Tao/suffering/toxins/liberation/transit planet, then chant hymn three times. Show modern place/house/land, calm helper, translucent listening souls, soft path to transit planet; no ghost horror/exorcism/occult/demons.""",
    86: """C086 flow lock:
Mental-health healing regimen summary. Show relatives reading chapters to patients, playing lecture video/audio before/after sleep, repeated daily listening/reading, patient later studying independently and helping others. Modern Vietnamese home/bedroom/living room, books, phone/tablet/speaker, caregiver near patient, calm night/morning routine, ordinary medication context if mentioned. No horror possession, restraints, hospital drama, demon imagery, or instant miracle-cure framing."""
}


VIETNAM_VISUAL_IDENTITY = """Vietnamese visual identity rule:
Use an international modern cinematic/editorial look: premium lensing, controlled natural light, restrained color grade, tactile realism, mature composition. Modernity should come from camera grammar and polish, not from adding modern props unless the excerpt requires them.
Keep the cultural ground clearly Vietnam through faces, body language, warm family/classroom atmosphere, books, tea/coffee, plants, and practical rooms. The pham-tran timeline changes by story stage: early Chapter 8/pre-teaching scenes are poor modern Vietnamese countryside, with low houses, sparse lights, simple electric lighting, cement/tile floors, modest furniture, and a quiet rural night; later teaching/Covid/post-Covid scenes move into cleaner, brighter city classrooms or office-classrooms. Poverty should read as modest present-day rural life, not old dynastic deprivation, oil-lamp nostalgia, or patched costume. If an early frame needs atmosphere, choose a simple village home, lane, yard, or window view with low houses and few lights, not high-rises or a city skyline. In later classroom/lecture/tea/coffee scenes, Vietnam may look cleaner, brighter, more spacious, and better funded: clean teaching rooms, proper tables and chairs, shelves, notebooks, cups of tea or coffee, and organized disciples/students, while keeping a warm Vietnamese human atmosphere. In Covid/pandemic-era and all post-Covid Earth scenes, make the world distinctly modern and polished: LED/tube lighting, office-like tables and chairs, a proper magnetic whiteboard, marker pens, eraser, organized seating, and a serious modern training-room feel. Avoid rural river-delta/water-village nostalgia in modern teaching scenes; if water is unavoidable after the modern shift, use an urban canal/lake/riverfront with concrete paths, streetlights, apartments/townhouses, and city context.
Phase override: C008 is the poor modern countryside / return-to-wisdom phase. C009-C015 are early teaching and disciple-gathering chapters, so Earth scenes default to cleaner rented classrooms or supported learning rooms unless the local excerpt is a flashback. C016+ is the Covid/post-Covid modern office-classroom era.
International travel override: when the excerpt names Cebu/Philippines, India, Nepal, Bihar, Gaya, Mahabodhi, Bodhi tree, Nalanda University, New Delhi, Patna, airport, plane, bus, hotel, relic, ruins, or pilgrimage, follow that named real-world place literally while keeping Nalas as the same Vietnamese pham-tran teacher with thin glasses and modern travel clothes.
World split rule:
- Pham tran / Earth / ordinary life: clearly Vietnamese, grounded, modern-cinematic, humble, no Jesus/church/angel styling, no halo or luminous ring/crown/corona above any human head.
- Thien duong / thien gioi / heaven / dream / tuelinh / cosmic memory / golden spiritual space: show Cha Nalas Nalanda in his stable divine Father manifestation, a Western sacred / traditional Christian Sacred-Heart Jesus heavenly form rather than the pham-tran Vietnamese teacher. Use Renaissance/Baroque-inspired heaven, white-gold clouds, cathedral-like depth, marble/ivory/gold atmosphere, Jesus-like compassion, saintly calm, angelic or light-messenger presence when supported by the excerpt. His heavenly identity must be stable and close to the canonical heaven-Father reference: one fixed traditional Jesus-like portrait in every lane, apparent age 40-42, center-parted shoulder-length wavy dark chestnut-brown hair, full neat brown beard and moustache, warm olive/light-tan Mediterranean/Semitic features, pure white flowing robe, no wings, inner warm golden light, outer sapphire-blue/lucy-blue cosmic aura, golden particles and blue cosmic energy particles, sacred-heart style gentle inner radiance, and calm compassionate Jesus-like authority. No other male tuelinh, attendant, or messenger should share this full signature; surrounding male figures should mostly be short-haired or clean-shaven/light-stubble, with lower glow, distinct robe accents, and no Sacred Heart / glowing heart icon / heart-shaped chest light / radiant chest emblem. Do not make him elderly, grey-haired, white-bearded, clean-shaven, youthful, baby-faced, short-haired, youthful 30s actor-Jesus, 45+ old Father, model-like fantasy handsome, or visually identical to Giac/Chap.
If Giac and Chap appear in heaven, they may be Western celestial messengers, angels, saint-like figures, or subtle light presences. If they appear in Earth teaching scenes, keep them ordinary and Vietnamese.
Children in heaven may sit, play, or learn in a Western heavenly garden or cloud-lit sacred space; do not stage them in a Chinese fantasy temple academy.
Dragon vision rule:
When the excerpt mentions the jade-green dragon or a dragon vision, make it a major dream-vision event, not a tiny snake. Show a huge jade-green celestial dragon with a large head lower in the frame, tail rising up toward the sky, a long powerful body bending in six visible sweeping curves, and large long whiskers/beard flowing through the air. Keep it sacred and Vietnamese/Lac Viet dreamlike rather than imperial Chinese palace style: no pearl-chasing pose, no Chinese pagoda/palace, no red lanterns, no xianxia costume, no ornate court setting.
Yin/Yang visual rule:
When the excerpt mentions Yin Yang or a yin-yang energy embryo, avoid a literal Taoist/Taijitu emblem, black-white yin-yang icon, or Chinese philosophical symbol as the main image. Prefer abstract balanced dual forces: interwoven gold-blue light, twin currents, a luminous dual energy filter, or a subtle non-cultural equilibrium sphere grounded in the Vietnamese/Western-heaven scene context.
Avoid Chinese, Japanese, Korean, or generic pan-Asian visual language everywhere: no hanfu, tang suit, Chinese imperial robes, topknots, high hair buns, wuxia, xianxia, Chinese pagoda, Chinese palace garden, Chinese stone temple courtyard, giant circular stone relief, ornate round gate, hanging bells, red lanterns, calligraphy scrolls, kimono, hanbok, samurai, shoji, torii, or k-drama palace styling."""


COMMON_NEGATIVE_PROMPT = (
    "text, letters, subtitles, watermark, logo, fantasy throne, "
    "generic cosmic portal hero pose, Chinese palace, Chinese pagoda, hanfu, tang suit, "
    "wuxia, xianxia, Chinese imperial robes, topknot, high hair bun, Chinese immortal sage, "
    "Chinese ancient scholar, Chinese monk robe, Chinese court official, red lanterns, "
    "calligraphy scrolls, Chinese garden pavilion, Chinese stone temple courtyard, "
    "Chinese fantasy academy, giant circular stone relief, ornate round gate, hanging bells, "
    "Chinese imperial palace dragon, pearl-chasing dragon, Chinese palace-dragon styling, "
    "literal Taoist yin-yang symbol, black-white Taijitu emblem, Chinese philosophical diagram, "
    "Japanese kimono, Korean hanbok, samurai, shoji, torii, k-drama palace, "
    "generic pan-Asian costume, Oriental fantasy, bad anatomy, extra limbs, distorted face, "
    "blurry, low quality, cartoon, anime, horror, gore, demon, modern sci-fi armor, "
    "weapons, chaotic clutter, bare-faced mortal Nalas, mortal Nalas without glasses, "
    "missing eyeglasses on the pham-tran teacher, invisible eyeglasses, bare-looking mortal face, spare eyeglasses beside a visible Nalas, "
    "loose eyeglasses on bed or desk while Nalas is visible, identical Giac and Chap, duplicate angel clones, "
    "messengers with the same face, messengers resembling Father Nalas, white-haired identical messenger men, "
    "thatched hut, mud wall, clay wall, "
    "oil lamp, kerosene lamp, patched clothing, ragged poverty clothes, "
    "ao nau peasant costume, antique tea house, old wooden tea-room classroom, bamboo blinds, "
    "low floor mats, sitting on floor, historical peasant village, medieval interior, "
    "rustic ancient classroom, dark blank old chalkboard, floating market, river-delta tourism postcard, "
    "ancient rural costume drama, scenic travel-poster countryside, wooden sampan as default mood, "
    "East Asian wrap robe, cross-collar hanfu, kimono-like overlapping collar, monk-like wrap robe, "
    "long-haired bearded messenger, Jesus-like messenger, shoulder-length loose hair on messenger, "
    "full beard on messenger, Father-like messenger face, central chest glow on messenger, "
    "messenger holding light at the center of his chest, earthen wall, woven bamboo wall, "
    "straw hut, thatch roof, exposed bamboo rafters, exposed thatch roof, dirt floor, "
    "ancient hut interior, nostalgic oil-lamp hut"
)


CELESTIAL_SCENE_TERMS = re.compile(
    r"\b(dream|dreams|dreamed|heavenly temple|temple in heaven|lake in heaven|tuelinh space|cosmic|"
    r"temple of Nalas Nalanda|golden energy|sparkling golden energy space|spiritual space|"
    r"dragon|memory travel|tour around the universe|throughout the memories|central planet)\b",
    flags=re.I,
)

HEAVEN_SETTING_TERMS = re.compile(
    r"\b(scenery in heaven|heavenly scenery|heavenly garden|heavenly children|"
    r"in heaven there|heaven is still|the scenery in heaven|entered heaven|"
    r"went to heaven|returned to heaven|returns to heaven|heavenly space)\b",
    flags=re.I,
)

HEAVEN_MENTION_ONLY_TERMS = re.compile(
    r"\b(people in heaven|those who live in heaven|someone may be afraid of people in heaven|"
    r"so-called paradise|recognized to have finished.*heaven|not afraid.*heaven)\b",
    flags=re.I | re.S,
)

HEAVEN_LECTURE_TERMS = re.compile(
    r"\b(tuelinh|tuelinhs|mature tuelinhs|yin and yang energy embryos|"
    r"energy filter|my children|Father)\b",
    flags=re.I,
)

MESSENGER_SCENE_TERMS = re.compile(
    r"\b(Giac|Chap|two messengers|five messengers|several messengers|"
    r"the messengers|male messengers|adult men|two adult men)\b",
    flags=re.I,
)

DIVINE_NALAS_PRESENCE_TERMS = re.compile(
    r"\b(Father Nalas|Cha Nalas|my children|twenty-four mature tuelinhs|mature tuelinhs|"
    r"Mind Dharma|teacher's place of work and teaching in heaven|"
    r"You summon|summon twenty-four|when I incarnate|I teach this knowledge|"
    r"Father (?:said|asked|replied|answered|summoned|taught|teaches|lectured|"
    r"explained|showed|waited|sat|stood|appeared|smiled|looked)|"
    r"the teacher (?:said|asked|replied|answered|summoned|taught|teaches|lectured)|"
    r"Nalas Nalanda (?:said|asked|replied|answered|summoned|taught|teaches|lectured|waited))\b",
    flags=re.I,
)

EXPLICIT_EARTH_SETTING_TERMS = re.compile(
    r"\b(streetlights|roads in the city|capital|classroom|students|student|"
    r"office|rented classroom|house to lecture|coffee|cafe|hospital|ward street|"
    r"apartment|townhouse|shopfront|scooters|cars|hotel|airport|plane|flight|bus|"
    r"pilgrimage|relic|ruins|mahobadhi|mahabodhi|bodhi tree|nalanda university|"
    r"cebu|philippines|india|nepal|new delhi|patna|bihar|gaya)\b",
    flags=re.I,
)

INTERNATIONAL_TRAVEL_TERMS = re.compile(
    r"\b(cebu|philippines|english school|swimming pool|india|nepal|bihar|gaya|"
    r"mahabodhi|bodhi tree|nalanda university|new delhi|patna|pilgrimage|"
    r"relic|ruins|ancient capital)\b",
    flags=re.I,
)

INTERNATIONAL_TRAVEL_CHAPTERS = {39, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52}
HEAVEN_FATHER_LECTURE_CHAPTERS = {55, 56, 57, 58, 59, 60, 61, 62}

EARTH_TEACHING_TERMS = re.compile(
    r"\b(human world|human life|classroom|students|student|lecture|lectures|"
    r"sermon|sermons|teacher|teaching|teachings|listening to his teachings|"
    r"rented the classroom|house to lecture|class|classes|disciple|disciples|"
    r"tea|coffee|cafe|study group|learning room)\b",
    flags=re.I,
)

MODERN_TEACHING_STAGE_TERMS = re.compile(
    r"\b(classroom|class|classes|students|student|lecture|lectures|sermon|sermons|"
    r"teacher asked|teacher replied|teacher said|teaching|teachings|disciple|disciples|"
    r"rented the classroom|house to lecture|tea|coffee|cafe|study group|learning room)\b",
    flags=re.I,
)

COVID_STAGE_TERMS = re.compile(
    r"\b(covid\s*-?\s*19|covid|coronavirus|pandemic|lockdown|quarantine|"
    r"social distancing|infected|hazardous virus|deadly pandemic|post-pandemic|"
    r"mental health diseases)\b",
    flags=re.I,
)

EARLY_RURAL_FLASHBACK_TERMS = re.compile(
    r"\b(29 years old|early awakening|first awakened|new-year night|cold rural night|"
    r"poor rural|poor countryside|humble countryside|before he opened classes|"
    r"when he first incarnated|newly incarnated)\b",
    flags=re.I,
)


EARTH_ONLY_NEGATIVE_PROMPT = (
    "Jesus costume, God-Father costume, biblical savior robe, white-robed deity, "
    "church iconography, cathedral, angel wings, halo as costume, saint painting, "
    "Western heaven clouds, divine throne, halo, luminous ring above head, glowing crown "
    "above head, saintly head corona"
)

SLEEP_BODY_TERMS = re.compile(
    r"\b(sleep|sleeping|asleep|fell into a deep sleep|body asleep|sleeping body|"
    r"mortal body.*asleep|human body.*asleep|form body.*asleep)\b",
    flags=re.I | re.S,
)

SLEEP_BODY_LOGIC_RULE = (
    "Sleeping-body realism rule: if the mortal body is asleep, stage him in a natural "
    "sleeping pose, not a symbolic ritual pose. Prefer lying on his side or back with "
    "one arm relaxed near the pillow or under the blanket, both shoulders comfortable, "
    "breathing naturally. Do not place a hand pressed over the glowing heart/chest unless "
    "the excerpt explicitly says he wakes or consciously touches his chest. The sleeping "
    "mortal Nalas must still wear his thin metal eyeglasses on his face, because the glasses "
    "are part of his locked pham-tran identity. Do not remove the glasses for sleep. Never "
    "show duplicate eyeglasses or a spare pair on the bed/table/desk. Avoid impossible neck, "
    "wrist, shoulder, or blanket "
    "geometry; the pose must look like someone could actually sleep that way."
)

VISIBLE_MORTAL_BODY_TERMS = re.compile(
    r"\b(sleeping body|sleeping mortal body|sleeping human body|sleeping earthly body|"
    r"body asleep|body was asleep|body fell asleep|fell into a deep sleep|deep sleep|"
    r"when he sleeps|starting to go to sleep|fall into a deep sleep|waking body|"
    r"waking him up|woke up|sat up|couldn't sleep|on Earth|journey on Earth|"
    r"Earth body|body is 29 years old|body was 29 years old|29 years old|"
    r"getting married|married and has children|wife|friends and relatives|"
    r"middle of the house|inside the house|glass windows|moonlight|courtyard|yard|"
    r"opened the door|stepped out|walked to the garden|left side of the house|"
    r"staring intently at him|looking at him|ran straight into the house|closed the door|"
    r"look through the window|standing in front of them|step out and approach|"
    r"rooster crowed|meet that person|lead him to meet a woman|woman has spiritual abilities|"
    r"old man came to his house|older man|older woman came to him|went to meet the woman)\b",
    flags=re.I | re.S,
)

INTERNAL_FATHER_ONLY_TERMS = re.compile(
    r"\b(awaken Father|awaken the connection between father and his body|"
    r"father and his body|father in his body|father within him|"
    r"awakened the father in his body|body general)\b",
    flags=re.I,
)

C008_VISIBLE_DIVINE_FATHER_TERMS = re.compile(
    r"\b(temple of Nalas Nalanda|lake in heaven|returning to visit your homeland|"
    r"sparkling golden energy space|tour around the universe|re-visiting the memories|"
    r"Giac immediately said to him.*Fathe\s*r|qualified to transform.*Fathe\s*r|"
    r"greeted,\s*[\"“]?Fathe\s*r|he come to visit)\b",
    flags=re.I | re.S,
)


def frame_is_celestial(excerpt, anchor):
    text = f"{excerpt}\n{anchor}"
    if CELESTIAL_SCENE_TERMS.search(text) or HEAVEN_SETTING_TERMS.search(text):
        return True
    if HEAVEN_LECTURE_TERMS.search(text) and not EXPLICIT_EARTH_SETTING_TERMS.search(text):
        return True
    if (
        MESSENGER_SCENE_TERMS.search(text)
        and not EXPLICIT_EARTH_SETTING_TERMS.search(text)
        and not MODERN_TEACHING_STAGE_TERMS.search(text)
    ):
        return True
    if EARTH_TEACHING_TERMS.search(text):
        return False
    if HEAVEN_MENTION_ONLY_TERMS.search(text):
        return False
    return False


def frame_forced_celestial(chapter_number, lane_index, side):
    """Chapter 21 is a heaven-temple lecture after the opening sleep transition."""
    try:
        chapter_number = int(chapter_number)
        lane_index = int(lane_index or 0)
    except (TypeError, ValueError):
        return False
    return chapter_number == 21 and (lane_index >= 3 or (lane_index == 2 and side == "end"))


def frame_needs_pham_tran_reference(excerpt, anchor, force_celestial=False):
    text = f"{excerpt}\n{anchor}"
    if not (force_celestial or frame_is_celestial(excerpt, anchor)):
        return True
    return bool(VISIBLE_MORTAL_BODY_TERMS.search(text))


def frame_needs_divine_nalas_reference(excerpt, anchor, chapter_number, force_celestial=False):
    if force_celestial:
        return True
    return frame_has_divine_nalas_presence(excerpt, anchor, chapter_number)


def frame_has_divine_nalas_presence(excerpt, anchor, chapter_number):
    text = f"{excerpt}\n{anchor}"
    if not frame_is_celestial(excerpt, anchor):
        return False
    try:
        chapter_int = int(chapter_number)
    except (TypeError, ValueError):
        chapter_int = None
    if chapter_int == 8 and C008_VISIBLE_DIVINE_FATHER_TERMS.search(text):
        return True
    if INTERNAL_FATHER_ONLY_TERMS.search(text) and not re.search(
        r"\b(Father (?:said|asked|replied|answered|taught|teaches|lectured|"
        r"appeared|sat|stood|showed|summoned)|Father Nalas|Cha Nalas|my children|"
        r"temple in heaven|lake in heaven|returned to heaven|teacher's place of work and teaching in heaven)\b",
        text,
        flags=re.I,
    ):
        return False
    if chapter_int == 8 and re.search(
        r"\b(two messengers|Giac|Chap|five messengers|adult men|two adult men|"
        r"dragon|old man|older man|old woman|older woman|went into his dream|go into his dream)\b",
        text,
        flags=re.I,
    ) and not re.search(
        r"\b(Father (?:said|asked|replied|answered|taught|teaches|lectured|"
        r"appeared|sat|stood|showed|summoned)|Father Nalas|Cha Nalas|my children|"
        r"temple in heaven|lake in heaven|teacher's place of work and teaching in heaven)\b",
        text,
        flags=re.I,
    ):
        return False
    if chapter_int in HEAVEN_FATHER_LECTURE_CHAPTERS:
        earth_only_setup = re.search(
            r"\b(works at the office|returned home early|returned home earlier|"
            r"children had gone to bed|body fell asleep|fell asleep early|"
            r"deep sleep|mortal body|human body|form body)\b",
            excerpt,
            flags=re.I,
        )
        heaven_presence = re.search(
            r"\b(returned to heaven|sat in his temple|temple on the central planet|"
            r"private working space|pyramid|Father|my children|children in heaven|"
            r"five eldest|five messengers|tuelinh children|tuelinhs)\b",
            excerpt,
            flags=re.I,
        )
        if not earth_only_setup or heaven_presence:
            return True
    if int(chapter_number) == 21 and re.search(
        r"\b(temple|tuelinh|tuelinhs|Mind Dharma|mature tuelinhs|my children|"
        r"single energy filter|dual energy filter|yin and yang energy embryo)\b",
        text,
        flags=re.I,
    ):
        return True
    if DIVINE_NALAS_PRESENCE_TERMS.search(text):
        return True
    if frame_needs_pham_tran_reference(excerpt, anchor) and re.search(
        r"\b(mortal body|human body|form body|sleeping body|body asleep|sleeping on Earth)\b",
        text,
        flags=re.I,
    ):
        return False
    return False


def chapter_is_modern_era(chapter_number):
    return int(chapter_number) >= MODERN_ERA_START_CHAPTER


def chapter_is_early_teaching(chapter_number):
    return EARLY_TEACHING_START_CHAPTER <= int(chapter_number) < MODERN_ERA_START_CHAPTER


def chapter_is_international_travel(chapter_number):
    try:
        return int(chapter_number) in INTERNATIONAL_TRAVEL_CHAPTERS
    except (TypeError, ValueError):
        return False


def frame_visual_mode_note(excerpt, anchor, chapter_number):
    text = f"{excerpt}\n{anchor}"
    if frame_is_celestial(excerpt, anchor):
        has_divine_nalas = frame_has_divine_nalas_presence(excerpt, anchor, chapter_number)
        if INTERNATIONAL_TRAVEL_TERMS.search(text) or chapter_is_international_travel(chapter_number):
            mortal_room = (
                "If the sleeping, waking, or traveling mortal body appears, keep the Earth layer "
                "in the literal international travel/pilgrimage setting named by the excerpt: "
                "Cebu/Philippines English-school pool, India/Nepal pilgrimage bus, Mahabodhi/Bodhi "
                "tree, Nalanda University red-brick ruins, Nepal relic, New Delhi hotel, airport, "
                "or airplane cabin. Nalas remains the same Vietnamese pham-tran teacher wearing "
                "thin glasses and modern travel/teaching clothes. Do not convert the Earth layer "
                "into a Vietnamese classroom or city street."
            )
        elif chapter_is_modern_era(chapter_number):
            mortal_room = (
                "If the sleeping or waking mortal body appears, keep that body in the modern "
                "Vietnamese era: around Covid, Nalas is about 32-35, neat and formal, and the room "
                "should use modern lighting, tiled/painted interiors, desks/chairs, whiteboard, and "
                "office-classroom furniture in a normal city district rather than oil-lamp poverty, "
                "countryside, or rural river scenery."
            )
        elif chapter_is_early_teaching(chapter_number):
            mortal_room = (
                "If the sleeping or waking mortal body appears, keep that body in the early teaching "
                "period: a clean rented classroom, modest learning room, or ordinary Vietnamese room "
                "connected to classes and disciples, with notebooks, tea, shelves, improved electric "
                "lighting, proper tables/chairs when natural, and no return to the poor pre-teaching "
                "countryside unless the excerpt explicitly says flashback."
            )
        else:
            mortal_room = (
                "If the sleeping or waking mortal body appears, keep that body and its room "
                "clearly Vietnamese and in the correct early phase: poor modern countryside/village "
                "home, sparse night lights, simple electric lighting, cement/tile floor, modest furniture, "
                "and no high-rise city view. Keep Nalas modern, clean, and wearing glasses; do not make "
                "him an old scholar, monk, or costume-drama peasant."
            )
        if has_divine_nalas:
            note = (
                "This lane includes a heaven/dream/spiritual layer where Cha Nalas Nalanda is "
                "present or teaching. Use Western sacred/celestial visual grammar for that layer. "
                "In heaven, the primary Nalas figure is Cha Nalas Nalanda in divine Father form, "
                "a stable traditional Chua/Sacred-Heart-Jesus heavenly manifestation: one fixed "
                "traditional Jesus-like portrait every time, apparent age 40-42, fatherly rather than boyish or elderly, "
                "center-parted shoulder-length wavy dark chestnut-brown hair, full neat brown beard "
                "and moustache, warm olive/light-tan Mediterranean/Semitic features, pure white "
                "flowing robe, no wings, inner warm golden light, outer sapphire-blue/lucy-blue "
                "cosmic aura, golden particles and blue cosmic energy particles, and "
                "open-handed compassionate authority. Keep him close to the attached heaven-Father "
                "canonical reference and readable immediately as traditional Jesus-inspired "
                "sacred Father imagery. Make all other male tuelinhs or attendants clearly less central and visually distinct, without the full Jesus-like hair+beard+robe+heart signature; default them to shorter hair or clean-shaven/light-stubble faces with lower glow. Do not make him elderly, grey-haired, white-bearded, "
                "clean-shaven, younger/boyish, baby-faced, short-haired, youthful 30s actor-Jesus, 45+ older Father, 50s/60s old Father, modern actor/model-like fantasy handsome, or visually identical to Giac/Chap. Do not make the main heavenly figure the "
                "short-haired Vietnamese pham-tran teacher in a shirt. Use white-gold heavenly "
                f"clouds, cathedral-like depth, Renaissance/Baroque sacred calm, angels or light messengers when suitable. {mortal_room}"
            )
        else:
            note = (
                "This lane includes a heaven/dream/spiritual layer, but the excerpt does not "
                "clearly make Cha Nalas Nalanda's divine Father body the main visible figure. "
                "Use Western sacred/celestial grammar for Giac, Chap, tuelinhs, light messengers, "
                "or the heavenly environment, but do not invent a large Jesus-like Nalas poster "
                "unless the local excerpt shows him present or teaching in heaven. If the sleeping "
                "or waking mortal body appears, keep that Vietnamese mortal body as the emotional "
                f"anchor. {mortal_room}"
            )
        if re.search(r"\bdragon\b", f"{excerpt}\n{anchor}", flags=re.I):
            note += (
                " The dragon is a key Chapter 8 dream event: render it as a huge jade-green sacred "
                "dragon, not a tiny snake. Its large head is low near the ground looking at Nalas, "
                "its tail rises upward toward the sky, its body bends into six visible sweeping "
                "sections, and its long whiskers/beard curl with strange breath. Keep it dreamlike "
                "and sacred, without Chinese palace, pagoda, red lantern, pearl-chasing, or xianxia styling."
            )
        return note
    if INTERNATIONAL_TRAVEL_TERMS.search(text) or chapter_is_international_travel(chapter_number):
        return (
            "This lane is pham tran / Earth / real-world international travel or pilgrimage unless "
            "the local excerpt explicitly moves into heaven, dream, tuelinh, or cosmic memory. Keep "
            "the named setting literal: Cebu/Philippines English-school pool, India/Nepal pilgrimage "
            "bus or relic, Mahabodhi temple and Bodhi tree, ancient Nalanda University red-brick ruins, "
            "Nepal birthplace/capital relic, New Delhi hotel/airport, or airplane cabin. Nalas remains "
            "the Vietnamese mortal teacher with thin glasses and modern travel/teaching clothes. Do not "
            "use Jesus, church, angel, cathedral, halo, Western heavenly imagery, Vietnamese city-classroom "
            "default, or Chinese temple fantasy in these Earth travel scenes."
        )
    return (
        "This lane is pham tran / Earth / ordinary life unless the local excerpt explicitly "
        "moves into heaven or dream. Keep it Vietnamese, grounded, and modern-cinematic; do not "
        "use Jesus, church, angel, cathedral, halo, or Western heavenly imagery in Earth scenes. "
        "If the excerpt only mentions heaven, paradise, or spirits inside a thought, complaint, "
        "memory, or spoken idea, keep the image in the mortal Vietnamese setting and show only "
        "human emotion, not heavenly figures. If Giac or Chap only observe an Earth classroom, "
        "lecture, healing, or human-world teaching scene, do not show Jesus, angels, cathedral "
        "clouds, or heaven above the room; keep the scene pham tran Vietnam."
    )


def frame_messenger_identity_note(excerpt, anchor):
    text = f"{excerpt}\n{anchor}"
    if not MESSENGER_SCENE_TERMS.search(text):
        return "No special messenger identity lock needed unless Giac, Chap, or the five messengers are visible."
    note = (
        "Messenger identity lock for this exact frame: every true messenger shown here must read "
        "as a mature adult man. Giac and Chap are two different male messengers, not one man and "
        "one woman, not children, not elderly duplicates unless the excerpt explicitly says a "
        "temporary old-man or old-woman disguise, and not Father Nalas clones. Keep Giac leaner, "
        "gold-white, analytical, and precise; keep Chap warmer, rose-gold/amber, softer, and "
        "protective. Their true celestial clothes should read as Western sacred early-Christian "
        "or Greco-Roman-inspired simple tunics/mantles with role-colored accents, not East Asian "
        "wrap robes, cross-collar hanfu, kimono-like collars, monk robes, or court-sage costumes. "
        "Keep messenger hair short or tied back, clean-shaven or light stubble at most; no full "
        "Jesus beard, no shoulder-length loose hair, no Father-like face, and no bright glow "
        "centered on the chest. "
        "If five messengers appear, show five distinct adult male roles with separate "
        "faces, aura colors, postures, and markers. Do not give any messenger the Father's full "
        "Jesus-like hair+beard+ivory robe+radiant-heart signature."
    )
    if re.search(r"\b(two adult men|adult men|two men)\b", text, flags=re.I):
        note += (
            " This beat specifically asks for two adult men; do not soften it into a couple, "
            "a male/female pair, siblings, children, girls, or vague spirits."
        )
    if re.search(r"\b(old man|older man|old woman|older woman)\b", text, flags=re.I):
        note += (
            " The old-man/old-woman figures are temporary disguise beats only. Use them only "
            "because the local excerpt says so; do not apply old-woman form to the earlier true "
            "two-male-messenger scenes."
        )
    return note


def frame_sleep_body_note(excerpt, anchor, chapter_story_guide="", lane_index=0):
    if SLEEP_BODY_TERMS.search(f"{excerpt}\n{anchor}"):
        return SLEEP_BODY_LOGIC_RULE
    if int(lane_index or 0) <= 2 and re.search(
        r"\b(sleeping mortal body|sleeping body|fell into deep sleep|fell into a deep sleep|deep sleep)\b",
        chapter_story_guide,
        flags=re.I,
    ):
        return SLEEP_BODY_LOGIC_RULE
    return "No sleeping body logic needed unless the local excerpt shows someone asleep."


def frame_earth_stage_note(excerpt, anchor, chapter_number):
    text = f"{excerpt}\n{anchor}"
    if frame_is_celestial(excerpt, anchor):
        if INTERNATIONAL_TRAVEL_TERMS.search(text) or chapter_is_international_travel(chapter_number):
            return (
                "Earth stage note: if the mortal body or real-world layer appears inside this "
                "celestial/memory lane, keep it in the literal international travel setting named "
                "by the excerpt: Cebu/Philippines, India/Nepal pilgrimage, Mahabodhi/Bodhi tree, "
                "Nalanda University ruins, Nepal relic, New Delhi hotel/airport, or airplane cabin. "
                "Keep Nalas as the approved Vietnamese pham-tran teacher with thin glasses and modern "
                "travel clothes. Do not force the Earth layer into Vietnam, a generic classroom, or old "
                "countryside styling."
            )
        if chapter_is_modern_era(chapter_number):
            return (
                "Earth stage note: if the sleeping or waking mortal body appears inside this "
                "celestial lane, use the post-Covid modern-era pham-tran identity: the same "
                "approved Vietnamese Nalas, but older than chapter 8, about 32-35 during Covid "
                "and gradually older afterward. The Earth room/body layer should look modern "
                "Vietnamese, urban, and contemporary, not the early oil-lamp/rural/countryside look."
            )
        if chapter_is_early_teaching(chapter_number):
            return (
                "Earth stage note: if the sleeping or waking mortal body appears inside this celestial "
                "lane, place that body in the early teaching phase: a clean Vietnamese learning room, "
                "rented classroom, or practical room connected to classes and disciples. Use notebooks, "
                "tea, shelves, improved electric lighting, and proper tables/chairs when natural. Do not "
                "force the mortal body back into the poor Chapter 8 countryside unless the local excerpt "
                "explicitly says flashback or early awakening."
            )
        return (
            "Earth stage note: if the sleeping or waking mortal body appears inside this celestial "
            "lane, keep that body in the approved Vietnamese pham-tran identity; otherwise do not "
            "force the Earth classroom setting into true heaven/dream imagery."
            )
    if COVID_STAGE_TERMS.search(text):
        return (
            "Earth stage note: this is the Covid/pandemic-era teaching or public-health period. "
            "Keep the same approved mortal Nalas face/body, but make the Earth setting clearly "
            "modern 2020 Vietnam. At this Covid point Nalas is about 32-35 years old: a mid-30s "
            "Vietnamese teacher with calm compassion, learned presence, tidy short dark hair, thin "
            "glasses, and a similar body to the approved pham-tran reference; do not make him "
            "elderly, 45+, grey-haired, or frail. Dress him more formally: white button-down shirt "
            "or light dress shirt, optionally a dark blazer, clean and lịch sự. Use a modern "
            "Vietnamese office-classroom or training room with LED ceiling panels or fluorescent "
            "tube lights, office-style desks and chairs, a proper magnetic whiteboard or whiteboard "
            "on wheels, visible marker pens and eraser, organized notebooks, bookshelves, tea/coffee, "
            "and students seated like a serious modern class. The whiteboard may be clean or have "
            "simple non-readable marker strokes/diagrams; avoid fake legible text. Use masks or "
            "sanitizer only if the excerpt supports infection/lockdown context. Avoid hospital drama "
            "unless the excerpt is medical; avoid sci-fi lab, corporate luxury, hotel styling, old "
            "wooden tea room, rustic poverty, countryside riverbank, village canal, temple fantasy, "
            "or ancient classroom."
        )
    if INTERNATIONAL_TRAVEL_TERMS.search(text) or chapter_is_international_travel(chapter_number):
        return (
            "Earth stage note: this excerpt is real-world international travel/pilgrimage. Follow "
            "the named place literally instead of the generic C016+ Vietnam baseline: Cebu/Philippines "
            "English-school pool, India/Nepal pilgrimage roads and buses, Mahabodhi temple/Bodhi tree, "
            "Nalanda University red-brick ruins, Nepal ancient-capital or birthplace relic with lake/"
            "iron pillar, New Delhi hotel/airport, or airplane cabin. Nalas remains the same approved "
            "Vietnamese mortal teacher with thin metal glasses, modern clean travel/teaching clothes, "
            "and compassionate scholarly presence. Avoid Vietnamese city classroom defaults, old rural "
            "poverty rooms, Chinese temple fantasy, and pure heaven styling unless the excerpt explicitly "
            "enters heaven or cosmic memory."
        )
    if chapter_is_modern_era(chapter_number):
        age_note = (
            "Nalas is about 32-35 during the Covid chapter; in later chapters he should feel "
            "progressively more mature and established, never like the 29-year-old awakening body. "
            "For the Covid chapter, keep him mid-30s, calm, compassionate, learned, and physically "
            "similar to the approved reference; do not make him elderly, 45+, grey-haired, or frail."
            if int(chapter_number) == MODERN_ERA_START_CHAPTER
            else (
                "Nalas is now after the Covid-era shift, older and more established than the "
                "32-35 Covid stage while preserving the same approved face/body continuity."
            )
        )
        return (
            "Earth stage note: this chapter is in the post-Covid modern era. "
            f"{age_note} Default Earth/pham-tran scenes to a modern Vietnamese world: electric "
            "lighting, LED panels or fluorescent tube lights, proper desks and chairs, whiteboard "
            "or magnetic board when teaching, marker pens, shelves, organized notebooks, tea or "
            "coffee, paved streets, city alleys, shopfronts, streetlights, scooters/cars when natural, "
            "and contemporary daily objects. The default outdoor frame should be an ordinary "
            "Vietnamese ward/district, not a scenic village. For generic emotional scenes, choose "
            "a city home, apartment room, paved ward alley, shopfront, office-classroom, or training "
            "room rather than a beautiful rural landscape. Avoid reverting to oil lamps, floor "
            "mats, low tables, bamboo blinds, antique tea rooms, patched clothes, poor rural hut "
            "staging, countryside rivers, muddy canals, rice fields, fishing boats, riverside "
            "villages, rural lotus ponds, floating markets, river-delta nostalgia, rural water "
            "villages, or mien que song nuoc. If water must appear, it must be "
            "urban infrastructure: concrete canal, city lake, or riverfront promenade with railings, "
            "streetlights, apartment/townhouse background, and visible modern city context."
        )
    if MODERN_TEACHING_STAGE_TERMS.search(text):
        return (
            "Earth stage note: this is the later teaching/classroom period. Keep the same approved "
            "mortal Nalas face/body, but the setting should be clean, bright, modern, and khang trang: "
            "a Vietnamese teaching room with proper tables/chairs, shelves, books, notebooks, tea or "
            "coffee cups, potted plants, organized students/disciples, and improved electric lighting. "
            "Use a whiteboard or magnetic board when a board is natural. Do not use a rustic tea house, "
            "low floor table, oil-lamp room, corporate-office luxury, hotel styling, temple fantasy, "
            "or ancient Chinese classroom."
        )
    if chapter_is_early_teaching(chapter_number):
        return (
            "Earth stage note: this chapter belongs to the early teaching period after Nalas has "
            "begun classes and gathered students. Even if the excerpt is reflective or doctrinal, "
            "default the pham-tran setting to a clean rented classroom, modest but supported learning "
            "room, student discussion space, or practical Vietnamese teaching room with proper "
            "tables/chairs, notebooks, shelves, tea, improved electric lighting, and organized "
            "disciples/students. Do not revert to poor countryside, river-village scenery, floor mats, "
            "oil lamps, ancient rooms, or old-scholar styling unless the local excerpt explicitly "
            "says flashback, past life, old village, or early awakening. For Chapter 15, past-life "
            "flashbacks may be ancient South Asian/princely/ascetic only when the excerpt says so; "
            "present-class scenes stay modern early-teaching."
        )
    return (
        "Earth stage note: this is the pre-teaching or ordinary mortal period unless the excerpt "
        "clearly shows a later class/lecture/tea/coffee setting. Place it in a poor but present-day "
        "Vietnamese countryside/village setting around 2014-2019: low modest houses, quiet yard, "
        "simple rural lane, sparse night lights, electric bulb or fluorescent tube light, fan when natural, "
        "cement or plain tile floor, worn plaster or brick walls, simple wooden bed/table/chairs, books, "
        "notebooks, and ordinary objects. Nalas should look modern and clean, wearing thin glasses, "
        "a clean T-shirt, polo, or casual shirt with simple trousers. Do not use high-rise buildings, "
        "city skyline, apartment towers, busy traffic, polished city interior, luxury room, thầy đồ styling, "
        "monk robe, Chinese scholar robe, oil-lamp nostalgia, patched clothing, or historical-drama clothing."
    )


def mortal_age_negative_prompt(chapter_number):
    chapter_number = int(chapter_number)
    if chapter_number == 8:
        return (
            ", age drift on mortal Nalas, different age between start and end, different Nalas face, "
            "older Chapter 8 mortal Nalas, elderly Chapter 8 Nalas, middle-aged Chapter 8 teacher, "
            "40-year-old Chapter 8 Nalas, 45-year-old Chapter 8 Nalas, grey hair on Chapter 8 Nalas, "
            "deep wrinkles on Chapter 8 Nalas, receding hairline on Chapter 8 Nalas, frail older Nalas, "
            "baby-faced Chapter 8 Nalas, teenage-looking Nalas, college-boy Nalas, slim young actor Nalas, "
            "K-drama youthful Nalas, narrow-faced youthful Nalas, thin-necked model Nalas, "
            "handsome unrelated younger man replacing Nalas"
        )
    if chapter_number == MODERN_ERA_START_CHAPTER:
        return (
            ", age drift on mortal Nalas, different age between start and end, different Nalas face, "
            "elderly Covid Nalas, 45-year-old Covid Nalas, 50-year-old Covid Nalas, grey-haired Covid Nalas, "
            "frail Covid Nalas, teenage-looking Covid Nalas, college-boy Covid Nalas, unrelated younger man replacing Nalas"
        )
    return (
        ", age drift on mortal Nalas, different age between start and end, different Nalas face, "
        "unrelated younger man replacing Nalas, unrelated older man replacing Nalas"
    )


def frame_negative_prompt(excerpt, anchor, chapter_number, force_celestial=False):
    sleep_negative = ""
    if SLEEP_BODY_TERMS.search(f"{excerpt}\n{anchor}"):
        sleep_negative = (
            ", duplicate eyeglasses, eyeglasses both on face and on bed, second pair of glasses, "
            "sleeping Nalas without glasses, removed glasses while sleeping, loose glasses on bedside table, "
            "hand pressed over heart while sleeping, symbolic hand-on-chest sleeping pose, "
            "impossible sleeping posture, twisted sleeping wrist, twisted sleeping shoulder"
        )
    if force_celestial or frame_is_celestial(excerpt, anchor):
        celestial_common = COMMON_NEGATIVE_PROMPT
        for allowed in [
            "Jesus costume, God-Father costume, ",
            "white-robed savior pose, church iconography, angel wings, ",
        ]:
            celestial_common = celestial_common.replace(allowed, "")
        celestial_identity_negative = (
            ", elderly God-Father Nalas, old Father Nalas, grandfather Father Nalas, grey-haired Father Nalas, "
            "white-bearded Father Nalas, long white beard, clean-shaven divine Father, "
            "teenage Father Nalas, boyish Father Nalas, youthful angelic Father, baby-faced Father Nalas, "
            "handsome young savior Father, young Jesus-looking actor, modern actor Jesus, model-like fantasy Father, "
            "25-year-old Father Nalas, 30-year-old Father Nalas, 35-year-old youthful Father Nalas, "
            "mid-30s Father Nalas, 45-year-old older Father Nalas, 50-year-old Father Nalas, 60-year-old Father Nalas, "
            "short-haired heavenly Father Nalas, mortal Vietnamese teacher as heavenly Father, "
            "Father Nalas changing age, Father Nalas with different face in the same chapter, "
            "young version of Father Nalas, old version of Father Nalas, off-reference Father face, "
            "generic angel replacing Father Nalas, Father Nalas not resembling the canonical reference, "
            "messenger replacing Father Nalas, messenger with Father Nalas face, messenger with identical Jesus-like beard, "
            "multiple Jesus-like Fathers, duplicate Father Nalas, attendants with Father Nalas face, "
            "male tuelinhs with same shoulder-length brown hair and full beard as Father Nalas, "
            "second bearded long-haired Jesus-like man, Jesus-like attendant clone, radiant-heart attendant, "
            "Sacred Heart on messenger, Sacred Heart on attendant, glowing heart on Giac, glowing heart on Chap, "
            "heart-shaped chest light on messenger, radiant chest emblem on attendant, multiple sacred hearts in one frame, "
            "wings on Father Nalas, angel wings on Father Nalas, dark tone on Father Nalas, aggressive face, "
            "evil expression, horror-like Father Nalas, distorted Father face"
        )
        return f"{celestial_common}{celestial_identity_negative}{sleep_negative}{mortal_age_negative_prompt(chapter_number)}"
    return f"{COMMON_NEGATIVE_PROMPT}, {EARTH_ONLY_NEGATIVE_PROMPT}{sleep_negative}{mortal_age_negative_prompt(chapter_number)}"


def chapter_flow_note(chapter_number):
    if int(chapter_number) == 8:
        return C008_STORY_FLOW_LOCK
    if int(chapter_number) in EARLY_TEACHING_FLOW_LOCKS:
        return EARLY_TEACHING_FLOW_LOCKS[int(chapter_number)]
    if int(chapter_number) in MODERN_CHAPTER_FLOW_LOCKS:
        return MODERN_CHAPTER_FLOW_LOCKS[int(chapter_number)]
    return (
        "Chapter flow rule: read this chapter's story guide before batching. Each lane should follow "
        "the local excerpt and the chapter's actual sequence of people, places, transformations, "
        "and turning points. Do not flatten the chapter into generic teacher portraits, generic "
        "heaven posters, or repeated emotional desk scenes."
    )


def read_ch8_anchor_sections():
    if not CH8_PROMPT_DNA_PATH.exists():
        return "", ""
    text = CH8_PROMPT_DNA_PATH.read_text(encoding="utf-8", errors="replace")
    start_match = re.search(
        r"##\s*2\..*?START IMAGE PROMPT.*?(?=##\s*3\.)",
        text,
        flags=re.I | re.S,
    )
    end_match = re.search(
        r"##\s*3\..*?END IMAGE PROMPT.*",
        text,
        flags=re.I | re.S,
    )
    start_anchor = start_match.group(0).strip() if start_match else ""
    end_anchor = end_match.group(0).strip() if end_match else ""
    return start_anchor, end_anchor


def split_manifest_chapter(chapter):
    image_count = int(chapter["target_image_count"])
    if image_count % 2:
        image_count += 1
    pair_count = max(1, image_count // 2)
    return pair_count, pair_count * 2


def read_chapter_brief(chapter_number):
    brief_path = BRIEF_DIR / f"C{chapter_number:03d}.md"
    if not brief_path.exists():
        raise RuntimeError(f"Missing chapter visual brief: {brief_path}")
    return brief_path.read_text(encoding="utf-8").strip()


def read_chapter_story_guide(chapter_number):
    guide_path = STORY_GUIDE_DIR / f"C{chapter_number:03d}.md"
    if not guide_path.exists():
        raise RuntimeError(
            f"Missing chapter story guide: {guide_path}. Build/read a story guide before batching "
            "this chapter so the images do not collapse into generic repeated classroom/heaven scenes."
        )
    return guide_path.read_text(encoding="utf-8").strip()


def lane_frame_prompt(chapter, lane_index, lane_count, side, excerpt, dna, chapter_brief, chapter_story_guide, anchor):
    phase = "START" if side == "start" else "END"
    force_celestial = frame_forced_celestial(chapter["chapter"], lane_index, side)
    is_celestial = force_celestial or frame_is_celestial(excerpt, anchor)
    has_divine_nalas = force_celestial or frame_has_divine_nalas_presence(excerpt, anchor, chapter["chapter"])
    if side == "start":
        motion_note = (
            "Compose the beginning of this lane: the scene is entering the story beat, "
            "with unresolved energy and clear room for transformation."
        )
    else:
        motion_note = (
            "Compose the ending of this lane: the same story beat has advanced, "
            "with a visible emotional or cosmic change from the start frame."
        )
    if is_celestial and has_divine_nalas:
        identity_note = (
            "Default to the literal excerpt. This frame is in heaven/dream/tuelinh/celestial "
            "space, so show Cha Nalas Nalanda through his divine Father manifestation, not "
            "through the pham-tran Vietnamese teacher body. Only show the mortal human body if "
            "the excerpt explicitly shows it sleeping, waking, or lying on Earth."
        )
        pair_identity = (
            "Keep Cha Nalas Nalanda's divine Father identity, sacred white-gold heavenly setting, "
            "traditional Jesus-like compassion, emotional state, lighting language, camera grammar, and world "
            "style consistent with the paired frame. His divine Father face must remain stable: "
            "one fixed traditional Jesus-like portrait, apparent age 40-42, center-parted shoulder-length "
            "dark chestnut-brown hair, neat brown beard and moustache, luminous ivory-white robe, "
            "radiant inner light, and close resemblance to the attached "
            "heaven-Father canonical reference; never switch him between young "
            "messenger, mortal teacher, and elderly white-bearded God-Father. If a mortal Earth body appears, keep it "
            "separate and secondary."
        )
    elif is_celestial:
        identity_note = (
            "Default to the literal excerpt. This frame includes heaven/dream/tuelinh/celestial "
            "space, but Cha Nalas Nalanda's divine Father body is not necessarily the main visible "
            "figure. Use Western sacred heavenly grammar for Giac, Chap, tuelinhs, light messengers, "
            "or the spiritual environment. If the excerpt shows only the sleeping/waking mortal body "
            "on Earth, keep that Vietnamese pham-tran body as the visual anchor and do not invent a "
            "large Jesus-like Nalas figure."
        )
        pair_identity = (
            "Keep the split heaven/Earth language consistent with the paired frame: sacred white-gold "
            "heavenly light for the spiritual layer, and a modern Vietnamese mortal room/body layer "
            "when the excerpt shows the human form. Do not change the main subject between frames."
        )
    else:
        identity_note = (
            "Default to the literal excerpt. If the excerpt is on Earth or inside ordinary life, "
            "show Nalas Nalanda through his mortal human form body, not as a revealed cosmic deity. "
            "Use dream, heaven, temple, tuelinh, dragon, aura, or cosmic-energy imagery only when "
            "the excerpt explicitly says the scene is a dream/heaven/spiritual memory/cosmic space."
        )
        pair_identity = (
            "Keep Nalas Nalanda's human identity, face, age stage, clothing family, emotional state, "
            "setting, lighting language, camera grammar, and world style consistent with the paired frame."
        )
    anchor_block = f"\nProvided chapter anchor prompt:\n{anchor}\n" if anchor else ""
    return f"""Create one standalone cinematic 16:9 {phase} image for an audiobook video lane.

Book chapter: Chapter {chapter['chapter']} - {chapter['title']}
Video duration for this chapter: {chapter['duration_minutes']} minutes.
Lane: {lane_index} of {lane_count}.
Frame in pair: {phase}.

Character and world DNA, with mandatory fidelity rule:
{dna}
{identity_note}

{PHAM_TRAN_CHARACTER_DNA}

{PHAM_TRAN_GLASSES_RULE}

{PHAM_TRAN_AGE_CONTINUITY_LOCK}

{DIVINE_NALAS_CHARACTER_DNA}

{FIVE_MESSENGERS_DNA}

{EARTH_STAGE_RULE}

{PHAM_TRAN_PHASE_TIMELINE}

{EARLY_RURAL_MATERIAL_LOCK}

{STORY_FOCUS_PRIORITY_RULE}

{VIETNAM_VISUAL_IDENTITY}

Current frame world mode:
{frame_visual_mode_note(excerpt, anchor, chapter['chapter']) if not force_celestial else "C021 heaven-temple override: this frame remains in the heavenly temple / Father teaching Mind Dharma unless the excerpt explicitly shows the sleeping Earth body. Use stable divine Father Nalas in traditional Chua/Sacred-Heart-Jesus form: one fixed traditional Jesus-like portrait every time, apparent age 40-42, fatherly rather than boyish or elderly, center-parted shoulder-length wavy dark chestnut-brown hair, full neat brown beard and moustache, warm olive/light-tan Mediterranean/Semitic features, pure white flowing robe, no wings, inner warm golden light, outer sapphire-blue/lucy-blue cosmic aura, golden particles and blue cosmic energy particles, sacred-heart style gentle inner radiance, and calm compassionate authority. Keep him close to the attached heaven-Father canonical reference and readable immediately as traditional Jesus-inspired sacred Father imagery. Keep him distinct from Giac, Chap, and mature tuelinhs; only Father may have the full Jesus-like hair+beard+ivory robe+radiant heart signature. Other male tuelinhs must have different faces, lower glow, shorter or tied-back hair, clean-shaven/light-stubble faces, distinct robe accents, and no Sacred Heart / glowing heart icon / heart-shaped chest light / radiant chest emblem; no second long-haired full-bearded Jesus-like man. Do not make him young/clean-shaven, baby-faced, model-like youthful, youthful 30s actor-Jesus, 45+ old Father, modern-actor handsome, 50s/60s old, winged, dark, aggressive, evil, horror-like, or elderly white-bearded. Do not turn it into a modern Vietnamese classroom merely because Father mentions human-world practice."}

Current messenger identity logic:
{frame_messenger_identity_note(excerpt, anchor)}

Current body/action logic:
{frame_sleep_body_note(excerpt, anchor, chapter_story_guide, lane_index)}

Current pham-tran timeline stage:
{frame_earth_stage_note(excerpt, anchor, chapter['chapter']) if not force_celestial else "No pham-tran classroom stage for this frame unless the sleeping/waking Earth body is explicitly visible. Keep any Earth reference as a small vision/orb or distant explanation, while the main scene stays in heaven."}

Chapter-specific visual brief:
{chapter_brief}

Chapter-specific story guide, mandatory:
{chapter_story_guide}

Chapter flow lock:
{chapter_flow_note(chapter['chapter'])}
{anchor_block}
Story beat excerpt to visualize:
{excerpt}

Pair continuity:
This image is part of a start/end pair for one video lane. {pair_identity} {motion_note}

Visual direction:
Transform the exact excerpt into cinematic spiritual realism for a premium book/audiobook plate. Make the image emotionally clear and concrete using only the people, setting, action, and spiritual layer supported by this lane's excerpt and chapter brief. Do not pull imagery from another chapter or another part of the chapter. Do not render written words from the excerpt. No subtitles, no labels, no watermark, no logo. Avoid collage, panels, split-screen, UI, and poster layouts.

Negative prompt:
{frame_negative_prompt(excerpt, anchor, chapter['chapter'], force_celestial=force_celestial)}."""


def prepare_chapter_lane_pairs(manifest, chapter_number, pairs_per_batch):
    dna = read_dna_for_chapter(chapter_number)
    chapter_brief = read_chapter_brief(chapter_number)
    chapter_story_guide = read_chapter_story_guide(chapter_number)
    ch8_start_anchor, ch8_end_anchor = read_ch8_anchor_sections()
    chapter = next(item for item in manifest["chapters"] if item["chapter"] == chapter_number)
    text = Path(chapter["text_path"]).read_text(encoding="utf-8")
    pair_count, target_image_count = split_manifest_chapter(chapter)
    segments = excerpt_segments(text, target_image_count)

    prompt_dir = PAIR_PROMPT_DIR / f"C{chapter_number:03d}"
    output_dir = PAIR_IMAGE_DIR / f"C{chapter_number:03d}"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    lanes = []
    items = []
    for lane_index in range(1, pair_count + 1):
        start_excerpt = segments[(lane_index - 1) * 2]
        end_excerpt = segments[(lane_index - 1) * 2 + 1]
        start_anchor = ch8_start_anchor if chapter_number == 8 and lane_index == 1 else ""
        end_anchor = ch8_end_anchor if chapter_number == 8 and lane_index == pair_count else ""
        lane_items = []
        for side, excerpt, anchor in [
            ("start", start_excerpt, start_anchor),
            ("end", end_excerpt, end_anchor),
        ]:
            filename = f"C{chapter_number:03d}_lane_{lane_index:03d}_{side}.png"
            item = {
                "chapter": chapter_number,
                "lane_index": lane_index,
                "side": side,
                "filename": filename,
                "target": str(output_dir / filename),
                "use_pham_tran_ref": frame_needs_pham_tran_reference(
                    excerpt,
                    anchor,
                    frame_forced_celestial(chapter_number, lane_index, side),
                ),
                "use_divine_nalas_ref": frame_needs_divine_nalas_reference(
                    excerpt,
                    anchor,
                    chapter_number,
                    frame_forced_celestial(chapter_number, lane_index, side),
                ),
                "prompt": lane_frame_prompt(
                    chapter,
                    lane_index,
                    pair_count,
                    side,
                    excerpt,
                    dna,
                    chapter_brief,
                    chapter_story_guide,
                    anchor,
                ),
            }
            lane_items.append(item)
            items.append(item)
        lanes.append(
            {
                "lane_index": lane_index,
                "start_target": lane_items[0]["target"],
                "end_target": lane_items[1]["target"],
                "items": lane_items,
            }
        )

    batches = []
    for start in range(0, len(lanes), pairs_per_batch):
        batch_no = len(batches) + 1
        batch_lanes = lanes[start : start + pairs_per_batch]
        batch_items = [item for lane in batch_lanes for item in lane["items"]]
        prompt_path = prompt_dir / f"C{chapter_number:03d}_lane_batch_{batch_no:03d}.txt"
        output_stem = output_dir / f"_lane_batch_{batch_no:03d}.png"
        lines = [
            f"Generate {len(batch_items)} separate standalone cinematic 16:9 images.",
            "The images are arranged as start/end pairs for audiobook video lanes.",
            "Do not create a collage, grid, poster, contact sheet, or multi-panel image.",
            "Each requested image must be a separate image output in exactly the order listed.",
            "",
        ]
        for lane in batch_lanes:
            for item in lane["items"]:
                label = item["side"].upper()
                lines.append(f"Lane {lane['lane_index']:03d} {label} image:")
                lines.append(item["prompt"])
                lines.append("")
        atomic_write_text(prompt_path, "\n".join(lines).strip() + "\n")
        batches.append(
            {
                "batch": batch_no,
                "prompt_file": str(prompt_path),
                "output_stem": str(output_stem),
                "targets": [item["target"] for item in batch_items],
                "lanes": [lane["lane_index"] for lane in batch_lanes],
                "items": [
                    {
                        "lane_index": item["lane_index"],
                        "side": item["side"],
                        "target": item["target"],
                        "use_pham_tran_ref": item["use_pham_tran_ref"],
                        "use_divine_nalas_ref": item["use_divine_nalas_ref"],
                    }
                    for item in batch_items
                ],
                "use_pham_tran_ref": any(item["use_pham_tran_ref"] for item in batch_items),
                "use_divine_nalas_ref": any(item["use_divine_nalas_ref"] for item in batch_items),
            }
        )

    chapter_plan = {
        **chapter,
        "prompt_dir": str(prompt_dir),
        "output_dir": str(output_dir),
        "target_lane_count": pair_count,
        "target_pair_count": pair_count,
        "target_image_count": target_image_count,
        "pairs_per_batch": pairs_per_batch,
        "lanes": lanes,
        "items": items,
        "batches": batches,
    }
    atomic_write_text(
        prompt_dir / "chapter_lane_pair_plan.json",
        json.dumps(chapter_plan, ensure_ascii=False, indent=2),
    )
    log(
        f"prepared C{chapter_number:03d} with {pair_count} lane pairs, "
        f"{target_image_count} images, {len(batches)} pair batches"
    )
    return chapter_plan


def write_pair_manifest(manifest, pairs_per_batch):
    chapters = []
    total_lanes = 0
    total_images = 0
    for chapter in manifest["chapters"]:
        pair_count, image_count = split_manifest_chapter(chapter)
        total_lanes += pair_count
        total_images += image_count
        chapters.append(
            {
                "chapter": chapter["chapter"],
                "duration_minutes": chapter["duration_minutes"],
                "target_lane_count": pair_count,
                "target_pair_count": pair_count,
                "target_image_count": image_count,
                "pairs_per_batch": pairs_per_batch,
                "prompt_dir": str(PAIR_PROMPT_DIR / f"C{chapter['chapter']:03d}"),
                "output_dir": str(PAIR_IMAGE_DIR / f"C{chapter['chapter']:03d}"),
            }
        )
    pair_manifest = {
        "chapter_range": manifest.get("chapter_range", [8, 86]),
        "images_per_minute": manifest["images_per_minute"],
        "pairs_per_minute": manifest["images_per_minute"] / 2,
        "pairs_per_batch": pairs_per_batch,
        "total_minutes": manifest["total_minutes"],
        "total_lane_pairs": total_lanes,
        "total_target_images": total_images,
        "chapters": chapters,
    }
    atomic_write_text(PAIR_MANIFEST_PATH, json.dumps(pair_manifest, ensure_ascii=False, indent=2))
    return pair_manifest


def run_pair_batches(chapter_plan, start_batch, limit_batches, model, timeout, wait_on_rate_limit, force):
    selected = [batch for batch in chapter_plan["batches"] if batch["batch"] >= start_batch]
    if limit_batches:
        selected = selected[:limit_batches]
    for batch in selected:
        targets = [Path(path) for path in batch["targets"]]
        if not force and all(path.exists() for path in targets):
            log(f"C{chapter_plan['chapter']:03d} lane batch {batch['batch']:03d}: skip existing")
            continue
        command = [
            "node",
            str(CODEX_IMAGEN),
            "--json",
            "--model",
            model,
            "--timeout",
            str(timeout),
            "--retries",
            "4",
            "--output",
            batch["output_stem"],
            "--prompt-file",
            batch["prompt_file"],
        ]
        if CANONICAL_PHAM_TRAN_REF.exists() and batch.get("use_pham_tran_ref", True):
            command.extend(["--input-ref", str(CANONICAL_PHAM_TRAN_REF), "--image-detail", "high"])
        if CANONICAL_HEAVEN_FATHER_REF.exists() and batch.get("use_divine_nalas_ref", False):
            command.extend(["--input-ref", str(CANONICAL_HEAVEN_FATHER_REF), "--image-detail", "high"])
        attempt = 1
        while True:
            log(f"C{chapter_plan['chapter']:03d} lane batch {batch['batch']:03d}: start attempt {attempt}")
            completed = subprocess.run(
                command,
                cwd=str(ROOT),
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            stdout_log = LOG_DIR / f"C{chapter_plan['chapter']:03d}_lane_batch_{batch['batch']:03d}.stdout.log"
            stderr_log = LOG_DIR / f"C{chapter_plan['chapter']:03d}_lane_batch_{batch['batch']:03d}.stderr.log"
            stdout_log.write_text(completed.stdout, encoding="utf-8")
            stderr_log.write_text(completed.stderr, encoding="utf-8")
            if completed.returncode == 0:
                break
            rate = parse_rate_limit(completed.stderr)
            if wait_on_rate_limit and rate:
                wait_seconds, reset_at = rate
                log(
                    f"C{chapter_plan['chapter']:03d} lane batch {batch['batch']:03d}: "
                    f"rate limited, wait {wait_seconds}s reset={reset_at}"
                )
                time.sleep(wait_seconds)
                attempt += 1
                continue
            if wait_on_rate_limit and is_transient(completed.stderr):
                wait_seconds = min(900, 60 * attempt)
                log(
                    f"C{chapter_plan['chapter']:03d} lane batch {batch['batch']:03d}: "
                    f"transient failure, wait {wait_seconds}s"
                )
                time.sleep(wait_seconds)
                attempt += 1
                continue
            raise RuntimeError(completed.stderr[-1500:] or completed.stdout[-1500:])

        result = parse_json(completed.stdout)
        images = result.get("images") or []
        if len(images) < len(targets):
            raise RuntimeError(f"Expected {len(targets)} images, got {len(images)}")
        for image, target in zip(images, targets):
            source = Path(image["path"])
            if target.exists() and force:
                target.unlink()
            if target.exists():
                continue
            source.replace(target)
            log(f"C{chapter_plan['chapter']:03d}: saved {target.name}")


def verify_chapter_pairs(chapter_number):
    plan_path = PAIR_PROMPT_DIR / f"C{chapter_number:03d}" / "chapter_lane_pair_plan.json"
    if not plan_path.exists():
        raise RuntimeError(f"Missing pair plan for chapter {chapter_number}")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    starts = 0
    ends = 0
    complete = 0
    missing = []
    for lane in plan["lanes"]:
        start_path = Path(lane["start_target"])
        end_path = Path(lane["end_target"])
        has_start = start_path.exists()
        has_end = end_path.exists()
        starts += 1 if has_start else 0
        ends += 1 if has_end else 0
        complete += 1 if has_start and has_end else 0
        if not (has_start and has_end):
            missing.append(lane["lane_index"])
    status = {
        "chapter": chapter_number,
        "target_lane_pairs": plan["target_lane_count"],
        "target_images": plan["target_image_count"],
        "start_images": starts,
        "end_images": ends,
        "complete_pairs": complete,
        "missing_pair_lanes": missing[:50],
        "missing_pair_lanes_count": len(missing),
    }
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-manifest", action="store_true")
    parser.add_argument("--extract-text", action="store_true")
    parser.add_argument("--prepare-chapter", type=int)
    parser.add_argument("--run-chapter", type=int)
    parser.add_argument("--verify-chapter", type=int)
    parser.add_argument("--pairs-per-batch", type=int, default=2)
    parser.add_argument("--images-per-minute", type=float, default=4.0)
    parser.add_argument("--start-batch", type=int, default=1)
    parser.add_argument("--limit-batches", type=int, default=0)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--wait-on-rate-limit", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.build_manifest:
        manifest = build_manifest(args.images_per_minute)
        pair_manifest = write_pair_manifest(manifest, args.pairs_per_batch)
        log(
            f"pair manifest: {len(pair_manifest['chapters'])} chapters, "
            f"{pair_manifest['total_lane_pairs']} lane pairs, "
            f"{pair_manifest['total_target_images']} images"
        )
    if args.extract_text:
        manifest = load_manifest() if MANIFEST_PATH.exists() else build_manifest(args.images_per_minute)
        extract_chapter_texts(manifest)
    if args.prepare_chapter:
        manifest = load_manifest()
        write_pair_manifest(manifest, args.pairs_per_batch)
        prepare_chapter_lane_pairs(manifest, args.prepare_chapter, args.pairs_per_batch)
    if args.run_chapter:
        manifest = load_manifest()
        chapter_plan_path = PAIR_PROMPT_DIR / f"C{args.run_chapter:03d}" / "chapter_lane_pair_plan.json"
        if chapter_plan_path.exists():
            chapter_plan = json.loads(chapter_plan_path.read_text(encoding="utf-8"))
            if not plan_paths_match_current_root(chapter_plan):
                log(f"C{args.run_chapter:03d}: cached lane plan points outside this repo, regenerating")
                chapter_plan = prepare_chapter_lane_pairs(manifest, args.run_chapter, args.pairs_per_batch)
        else:
            chapter_plan = prepare_chapter_lane_pairs(manifest, args.run_chapter, args.pairs_per_batch)
        run_pair_batches(
            chapter_plan,
            args.start_batch,
            args.limit_batches,
            args.model,
            args.timeout,
            args.wait_on_rate_limit,
            args.force,
        )
    if args.verify_chapter:
        verify_chapter_pairs(args.verify_chapter)


if __name__ == "__main__":
    main()
