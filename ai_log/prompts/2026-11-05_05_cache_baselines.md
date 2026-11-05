# Prompt: cache and baselines

Date: 2026-11-05. Given verbatim to Claude Code (claude-opus-5-5). The text below is unchanged.

````text
Context: CSE655 project, repo = current folder. Read docs/decision_rules.md (rules-v1.1),
configs/rules.json and results/decisions/*.json first; follow them exactly. Windows, .venv,
install nothing, do not search outside Project/. Commit every script BEFORE running it.
Keep code simple and commented (exam).

0. Move report_notes.txt and ai_journal_notes.md from the Project/ root into ai_log/ (overwrite).

1. src/metrics.py: mae, rmse, r2 (in cells), and scene-level bootstrap exactly as section 8
   (B=10,000, seed 42, 95% percentile CI, resample scenes with all their images, paired option
   for the ratio of two models). Add a tiny self-test on synthetic numbers (no real data).

2. scripts/build_cache.py, tracked_run(category="preprocess", model="none"):
   - Inputs: splits/splits.csv, stain.json, resolution.json, blur_levels.json.
   - Images: nuclei stain from stain.json, blur levels from blur_levels.json, all splits.
   - Build BOTH resolutions in this one run: main and ablation from resolution.json
     (PIL BOX resize, uint8). Reason: the ablation needs the same images, and one read of the
     TIFs is cheaper than two.
   - Write data/cache/{split}_{WxH}.npz with: images (uint8, N x H x W), count, blur, scene_id.
   - Normalisation stats per resolution from TRAIN pixels only -> results/norm_stats.json.
   - results/cache_manifest.json: file names, shapes, SHA-256 of each npz, image counts per split.
   - Checks printed as PASS/FAIL: image counts 1200/400/400/400 per resolution; every scene has
     exactly 4 images (one per blur level); no NaN; dtype uint8; train mean target = 50.05.

3. scripts/baselines.py, tracked_run(category="baseline", model="mean_and_brightness"):
   - Reads TRAIN and VAL caches at the MAIN resolution only. Must not open any test file.
   - Mean baseline: predict the train mean for every val image.
   - Brightness baseline (section 7, fixed in advance): feature = mean uint8 pixel value of the
     cached image; OLS count = a + b*feature fitted on train only; predict val.
   - Report val MAE, RMSE, R2 with scene bootstrap CIs; also MAE per blur level.
   - Save fitted parameters to results/baselines/brightness_params.json and the val results to
     results/baselines_val.json and results/baselines_val_per_blur.csv.
   - Also print the analytic check: test_seen MAE of the mean baseline should be 25.85
     (computed from labels in splits.csv only, without opening test images).

4. Commit all outputs and run folders, tag cache-v1, push. STOP: no model code, no training.

Session log as usual: ai_log/prompts and ai_log/sessions, 2026-11-05_05_cache_baselines.

Summary: all PASS/FAIL, cache sizes on disk, norm stats, baseline val numbers with CIs and per
blur level, brightness fit (a, b), energy and duration per run, anything unexpected.
````
