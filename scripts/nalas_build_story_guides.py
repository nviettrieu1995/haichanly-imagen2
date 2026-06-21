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
EARLY_TEACHING_START_CHAPTER = 9
MODERN_ERA_START_CHAPTER = 16


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
    if chapter >= MODERN_ERA_START_CHAPTER and "modern_era" not in profiles:
        profiles.append("modern_era")
    return profiles


def chapter_is_early_teaching(chapter):
    return EARLY_TEACHING_START_CHAPTER <= int(chapter) < MODERN_ERA_START_CHAPTER


def profile_rules(chapter, profiles):
    lines = []
    if "covid_or_pandemic" in profiles:
        lines.append(
            "- Covid/pandemic beats must look clearly modern: Nalas about 32-35 during Covid, neat hair, thin glasses, white/light shirt or blazer, LED/tube lights, magnetic whiteboard, marker pens, desks/chairs, shelves, notebooks, tea/coffee, city office-classroom. Do not use huts, oil lamps, floor mats, or old village rooms."
        )
    elif chapter >= MODERN_ERA_START_CHAPTER:
        lines.append(
            "- Earth/pham-tran beats are post-Covid/modern-era by visual baseline: ordinary Vietnamese city districts, apartments, townhouses, offices, training rooms, paved alleys, scooters/cars, LED or fluorescent lights, proper furniture, whiteboard when teaching."
        )
    elif chapter_is_early_teaching(chapter):
        lines.append(
            "- This chapter is after Nalas has begun teaching and gathering students. Do not send Earth scenes back to the poor countryside phase unless the local excerpt explicitly says flashback, past life, old village, or early awakening. Default Earth scenes to an early teaching period: rented classroom, crowded but clean learning room, proper tables/chairs, notebooks, tea, shelves, improved electric lighting, and organized disciples/students. Nalas keeps thin glasses and clean modern clothes such as a neat shirt, polo, or light casual shirt; he is not a thay do, monk, old scholar, ancient peasant, or costume-drama figure."
        )
    else:
        lines.append(
            "- Earth/pham-tran beats before formal teaching are poor modern Vietnamese countryside/village life: Nalas looks modern and clean in T-shirt/polo/casual shirt, always wearing thin glasses, but the setting is modest rural home/yard/lane with sparse lights, low houses, simple electric bulb or fluorescent tube light, cement/tile floor, worn plaster/brick wall, and simple furniture. Do not use city skyline, apartment towers, luxury interiors, thầy đồ styling, monk robes, oil-lamp nostalgia, or historical costume drama. Once the excerpt shows classes/students/disciples/teaching, move to a cleaner, better-supported learning room."
        )
    if "earth_modern_teaching" in profiles:
        lines.append(
            "- Teaching/class/course beats should not all use the same composition. Vary teacher at board, student reaction, desk/table discussion, tea/coffee pause, notebook close-up, office/classroom wide shot, and abstract lesson visualization only when the excerpt supports it."
        )
    if "heaven_or_tuelinh" in profiles:
        lines.append(
            "- Heaven/temple/tuelinh beats use Western sacred heavenly grammar. When Cha Nalas/Father/Teacher is present in heaven, show him as stable divine Father Nalas in traditional Chua/Sacred-Heart-Jesus form: one fixed traditional Jesus-like portrait in every lane, apparent age 40-42, fatherly rather than boyish or elderly, center-parted shoulder-length wavy dark chestnut-brown hair, full neat brown beard and moustache, warm olive/light-tan Mediterranean/Semitic features, pure white flowing robe, no wings, inner warm golden light, outer sapphire-blue/lucy-blue cosmic aura, golden particles and blue cosmic energy particles, sacred-heart style gentle inner radiance, and calm compassionate authority. Keep him close to the heaven-Father canonical reference, immediately readable as familiar sacred Jesus-like imagery, and do not drift into a younger/older face. Only Father may carry the full Jesus-like hair+beard+ivory robe+radiant heart signature; other male tuelinhs/attendants must have distinct faces, lower glow, shorter or tied-back hair, clean-shaven/light-stubble faces, distinct robe accents, and absolutely no Sacred Heart, glowing heart icon, heart-shaped chest light, or radiant chest emblem. Do not make him a young clean-shaven messenger, a baby-faced or model-like youthful savior, a youthful 30s actor-Jesus, a 45+ older Father, a modern-actor Jesus, a short-haired pham-tran teacher, dark/aggressive/evil/horror-like, winged, or an elderly white-bearded God-Father. When the excerpt only mentions a sleeping/waking Earth body, keep the mortal Vietnamese body as the anchor and do not invent a giant divine poster."
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


EARLY_TEACHING_FLOW_LOCKS = {
    9: """Chapter 9 step-by-step lock:
- This is the Four Commandments / Gathering of Humanity chapter, not a generic classroom chapter.
- Opening memory: Giac proudly follows Nalas Nalanda's human work over years; many sick and suffering people recover by studying the two truths, not by magic.
- Earth classroom beat: Nalas prepares to lecture to nearly one hundred students in a rented classroom inside a house. The space is cramped but serious, warm, and alive; Giac blends into the class atmosphere to listen. Show crowd pressure, notebooks, attentive faces, and an early supported classroom, not a poor pre-teaching home.
- Name/explanation beat: Nalas explains the name Nalas Nalanda and the first tuelinh identity to students. Show this as a lecture moment, not a deity poster.
- Heaven/cosmic beats: when the text moves to God/Father creating humans or the four commandments, use Western sacred heaven with stable divine Father Nalas; keep Earth students out unless the excerpt is explicitly classroom.
- Human-world beats: families, parents, spouses, children, society, nation, and teacher-student life are the four forms of practice. Show concrete human scenarios when the excerpt reaches them.
- Avoid repeating the same front-facing teacher image; alternate crowded room, Giac listening, student reactions, family/society/nation examples, and Western sacred Father scenes.""",
    10: """Chapter 10 step-by-step lock:
- This is the Congress of Unifying the Practising Path of the Tuelinhs, not a repeat of Chapter 9.
- Opening classroom: students arrive before Nalas, a previous lecture recording plays, conversations overlap, and Nalas sips hot tea before class. A young student asks why tuelinhs must become humans and why animal souls can incarnate. Make this specific.
- Cosmic memory: Father observes the tuelinh life-form, destructive energy storms, and a yin-yang energy embryo growing into a giant energy sphere before exploding into a mature tuelinh. Use Western sacred/cosmic grammar, not Chinese yin-yang symbols.
- Creation beats: God uses five groups of smallest particles and complex energy structures to create plants, animals, insects, rocks, and ancient trees. Visualize the mechanism clearly instead of generic glowing circles.
- White-powder beat: Father holds a small glass jar containing white powder while tuelinhs stand around him and learn about a habitable human-world environment.
- Closing beat: tuelinhs become enthusiastic to incarnate as humans; the four practice forms are family, society, nation, and teachers/students. Show a real transition toward human practice.""",
    11: """Chapter 11 step-by-step lock:
- This chapter is about Ignorant Wisdom through class reactions, healing, and information/energy response.
- Opening classroom: students are attentive and tearful while Nalas sips hot tea; many have illnesses and suffering, and the room feels like relief after many lifetimes.
- Question beat: students ask why their bodies become warm, hot, sweaty, drowsy, painful, nauseous, or itchy when listening to lectures. Show believable bodies/faces in class, not symbolic statues.
- Teaching mechanism: Nalas explains negative information, positive truthful information, soul/body coldness, warmth, illness, and healing. Use subtle abstract particles around real people only when supported.
- Tea continuity: students bring new cups of hot tea to Nalas's table; he uses tea to concentrate and connect with memory/wisdom.
- Avoid generic miracle imagery; the emphasis is classroom healing reactions, compassion, and explanatory teaching.""",
    12: """Chapter 12 step-by-step lock:
- This chapter is Enlightened Wisdom: standards for distinguishing ignorant and enlightened wisdom.
- Opening lecture: a student asks for clear standards because religions/philosophies confuse people; Nalas answers through the two truths and smallest energy particle knowledge.
- Class rhythm: the lecture is interrupted by questions, Nalas sits beside the table sipping tea, then stands to continue. Vary seated tea, standing lecture, student question, and board/diagram compositions.
- Doctrine beats: enlightened wisdom means understanding information in people, animals, events, phenomena, intelligence, and destructive energy; controlling harmful information and activating positive information.
- Heaven/cosmic references may appear as conceptual visualizations, but Earth classroom excerpts should stay grounded and Vietnamese, with no Jesus/angel overlay unless the text truly enters heaven.
- Keep this chapter clean, intellectual, and classroom-focused, not rural or mystical-poster focused.""",
    13: """Chapter 13 step-by-step lock:
- This chapter is the State of Ignorant Soul through long courses, illness, travel, recovery, and student discipline.
- Opening course beat: one extraordinary class per week, six hours per lecture, seven months total. Students range from children to people over sixty, with many illnesses.
- Travel beat: students come from across the country, by plane, overnight driving, or renting near the classroom. Show arrival, tired families, notebooks, and expectation.
- Second-home beat: students arrive early, talk with classmates, share difficulties, and see the classroom as a second home.
- Teacher care beat: Nalas records illness and recovery information, checks on patients every week, announces results, and grieves failures when students do not follow instructions.
- Do not reduce this to one teacher-at-board image; show the course scale, mixed ages, illness/recovery, travel, family support, and classroom community.""",
    14: """Chapter 14 step-by-step lock:
- This chapter is the State of Enlightened Mind, organized around compassion, delight, and peace.
- Use a clear teaching-room baseline when the excerpt is instructional, with students/notebooks/board when natural.
- Visualize doctrine through restrained overlays only when useful: intellectual wave code fibres, yin-yang root embryo, positive energy controlling negative energy, and the three levels of enlightened mind.
- Compassion beats should show people helping/saving people and animals, possession/non-possession, love/hatred, wisdom/lack of knowledge, success/failure, action/inaction as concrete moral situations.
- Avoid making every frame abstract; alternate classroom explanation, student reflection, human examples, and restrained mechanism visualizations.""",
    15: """Chapter 15 step-by-step lock:
- This chapter begins in the present class: Nalas sips hot tea, students ask about his past lives, and he agrees to share memories to support the lesson on suffering and liberation.
- Present-class scenes remain early teaching period: clean Vietnamese learning room, students, tea, notebooks, thin glasses, modern Nalas.
- Past-life flashback scenes are allowed only when the excerpt moves there: South Asian crown prince, king and queen, wife and children, high-walled capital, temple study, escape southeast, teachers, meditation, asceticism, and the three metal-tool sounds.
- The past-life setting is ancient South Asian/princely/ascetic, not Chinese, not Vietnamese countryside, and not a fantasy martial-arts scene.
- Keep the chapter distinct by alternating present classroom storytelling, past-life palace/capital, escape journey, ascetic suffering, and the lesson about the middle path/liberation."""
}


MODERN_CHAPTER_FLOW_LOCKS = {
    17: """Chapter 17 step-by-step lock:
- This is the Truth of the Universe through smallest energy particle knowledge, not a generic lecture chapter.
- Setting baseline: modern post-Covid Vietnamese class/training room; students arrive early, eager for the next lesson about enlightened knowledge and energy particles.
- Opening focus: students' anticipation and the teacher introducing the truth of the universe as a practical standard, including parent-child misunderstandings and the idea that souls are not property.
- Doctrine focus: smallest positive/negative energy particles create humans, animals, tuelinhs, events, and interactions. Keep visualizations restrained and attached to the classroom explanation.
- Late focus: acquisition of information, interaction with positive/negative environments, internal toxins, suffering, and the struggle of yin/yang particles. Character and setting matter more than microscopic decorative detail.""",
    18: """Chapter 18 step-by-step lock:
- This chapter is the Truth of Enlightenment and correction of misunderstood enlightenment knowledge.
- Setting baseline: modern Vietnamese classroom with serious students who have studied for years; use teacher/student dialogue rather than isolated abstract symbols.
- Opening focus: a student reflects that earlier learners memorized the teacher's words but misunderstood because practice did not match learning.
- Conflict focus: disobedient/proud students return to suffering lessons; the teacher explains enlightenment as knowing origin, nature, humanity, tuelinhs, and liberating suffering by forcing out toxins.
- Doctrine focus: intellectual fibres, vibrational wave code, negative/positive energy particles, destructive vs sustainable transformation. Keep diagrams subtle and non-readable.""",
    19: """Chapter 19 step-by-step lock:
- This chapter begins with a very specific modern atmosphere: cold rain at the autumn-to-winter transition, wet city streets, and Nalas making hot tea in his office after walking through freezing rain.
- Earth setting is a modern teacher's office/classroom, not countryside. Use rain reflections, winter clothing, window light, desk, tea, and a quiet reflective mood.
- Story focus: the teacher reflects on students with illness, then discusses a girl's mental illness, her parents' misunderstanding, medicine suppressing her brain, and information disorder in the soul.
- Relationship focus: the love story and destructive transformation are shown through conversations and human consequences, not sensational imagery.
- Late focus: wrong-body/confused-soul explanations and decay/disintegration causing mental illness. Avoid explicit sexuality or shock imagery; keep it compassionate and clinical.""",
    20: """Chapter 20 step-by-step lock:
- This chapter is the positive counterpart after the cold rain: winter office warmth, hot fragrant tea, and the teacher with two students discussing successful practice.
- Key character: Loi Nalanda, over sixty, symbol of the sustainable transmutation mechanism. Show him as an older Vietnamese man with fulfilled family/business/social/spiritual life when the excerpt reaches him.
- Flashback context: war, poverty, death, business hardship, family life, social relationships, and spreading the two truths. Use restrained human scenes.
- Doctrine focus: positive/neutral/harmful energy particles and sustainable transmutation, but visualized through Nalas's explanation and Loi's life, not generic glowing science posters.
- Closing focus: balanced tuelinh structure that can control destructive energy; character and life evidence should anchor abstract mechanism.""",
    21: """Chapter 21 step-by-step lock:
- This chapter is Mind Dharma and has a clear split: the mortal teacher sleeps in a modern bright capital/city night, while his tuelinh leaves the body and returns to the heavenly homeland.
- Earth body: modern city room at night, streetlights and roads outside, Nalas asleep naturally with glasses on; no duplicate glasses and no rural/countryside room.
- Heaven body: Father Nalas teaches mature tuelinhs in Western sacred heaven with the stable Jesus-like divine Father style.
- Teaching focus: four types of Mind Dharma - dharma within dharma, dharma outside dharma, dharma unites dharma, and dharma denies dharma.
- Closing focus: Mind Dharma as the key to understanding two truths and moving through cosmic space by information values. Do not turn this into a normal classroom unless the excerpt returns to Earth.""",
    22: """Chapter 22 step-by-step lock:
- This chapter begins in the body, soul and wisdom therapy course: a weekend modern classroom, students arrive early, and an older mother waits quietly in the teacher's office.
- Key character: the devoted older woman/mother asking why her mentally ill child can be normal at class but abnormal at home. She should be present when the excerpt reaches that beat.
- Setting baseline: modern class/office, tea made by a student, organized students, serious compassionate atmosphere.
- Doctrine focus: information entanglement and how information changes nature in different environments; show family/patient environment effects through human scenes first.
- Late focus: relatives' sincere love, positive environment, mental illness recovery, and forcing out toxins. Avoid hospital-drama unless the excerpt demands it.""",
    23: """Chapter 23 step-by-step lock:
- This chapter is explicitly the pandemic-era memory: second year of a terrible epidemic, end-of-year/new-year hopes, deaths, economic collapse, and the teacher teaching amid that suffering.
- Setting baseline: modern Covid/pandemic Vietnam, office-classroom/training-room, city/home context, masks/sanitizer only if natural; no rural old-room look.
- Story focus: destructive power of decaying tuelinh shown through moral/social examples - same-sex love example, impure love, prostitution/adultery, hunting/fishing cruelty, corrupt professions, harmful teachers, arrogant students.
- Keep images compassionate and non-sensational: show consequences, loneliness, family suffering, social decay, and teaching explanation rather than explicit or judgmental shock scenes.
- Closing focus: great rescue of tuelinhs, rebuilding humanity, and Giac/Chap excited to accompany Father in the human world; use heaven only when the excerpt reaches Giac/Chap/Father.""",
    24: """Chapter 24 step-by-step lock:
- This chapter is the Unified Tao of the Universe taught in a modern class through the four forms of human life.
- Opening focus: student asks about Tao of the universe and the task of transforming the yin-yang embryo into an energy filter.
- Key human forms: family Tao, social Tao, national Tao, and teacher-student Tao. Show father/mother/son/daughter, spouse relationship, siblings, social interactions, national community, and classroom practice when supported.
- Doctrine focus: four forms encode the conference gathering humanity and create the practice environment for tuelinhs.
- Closing focus: students understand that sufficient quality/quantity of energy particles across all four forms is needed before returning home.""",
    25: """Chapter 25 step-by-step lock:
- This chapter opens before a healing course when the tuelinh within Nalas returns to heaven and chats with two messengers about toxins affecting souls.
- Split correctly: heaven conversation with two male messengers in Western sacred style when the excerpt is heaven; modern classroom when the excerpt enters the healing course.
- Earth course focus: students with illness, mental illness, and suffering share experiences; the teacher begins with the role of learner.
- Toxin focus: learner toxins such as laziness to study, arrogance, harming teachers/classmates, and frozen toxin clusters in negative energy.
- Practice focus: students follow Nalas to unfreeze and squeeze out toxins; show group practice and compassion, not horror/demonic imagery.""",
    26: """Chapter 26 step-by-step lock:
- This chapter continues after a short rest and cup of tea, moving from learner toxins to toxins of wisdom spreaders.
- Setting baseline: modern classroom/training room, teacher with tea, students recovering from intense inner conflict after the previous lesson.
- Role focus: religious leaders, teachers, knowledge spreaders, ritual/spell sellers, school teachers abusing scores/power, and harmful liberation teachings.
- Practice focus: students may see inner mental images of Buddha, God, devil, sweet words, and negative words like a movie in the mind; treat this as inner toxin imagery, not literal true deities.
- Closing focus: students speak to the tuelinh within, connect body-wisdom-soul, remember friends from past lives, and commit to helping others.""",
    27: """Chapter 27 step-by-step lock:
- This chapter is a new weekly lecture after quiet falls in the classroom, following learner and wisdom-spreader toxin lessons.
- Setting baseline: modern classroom with serious students; teacher asks about experiences breaking toxic ice in two interaction groups.
- Student case: a student reports nearly twenty years of demon/ancestor possession phenomena and asks why the knowledge heals mental illness.
- Doctrine focus: meditation and worship rituals do not produce true enlightenment; they can reveal old soul memories but not complete the human practice mission.
- Late focus: harmful ritual teachers, animal killing, sudden death, reincarnation with possession/mental illness, and forgiving harm to animals/others/self. Keep the tone compassionate, not horror."""
}


def custom_chapter_flow_rules(chapter):
    if chapter in EARLY_TEACHING_FLOW_LOCKS:
        return EARLY_TEACHING_FLOW_LOCKS[chapter]
    if chapter in MODERN_CHAPTER_FLOW_LOCKS:
        return MODERN_CHAPTER_FLOW_LOCKS[chapter]
    if chapter != 8:
        return ""
    return """Chapter 8 step-by-step lock:
- C008 is the return-to-wisdom journey, not a generic teacher portrait chapter.
- Opening heaven: Giac and Chap are two mature male messengers, not a male/female pair and not children.
- Early Earth: the 29-year-old mortal Nalas sleeps in a poor peaceful countryside home on a cold early-spring New Year night. He is modern and clean, always wearing thin glasses; the room/village is poor and moc mac, not a city apartment.
- Dream house: he stands inside the house at night, moonlight through glass windows, unsure whether dream or reality.
- Dragon beat: he hears strange breathing, opens the door, steps toward the left garden, and sees a huge jade-green dragon with large head low near the ground, tail up toward the sky, long whiskers/beard, and body curved into six sections. Do not make it a tiny snake.
- Transformation beat: the dragon passes the front door and transforms into two adult men. These are male messengers in human form; do not show one man and one woman here.
- Instruction beat: the two men say time is running out, they cannot teach him, and they will direct him to someone to study.
- Guide/teacher beat: months later he meets the adult male person announced in the dream; that man leads/directs him to a woman teacher with spiritual abilities. Include the male guide and the woman teacher when the excerpt reaches this beat.
- Disguise sequence: before meeting the woman teacher, one messenger appears as an old man in a dream and Nalas does not answer; the next night one messenger appears as an old woman and Nalas still does not answer.
- After meeting the woman teacher, the old man and old woman appear together and repeat that they cannot teach him and he must study with that woman for one year. This pair belongs only to the later step, not to the initial two adult men.
- Study/disappointment beat: he studies, becomes disappointed, burns the notes, and questions heaven/paradise people. Keep this human and grounded.
- Later return-of-wisdom beats: temple, lake in heaven, memory travel, and wisdom transfer may become Western sacred heavenly scenes. Father Nalas in heaven uses the stable Sacred-Heart-Jesus-like canonical form.
- Teaching-many-students beat: only after wisdom begins returning and he teaches many classes should Earth rooms improve into clean, supported classrooms with students."""


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
    custom_flow_text = custom_chapter_flow_rules(chapter)
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
{custom_flow_text}
- Story focus priority: first lock the correct character identity, relationship, chapter phase, and setting; second show the local action/emotion; only then add secondary props, particles, diagrams, or symbolic details when they clarify the beat. Do not overload a frame with every doctrine term.
- Always obey the local lane excerpt first. If the excerpt is a classroom conversation, show that exact class beat. If it is a technical doctrine, visualize it through the named mechanism rather than a generic glowing circle. If it is heaven, temple, tuelinh, Giac, Chap, or Father, use the correct heaven/Earth split.
- Whenever the mortal/pham-tran Nalas or Earth teacher body is visible, keep the approved identity: Vietnamese father-teacher, rounded-square gentle face, solid grounded build, calm scholarly compassion, and thin metal eyeglasses worn on his face. The glasses are mandatory even when he sleeps; do not show a bare-faced mortal Nalas and do not create a spare pair of glasses on a bed/table/desk.
- If Giac, Chap, two messengers, or five messengers appear, keep them role-distinct and non-cloned. All five true messengers are mature men. Giac is insight/discernment: restrained gold-white, slightly older, leaner oval face, high cheekbones, calm analytical gaze, precise still posture, with a small gold-white geometry or clear-light thread near the hands/chest. Chap is compassion/attachment-testing: warmer rose-gold, slightly younger or softer face, warmer eyes, humble protective posture, rose-gold sash or warm rose light held in the palm. If Father Nalas is present, Giac, Chap, and all messengers must have no Sacred Heart, no glowing heart icon, no heart-shaped chest light, and no radiant chest emblem; only Father has chest-heart radiance. The other three messengers, when present, are blue-white order/law with grid/archive/tablet markers, green-gold healing/transformation clearing toxins or carrying clean botanical light, and silver-violet transmission/transit with a gateway/path/arc marker. Do not render Giac and Chap as identical generic angels, identical white-haired men, women, children, or Father Nalas lookalikes. Only show old-woman form when the local excerpt explicitly says a messenger disguises as an old woman.
- Do not use old wooden tea houses, oil lamps, patched peasant clothes, Chinese costume drama, pagodas, hanfu, xianxia, or generic Asian fantasy. Poor countryside is allowed only when the chapter phase requires it, especially early C008; keep it present-day Vietnamese countryside, not historical costume rural nostalgia.
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
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig")) if MANIFEST_PATH.exists() else {"chapters": []}
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
