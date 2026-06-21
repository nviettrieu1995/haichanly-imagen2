# haichanly-imagen2

Clean, portable repo for generating Chapters 008-086 as start/end lane pairs for audiobook video production.

This package intentionally does not include previously generated output images. It includes the source books, chapter text, current art direction, DNA/reference files, and scripts needed to regenerate lane prompts and run auto lane batch.

## What Is Included

- Source PDFs: `Nalas Nalanda 1/2/3 (English).pdf`
- Chapter text: `nalas_chapters_08_86/chapter_text/C008-C086.txt`
- Chapter-level visual/story guides: `chapter_visual_briefs` and `chapter_story_guides`
- Character DNA:
  - `Chapter_8_Prompt_DNA.md`
  - `Chapter_8_DNA_Only.md`
  - `nalas_chapters_08_86/character_refs/five_messengers_DNA.md`
  - `nalas_chapters_08_86/character_refs/heaven_father_nalas_DNA.md`
- Canonical editable refs:
  - Mortal pham-tran Nalas: `character_refs/pham_tran_canonical/pham_tran_canonical.png`
  - Heaven Father Nalas: `character_refs/heaven_father_canonical/heaven_father_canonical.png`
- Batch scripts in `scripts/`

## What Is Not Included

Generated outputs are excluded:

- `nalas_chapters_08_86/generated_images/`
- `nalas_chapters_08_86/generated_lane_pairs/`
- `nalas_chapters_08_86/final_image_video/`
- `nalas_chapters_08_86/logs/`
- `nalas_chapters_08_86/qa_*`
- `nalas_chapters_08_86/debug/`
- Large prompt cache `nalas_chapters_08_86/lane_pair_prompts/`

The lane prompt cache is generated automatically by the runner. Keeping it out makes the repo much smaller and easier to move between machines.

## Requirements

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Required local tools:

- Python 3.11+
- Node.js 22+
- `codex-imagen` installed at:

```text
~/.codex/skills/codex-imagen/scripts/codex-imagen.mjs
```

The scripts use that path automatically through `Path.home()`.

## Quick Start: Auto Lane Batch

From the repo root:

```powershell
$env:PYTHONUTF8 = "1"
python -u .\scripts\nalas_parallel_lane_batch_runner.py --start-chapter 8 --end-chapter 86 --pairs-per-batch 1 --max-workers 1 --model gpt-5.5 --timeout 900 --job-retries 1 --wait-on-rate-limit
```

The first run will:

1. Build or normalize the chapter manifest.
2. Extract chapter text if needed.
3. Generate missing lane pair prompts into `nalas_chapters_08_86/lane_pair_prompts/`.
4. Generate images into `nalas_chapters_08_86/generated_lane_pairs/`.

To mirror valid generated pairs into the final video folder while the runner works, open another PowerShell window:

```powershell
python -u .\scripts\nalas_sync_final_images.py --start-chapter 8 --end-chapter 86 --watch --interval 15
```

Verify final coverage:

```powershell
python .\scripts\nalas_verify_final_images.py --start-chapter 8 --end-chapter 86
```

Expected complete target for Chapters 008-086:

```text
pairs=5294/5294 images=10588/10588 invalid=0 extras=0
```

## Run One Chapter

Prepare prompts and run only Chapter 21:

```powershell
python -u .\scripts\nalas_parallel_lane_batch_runner.py --start-chapter 21 --end-chapter 21 --pairs-per-batch 1 --max-workers 1 --model gpt-5.5 --timeout 900 --job-retries 1 --wait-on-rate-limit
python .\scripts\nalas_sync_final_images.py --chapter 21
python .\scripts\nalas_verify_final_images.py --chapter 21
```

Only run heaven lanes:

```powershell
python -u .\scripts\nalas_parallel_lane_batch_runner.py --start-chapter 21 --end-chapter 21 --only-divine-ref --pairs-per-batch 1 --max-workers 1 --model gpt-5.5 --timeout 900 --wait-on-rate-limit
```

Only run non-heaven/Earth lanes:

```powershell
python -u .\scripts\nalas_parallel_lane_batch_runner.py --start-chapter 21 --end-chapter 21 --exclude-divine-ref --pairs-per-batch 1 --max-workers 1 --model gpt-5.5 --timeout 900 --wait-on-rate-limit
```

## Editing Workflow

Edit chapter text:

```text
nalas_chapters_08_86/chapter_text/C0XX.txt
```

Edit chapter visual/story direction:

```text
nalas_chapters_08_86/chapter_visual_briefs/C0XX.md
nalas_chapters_08_86/chapter_story_guides/C0XX.md
```

Edit global DNA:

```text
Chapter_8_Prompt_DNA.md
Chapter_8_DNA_Only.md
nalas_chapters_08_86/character_refs/five_messengers_DNA.md
nalas_chapters_08_86/character_refs/heaven_father_nalas_DNA.md
```

Edit canonical references by replacing:

```text
nalas_chapters_08_86/character_refs/pham_tran_canonical/pham_tran_canonical.png
nalas_chapters_08_86/character_refs/heaven_father_canonical/heaven_father_canonical.png
```

After editing one chapter, rebuild that chapter prompt cache:

```powershell
python .\scripts\nalas_lane_pair_pipeline.py --prepare-chapter 21 --pairs-per-batch 1
```

Then rerun with `--force` only if you want to replace existing generated images:

```powershell
python -u .\scripts\nalas_parallel_lane_batch_runner.py --start-chapter 21 --end-chapter 21 --pairs-per-batch 1 --max-workers 1 --model gpt-5.5 --timeout 900 --job-retries 1 --wait-on-rate-limit --force
```

## Current Art Direction Lock

- Earth/pham-tran scenes: modern Vietnamese city/district life, not old rural hut imagery.
- Covid/post-Covid teaching scenes: modern office/classroom, LED or tube lights, whiteboard/magnetic board, markers, desks/chairs.
- Mortal Nalas: Vietnamese father-teacher, thin metal glasses always visible, including sleep.
- Heaven Father Nalas: stable Western sacred/Sacred-Heart-Jesus-like form, apparent age 40-42.
- Only Father has Sacred Heart/radiant chest. Messengers must not have heart-shaped chest lights or Father clones.
- Five messengers must stay role-distinct: Giac gold-white insight, Chap rose/amber compassion, blue-white law/order, green-gold healing, silver-violet transmission.

See the DNA files for the full current rules.
