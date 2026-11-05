# Decision rules — rules-v1

Frozen and tagged `rules-v1` before any check, split or training run.
Machine-readable copy: `configs/rules.json`. If the two disagree, this file is wrong and must be fixed
with a new tag; no rule changes after a check has run, except via a new tagged version with a reason.

Provenance: drafted with Claude (Desktop chat, 2026-11-05), reviewed and edited by me in the project
chat. My decisions and reasons: hold out 4 counts, light visual check, resolution and blur levels by
pre-registered rules (see ai_log/report_notes.txt).

## 0. Scope
Covers data preparation, baselines, evaluation and test protocol.
Training budget (steps, early stopping) is frozen separately (`rules-v2`) before the first training run.

## 1. Data and scenes
- Source: BBBC005 v1, 19,200 TIF files, expected 520×696 (H×W), uint8. Any file that differs → stop.
- Scene = (count, sample). 600 scenes; each exists at 16 blur levels × 2 stains.

## 2. Split
- `rng = numpy.random.default_rng(42)`; `perm = rng.permutation(numpy.arange(1, 26))`.
  perm[0:15] → train samples, perm[15:20] → val samples, perm[20:25] → test samples.
  One permutation shared by all counts.
- Held-out counts: 14, 40, 66, 91 (interior, spread over the range). Chosen before any image was
  viewed and before any model was run; only file-name statistics and 5 image summaries existed.
  All 25 samples of these counts → `test_unseen`. They never appear in train or val.
- Seen counts (20): train / val / test_seen by the sample permutation above.
- Scenes: train 300, val 100, test_seen 100, test_unseen 100.
- Why by sample index: all images of a scene stay in one split (same layout, r ≈ 0.89 across blur),
  and every count × blur cell is equally represented in every split.
- Why test_unseen may use train sample indices: scenes with the same sample index but a different
  count are independent (inventory control: r = −0.02).
- Source of truth: committed `splits/splits.csv` + `splits/splits.sha256` (numpy version is pinned,
  but the committed file is authoritative).
- "Training scenes" for all checks = train samples × seen counts. "First k training samples"
  = the k smallest train sample indices.

## 3. Stain identity (check A)
- Images: C1 F1, both stains, first 2 training samples. Native resolution, no smoothing.
- Per image: Otsu threshold (foreground = pixel > t), largest connected component.
- Channel X is the nuclei channel if, in both samples:
  containment(X in Y) = |X ∩ Y| / |X| ≥ 0.90 and area(X) / area(Y) ≤ 0.70.
- w2 passes → nuclei = w2 (as documented). w1 passes → nuclei = w1, conflict reported.
  Otherwise → stop; repeat on 5 samples; no cache until resolved.
- Why 0.90: a nucleus lies inside its cell; 10 % covers threshold/blur edge effects.
- Why 0.70: clear size margin; a ratio near 1 means the test cannot tell the channels apart.

## 4. Resolution (checks 1 and 2, nuclei channel, F1)
- Candidates (W×H): 128×96 (factor ≈5.44), 256×192 (≈2.72), 348×260 (2.0).
  Resize: PIL BOX (area averaging). 128×96 changes aspect by 0.4 % — accepted.
- Check 1 (size): C1 F1, first 5 training samples. d_native = equivalent diameter √(4A/π)
  of the largest Otsu component; median over samples. Pass at a candidate if d_native / factor ≥ 3.0 px.
  Why 3 px: smallest blob with a centre pixel brighter than its 3×3 neighbours; below it,
  appearance depends on sub-pixel position (aliasing).
- Check 2 (separation): C100 F1, first 5 training samples.
  Peaks at native: gaussian_filter(σ = 1.0 px), local maxima with maximum_filter
  (window = odd integer nearest to d_native/2, min 3), value > Otsu threshold of the smoothed image.
  Pairs: each peak with its nearest neighbour; unordered, duplicates removed.
  Dip test (unsmoothed image at the resolution tested): 21 points on the segment between the two centres,
  bilinear; centre mapping (r, c) → ((r+0.5)/f_y − 0.5, (c+0.5)/f_x − 0.5).
  Resolved if min(points 1..19) ≤ 0.80 × min(point 0, point 20).
  Pass if ≥ 90 % of pairs resolved at native remain resolved at the candidate.
  Why 0.80: a ≥ 20 % dip is a common "resolved" margin, close to Rayleigh (~26 % dip).
  Why 90 %: tolerance convention; small separability loss at C100 accepted.
- Decision: 128×96 passes both → main 128×96, ablation 256×192.
  Else 256×192 passes → main 256×192, ablation 128×96.
  Else main 348×260, ablation 256×192, reported.
- Never choose resolution by whether the acceptance rule passes (lower resolution weakens MAE_best too).
- Limitation: evidence is geometric; the resolution ablation is the empirical check.

## 5. Blur levels (check B1, chosen resolution, nuclei channel)
- Scenes: first training sample × each of the 20 seen counts.
- hp(img) = img − gaussian_filter(img, σ), σ = d_native / 2 / factor (nucleus radius at chosen resolution).
- D(F) = 1 − mean over scenes of Pearson r(hp(F1), hp(F)).
- K = ceil(D(F48) / 0.20) + 1, clipped to [4, 6].
- Targets t_k = k/(K−1) · D(F48), k = 0..K−1; for each, the unused level with D closest to t_k.
  F1 and F48 always included.
- Why high-pass: raw correlation is dominated by blob positions, which blur does not move (F1↔F48 raw r ≈ 0.89).
- Why 0.20: convention, each step loses ≤ ~20 % of shared fine detail; set so that D(F48) of 0.6–1.0 gives 4–6 levels.
- Why min 4: spec minimum ~2,000 images (4 × 600 = 2,400). Why max 6: energy.

## 6. Preprocessing (identical for every model)
- Input: nuclei channel, chosen blur levels, chosen resolution, cached once as uint8.
- Normalisation: x = (u8/255 − μ) / s, scalar μ, s over all train pixels → `results/norm_stats.json`.
- Target: count / 100; all metrics in cells (prediction × 100).
- Augmentation: horizontal flip p = 0.5, vertical flip p = 0.5. Nothing else (crops change the count).
- Pretrained models: conv1 weights summed over RGB → 1 input channel.
- Predictions used raw: no rounding, no clipping, no snapping to count levels.

## 7. Baselines
- Mean: mean of train targets (expected 50.05). Analytic check: MAE on test_seen = 25.85.
- Brightness: feature = mean pixel value (0–255) of the cached uint8 image at the chosen resolution,
  before normalisation. count = a + b · feature, ordinary least squares (numpy.linalg.lstsq), train only.
  No variants, no background subtraction.

## 8. Evaluation and acceptance
- Metrics: MAE, RMSE, R² (cells). Primary set: test_seen. Diagnostic: test_unseen (never used for decisions).
- MAE_best = lowest test_seen MAE among the standard models. MAE_mean = mean baseline on test_seen.
- Acceptance (decided on point estimates): MAE_own ≤ 1.15 · MAE_best and MAE_own ≤ 0.60 · MAE_mean.
- Uncertainty (reported, does not change the decision): bootstrap over test_seen scenes, B = 10,000,
  seed 42, 95 % percentile CI. Each resample draws 100 scenes with replacement (all K images of a scene go together).
  For the ratio MAE_own / MAE_best the same resampled scenes are used for both models (paired).
  Same procedure for all reported metric CIs.

## 9. Test protocol
- Only `scripts/evaluate_test.py` loads test_seen / test_unseen arrays; training/search scripts load train/val files only.
- One test run per final model: mean baseline, brightness baseline, own CNN, standard model 1, standard model 2.
  One forward pass gives both test_seen and test_unseen numbers.
- A second run needs `--force --reason "..."`; every run (forced or not) is appended to `results/test_log.csv`
  and reported.
- All tuning, early stopping and ablations use val. An ablation variant evaluated on test counts as an extra logged test use.
- Exception, documented: the file-sanity check (check F) reads all 19,200 files, including test files,
  for aggregate statistics only (shape, dtype, min/max/mean). No test image is displayed or used for any choice.

## 10. Carbon tracking
- Every compute script runs inside `tracked_run()` (src/carbon.py): OfflineEmissionsTracker,
  country_iso_code = "TUR", measure_power_secs = 5, stopped in a finally block.
  (OfflineEmissionsTracker with country_iso_code="TUR" already worked in scripts/check_env.py.)
- Run folder `runs/<YYYYMMDD-HHMMSS>_<category>_<model>_<hash4>/` with emissions.csv, config.json, metrics.json.
  Categories: env, preprocess, analysis, baseline, search, train, eval, measure. Status: ok / failed.
- short_run = duration < 3 × measure_power_secs → reported as "below measurement resolution".
- Project total = sum over `runs/index.csv`, failed runs included. Legacy `_env_check` row added without re-running.
- The first run of scripts/data_inventory.py was untracked; it is re-run once under the helper.
