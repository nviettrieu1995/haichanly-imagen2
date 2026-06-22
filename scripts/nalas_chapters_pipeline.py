#!/usr/bin/env python
import argparse
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
BOOKS = [
    ROOT / "Nalas Nalanda 1 (English).pdf",
    ROOT / "Nalas Nalanda 2 (English).pdf",
    ROOT / "Nalas Nalanda 3 (English).pdf",
]
DNA_PATH = ROOT / "Chapter_8_DNA_Only.md"
CH8_PROMPT_DNA_PATH = ROOT / "Chapter_8_Prompt_DNA.md"
CODEX_IMAGEN = Path.home() / ".codex" / "skills" / "codex-imagen" / "scripts" / "codex-imagen.mjs"

PIPELINE_ROOT = ROOT / "nalas_chapters_08_86"
TEXT_DIR = PIPELINE_ROOT / "chapter_text"
PROMPT_DIR = PIPELINE_ROOT / "image_prompts"
IMAGE_DIR = PIPELINE_ROOT / "generated_images"
LOG_DIR = PIPELINE_ROOT / "logs"
MANIFEST_PATH = PIPELINE_ROOT / "chapters_manifest.json"
MAX_EXCERPT_CHARS = 1000

PDF_SPACING_REPAIRS = [
    ("a nd", "and"),
    ("an d", "and"),
    ("T he", "The"),
    ("t he", "the"),
    ("th em", "them"),
    ("the m", "them"),
    ("gr oups", "groups"),
    ("gr oup", "group"),
    ("c hatted", "chatted"),
    ("fi lter", "filter"),
    ("w hether", "whether"),
    ("dr eam", "dream"),
    ("s ublime", "sublime"),
    ("practis ing", "practising"),
    ("intellec t", "intellect"),
    ("p articular", "particular"),
    ("hum ans", "humans"),
    ("h ave", "have"),
    ("i nside", "inside"),
    ("ev er", "ever"),
    ("ot hers", "others"),
    ("pe ople", "people"),
    ("bel ieve", "believe"),
    ("extraordin ary", "extraordinary"),
    ("knowledg e", "knowledge"),
    ("le sson", "lesson"),
    ("last ed", "lasted"),
    ("c reated", "created"),
    ("suf fering", "suffering"),
    ("mu st", "must"),
    ("pr actice", "practice"),
    ("unders tand", "understand"),
    ("rele ased", "released"),
    ("neu tral", "neutral"),
    ("infor mational", "informational"),
    ("embr yo", "embryo"),
    ("c annot", "cannot"),
    ("receiv ed", "received"),
    ("dest ruction", "destruction"),
    ("tal ented", "talented"),
    ("il lness", "illness"),
    ("enlig htened", "enlightened"),
    ("nega tive", "negative"),
    ("dev elop", "develop"),
    ("develo pment", "development"),
    ("esse nce", "essence"),
    ("c omplete", "complete"),
    ("fou r", "four"),
    ("n o", "no"),
    ("incar nating", "incarnating"),
    ("participat ed", "participated"),
    ("ac cept", "accept"),
    ("e nergy", "energy"),
    ("th at", "that"),
    ("o f", "of"),
    ("a re", "are"),
]

CHAPTER_DURATIONS_MIN = {
    8: 25, 9: 25, 10: 29, 11: 39, 12: 28, 13: 25, 14: 22, 15: 54,
    16: 32, 17: 38, 18: 23, 19: 25, 20: 25, 21: 27, 22: 36, 23: 27,
    24: 26, 25: 29, 26: 23, 27: 31, 28: 28, 29: 19, 30: 26, 31: 27,
    32: 22, 33: 23, 34: 23, 35: 21, 36: 25, 37: 23, 38: 33, 39: 28,
    40: 16, 41: 33, 42: 23, 43: 25, 44: 34, 45: 26, 46: 34, 47: 39,
    48: 38, 49: 33, 50: 32, 51: 36, 52: 32, 53: 48, 54: 38, 55: 26,
    56: 51, 57: 19, 58: 26, 59: 17, 60: 14, 61: 13, 62: 19, 63: 45,
    64: 56, 65: 81, 66: 41, 67: 36, 68: 32, 69: 61, 70: 101, 71: 72,
    72: 44, 73: 42, 74: 35, 75: 62, 76: 61, 77: 57, 78: 29, 79: 52,
    80: 47, 81: 59, 82: 48, 83: 6, 84: 4, 85: 11, 86: 6,
}

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
    "ninety": 90,
}


def log(message):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    with (LOG_DIR / "pipeline.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def parse_chapter_number(value):
    value = value.strip().lower().replace("-", " ")
    if value.isdigit():
        return int(value)
    total = 0
    for token in value.split():
        total += NUMBER_WORDS.get(token, 0)
    return total or None


def clean_text(text):
    text = text.replace("\u00ad", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def repair_pdf_spacing_artifacts(text):
    text = text.replace("\u00ad", "")
    text = re.sub(r"\b(Covid|COVID)\s*-\s*19\b", r"\1-19", text)
    for bad, good in PDF_SPACING_REPAIRS:
        def replace_match(match):
            value = match.group(0)
            if value.isupper():
                return good.upper()
            if value[:1].isupper():
                return good[:1].upper() + good[1:]
            return good

        text = re.sub(rf"\b{re.escape(bad)}\b", replace_match, text, flags=re.I)
    text = re.sub(r"\b([A-Za-z]+)\s*-\s*([A-Za-z]+)\b", r"\1-\2", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_page_text(text):
    cleaned = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            cleaned.append("")
            continue
        if re.fullmatch(r"\d{1,4}", line):
            continue
        if line.startswith("Nalas Nalanda -The Truth"):
            continue
        if line.startswith("Nalas Nalanda’s "):
            continue
        if line.startswith("Nalas Nalanda's "):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def scan_chapter_starts():
    chapter_rx = re.compile(
        r"^\s*Chapter\s+((?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve|Thirteen|Fourteen|Fifteen|Sixteen|Seventeen|Eighteen|Nineteen|Twenty|Thirty|Forty|Fifty|Sixty|Seventy|Eighty|Ninety|[-\s])+|\d{1,3})\s*$",
        re.I,
    )
    starts = []
    for book in BOOKS:
        reader = PdfReader(str(book))
        for page_index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            raw_lines = [line.strip() for line in text.splitlines()]
            nonempty_lines = [line for line in raw_lines if line]
            for raw_index, line in enumerate(raw_lines):
                match = chapter_rx.match(line)
                if not match:
                    continue
                number = parse_chapter_number(match.group(1))
                if not number:
                    continue
                title = ""
                title_lines = []
                seen_title = False
                for later in raw_lines[raw_index + 1 : raw_index + 16]:
                    if not later:
                        if seen_title:
                            break
                        continue
                    if re.match(r"^\d+$", later):
                        continue
                    if later.lower().startswith("chapter "):
                        break
                    if len(later) > 110 and seen_title:
                        break
                    title_lines.append(later)
                    seen_title = True
                if title_lines:
                    title = clean_text(" ".join(title_lines))
                starts.append(
                    {
                        "chapter": number,
                        "book": book.name,
                        "book_path": str(book),
                        "page_start": page_index + 1,
                        "title": title,
                    }
                )
                break
    starts.sort(key=lambda item: item["chapter"])
    return starts


def build_manifest(images_per_minute):
    starts = scan_chapter_starts()
    by_number = {item["chapter"]: item for item in starts}
    chapters = []
    for chapter in range(8, 87):
        if chapter not in by_number:
            raise RuntimeError(f"Missing Chapter {chapter} in PDF scan")
        current = by_number[chapter]
        next_start = by_number.get(chapter + 1)
        if next_start and next_start["book"] == current["book"]:
            page_end = next_start["page_start"] - 1
        else:
            page_end = len(PdfReader(current["book_path"]).pages)
        duration = CHAPTER_DURATIONS_MIN[chapter]
        image_count = max(2, math.ceil(duration * images_per_minute))
        chapters.append(
            {
                **current,
                "page_end": page_end,
                "duration_minutes": duration,
                "images_per_minute": images_per_minute,
                "target_image_count": image_count,
                "output_dir": str(IMAGE_DIR / f"C{chapter:03d}"),
                "prompt_dir": str(PROMPT_DIR / f"C{chapter:03d}"),
                "text_path": str(TEXT_DIR / f"C{chapter:03d}.txt"),
            }
        )
    total_minutes = sum(item["duration_minutes"] for item in chapters)
    total_images = sum(item["target_image_count"] for item in chapters)
    manifest = {
        "books": [str(path) for path in BOOKS],
        "chapter_range": [8, 86],
        "images_per_minute": images_per_minute,
        "total_minutes": total_minutes,
        "total_target_images": total_images,
        "chapters": chapters,
    }
    PIPELINE_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def extract_chapter_texts(manifest):
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    for chapter in manifest["chapters"]:
        reader = PdfReader(chapter["book_path"])
        chunks = []
        for page_no in range(chapter["page_start"], chapter["page_end"] + 1):
            text = reader.pages[page_no - 1].extract_text() or ""
            chunks.append(clean_page_text(text))
        body = clean_text("\n\n".join(chunks))
        Path(chapter["text_path"]).write_text(body, encoding="utf-8")
    log(f"extracted text for {len(manifest['chapters'])} chapters")


def load_manifest():
    return normalize_manifest_paths(json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig")))


def normalize_manifest_paths(manifest):
    manifest = dict(manifest)
    manifest["books"] = [str(path) for path in BOOKS]
    normalized_chapters = []
    for chapter in manifest.get("chapters", []):
        item = dict(chapter)
        chapter_number = int(item["chapter"])
        book_name = item.get("book") or Path(item.get("book_path", "")).name
        item["book"] = book_name
        item["book_path"] = str(ROOT / book_name)
        item["output_dir"] = str(IMAGE_DIR / f"C{chapter_number:03d}")
        item["prompt_dir"] = str(PROMPT_DIR / f"C{chapter_number:03d}")
        item["text_path"] = str(TEXT_DIR / f"C{chapter_number:03d}.txt")
        normalized_chapters.append(item)
    manifest["chapters"] = normalized_chapters
    return manifest


def split_sentence_units(text, target_words):
    text = repair_pdf_spacing_artifacts(text)
    if not text:
        return []
    rough_sentences = [
        item.strip()
        for item in re.findall(r".+?(?:[.!?][\"')\]]*(?=\s+|$)|$)", text)
        if item.strip()
    ]
    if not rough_sentences:
        rough_sentences = [text]
    units = []
    max_words = max(30, int(target_words * 1.6))
    for sentence in rough_sentences:
        sentence_words = re.findall(r"\S+", sentence)
        if len(sentence_words) <= max_words:
            units.append(sentence)
            continue
        for start in range(0, len(sentence_words), max_words):
            units.append(" ".join(sentence_words[start : start + max_words]))
    return units


def excerpt_segments(text, count):
    text = repair_pdf_spacing_artifacts(text)
    words = re.findall(r"\S+", text)
    if not words:
        return [""] * count
    target_words = max(20, math.ceil(len(words) / max(1, count)))
    units = split_sentence_units(text, target_words)
    unit_word_counts = [len(re.findall(r"\S+", unit)) for unit in units]
    segments = []
    unit_index = 0
    consumed_words = 0
    for index in range(count):
        if unit_index >= len(units):
            start = math.floor(index * len(words) / count)
            end = math.floor((index + 1) * len(words) / count)
            excerpt = " ".join(words[start:end])
            segments.append(re.sub(r"\s+", " ", excerpt).strip()[:MAX_EXCERPT_CHARS])
            continue
        if index == count - 1:
            excerpt_units = units[unit_index:]
            unit_index = len(units)
            segments.append(" ".join(excerpt_units)[:MAX_EXCERPT_CHARS])
            continue
        target_end = math.floor((index + 1) * len(words) / count)
        excerpt_units = []
        while unit_index < len(units) and (
            not excerpt_units or consumed_words < target_end
        ):
            excerpt_units.append(units[unit_index])
            consumed_words += unit_word_counts[unit_index]
            unit_index += 1
        excerpt = re.sub(r"\s+", " ", " ".join(excerpt_units)).strip()
        segments.append(excerpt[:MAX_EXCERPT_CHARS])
    return segments


def read_dna():
    dna = DNA_PATH.read_text(encoding="utf-8", errors="replace") if DNA_PATH.exists() else ""
    # Keep the useful English lines and avoid malformed mojibake headings.
    return clean_text(dna)


def chapter_prompt(chapter, image_index, image_count, excerpt, dna):
    role_cycle = [
        "opening wide establishing frame",
        "character-focused medium frame",
        "symbolic spiritual close detail",
        "emotional reaction frame",
        "cosmic transition frame",
        "quiet narration-hold frame",
        "heaven-and-Earth contrast frame",
        "memory or vision frame",
    ]
    role = role_cycle[(image_index - 1) % len(role_cycle)]
    return f"""Create one standalone cinematic 16:9 image for an audiobook video.

Book chapter: Chapter {chapter['chapter']} - {chapter['title']}
Video duration for this chapter: {chapter['duration_minutes']} minutes.
Image number: {image_index} of {image_count}.
Shot role: {role}.

Character and world DNA:
{dna}

Story beat excerpt to visualize:
{excerpt}

Visual direction:
Transform the excerpt into a cinematic spiritual sci-fi realism frame. Use Nalas Nalanda, Giac, Chap, heaven, Earth, dreams, cosmic gateways, memory light, universal energy, suffering, wisdom, and enlightenment only when they match the story beat. Make the image emotionally clear for an audiobook viewer. Do not render written words from the excerpt. No subtitles, no labels, no watermark, no logo. Avoid collage, panels, split-screen, UI, and poster layouts.

Negative prompt:
text, letters, subtitles, watermark, logo, bad anatomy, extra limbs, distorted face, blurry, low quality, cartoon, anime, horror, gore, demon, wings unless explicitly present in the story, modern sci-fi armor, weapons, chaotic clutter."""


def prepare_chapter_prompts(manifest, chapter_number, batch_size):
    dna = read_dna()
    chapter = next(item for item in manifest["chapters"] if item["chapter"] == chapter_number)
    text = Path(chapter["text_path"]).read_text(encoding="utf-8")
    image_count = chapter["target_image_count"]
    segments = excerpt_segments(text, image_count)
    prompt_dir = Path(chapter["prompt_dir"])
    output_dir = Path(chapter["output_dir"])
    prompt_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for image_index, excerpt in enumerate(segments, start=1):
        filename = f"C{chapter_number:03d}_img_{image_index:03d}.png"
        items.append(
            {
                "chapter": chapter_number,
                "image_index": image_index,
                "filename": filename,
                "target": str(output_dir / filename),
                "prompt": chapter_prompt(chapter, image_index, image_count, excerpt, dna),
            }
        )
    batches = []
    for start in range(0, len(items), batch_size):
        batch_no = len(batches) + 1
        batch_items = items[start : start + batch_size]
        prompt_path = prompt_dir / f"C{chapter_number:03d}_batch_{batch_no:03d}.txt"
        output_stem = output_dir / f"_batch_{batch_no:03d}.png"
        lines = [
            f"Generate {len(batch_items)} separate standalone cinematic 16:9 images.",
            "Do not create a collage, grid, poster, contact sheet, or multi-panel image.",
            "Each requested image must be a separate image output in the same order.",
            "",
        ]
        for item in batch_items:
            lines.append(f"Image {item['image_index']}:")
            lines.append(item["prompt"])
            lines.append("")
        prompt_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        batches.append(
            {
                "batch": batch_no,
                "prompt_file": str(prompt_path),
                "output_stem": str(output_stem),
                "targets": [item["target"] for item in batch_items],
                "image_indexes": [item["image_index"] for item in batch_items],
            }
        )
    chapter_plan = {**chapter, "items": items, "batches": batches, "batch_size": batch_size}
    (prompt_dir / "chapter_plan.json").write_text(
        json.dumps(chapter_plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log(f"prepared chapter {chapter_number} with {len(items)} images in {len(batches)} batches")
    return chapter_plan


def parse_json(stdout):
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start < 0 or end < start:
        raise RuntimeError(stdout[-1000:])
    return json.loads(stdout[start : end + 1])


def parse_rate_limit(stderr):
    if "usage_limit_reached" not in stderr:
        return None
    start = stderr.find("{")
    end = stderr.rfind("}")
    wait_seconds = 900
    reset_at = None
    if start >= 0 and end > start:
        try:
            payload = json.loads(stderr[start : end + 1])
            err = payload.get("error") or {}
            reset_at = err.get("resets_at")
            if isinstance(reset_at, (int, float)):
                wait_seconds = max(60, int(reset_at - time.time()) + 30)
            elif isinstance(err.get("resets_in_seconds"), (int, float)):
                wait_seconds = max(60, int(err["resets_in_seconds"]) + 30)
        except json.JSONDecodeError:
            pass
    return wait_seconds, reset_at


def is_transient(stderr):
    text = stderr.lower()
    return any(
        marker in text
        for marker in [
            "fetch failed",
            "econnreset",
            "etimedout",
            "eai_again",
            "server_error",
            "overloaded",
            "typeerror: terminated",
            "undici",
            "connection terminated",
            "stream terminated",
            "socket hang up",
            # The Codex backend sometimes returns a temporary HTML block page
            # under parallel image load. It includes the OpenAI SVG path in
            # stderr, so classify it as backoff/retry instead of a permanent
            # lane failure.
            "http 403 forbidden",
            "blocked-icon",
            "<html>",
        ]
    )


def run_batches(chapter_plan, start_batch, limit_batches, model, timeout, wait_on_rate_limit, force):
    selected = [batch for batch in chapter_plan["batches"] if batch["batch"] >= start_batch]
    if limit_batches:
        selected = selected[:limit_batches]
    for batch in selected:
        targets = [Path(path) for path in batch["targets"]]
        if not force and all(path.exists() for path in targets):
            log(f"C{chapter_plan['chapter']:03d} batch {batch['batch']:03d}: skip existing")
            continue
        command = [
            "node", str(CODEX_IMAGEN),
            "--json", "--model", model, "--timeout", str(timeout), "--retries", "4",
            "--output", batch["output_stem"],
            "--prompt-file", batch["prompt_file"],
        ]
        attempt = 1
        while True:
            log(f"C{chapter_plan['chapter']:03d} batch {batch['batch']:03d}: start attempt {attempt}")
            completed = subprocess.run(command, cwd=str(ROOT), text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            (LOG_DIR / f"C{chapter_plan['chapter']:03d}_batch_{batch['batch']:03d}.stdout.log").write_text(completed.stdout, encoding="utf-8")
            (LOG_DIR / f"C{chapter_plan['chapter']:03d}_batch_{batch['batch']:03d}.stderr.log").write_text(completed.stderr, encoding="utf-8")
            if completed.returncode == 0:
                break
            rate = parse_rate_limit(completed.stderr)
            if wait_on_rate_limit and rate:
                wait_seconds, reset_at = rate
                log(f"C{chapter_plan['chapter']:03d} batch {batch['batch']:03d}: rate limited, wait {wait_seconds}s reset={reset_at}")
                time.sleep(wait_seconds)
                attempt += 1
                continue
            if wait_on_rate_limit and is_transient(completed.stderr):
                wait_seconds = min(900, 60 * attempt)
                log(f"C{chapter_plan['chapter']:03d} batch {batch['batch']:03d}: transient failure, wait {wait_seconds}s")
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-manifest", action="store_true")
    parser.add_argument("--extract-text", action="store_true")
    parser.add_argument("--prepare-chapter", type=int)
    parser.add_argument("--run-chapter", type=int)
    parser.add_argument("--batch-size", type=int, default=3)
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
        log(f"manifest: {len(manifest['chapters'])} chapters, {manifest['total_minutes']} minutes, {manifest['total_target_images']} images")
    if args.extract_text:
        manifest = load_manifest() if MANIFEST_PATH.exists() else build_manifest(args.images_per_minute)
        extract_chapter_texts(manifest)
    if args.prepare_chapter:
        manifest = load_manifest()
        prepare_chapter_prompts(manifest, args.prepare_chapter, args.batch_size)
    if args.run_chapter:
        manifest = load_manifest()
        chapter_plan_path = PROMPT_DIR / f"C{args.run_chapter:03d}" / "chapter_plan.json"
        if chapter_plan_path.exists():
            chapter_plan = json.loads(chapter_plan_path.read_text(encoding="utf-8"))
        else:
            chapter_plan = prepare_chapter_prompts(manifest, args.run_chapter, args.batch_size)
        run_batches(chapter_plan, args.start_batch, args.limit_batches, args.model, args.timeout, args.wait_on_rate_limit, args.force)


if __name__ == "__main__":
    main()
