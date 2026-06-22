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
    if re.search(
        r"\b(cebu|philippines|english school|swimming pool|india|nepal|bihar|gaya|"
        r"mahabodhi|bodhi tree|nalanda university|new delhi|patna|pilgrimage|airport|"
        r"plane|flight|bus|hotel|relic|ruins|ancient capital|crown prince)\b",
        lower,
    ):
        profiles.append("international_travel_or_pilgrimage")
    if re.search(r"\b(classroom|class|students|lecture|course|teacher's office|office|whiteboard|tea|coffee)\b", lower):
        profiles.append("earth_modern_teaching")
    if re.search(r"\b(heaven|heavenly temple|temple in heaven|paradise|tuelinh|tuelinhs|giac|chap)\b", lower):
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
    elif "international_travel_or_pilgrimage" in profiles:
        lines.append(
            "- International travel/pilgrimage beats override the generic Vietnam-modern baseline. Follow the named location literally: Cebu/Philippines English-school pool when stated; India/Nepal pilgrimage buses, hotels, airports, Mahabodhi/Bodhi tree, Nalanda University red-brick ruins, Nepal ancient-capital relics, New Delhi hotel/airport, or airplane cabin when stated. Nalas remains the same pham-tran Vietnamese teacher with thin glasses and modern travel/teaching clothes. Do not convert these scenes into a Vietnamese city classroom or a generic heavenly temple."
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
            "- Heaven/celestial/tuelinh beats use Western sacred heavenly grammar only when the local excerpt truly enters heaven, paradise, tuelinh homeland, dream/cosmic teaching, or a visible spiritual Father scene. Do not convert real-world pilgrimage temples, hotel lectures, office classes, or technical mentions of tuelinh/energy into heaven. When Cha Nalas/Father/Teacher is present in true heaven, show him as stable divine Father Nalas in traditional Chua/Sacred-Heart-Jesus form: one fixed traditional Jesus-like portrait in every lane, apparent age 40-42, fatherly rather than boyish or elderly, center-parted shoulder-length wavy dark chestnut-brown hair, full neat brown beard and moustache, warm olive/light-tan Mediterranean/Semitic features, pure white flowing robe, no wings, inner warm golden light, outer sapphire-blue/lucy-blue cosmic aura, golden particles and blue cosmic energy particles, sacred-heart style gentle inner radiance, and calm compassionate authority. Keep him close to the heaven-Father canonical reference, immediately readable as familiar sacred Jesus-like imagery, and do not drift into a younger/older face. Only Father may carry the full Jesus-like hair+beard+ivory robe+radiant heart signature; other male tuelinhs/attendants must have distinct faces, lower glow, shorter or tied-back hair, clean-shaven/light-stubble faces, distinct robe accents, and absolutely no Sacred Heart, glowing heart icon, heart-shaped chest light, or radiant chest emblem. Do not make him a young clean-shaven messenger, a baby-faced or model-like youthful savior, a youthful 30s actor-Jesus, a 45+ older Father, a modern-actor Jesus, a short-haired pham-tran teacher, dark/aggressive/evil/horror-like, winged, or an elderly white-bearded God-Father. When the excerpt only mentions a sleeping/waking Earth body, keep the mortal Vietnamese body as the anchor and do not invent a giant divine poster."
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
- Late focus: harmful ritual teachers, animal killing, sudden death, reincarnation with possession/mental illness, and forgiving harm to animals/others/self. Keep the tone compassionate, not horror.""",
    28: """Chapter 28 step-by-step lock:
- This chapter is eliminating toxins as a national leader, not a generic healing-class chapter.
- Setting baseline: modern Vietnamese therapy classroom/training room; Nalas enters, students report strong body/soul reactions and improved illness, then he drinks hot tea before teaching.
- Key student case: a depressed male student with fear, anxiety, fast heartbeat, medication history, and repeated dreams of being a general ordering killings. Show him as a present-day student sharing in class; dream/leader images should be restrained memory overlays, not battlefield spectacle.
- National-leader focus: leadership toxins include arrogance, exploiting people, unfair taxes, disaster/epidemic profiteering, oppression, inciting hatred, invasion, and causing soldiers/people to die.
- Closing practice: the student and class face harmful leader-memory information, awaken positive/neutral/negative particles, and use enlightened wisdom to neutralize toxins. Keep it civic, compassionate, and non-graphic.""",
    29: """Chapter 29 step-by-step lock:
- This chapter continues after lunch break from the leader lesson into toxins as citizens of the nation.
- Setting baseline: the same modern classroom after a few hours' break; students become quiet when Nalas enters; he starts after the first cup of tea.
- Opening student case: a student reports difficulty breathing, headache, fear, sweating, and recognizing past-life harm as a leader; this proves that toxin removal can prevent future illness for children and elders.
- Citizen focus: leader is not master of the people; every leader is also a citizen. Show law, rights, obligations, working citizens, families, study, poverty, deception, theft, prohibited trade, and social unity as modern human examples.
- Closing practice: students speak to the tuelinh within, grateful for suffering and the three secrets, determined to squeeze out citizen-role toxins and help everyone/species. Avoid propaganda posters, flags as the only subject, or generic patriotic imagery.""",
    30: """Chapter 30 step-by-step lock:
- This chapter is toxins in love between men and women. Keep it as a serious modern classroom discussion, not romance-poster imagery.
- Opening focus: a student asks about same-sex love in different countries/religions; Nalas answers through smallest energy particles, the family model, and male/female yin-yang simulation.
- Human examples: love betrayal, fear of betrayal, mental illness, loss of self-control, sexual harassment, coercive or exploitative behavior, suicide pressure, and teaching young people about genuine love. Treat these as compassionate consequence scenes, never explicit sexuality or shock images.
- Doctrine focus: man/woman as symbolic positive/negative particle functions, family reproduction, yin-yang embryo movement, toxins absorbing/radiating information, and sustainable vs destructive transformation.
- Closing practice: forgiveness around past-life love harms, building genuine love/family, and neutralizing harmful love information. Keep all figures adult and clothed; no erotic staging.""",
    31: """Chapter 31 step-by-step lock:
- This chapter continues on Sunday afternoon from love toxins into husband-wife/spouse relationship toxins.
- Opening focus: a student asks about gender reassignment and how to practice positive energy after understanding the two truths; show as respectful classroom Q&A, not body spectacle.
- Key case: a Vietnamese woman shares suffering with a gambling-addicted husband, family debt, parents paying debts, pressure raising children, and wanting divorce. She should be visible when the excerpt reaches that story.
- Spouse focus: divorce, incompatibility, ignorance of why people marry, greed through spouse/relatives, bribery via a wife, and pressure/compression in married life. Use modern homes/offices/classroom examples, not melodrama.
- Closing practice: husband and wife learning to understand each other's toxins, preserve family through respect/love, forgive past spouse harms, and build happy married life. Keep tone compassionate and non-judgmental.""",
    32: """Chapter 32 step-by-step lock:
- This chapter is the relationship between parents and children and must show modern family pressure, not only abstract energy diagrams.
- Opening focus: Nalas asks whether parents have the right to decide children's education, career, future, and life; students answer that each person has an independent soul.
- Student examples: academic pressure leading to suicide note, abortion from fear or economics, parents not providing education, wealthy family property discrimination, neglected sick parents, and children hating parents. Show these carefully as aftermath, family tension, or classroom retelling, not graphic scenes.
- Doctrine focus: parents symbolize yin-yang embryo; children symbolize smallest particles born from it. Children can reflect parents' wisdom/toxins like a mirror.
- Closing practice: release painful parent-child memories, awaken particle groups, use love/solidarity and enlightened wisdom to heal the parent-child relationship.""",
    33: """Chapter 33 step-by-step lock:
- This chapter is sibling relationships as a symbol of synthetic energy particles in tuelinh structure.
- Opening focus: Nalas asks students to guess the sibling symbol; students guess yin-yang embryo or tuelinhs, then he explains synthetic positive/neutral/negative energy particles.
- Doctrine focus: neutral particles transmit information, positive particles protect reliable sustainable information, negative particles vibrate signals; blocked information creates hallucination, depression, anxiety, and schizophrenia.
- Human examples: siblings competing for wealth, land, money, positions, throne/power, and even knowledge. The Buddha/Devadatta example appears as a restrained historical/Buddhist teaching reference only when the excerpt reaches it; do not turn the whole chapter into ancient temple fantasy.
- Closing practice: awaken sibling-related particles, let enlightened wisdom re-encode toxins, and release competition. Use modern family scenes and classroom explanation first.""",
    34: """Chapter 34 step-by-step lock:
- This chapter opens with course-comparison Q&A before the employer-employee lesson.
- Opening focus: student asks why this body-wisdom-mind healing course is stronger than previous courses; Nalas explains one pandemic-year research break, transforming smallest-particle knowledge into understandable lectures, and stronger soul/brain reactions.
- Course setting: modern Covid/post-Covid classroom or teacher office with hot tea, LED/tube lights, whiteboard/marker, organized students, patients and relatives persevering through strong reactions.
- Employer-employee focus: social Tao roles, cause/effect of being boss/employee/leader/rich/poor, mutual benefit, employers not exploiting and employees not harming/resenting.
- Closing practice: both sides understand the two truths, help each other, eliminate toxins, and produce sustainable energy particles. Keep workplace examples modern and ordinary.""",
    35: """Chapter 35 step-by-step lock:
- This chapter is researcher and inventor toxins, framed by the idea that suffering can become practice material.
- Opening focus: Nalas starts a new lecture by asking students to learn from all events, toxic actions, kind actions, suffering, and liberation.
- Student emotion: a student says human life from birth to sickness/old age/death feels harsh and tiring; Nalas reframes practice as step-by-step climbing a high mountain with the two truths as super-power.
- Research/invention focus: agriculture, tools, medicine, body/world/space knowledge, enlightened knowledge, and the dark side of inventing poisons, stimulants, weapons, animal-harming methods, harmful products, and destructive technologies.
- Closing focus: special body-wisdom-soul healing class, information encoded into the soul, head/forehead reactions, and healing diseases of ignorant intellect, soul, and body. Use labs, notebooks, tools, and classroom sparingly; no sci-fi lab clutter.""",
    36: """Chapter 36 step-by-step lock:
- This chapter is businessman/producer toxins and should feel distinct from employer-employee.
- Opening focus: full modern class; Nalas asks if repeated toxin lessons are boring; students say the lessons are valuable because reactions and illnesses have reduced.
- Key teaching beat: a student says Nalas is not a business person because he collects no tuition; Nalas laughs and explains his energy filter as a factory, enlightened knowledge as valuable goods, super-energy particles as products, and teaching as distribution/technology transfer.
- Student case: a male student says mental health is nearly cured after seeing demons/God/Buddha promising wealth; Nalas redirects him away from ritual wealth dreams toward realistic small-scale business, learning, ethics, and feeding/educating children.
- Closing focus: production/business as a way to create sustainable energy particles by sharing enlightened wisdom. Keep examples contemporary: shops, small business, production tables, family finances, class discussion; no luxury wealth fantasy.""",
    37: """Chapter 37 step-by-step lock:
- This chapter is relationships with animals and all species.
- Opening focus: Nalas recalls the commandment to tame animals so their souls may become humans to practice; students define animals, plants, rocks, vegetation, insects, and smaller life.
- Key case: a woman whose family bought a mountain for stone exploitation, suffered mental health problems and hallucinations of snakes/tigers, then sold the mountain and changed business after learning the teacher's knowledge.
- Other cases: animal souls, tree/rock/soil souls, destroying mountains, dog-slaughter neighborhoods, restaurants, sudden family suffering, and students seeing snakes/tigers/dogs in illness. Keep these as compassionate environmental and moral consequence scenes, not graphic slaughter or horror.
- Closing practice: accept toxin images like a short film, activate kindness toward animals/all species, race against time to help all species, and re-encode the yin-yang embryo.""",
    38: """Chapter 38 step-by-step lock:
- This chapter is the final toxin-removal lecture: treating yourself and others, with a major healing-course evidence sequence.
- Opening focus: a woman near Nalas reports stage III breast cancer markers/bone scan improved after months in the therapy class; she still has sharp bone pain from toxin elimination. Show medical result papers only as unreadable documents, with hopeful classroom emotion.
- Course evidence: three metastatic cancer patients recover, many mental illness patients recover, illnesses decrease after one-third of the course, and the class shares joy. Do not show hospital gore or miracle-cure fantasy; keep it as testimony in a modern class.
- Farewell/oath memory: at the first session Nalas vows that if the healing course succeeds he will devote his life to spreading the two truths worldwide and hold no future classes in Vietnam; by the farewell party students are happy, sad, and promise to practice/spread the wisdom.
- Last lecture focus: treating self and others, not killing self/others, not provoking others' toxins, learning from toxic people and kind people, children as honesty/holiness, everyone/everything as teacher, and not becoming arrogant about helping/saving. Keep it human, mature, and compassionate.""",
    39: """Chapter 39 step-by-step lock:
- This chapter opens in Cebu City, Philippines, after dinner beside the swimming pool of an English school where the narrator, Truong Nalanda, and Duong Nalanda study English to spread Nalas's knowledge globally.
- Present frame focus: modern international student setting, pool reflections, night breeze, book-writing discussion, not Vietnam classroom and not countryside.
- Memory focus: one August 2018 night, the mortal body sleeps while Nalas's tuelinh travels across the universe instead of returning to heaven. If the sleeping body appears, keep the mortal Vietnamese Nalas wearing exactly one pair of thin glasses.
- Tuelinh teaching focus: on a vast planet, Father Nalas teaches many young tuelinhs/children about destructive energy. He can shift between giant cosmic tuelinh and mature human-like Father form. Use Western sacred/cosmic Father Nalas style with golden inner aura and sapphire-blue outer aura, no wings, not xianxia.
- Key doctrine beats: tuelinh decay like metastatic cancer, black-hole-like destructive storms, three cases of excess negative/balanced/filter states, universe decay into brown smoke, and dual energy filter producing lapis lazuli blue super-energy.
- Closing milestone: on October 12, 2018, Nalas achieves enlightenment and transforms the yin-yang embryo into a dual energy filter; students later see lapis lazuli particles while meditating. This is a major chapter image, not a minor detail.""",
    40: """Chapter 40 step-by-step lock:
- This chapter is a modern teacher-office/classroom morning with mentally ill patients and students, not a pilgrimage or heaven chapter.
- Opening focus: patients feel sleepy or headaches while listening; a woman compares direct lectures with social network videos; Nalas explains direct super-energy transmission from his tuelinh.
- Student question focus: how God, the first tuelinh, Father, and Buddha created everything and the universe.
- Teaching focus: ancestral/source particles are green like young banana leaves, born from singularities/doorways in space, moving in spiral orbits before heat exists.
- Mechanism focus: wave-particles transform differently in heatless, positive-heat, and negative-heat environments, becoming destructive, positive, or harmful energy particles.
- Keep the visual grounded in office/classroom with tea, patients, students, board or simple diagram when useful; cosmic particles are restrained overlays or lesson visuals, not the whole frame.""",
    41: """Chapter 41 step-by-step lock:
- This chapter continues after lunch break with tea, students, patients, and a modern board/pen explanation of destructive energy particles.
- Opening focus: students summarize ancestral particles and singularities before Nalas continues to destructive energy particles and their intelligence.
- Board focus: Nalas uses a pen to draw destructive energy particle structure. Show oval brown particle, green intellectual wave-code fibre, three points, and simple non-readable diagram strokes.
- Doctrine focus: destructive particles come from wave-particles moving in heatless space; they do not rotate or bond into larger structures; they have excess brown heat and decay power.
- Human application focus: destructive energy moving into the soul causes information disorder, mental illness, pain, and loss of control; positive practice can absorb/detonate it.
- Avoid full cosmic battle as the default. The main anchor is a modern class/office with attentive people and a board, with restrained particle visualization.""",
    42: """Chapter 42 step-by-step lock:
- This chapter is the first day of the India/Nepal pilgrimage in Gaya, Bihar, at Mahabodhi temple and the Bodhi tree under full moonlight.
- Real-world setting focus: temple grounds, ancient Bodhi tree, monks/pilgrims/visitors, moonlight, chanting, security/crowd context. This is a real Indian pilgrimage site, not heaven and not a Vietnamese classroom.
- Action focus: after visitors thin out, students sit around Nalas under the Bodhi tree; he guides them to close their eyes and become smallest energy particles.
- Inner journey focus: destructive brown space, green wave-particles, red sparks/explosions, first positive particles, cold spaces, first negative particles, and repeated appearance/erasure of yin-yang particles.
- Return focus: students open eyes under the moonlit Bodhi tree, feeling wind and energy, while Nalas summarizes the first yin-yang particles.
- Use cosmic visuals as guided inner vision layered from the Bodhi-tree scene; do not turn Mahabodhi temple into Western heaven or Chinese fantasy.""",
    43: """Chapter 43 step-by-step lock:
- This chapter begins at autumn dawn in a hotel garden near the holy land where Buddha attained enlightenment; Nalas wakes early, thoughtful, with past-life memories increasing.
- Morning travel-life focus: breakfast with Indian dishes, then a hotel living room where Nalas brings Vietnamese tea and tea utensils from home.
- Key mood: Vietnamese tea at an Indian relic connects past and present, Vietnam and India, teacher and students.
- Teaching setup: students ask about positive/negative particles from wave-particles versus particles from yin-yang embryos; Nalas asks them to bring the whiteboard closer.
- Board focus: positive/negative particles have three parts and intellectual wave-code structures; internal/external environment and heat/information change their nature.
- Keep this as hotel garden/living-room teaching with tea and portable whiteboard, not a formal classroom, not a temple, and not pure abstract particles.""",
    44: """Chapter 44 step-by-step lock:
- This chapter is the second evening back at Mahabodhi temple and the Bodhi tree: sunset, temple lights, moonlight, security gate, worship inside, walking around the temple and tree, and many pilgrims/monks/Western visitors before quiet.
- Earth anchor: after the crowd thins around 7pm, Nalas and students gather under the Bodhi tree. This is a real Indian pilgrimage night, not heaven.
- Lecture focus: the miraculous yin-yang energy embryo and Big Bang. Students ask how positive and negative particles bond while destructive particles cannot.
- Inner journey focus: colorful positive and negative particles seek each other; most embryos are destroyed; one special bright-yellow positive particle and grey-white negative particle bond into the magical embryo that detonates destructive particles and grows.
- First-tuelinh focus: the embryo matures into a super-giant energy sphere; at the center appears the first tuelinh, operating negative and positive particles; the Big Bang releases countless particles.
- Return focus: students open eyes under the Bodhi tree and feel respect/gratitude for the supreme soul. Avoid xianxia, Chinese temple, and generic space poster imagery.""",
    45: """Chapter 45 step-by-step lock:
- This chapter moves by bus from Mahabodhi to the ancient Nalanda University ruins in Bihar after bad roads, lunch, and rest.
- Setting focus: vast red-brick ruins, moss, old foundations and walls, lawns, autumn afternoon light, regret for a destroyed Buddhist university. Do not use modern classroom or Vietnamese city.
- Character/past-life focus: Truong Nalanda shares a realistic dream of a past life here; Duong Nalanda was his sister; Nalas says he was once a great king in this region and used the first tuelinh's name to save her life.
- Group focus: students meditate, lie on grass, sit around Nalas, and feel old memories at the ruins.
- Lecture focus: mechanism of particle production of the yin-yang embryo, original positive/negative particles, information copying, negative and positive particle production, neutral particles, and environment reaction.
- Keep ruins/lawn/student circle as the visual anchor; particle diagrams or glowing embryos are support, not a replacement for the Nalanda location.""",
    46: """Chapter 46 step-by-step lock:
- This chapter continues at Nalanda University ruins under big trees and autumn breeze, with students confused after the previous lecture; some unconsciously pull grass while thinking.
- Teaching focus: Nalas simplifies how to remember difficult particle knowledge and then guides students to become smallest positive particles inside the universe's yin-yang embryo.
- Inner journey focus: stages from embryo formation to mature embryo, adult tuelinh, and pre-Big Bang; yellow positive particles, grey-white negative particles, fire-red, green, black, blood-red, ivory-white particles, and destructive particles attacking the membrane.
- First-tuelinh focus: a mature tuelinh works hard at the center of a giant energy sphere, selecting valuable yellow/grey-white particles for his body.
- Closing focus: everyone returns to present as afternoon sunlight fades and darkness covers Nalanda ruins before they go back to the hotel.
- Do not make this a classroom, sci-fi lab, or generic galaxy scene; keep the physical chapter location visible whenever possible.""",
    47: """Chapter 47 step-by-step lock:
- This chapter is day nine of the India/Nepal journey at the ancient capital where Prince Siddhartha grew up, surrounded by extensive rice fields, then at the nearby relic where the crown prince was born.
- Morning setting: bus arrives at high brick walls and ruins of the ancient capital in Nepal; Nalas points out palace foundations, southeast expansion, and the prince leaving the capital.
- Afternoon setting: bus to the birthplace relic, sunset behind forests/hills, huge house preserving birth traces, lake, tall iron pillar, and lawn where students sit.
- Lecture focus: students ask about the first tuelinh; Nalas explains production and linking mechanisms, yin-yang embryo bonding, synthetic particle bonding, and gives two examples: man-woman marriage and students following him on the enlightenment mission.
- Reverence focus: Nalas states the first tuelinh is God/Father and also Buddha after human practice. If visualized spiritually, use stable Western sacred Father Nalas, but keep the Earth frame in real Nepal unless the excerpt moves inward.
- Closing focus: late night on the grass, people leaving, pilgrimage completed, group preparing to return home. Do not replace Nepal relics with heaven or a generic temple classroom.""",
    48: """Chapter 48 step-by-step lock:
- This chapter begins on a plane from Patna to New Delhi after the ten-day pilgrimage; students are tired and asleep while the plane taxis/takes off, and Nalas looks through the window saying goodbye to the land of memories.
- Earth anchor: modern airplane cabin, airport runway, tired students, Nalas awake with thin glasses; later New Delhi airport and hotel. Do not default to Vietnam.
- Inner-reality focus: Nalas recalls past lives and the wisdom he regained from pilgrimage, then invites the reader into memories of his homeland: the central planet called heaven, Buddha's country, or God's country.
- Celestial focus: the first tuelinh/Father after the Big Bang, operating particles, building the House of Tuelinhs, crystal caves where baby tuelinhs are born, gold/precious-stone architecture, calm seas and lakes glowing with lapis lazuli, iridescent grass/trees, hills where children play/transform, and golden super-energy particles.
- Father style lock: true heaven scenes use the approved Western sacred Jesus-like Father Nalas: pure white robe, no wings, stable age 40-42, gentle beard, golden inner aura, sapphire-blue outer aura, compassionate authority.
- Closing focus: Nalas opens his eyes as the plane lands in New Delhi; students wake. Keep the plane-memory frame clear, not only a standalone heaven poster.""",
    49: """Chapter 49 step-by-step lock:
- This chapter is a New Delhi hotel day before flying back to Vietnam, not a heaven scene by default.
- Opening focus: after breakfast everyone chooses coffee at the hotel coffee bar, sits in the hotel living room, and Duong Nalanda brings Nalas a fragrant hot cocoa because coffee can trigger his allergy.
- Group focus: Loi Nalanda asks Nalas to share the wisdom gained from the pilgrimage; students want to spend the day listening before going to the airport after dinner.
- Teaching focus: Nalas describes the current universe from a hotel living-room lecture: central magical planet, pyramid gemstone at the core, solar systems, galaxies, galaxy layers, rotating cosmic sphere, energy beams, fire particles, and one universe surrounded by destructive energy.
- Doctrine focus: three matter groups with simple, complex, and super-complex intellectual wave codes; eight particle colors/types; tuelinh babies, souls of rocks/trees/animals, planets, and transformation mechanisms.
- Closing focus: students feel overwhelmed and rest on hotel sofas after receiving vast information. Use hotel/coffee/sofa/modern travel setting plus restrained universe overlay; avoid making every frame pure space art.""",
    50: """Chapter 50 step-by-step lock:
- This chapter is the final afternoon of the India/Nepal pilgrimage in a New Delhi hotel living room after lunch, not a Vietnamese classroom.
- Opening focus: Nalas relaxes with students in the hotel living room and invites questions because they are Nalandas who must teach this knowledge clearly to others.
- Student-question focus: a student asks about the spinning/rotation mechanism; Nalas tests understanding by asking whether spinning exists within humans and tuelinhs.
- Human-emotion focus: show the circular movement of happy, sad, and neutral emotions through calm student dialogue, not melodrama.
- Teaching focus: spinning has two forms - physical rotation while moving and internal circulation of information waves. Apply this to ancestral wave-particles, destructive particles, smallest energy particles, yin-yang embryos, humans, tuelinhs, animals, and the universe.
- Keep the Earth anchor as hotel/travel teaching with sofas, tea/water/notebooks, travel fatigue, and restrained particle/rotation overlays. Do not convert the chapter into a pure cosmic poster or a normal Vietnam office class.""",
    51: """Chapter 51 step-by-step lock:
- This chapter begins on the flight back to Hanoi after the pilgrimage. The Earth anchor is an airplane cabin, small windows, airport runway, tired students, and Nalas closing his eyes with thin glasses.
- Opening mood: students remember Buddha's footsteps, past-life stories, roots, and the urgency of racing against time; Nalas hides deep emotion because the mission is not finished.
- Transition focus: when the plane takes off, Nalas enters tuelinh memory; keep the airplane-body frame clear before moving into cosmic memory.
- Memory focus: first tuelinh after the Big Bang surveys the central magical planet, embryos growing in crystal rocks, the heat source from the explosion, and outer universe space filled with rotating particles and forming yin-yang embryos.
- Conflict focus: at the boundary between universe space and destructive energy, explosion heat is being consumed and destructive/wave particles threaten the cosmic sphere; this is the battle for survival between destructive energy and the universe.
- Use Western sacred/cosmic Father memory for the first-tuelinh scenes, but do not show Jesus/Father inside the airplane cabin unless the excerpt is clearly memory/inner vision.""",
    52: """Chapter 52 step-by-step lock:
- This chapter continues Nalas's memory journey while his mortal body sleeps on the flight returning to Hanoi; it is not a normal classroom chapter.
- Memory focus: after building the central planet, first tuelinh realizes information transmission is interrupted across the expanded universe after the Big Bang.
- System-building focus: in his central-planet workplace he builds a pyramid-like information processing center, synthetic particle clusters as stations, neutral-particle transmission wires, negative particles receiving signals, and positive particles pushing data.
- Energy-wire focus: connect suns, galaxies, and the central planet with bright energy strings so galaxies rotate stably around the central planet and information can return to the center.
- Structural focus: the whole information-transceiver system is like a giant tuelinh/soul spread through the universe; simple planets and physical structures move through it without damaging it.
- Closing Earth anchor: the memory abruptly shifts back to the airplane, where the teacher's body is sleeping deeply with one hour before landing at Hanoi airport. If showing the body, Nalas must wear one pair of thin glasses and have no spare glasses on the seat/table.""",
    53: """Chapter 53 step-by-step lock:
- This chapter returns to a modern Hanoi office on a cold autumn morning: Nalas sits on a sofa, eyes closed, enjoying hot Vietnamese tea before students arrive.
- Human-case focus: students unexpectedly enter with a sad older woman whose mother is over seventy, seriously ill in hospital, and unlikely to survive. Show the woman, the student who brought her, tea being prepared, and the compassionate office atmosphere.
- Teaching focus: Nalas does not perform a miracle cure; he explains life completion, the mother's soul, devotion to children/grandchildren, illness, separation, and the correct understanding of death.
- Board focus: after a brief humorous exchange, Nalas draws the intellectual wave-code fibre on a whiteboard beside the coffee table using a pen.
- Doctrine focus: everything is information - wave-particles, destructive particles, energy particles, first tuelinh, universe, tuelinhs, souls, humans as vehicles/homes for tuelinhs, and interactions as information reactions.
- Keep this chapter modern Hanoi office/classroom: sofa, hot tea, coffee table, whiteboard, students, older woman. Do not turn mentions of temples, Buddha, God, or death into a literal heaven scene unless the excerpt explicitly leaves the office.""",
    54: """Chapter 54 step-by-step lock:
- This chapter continues in Nalas's modern Hanoi office after the woman leaves and after lunch; students nap in chairs, wash their faces, drink water/tea, and gather when a male student asks what first tuelinh did before creating the human practice environment.
- Earth anchor: office/classroom with post-lunch Vietnamese nap rhythm, hot tea, chairs, students waking, not an old wooden tea house or countryside room.
- Heaven-memory focus: first tuelinh creates baby tuelinhs in miraculous crystal rocks inside a giant cave, raises them on the central planet, builds gold/precious-stone houses and a vast temple, and teaches them about the universe.
- Loss focus: older tuelinh children secretly go to destructive-energy areas to practice detonating particles; many are attacked, injured, or disintegrated, and Father suffers while healing survivors.
- Decision focus: after analyzing solar-system rotation, his own embryo, and children's weakness, first tuelinh decides to create a harsh practice environment: Earth/human life as a school for tuelinhs and souls.
- Closing focus: conference in heaven to unify the practice path, then tuelinhs incarnate as humans; first tuelinh also incarnates in important eras to lead them. Keep memory scenes Western sacred/cosmic Father style, distinct from the modern office frame.""",
    55: """Chapter 55 step-by-step lock:
- This chapter is the first spring after Nalas transforms the yin-yang embryo into a dual energy filter. Earth opening: cold rainy spring night; the mortal body sleeps after children go to bed so the tuelinh can return to heaven.
- Heaven setting: Nalas's tuelinh returns to his private working space on the central planet, not a human classroom. A messenger opens the door; iridescent golden super-energy particles float around a magical pyramid that pulses like a heart.
- Pyramid-memory focus: the pyramid replays congresses unifying the tuelinh path and gathering humanity, then shows Nalas sitting with his five eldest tuelinh children.
- Five-messenger origin: the five eldest children are all male/mature tuelinhs who will incarnate as humans, lead the first humans, later operate the cause-and-effect tree system, and become his five messengers. Do not replace them with women, children, or clone-like angels.
- Past-life montage focus: the pyramid shows Nalas's human lives - forest tribe survivor, soldier who avoids killing, trader/businessman, teacher, stay-at-home mother/father, and other Tao-form lives - as lessons in positive/negative energy production.
- Keep true heaven scenes in Western sacred Father Nalas style with golden inner and sapphire-blue outer aura; keep mortal sleep glimpses modern and natural with glasses if the body is visible.""",
    56: """Chapter 56 step-by-step lock:
- This chapter is a heaven lecture to children/tuelinhs, not an Earth classroom. Earth setup only: Nalas works at the office, returns home early after receiving a tuelinh signal, waits for the body to sleep after his children sleep, then the tuelinh returns to heaven.
- Heaven anchor: Father Nalas sits in his temple on the central planet before thousands of tuelinh children who gather quickly and become quiet.
- Teaching focus: he explains that he has been busy teaching the human body-soul-wisdom therapy class and upgrading particle knowledge after the India pilgrimage.
- Achievement focus: he announces the successful transformation of his yin-yang energy embryo into a dual energy filter and the completion of a mission to create new energy superparticles for the universe.
- Doctrine focus: enlightened knowledge of the two truths, energy particles, secret information in intellectual wave code, and the path for children before incarnating as humans.
- Use stable traditional Jesus-like Father Nalas in Western sacred heaven; no Vietnamese mortal teacher, no modern office, no Chinese temple academy in the main heaven lecture frames.""",
    57: """Chapter 57 step-by-step lock:
- This chapter continues the same heavenly temple lecture. A tuelinh child asks Father about ignorant wisdom in action and whether speaking ill of harmful people is also ignorance.
- Dialogue focus: show a child standing respectfully among many tuelinhs while Father answers with compassion and authority.
- Moral focus: Father explains the poisonous-snake/toxin metaphor, warning that attacking another person's toxins provokes more toxins. Avoid literal horror snake imagery unless subtle and symbolic.
- Doctrine focus: ignorant wisdom in action is higher than ideology; black negative particles with very strong electric waves bond with ivory-white, green, fire-red, or yellow positive particles and destroy their sustainable information value.
- Keep the frame as a Western sacred heavenly classroom/temple with tuelinh children; do not shift to Earth examples unless a lane excerpt specifically describes a human-world example.""",
    58: """Chapter 58 step-by-step lock:
- This chapter continues Father teaching children in the heavenly temple about ignorant wisdom in spreading false knowledge.
- Opening debate: Father gives two situations - war between countries with many deaths versus one person creating and spreading false knowledge about human/tuelinh origin and mission. Two children answer differently.
- Teaching focus: Father explains that false knowledge causes greater long-term harm because everything is information and wrong information makes tuelinhs produce countless blood-red negative particles.
- Example focus: religious/ideological/knowledge spreaders teaching false liberation, origin, mission, wealth, desire, or power. Keep examples as restrained lesson visions around the temple, not propaganda posters or modern social-media collages.
- Doctrine focus: blood-red negative particles with super-strong electric waves, spreading false knowledge, decay of tuelinh structure, and the possibility of being saved by accurate information.
- Keep Father Nalas visually stable and Jesus-like; surrounding children/tuelinhs must not copy his long hair, full beard, robe, or radiant-heart signature.""",
    59: """Chapter 59 step-by-step lock:
- This chapter continues in the heavenly temple. A child asks how Father can save tuelinhs whose wisdom is easily manipulated by negative particles and toxins.
- Compassion focus: Father reassures the children that he will not abandon any tuelinh; five messengers, the transit planet, and the information transmission/reception system support the rescue of all souls practicing in the human world.
- Solution focus: first solution is using all four Tao interaction scenarios to stimulate and force out toxins over many lifetimes; second solution is creating environments with accurate information about origin, mission, and liberation from suffering.
- Human-world reference: his current students often came through mental illness and suffering before trusting enlightened knowledge. These can appear as soft vision windows, but the main frame remains Father teaching in heaven.
- Doctrine focus: wisdom easily vibrated/manipulated, negative grey/black/blood-red particles, aggregate imbalance, rejection of saving knowledge until suffering matures.
- Keep the tone deeply compassionate and ordered, not apocalyptic or horror-like.""",
    60: """Chapter 60 step-by-step lock:
- This chapter continues the same heavenly temple lesson and shows Father teaching the nature of intelligence with sustainable development characteristics.
- Opening focus: tuelinh children discuss how environments can change intellectual nature toward sustainable development or destruction and wonder whether they will be strong enough as humans.
- Vision-sequence focus: Father shows images of people born poor who study hard, farmers improving crops, workers and engineers building useful projects, scientists creating medicines/vaccines/transport/machines, businesspeople overcoming hardship, and teachers creating useful knowledge.
- Doctrine focus: these people represent sustainable-development intelligence: overcoming adversity, understanding harmful information, creating beneficial values, and producing positive energy structures.
- Composition rule: alternate heavenly temple wide shots, child reaction shots, Father presenting luminous vision windows, and concrete human-world vignettes inside those visions. Do not turn the whole chapter into a random modern classroom montage.
- Maintain Father Nalas as the stable Western sacred Jesus-like divine teacher, no wings, golden inner light and sapphire-blue aura, distinct from all children and attendants.""",
    61: """Chapter 61 step-by-step lock:
- This chapter remains in the same heavenly temple sermon, not an Earth classroom.
- Opening focus: tuelinh children are excited because many of them have the miraculous energy embryo and may accompany/help humans after incarnation.
- Teaching turn: Father interrupts gently and introduces the more miraculous grey-white weak negative particle plus fire-red very-strong positive particle embryo.
- Doctrine focus: this embryo spreads sustainable development values, balances positive/negative energy, and detonates destructive particles through low-toxicity, low-heat, low-vibration transformation.
- Composition rule: keep Father Nalas in Western sacred Jesus-like heavenly form, with children/tuelinhs listening, luminous non-Chinese particle diagrams, and small vision windows only when needed.""",
    62: """Chapter 62 step-by-step lock:
- This chapter is the closing part of the heavenly temple sermon before the physical human body wakes.
- Opening focus: children recognize the previous embryo type among many tuelinhs and listen as Father says the sermon is nearly over because his mortal body is about to wake.
- Teaching focus: Father explains that every wisdom type is natural in tuelinhs/humans, but even strong embryos must transform into energy filters before fully detonating destructive energy.
- Transformation path: reduce negative particle electric waves/toxins while increasing positive particles from weak to strong, very strong, then super strong.
- Earth-body reference: if the excerpt shows waking, use modern mortal Nalas with glasses in a believable sleeping/waking pose; otherwise stay in Western sacred heaven with the same Jesus-like Father.""",
    63: """Chapter 63 step-by-step lock:
- This chapter returns to a modern Vietnamese classroom in freezing winter rain; the room becomes strangely warm from Nalas's lecture even without a heater.
- Opening human case: a student shares that his family slaughtered animals for a restaurant, then suffered business decline, depression, and loss of control before recovery through the knowledge and stopping the business.
- Teaching focus: killing animals creates black negative particles and blocks practice; eating meat/vegetarian debate is secondary, while not killing or ordering slaughter matters.
- Cosmic lesson: guide students as smallest particles through wave-particles, destructive particles, yin-yang embryos, first tuelinh, trees/rocks/soil souls, animal souls, and the animal-to-human practice path.
- Composition rule: anchor scenes in the winter classroom with students, tea, sweat/warmth, and compassionate testimony; cosmic mechanisms appear as restrained class-guided visualizations, not standalone space posters or graphic slaughter.""",
    64: """Chapter 64 step-by-step lock:
- This chapter is a modern class on the Tuelinh's Journey of Transformation, with students discussing animal souls becoming tuelinhs/humans before Nalas corrects and expands the lesson.
- Opening focus: students talk excitedly about trees/rocks/soil to animals to humans, while Nalas warns not to destroy animals, forests, mountains, minerals, or life forms.
- Negative paths: ignorant wisdom in ideology, ignorant wisdom in action, and spreading false knowledge; show decay and negative particles as restrained instructional overlays, never horror.
- Positive paths: helping people/animals/all things, spreading sustainable development values, and building solidarity through accurate knowledge.
- Composition rule: modern classroom, whiteboard/diagrams, student discussion, and specific moral examples should drive the images; avoid generic mystical posters and avoid literal demons except as subdued toxin-imagery if named.""",
    65: """Chapter 65 step-by-step lock:
- This chapter opens in Nalas's modern office: Duong, Truong Nalanda, and students arrive from far provinces with bags of fruit, candies, tea, and questions.
- Human frame: recovered students discuss mental illness healing, spreading knowledge, and whether patients should learn about the transiting planet.
- Transiting-planet lesson: show it as a spiritual/celestial administrative realm with resting places like inns/hotels/villas/bridges, the Return of Tao Council, Executive Council, Administrative Council, and the cause-and-effect tree.
- Five messengers: all five are adult male messengers operating the cause-and-effect system; do not make them women, children, clones, or identical to Father Nalas.
- Hell/prison gates: Nalas says demons/beasts are illusions from particle reactions, so visualize them symbolically and restrained, with no gore or sensational horror; keep office lecture and compassion visible when possible.""",
    66: """Chapter 66 step-by-step lock:
- This chapter is a modern Vietnamese home near Tet, not a temple or old countryside scene.
- Opening focus: Nalas waters orchids on the balcony in cold weather beside kumquat/peach/New Year plants, then drinks hot tea with Ms. Phuong and her children Dzung and Nga.
- Story focus: Dzung's return from US study, helping trapped souls at dorm/campus, and Ms. Phuong's forensic/autopsy work causing resentful souls to follow and bombard her with toxic particles.
- Teaching focus: trapped souls, resentment, particle copying/bombardment, mental illness, shoulder/neck/head pain, and the danger of overusing meditation/supernatural powers.
- Composition rule: warm family-like Tet visit, tea, fruit/cakes, balcony plants, modern home, and restrained translucent soul-energy overlays; no demon horror or antique rural styling.""",
    67: """Chapter 67 step-by-step lock:
- This chapter takes place in Nalas's modern office with students and a worn-looking man affected by many spiritual/religious practices.
- Character focus: the man has dull eyes, pale tired skin, tension, illness, and confusion from tantra, meditation, pure land prayer, rituals, spirit/demon/ancestor voices, third-eye/chakra loss of control, and followers becoming possessed.
- Teaching focus: Nalas compassionately challenges false methods and explains origin, mission, smallest particles, Earth practice, and why rituals/spells/supernatural powers cannot create sustainable enlightened energy.
- Visual distinction: Buddha/God/devil/dead-soul images are mental toxin-movie imagery or delusion, not true deities appearing in the room.
- Composition rule: modern office/classroom, tea, students listening, worn man gradually calming; keep it clinical and humane, not exorcism horror.""",
    68: """Chapter 68 step-by-step lock:
- This chapter opens in a hot Hanoi summer office/classroom with Nalas drinking hot tea; Truong, Duong Nalanda, and students enter with iced coffee, fruit, and cakes.
- Story beat: Nalas knowingly drinks fragrant iced coffee despite allergy, sneezes and gets a runny nose, then uses the moment to clarify that coffee allergy is not the true law of cause and effect.
- Teaching focus: cause and effect is a universal transformation mechanism, not a religious punishment or Buddhist/Hindu-only idea.
- Inner journey: students close their eyes and become smallest particles; Nalas appears as a shiny yellow guide particle through wave-particles, destructive particles, yin-yang embryos, first tuelinh, galaxies, energy wiring, and baby tuelinhs.
- Composition rule: keep the lecture anchored by modern Hanoi summer, iced coffee/tea/student dialogue, then use restrained cosmic visualizations as guided lesson sequences; avoid pure generic space art.""",
    69: """Chapter 69 step-by-step lock:
- This chapter continues a modern class lecture about the law of cause and effect for tuelinhs and souls in human-world practice.
- First-tuelinh planning focus: show his analysis that human interaction scenarios, milestones, marriage, illness, death, environment, family, parents, and place/time of incarnation must be linked into practice plans.
- Cause-and-effect system: a protected space beside the universe pyramid, a giant pyramid twenty times taller than an adult, five adult male messengers working on a large plane at the top, and stored positive/negative causal particles around it.
- Four Tao rules: family Tao, social Tao, teacher-student Tao, and national Tao; include both prohibited harms and required positive values.
- Composition rule: alternate modern classroom explanation with clear celestial-system visualizations; keep five messengers male and distinct, no Chinese court bureaucracy, no generic angels replacing the actual system.""",
    70: """Chapter 70 step-by-step lock:
- This chapter is the Unified Tao through Family Tao, framed as a modern course memory after the narrator explains the lectures were edited into an easier order.
- Opening focus: Nalas with hot tea, students asking how four Tao forms produce particles and unify with the universe.
- Family Tao content: marriage between man and woman, husband-wife fidelity, adultery temptation, spouse death with or without children, spouse with social status, how couples treat each other, parent-child duties, siblings, ancestors, and dead/living family links.
- Human examples should be contemporary and restrained: classroom Q&A, family table conversations, couples in conflict or forgiveness, widowed parent caring for children, leader-spouse ethical pressure, sibling sharing/competition.
- Composition rule: keep sensitive issues non-explicit and adult; use modern Vietnamese classroom plus concrete family vignettes, with particle diagrams as support rather than the main image.""",
    71: """Chapter 71 step-by-step lock:
- This chapter continues the Unified Tao through Social Tao after students discuss the previous Family Tao lecture running long.
- Opening focus: modern classroom, Nalas explaining that Tao is the worldview of the universe and cannot abandon family/social/national/teacher-student life.
- Social Tao content groups: treating animals, protecting natural resources, employee-employer relations, employer-employee duties, products/livelihood/production, love/social/work relationships, human trafficking rescue, respect across age/race/religion, and helping people in danger.
- Visual examples should be modern and ordinary: animal rescue/protection, forest/water/resource protection, ethical workplace/factory/office, rescuing/reporting trafficking as a safe civic scene, and people helping one another.
- Composition rule: no graphic violence, slaughter, sexualized scenes, or propaganda posters; keep Nalas and students in the modern classroom as the anchor and show Social Tao examples as grounded vignettes or board-supported lesson visuals.""",
    72: """Chapter 72 step-by-step lock:
- This chapter is the Unified Tao through National Tao, not a generic patriotic poster.
- Opening focus: modern classroom; Nalas asks students to recall the value of National Tao, then drinks hot tea before continuing.
- National Tao content groups: head of state and territory/people, leaders and managers serving the nation, and ordinary people's relationship with country, territory, laws, obligations, resources, and leaders.
- Negative examples include war, invasion, terrorism, corruption, epidemics mishandled, poverty, exploitation, nepotism, superstition in religion/belief, destructive policies, and natural-resource harm. Show these as restrained civic vignettes, not violent spectacle.
- Positive examples include peace policy, anti-corruption, disaster/epidemic response, education, protecting resources, productive citizens, unity across ethnicities/religions/countries, and rejecting war. Keep Nalas/classroom as anchor with modern civic scenes and subtle particle overlays.""",
    73: """Chapter 73 step-by-step lock:
- This chapter is the Unified Tao through Teacher-Student Tao after the National Tao lecture lunch break.
- Opening focus: students discuss how leaders spreading enlightened knowledge produce many yellow particles; Nalas uses that to explain the power of knowledge.
- Content groups: teacher treats student, student treats teacher, students treat each other, and the value of knowledge itself.
- Negative examples include teachers abusing/harming students, teaching theft/violence/superstition/false origin knowledge, students disrespecting or harming teachers, students spreading division, and harmful knowledge such as weapons, animal-destruction methods, scams, addiction, superstition, extremist knowledge, and false religion/spirituality.
- Positive examples include teachers caring for students, students respecting/applying/protecting teachers, students helping each other avoid harmful acts, and creating/spreading accurate enlightened knowledge. Keep the visual world as modern classroom, school/learning contexts, and knowledge-sharing vignettes; no sensational abuse imagery.""",
    74: """Chapter 74 step-by-step lock:
- This chapter begins in Nalas's modern office when students quietly enter and find him sitting with eyes closed in a meditative/memory state; a student refreshes his tea and everyone waits respectfully.
- Human case: students ask about a murdered mother and child and the husband affected by depression/mental illness and a trapped soul/evil-spirit influence. Treat this as compassionate office retelling, never graphic murder.
- Teaching focus: journey after the end of human life, transiting planet, suicide/accident/sudden death/being killed, souls trapped at the death location, and the Executive Council receiving souls after enlightened preaching.
- Distinction: prayer rituals without enlightened teaching do not return the soul; preaching enlightened wisdom to the dead person's location and relatives can help the soul return.
- Composition rule: alternate office/tea/student Q&A, restrained memory overlays of a death-location soul, and symbolic transiting-planet reception; no horror demons, gore, or sensational crime scenes.""",
    75: """Chapter 75 step-by-step lock:
- This chapter starts a new technical lecture after difficult particle knowledge, with excited students ready to learn how life reactions produce energy particles through the four Tao forms.
- Subject lock: grey negative energy particles with strong electric waves, the reaction that produces ignorance in ideology.
- Structure: four environments and five stages - desire, decoding/encoding, ideology creation, action, and intellectual wave-code fibre/causal particles.
- Example lock: adultery creates grey negative particles through desire, attraction to a young woman at work, denial of positive information from faithful wife/family, ideology of self-satisfaction, and hidden action. Show only adult, non-explicit, emotionally restrained modern vignettes.
- Composition rule: mostly modern classroom with board/diagram and calm teacher; particle mechanics are overlays. Avoid erotic staging, explicit adultery, moral-shock melodrama, or pure abstract diagrams without the classroom frame.""",
    76: """Chapter 76 step-by-step lock:
- This chapter is the action-level counterpart to C075: black negative particles with very strong electric waves.
- Opening focus: lunch-break student conversation about Nalas teaching all day without fatigue and students standing to see him in a crowded class.
- Teaching focus: ignorance in action harms people, animals, and all things at large scale and can include killing; it still follows four environments and five production stages.
- Example lock: pig slaughter business. A man starts a slaughterhouse, becomes wealthy, denies positive information about not killing, and each slaughter produces black causal particles. Show business/decision/industrial context only in restrained, non-graphic ways; no visible killing, gore, suffering animals, or slaughter close-ups.
- Composition rule: modern classroom and ethical business vignettes with subdued black-particle overlays; keep it analytical and compassionate, not horror or shock imagery.""",
    77: """Chapter 77 step-by-step lock:
- This chapter is ignorance in spreading false knowledge: blood-red negative particles with super-strong electric waves.
- Opening focus: Nalas begins class after students finish talking; he asks what is special after grey and black particle lessons, then explains using toxins to remove toxins.
- Teaching focus: false knowledge about origin, mission, practice, superstition, destructive methods, and values that harm sustainable development; use blood-red wave-code overlays sparingly.
- Example locks: spreading superstitious/prayer/ritual knowledge and the Devadatta-Buddha sangha-harmony story. The Devadatta example should appear only when the excerpt reaches it, as a restrained historical teaching vignette, not the chapter's default setting.
- Composition rule: modern classroom remains the anchor; show misinformation/spiritual-pride scenes as lesson windows. No demon horror, no attack spectacle, no Chinese temple fantasy, and no fake religious poster.""",
    78: """Chapter 78 step-by-step lock:
- This chapter uses the hot teapot on the table as the concrete analogy for destructive energy detonation.
- Opening focus: Nalas asks how to boil water and brew tea; students mention electric kettle, pot, heat, teapot material, water temperature, tea quality, and brewing time.
- Teaching focus: destructive energy detonation requires tools, pressure, compression, the human body/soul/tuelinh, ideology, action, the four Tao forms, and the two truths.
- Method steps: immerse in negative thoughts only after interaction with a Tao content, use the truth of the universe to avoid sinking into suffering, then use the truth of enlightenment to create positive thought and detonate destructive energy.
- Composition rule: keep hot tea/teapot/electric kettle/classroom visible in opening lanes; later show guided inner-practice overlays. Do not make it a generic cosmic explosion or dangerous self-harm-looking scene.""",
    79: """Chapter 79 step-by-step lock:
- This chapter teaches practice producing green positive particles, the development-level positive counterpart.
- Setting baseline: modern classroom/training room, students analyzing particle reactions; if Covid/post-Covid cues appear, use polished LED/whiteboard/office-classroom style.
- Teaching focus: green positive particles with strong electric waves, positive particle controlling negative particle, positive/negative environments, five stages, and collecting a green particle at the causal tree on the central planet.
- Human meaning: producing green positive particles through development actions, letting go of attachment/selfishness, relying on positive people/knowledge, and thinking about origin/mission/liberation methods.
- Composition rule: use classroom, board diagrams, calm student practice, green light overlays, and concrete development/helping vignettes; avoid all-green one-note palette or pure abstract particle wallpaper.""",
    80: """Chapter 80 step-by-step lock:
- This chapter teaches practice producing fire-red positive particles, distinct from C079 by spreading development values.
- Opening focus: students analyze the morning example and compare green/fire-red/yellow production; Nalas explains the value of spreading sustainable development.
- Teaching focus: fire-red particles with very strong electric waves, desire to spread values, positive particle controlling negative particle, five stages, action to spread useful values, and causal-tree collection.
- Human examples include becoming a teacher, researching, sharing valuable knowledge/methods, and spreading values that help people and all species.
- Composition rule: modern classroom anchor plus teaching/research/spreading-value vignettes with warm fire-red overlays. Avoid aggressive flames, war imagery, or pure red fantasy magic.""",
    81: """Chapter 81 step-by-step lock:
- This chapter teaches yellow positive particles, the solidarity/unified positive energy higher than green and fire-red.
- Opening focus: Nalas asks why yellow unified positive particles are most valuable; students explain comprehensive information, solidarity, super-strong waves, and protection by weak grey-white negative particles.
- Key metaphor: solid house of ignorance, cool lake/water, lush green forest, sun of spreading values, and united people standing on the porch who can see inside the house and share outside truths without entering and causing conflict.
- Teaching focus: solidarity to spread sustainable values, envy/inequality comparisons, positive and negative environments, five stages, and yellow particle collection at the causal tree.
- Composition rule: modern classroom remains the base, with the house/porch/sun/forest/lake as a clear conceptual visualization. Avoid literal text, flags, religious symbols, or a flat infographic.""",
    82: """Chapter 82 step-by-step lock:
- This chapter is the emotional and technical culmination: Energy Filter - Unified Tao of the Universe.
- Opening emotion: Nalas and students drink hot tea with mixed happiness and regret after the mental-health research course succeeds; many patients recover, but he regrets not opening class earlier and leaving Vietnam soon to spread knowledge worldwide.
- Single energy filter: conditions include enough yellow particles in all four Tao interactions and dedication to unity/spreading enlightened knowledge; Father/Nalas directly helps transform qualified tuelinhs near end of human life.
- Dual energy filter: after single filter, produce shiny yellow positive superparticles and lapis-lazuli blue negative superparticles, replace synthetic particles, store/fire destructive energy, and produce superparticles for universe operation.
- Composition rule: alternate tea/classroom emotion with refined filter visualizations in gold and lapis blue. Keep Father/divine form only when the excerpt truly shifts to celestial help; otherwise use mortal Nalas in modern classroom with glasses.""",
    83: """Chapter 83 step-by-step lock:
- This short chapter explains the Hymn / Great Mantra Nalas Nalanda as praise and gratitude to Father Nalas, not a normal classroom lecture.
- Visual mode: sacred, textless hymn atmosphere. Show practitioners or tuelinhs uniting with Father Nalas's root power, peace, healing, and return to homeland through golden and sapphire-blue light.
- If Father appears, use the stable Western sacred Jesus-like Father form, no wings, warm golden inner light, sapphire-blue aura, and compassionate authority.
- Do not render the hymn lyrics as fake text, calligraphy, subtitles, scrolls, or book pages. The image should imply singing/chanting and gratitude through faces, posture, light, and space.
- Composition rule: no magical spell poster, no occult ritual, no Asian temple/calligraphy styling; keep it premium, reverent, and textless.""",
    84: """Chapter 84 step-by-step lock:
- This short chapter explains the symbol of the Unified Tao of the Universe.
- Symbol lock: a textless four-wing golden emblem inspired by the word Tao, with four branches for Family Tao, Social Tao, National Tao, and Teacher-Student Tao, intersecting at a central mind/soul point.
- Motion lock: clockwise/upward/golden when positive particles are produced; inverted/dimmed only when the excerpt discusses negative particles; shiny golden upgrade when single energy filter is achieved; outward golden emblems when the energy embryo produces superparticles.
- Avoid readable letters, fake Chinese/Vietnamese calligraphy, Taijitu/yin-yang icon, religious talisman, logo design, UI diagram, or flat infographic.
- Composition rule: can be symbolic/celestial, but keep it tied to tuelinh transformation and the four human Tao forms through subtle human-life vignettes around the emblem.""",
    85: """Chapter 85 step-by-step lock:
- This chapter is a practical method for helping trapped tuelinhs and souls return to the transiting planet.
- Subject: souls trapped at places of death due to killing, murder, suicide, accident, disaster, war, epidemic, or sudden death; helping requires enlightened knowledge and may be followed by the hymn/great mantra.
- Conditions: helpers must study the full Nalas Nalanda knowledge first, stay fearless and compassionate, preach to living people when present, and direct the sermon toward trapped souls.
- Steps: preach origin, mission, suffering/tribulations in four Tao forms, toxins/good elements, sustainable vs decay path, liberation method, unified Tao, and value of transiting planet; then chant the hymn three times as gratitude/support.
- Composition rule: modern location/house/land with a calm helper speaking, translucent listening souls, and a soft path to the transiting planet. No ghost-horror, exorcism, occult ritual, demon monster, or sensational haunted-house style.""",
    86: """Chapter 86 step-by-step lock:
- This chapter is an application/regimen summary for mental-health-related illnesses, not a mystical scene.
- Subject: relatives reading chapters to patients, playing lecture videos/audio before and after sleep, repeated daily listening/reading, patient gradually becoming awake enough to study independently, and later helping others.
- Visual anchors: modern Vietnamese home/bedroom/living room, books, phone/tablet/speaker, caregiver sitting near patient, night and morning routines, calm supervision, ordinary medical/medication context if mentioned.
- Sensitive rule: do not depict distress as horror, possession, restraints, hospital drama, or demon imagery; show care, patience, information re-encoding as gentle light, and family support.
- Medical caution for imagery: do not imply instant miracle cure in a single frame; show a process of repeated listening, reading, stabilization, and compassionate relatives."""
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
