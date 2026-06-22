# Runbook

## Prepare Environment

```powershell
python -m pip install -r requirements.txt
node --version
```

Make sure this file exists:

```text
~/.codex/skills/codex-imagen/scripts/codex-imagen.mjs
```

## Full Auto Lane Batch

Preflight prompt coverage after preparing/regenerating prompts:

```powershell
python .\scripts\nalas_verify_prompt_coverage.py --start-chapter 8 --end-chapter 86
```

Terminal 1:

```powershell
$env:PYTHONUTF8 = "1"
python -u .\scripts\nalas_parallel_lane_batch_runner.py --start-chapter 8 --end-chapter 86 --pairs-per-batch 1 --max-workers 1 --model gpt-5.5 --timeout 900 --job-retries 1 --wait-on-rate-limit
```

Terminal 2:

```powershell
python -u .\scripts\nalas_sync_final_images.py --start-chapter 8 --end-chapter 86 --watch --interval 15
```

Verification:

```powershell
python .\scripts\nalas_verify_final_images.py --start-chapter 8 --end-chapter 86
```

## Regenerate Chapter Guides

```powershell
python .\scripts\nalas_build_story_guides.py --start-chapter 8 --end-chapter 86 --force
python .\scripts\nalas_build_visual_briefs.py --start-chapter 8 --end-chapter 86 --force
python .\scripts\nalas_verify_prompt_coverage.py --start-chapter 8 --end-chapter 86 --skip-prompts
```

## Regenerate One Chapter Prompt Cache

```powershell
python .\scripts\nalas_lane_pair_pipeline.py --prepare-chapter 21 --pairs-per-batch 1
python .\scripts\nalas_verify_prompt_coverage.py --chapter 21
```

## Replace One Chapter Images

```powershell
python -u .\scripts\nalas_parallel_lane_batch_runner.py --start-chapter 21 --end-chapter 21 --pairs-per-batch 1 --max-workers 1 --model gpt-5.5 --timeout 900 --job-retries 1 --wait-on-rate-limit --force
python .\scripts\nalas_sync_final_images.py --chapter 21
python .\scripts\nalas_verify_final_images.py --chapter 21
```

## Notes

- Use `--pairs-per-batch 1` for the safest 2-image start/end batch behavior.
- Raise `--max-workers` only if the account quota and backend stability allow it.
- If a package is moved to a different path, the scripts normalize stale manifest paths and regenerate stale lane plans automatically.
