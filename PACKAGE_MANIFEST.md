# haichanly-imagen2 Package Manifest

This is a clean source repo for the Nalas Chapters 008-086 lane-batch image pipeline.

## Included

- `scripts/*.py`: extraction, prompt preparation, auto lane batch, sync, and verification tools.
- `Nalas Nalanda 1 (English).pdf`
- `Nalas Nalanda 2 (English).pdf`
- `Nalas Nalanda 3 (English).pdf`
- `Chapter_8_DNA_Only.md`
- `Chapter_8_Prompt_DNA.md`
- `nalas_chapters_08_86/chapters_manifest.json`
- `nalas_chapters_08_86/lane_pairs_manifest.json`
- `nalas_chapters_08_86/chapter_text/`
- `nalas_chapters_08_86/chapter_visual_briefs/`
- `nalas_chapters_08_86/chapter_story_guides/`
- `nalas_chapters_08_86/character_refs/five_messengers_DNA.md`
- `nalas_chapters_08_86/character_refs/heaven_father_nalas_DNA.md`
- `nalas_chapters_08_86/character_refs/pham_tran_canonical/`
- `nalas_chapters_08_86/character_refs/heaven_father_canonical/`

## Excluded

- Previous generated output images.
- Previous final video image folders.
- Previous generated lane pairs.
- Large generated prompt cache `lane_pair_prompts/`.
- Backup folders, QA contact sheets, debug folders, old style demos, and rejected images.

## Generated At Runtime

These folders will be created by scripts when needed:

- `nalas_chapters_08_86/lane_pair_prompts/`
- `nalas_chapters_08_86/generated_lane_pairs/`
- `nalas_chapters_08_86/final_image_video/`
- `nalas_chapters_08_86/logs/`

The repo is designed so these runtime outputs can be deleted and rebuilt.
