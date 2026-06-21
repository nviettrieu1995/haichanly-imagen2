#!/usr/bin/env python
import argparse
import json
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MD = ROOT / "ke_hoach_prompt_video_tue_linh_DNA_prompt_chuan.md"
CODEX_IMAGEN = Path.home() / ".codex" / "skills" / "codex-imagen" / "scripts" / "codex-imagen.mjs"
BASE_PROMPT_DIR = ROOT / "01_PROMPT_DNA" / "CH08_full_25min_base_batches"
BASE_OUT_DIR = ROOT / "03_IMAGES_SCENES" / "CH08_full_25min_base"
MIN46_PROMPT_DIR = ROOT / "01_PROMPT_DNA" / "CH08_full_25min_min46_batches"
MIN46_OUT_DIR = ROOT / "03_IMAGES_SCENES" / "CH08_full_25min_min46"
FULL100_PROMPT_DIR = ROOT / "01_PROMPT_DNA" / "CH08_full_25min_full100_batches"
FULL100_OUT_DIR = ROOT / "03_IMAGES_SCENES" / "CH08_full_25min_full100"
STARTEND_PROMPT_DIR = ROOT / "01_PROMPT_DNA" / "CH08_start_end_batches"
STARTEND_OUT_DIR = ROOT / "02_IMAGES_START_END"
LOG_DIR = ROOT / "logs"


def log(message):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    with (LOG_DIR / "ch08_auto_lane_batch.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def ascii_slug(value):
    value = value.translate(str.maketrans({"đ": "d", "Đ": "D"}))
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return value[:54] or "scene"


def extract_scenes():
    text = SOURCE_MD.read_text(encoding="utf-8-sig")
    section_match = re.search(
        r"^# PHẦN 3 .*?VIDEO 25 PHÚT\s*(.*?)^# PHẦN 4 ",
        text,
        re.S | re.M,
    )
    if not section_match:
        raise RuntimeError("Cannot find PHAN 3 / PHAN 4 scene prompt section")
    section = section_match.group(1)
    scene_re = re.compile(r"^## Cảnh\s+(\d+)\s+—\s+(.+?)\s*$", re.M)
    matches = list(scene_re.finditer(section))
    scenes = []
    for index, match in enumerate(matches):
        scene_no = int(match.group(1))
        title = match.group(2).strip()
        block_start = match.end()
        block_end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        block = section[block_start:block_end]
        duration_match = re.search(r"\*\*Thời lượng:\*\*\s*([^\n]+)", block)
        duration = duration_match.group(1).strip() if duration_match else ""
        prompt_match = re.search(
            r"### Prompt ảnh(?: kết thúc)?\s*\n\s*```text\s*\n(.*?)\n```",
            block,
            re.S,
        )
        if not prompt_match:
            raise RuntimeError(f"Missing image prompt for scene {scene_no}")
        slug = ascii_slug(title)
        scenes.append(
            {
                "scene": scene_no,
                "title": title,
                "duration": duration,
                "filename": f"S{scene_no:02d}_{slug}_v01.png",
                "prompt": prompt_match.group(1).strip(),
            }
        )
    return scenes


def extract_start_end():
    text = SOURCE_MD.read_text(encoding="utf-8-sig")
    section_match = re.search(
        r"^# PHẦN 9 .*?BẢN CHUẨN DNA\s*(.*?)^# PHẦN 10 ",
        text,
        re.S | re.M,
    )
    if not section_match:
        raise RuntimeError("Cannot find PHAN 9 start/end prompt section")
    blocks = re.findall(r"```text\s*\n(.*?)\n```", section_match.group(1), re.S)
    if len(blocks) < 2:
        raise RuntimeError("Cannot extract both opening and ending prompts")
    return [
        {
            "scene": 0,
            "title": "Opening image",
            "duration": "intro",
            "variant": 1,
            "filename": "CH08_opening_v01.png",
            "prompt": blocks[0].strip(),
        },
        {
            "scene": 99,
            "title": "Ending image",
            "duration": "outro",
            "variant": 1,
            "filename": "CH08_ending_v01.png",
            "prompt": blocks[1].strip(),
        },
    ]


def expand_with_counts(scenes, counts):
    roles = [
        "wide establishing shot for the start of this scene",
        "medium cinematic shot focusing on the main action and readable subject",
        "close detail or transition shot for slow audiobook pacing",
        "alternate angle with deeper atmosphere and clear visual continuity",
        "final transitional image that prepares the next scene",
        "slow atmospheric insert for extended narration pacing",
        "symbolic visual detail that can hold under voice-over",
        "secondary wide shot with a different camera distance",
        "quiet contemplative image for slow zoom in CapCut",
        "luminous transition frame for crossfade editing",
        "extra continuity shot preserving the same world and energy palette",
        "closing beat for this long scene before moving onward",
    ]
    expanded = []
    for scene in scenes:
        count = counts.get(scene["scene"], 1)
        for variant in range(1, count + 1):
            item = dict(scene)
            item["variant"] = variant
            item["asset_id"] = f"S{scene['scene']:02d}_v{variant:02d}"
            item["filename"] = f"S{scene['scene']:02d}_{ascii_slug(scene['title'])}_v{variant:02d}.png"
            item["prompt"] = (
                f"{scene['prompt']}\n\n"
                f"Shot role for this generated image: {roles[min(variant - 1, len(roles) - 1)]}. "
                "Keep it as one standalone 16:9 cinematic frame, no text, no watermark."
            )
            expanded.append(item)
    return expanded


def expand_min46(scenes):
    expanded = expand_with_counts(scenes, {
        1: 3,
        2: 3,
        3: 2,
        4: 3,
        5: 3,
        6: 3,
        7: 3,
        8: 3,
        9: 5,
        10: 3,
        11: 3,
        12: 3,
        13: 3,
        14: 3,
        15: 2,
        16: 1,
    })
    if len(expanded) != 46:
        raise RuntimeError(f"min46 profile produced {len(expanded)} images instead of 46")
    return expanded


def expand_full100(scenes):
    expanded = expand_with_counts(scenes, {
        1: 6,
        2: 6,
        3: 4,
        4: 6,
        5: 6,
        6: 6,
        7: 8,
        8: 6,
        9: 12,
        10: 6,
        11: 8,
        12: 6,
        13: 6,
        14: 6,
        15: 6,
        16: 2,
    })
    if len(expanded) != 100:
        raise RuntimeError(f"full100 profile produced {len(expanded)} images instead of 100")
    return expanded


def write_batch_files(scenes, batch_size, prompt_dir, out_dir):
    prompt_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    batches = []
    for start in range(0, len(scenes), batch_size):
        batch = scenes[start : start + batch_size]
        batch_no = len(batches) + 1
        prompt_path = prompt_dir / f"CH08_lane_batch_{batch_no:02d}.txt"
        output_stem = out_dir / f"_lane_batch_{batch_no:02d}.png"
        lines = [
            f"Generate {len(batch)} separate cinematic 16:9 images for Chapter 08 / full 25-minute video storyboard.",
            "Do not make a collage, grid, contact sheet, poster, or multi-panel layout.",
            "Each requested scene must be a separate standalone image output, in the same order as listed.",
            "No text, no watermark, no logo in any image. Preserve character DNA and negative prompts exactly when present.",
            "",
        ]
        for item_index, scene in enumerate(batch, start=1):
            lines.append(
                f"Image {item_index} - Scene {scene['scene']:02d}"
                f"{' / variant ' + str(scene.get('variant')) if scene.get('variant') else ''}: "
                f"{scene['title']} ({scene['duration']})"
            )
            lines.append(scene["prompt"])
            lines.append("")
        prompt_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        batches.append(
            {
                "batch": batch_no,
                "prompt_file": str(prompt_path),
                "output_stem": str(output_stem),
                "scene_numbers": [scene["scene"] for scene in batch],
                "targets": [str(out_dir / scene["filename"]) for scene in batch],
            }
        )
    manifest = {
        "source": str(SOURCE_MD),
        "prompt_dir": str(prompt_dir),
        "output_dir": str(out_dir),
        "batch_size": batch_size,
        "scene_count": len(scenes),
        "scenes": scenes,
        "batches": batches,
    }
    (prompt_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return batches


def parse_json(stdout):
    stdout = stdout.strip()
    if not stdout:
        raise RuntimeError("codex-imagen returned empty stdout")
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start < 0 or end < start:
        raise RuntimeError(f"Cannot find JSON in stdout: {stdout[:300]}")
    return json.loads(stdout[start : end + 1])


def parse_rate_limit(stderr):
    if "usage_limit_reached" not in stderr:
        return None
    start = stderr.find("{")
    end = stderr.rfind("}")
    if start < 0 or end < start:
        return {"wait_seconds": 15 * 60, "message": "usage limit reached"}
    try:
        payload = json.loads(stderr[start : end + 1])
    except json.JSONDecodeError:
        return {"wait_seconds": 15 * 60, "message": "usage limit reached"}
    error = payload.get("error") or {}
    reset_at = error.get("resets_at")
    wait_seconds = error.get("resets_in_seconds")
    if isinstance(reset_at, (int, float)):
        wait_seconds = max(60, int(reset_at - time.time()) + 30)
    elif isinstance(wait_seconds, (int, float)):
        wait_seconds = max(60, int(wait_seconds) + 30)
    else:
        wait_seconds = 15 * 60
    return {
        "wait_seconds": wait_seconds,
        "message": error.get("message") or "usage limit reached",
        "resets_at": reset_at,
    }


def is_transient_failure(stderr):
    transient_markers = [
        "fetch failed",
        "transient generation failure",
        "ECONNRESET",
        "ETIMEDOUT",
        "EAI_AGAIN",
        "server_error",
        "overloaded",
        "temporarily unavailable",
        "network",
    ]
    lowered = stderr.lower()
    return any(marker.lower() in lowered for marker in transient_markers)


def run_batch(batch, model, timeout_seconds, force, wait_on_rate_limit):
    target_paths = [Path(path) for path in batch["targets"]]
    if not force and all(path.exists() for path in target_paths):
        log(f"batch {batch['batch']:02d}: skip, all targets already exist")
        return "skipped"

    command = [
        "node",
        str(CODEX_IMAGEN),
        "--json",
        "--model",
        model,
        "--timeout",
        str(timeout_seconds),
        "--retries",
        "4",
        "--output",
        batch["output_stem"],
        "--prompt-file",
        batch["prompt_file"],
    ]
    attempt = 1
    while True:
        log(f"batch {batch['batch']:02d}: start scenes {batch['scene_numbers']} attempt {attempt}")
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode == 0:
            break
        rate_limit = parse_rate_limit(completed.stderr)
        if not (wait_on_rate_limit and rate_limit):
            if not (wait_on_rate_limit and is_transient_failure(completed.stderr)):
                break
            wait_seconds = min(900, 60 * attempt)
            log(f"batch {batch['batch']:02d}: transient failure, waiting {wait_seconds}s before retry")
        else:
            wait_seconds = rate_limit["wait_seconds"]
            reset_at = rate_limit.get("resets_at")
            reset_note = f" resets_at={reset_at}" if reset_at else ""
            log(
                f"batch {batch['batch']:02d}: rate limited, waiting {wait_seconds}s before retry{reset_note}"
            )
        time.sleep(wait_seconds)
        attempt += 1

    (LOG_DIR / f"ch08_batch_{batch['batch']:02d}.stdout.log").write_text(
        completed.stdout,
        encoding="utf-8",
    )
    (LOG_DIR / f"ch08_batch_{batch['batch']:02d}.stderr.log").write_text(
        completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        log(f"batch {batch['batch']:02d}: failed exit={completed.returncode}")
        raise RuntimeError(completed.stderr[-1200:] or completed.stdout[-1200:])

    result = parse_json(completed.stdout)
    images = result.get("images") or []
    if len(images) < len(target_paths):
        log(f"batch {batch['batch']:02d}: only {len(images)} images for {len(target_paths)} targets")
        raise RuntimeError("codex-imagen returned fewer images than requested")

    for image, target in zip(images, target_paths):
        source = Path(image["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and force:
            target.unlink()
        if target.exists():
            log(f"batch {batch['batch']:02d}: keep existing {target.name}")
            continue
        source.replace(target)
        log(f"batch {batch['batch']:02d}: saved {target.name}")
    return "done"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=3)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--limit-batches", type=int, default=0)
    parser.add_argument("--start-batch", type=int, default=1)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--profile", choices=["base", "min46", "full100", "startend"], default="base")
    parser.add_argument("--wait-on-rate-limit", action="store_true")
    parser.add_argument("--missing-only", action="store_true")
    args = parser.parse_args()

    scenes = extract_scenes()
    if args.profile == "startend":
        scenes = extract_start_end()
        prompt_dir = STARTEND_PROMPT_DIR
        out_dir = STARTEND_OUT_DIR
    elif args.profile == "min46":
        scenes = expand_min46(scenes)
        prompt_dir = MIN46_PROMPT_DIR
        out_dir = MIN46_OUT_DIR
    elif args.profile == "full100":
        scenes = expand_full100(scenes)
        prompt_dir = FULL100_PROMPT_DIR
        out_dir = FULL100_OUT_DIR
    else:
        prompt_dir = BASE_PROMPT_DIR
        out_dir = BASE_OUT_DIR
    if args.missing_only:
        scenes = [scene for scene in scenes if not (out_dir / scene["filename"]).exists()]
    batches = write_batch_files(scenes, args.batch_size, prompt_dir, out_dir)
    log(f"prepared {len(scenes)} scenes into {len(batches)} batches")
    if args.prepare_only:
        return

    selected = [batch for batch in batches if batch["batch"] >= args.start_batch]
    if args.limit_batches:
        selected = selected[: args.limit_batches]
    for batch in selected:
        run_batch(batch, args.model, args.timeout, args.force, args.wait_on_rate_limit)
    log("lane batch finished")


if __name__ == "__main__":
    main()
