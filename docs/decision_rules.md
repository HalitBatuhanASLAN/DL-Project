# Decision rules — rules-v2.1

`rules-v1` was frozen and tagged before any check, split or training run. `rules-v1.1` revises
check 2 of section 4 after that check had run; see "Changes from rules-v1". `rules-v2` freezes
training, measurement and reporting before the first training run; see "Changes from rules-v1.1".
`rules-v2.1` changes the initialisation of the output layer (section 11.1) before any LR search or
real training; see "Changes from rules-v2".
Machine-readable copy: `configs/rules.json`. If the two disagree, this file is wrong and must be fixed
with a new tag; no rule changes after a check has run, except via a new tagged version with a reason.

Provenance: drafted with Claude (Desktop chat, 2026-11-05), reviewed and edited by me in the project
chat. My decisions and reasons: hold out 4 counts, light visual check, resolution and blur levels by
pre-registered rules (see ai_log/report_notes.txt).

## Changes from rules-v2
- Changed: section 11.1 only. The weights of the final linear layer start at zero for every
  model (own_cnn, own_cnn_ds, resnet18, mobilenet_v3_small); its bias stays 0.5005. Every other
  layer is unchanged. `configs/rules.json`: `training.output_weight_init = "zeros"`.
- Reason (mine, verbatim): "Every model then starts by predicting the training mean, which is
  exactly the mean baseline, so no model wastes its first steps. ResNet-18 started at about
  131 cells error with the default head initialisation. The same rule for all models keeps
  the comparison fair."
- Observation that led to it: in the infra-v1 smoke tests (20 steps, before any LR search),
  ResNet-18 started at about 131 cells error despite the output bias 0.5005, because the new head
  used the default initialisation on 512 features. After 20 steps ResNet-18 (val MAE 56.75) and
  MobileNetV3-Small (50.41) were still worse than the mean baseline (25.85 on val).
- Timing: the decision was recorded on 2026-11-05 (ai_log notes) and implemented on 2026-11-10.
  No training, LR search or test run happened in between; only the 20-step smoke tests existed.
- Consequence: at step 0 every model predicts 50.05 cells for every image, so its val MAE equals
  the mean baseline (25.85). Checked by the init check (tag `infra-v1.1`). With zero head weights
  the first backward pass reaches only the head; the rest of the network gets a gradient from
  step 2 on, once the head weights are non-zero.

## Changes from rules-v1.1
- Added: section 11. Changed: sections 0, 9 and 10. Sections 1-8 are unchanged, including the
  acceptance rule.
- State at freezing: no model trained, no LR search run, no test metric computed. Val baselines
  are known (mean MAE 25.85, brightness MAE 1.08).
- Disclosure: the comparison with the brightness baseline was added after seeing that val result.
  The section 9 exception for build_cache.py and the tracking of all runs were written after
  those runs had happened; they describe past behaviour and do not make it pre-registered.
- Correction before freezing: my first wording of the own-CNN reason said the network sees "about
  6 nuclei" at once. That was wrong: 38 px is about 6.5 nucleus diameters across, a width and not
  a number of nuclei, and an area that wide can hold far more than 6 nuclei at high counts.
  Section 11 has the corrected reason.

## Changes from rules-v1
- What changed (section 4, check 2 only):
  peak smoothing σ = 1.0 px → σ = d_native / 4; new condition that a pair counts as a candidate
  pair only if its centres are ≥ d_native / 2 apart. The window wording is kept as "odd integer
  nearest to d_native/2", which is the same 15 px as before at d_native = 31.7 px.
  Everything else is unchanged: 0.80 dip, 0.90 retention, 21 points, candidate order, ablation mapping.
- Principle (the only one): peaks and pairs are measured at nucleus scale. d_native = 31.7 px, and
  the rules-v1 detector worked at sub-nucleus scale (σ 1 px, window 15 px).
- Reason: check 2 is meant to test whether separate nuclei stay separate. Under rules-v1 it mostly
  tested texture inside single nuclei: 164, 154, 157, 160, 185 peaks in 100-nuclei images (samples
  1, 4, 7, 8, 10), and 80 % of the 540 pairs closer than one nucleus diameter.
- rules-v1 outcome: check 1 passed at all candidates. Check 2 retention (299 pairs resolved at
  native): 128×96 0.63, 256×192 0.86, 348×260 0.8997 (269 of 299). No candidate passed both, so the
  fallback applied: main 348×260, ablation 256×192. Blur levels F1, F23, F39, F48, K = 4.
  Tag `data-v1`; decision files kept as `results/decisions/*_v1.json`.
- Disclosure: this revision was made after seeing that outcome, and after seeing a diagnostic on
  the same pairs (retention 0.95 / 0.99 / 1.00 for pairs ≥ d_native apart). It is not pre-registered
  in the sense of rules-v1. The values follow from the principle and were not tuned to a result.
- Stain result (section 3, rule unchanged, check not repeated): nuclei = w1, in conflict with the
  BBBC page, which says w2. C1 F1, samples 1 and 4: containment(w1 in w2) 1.00 / 1.00, area ratio
  0.31 / 0.25. `results/decisions/stain.json` stands.

## 0. Scope
Covers data preparation, baselines, evaluation and test protocol.
Training, measurement and reporting are frozen in section 11 (`rules-v2`), before the first
training run.

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
  Peaks at native: gaussian_filter(σ = d_native/4), local maxima with maximum_filter
  (window = odd integer nearest to d_native/2, min 3), value > Otsu threshold of the smoothed image.
  Pairs: each peak with its nearest neighbour; unordered, duplicates removed. Of these, only pairs
  with centres ≥ d_native/2 apart are candidate pairs; all counts below are over candidate pairs.
  Dip test (unsmoothed image at the resolution tested): 21 points on the segment between the two centres,
  bilinear; centre mapping (r, c) → ((r+0.5)/f_y − 0.5, (c+0.5)/f_x − 0.5).
  Resolved if min(points 1..19) ≤ 0.80 × min(point 0, point 20).
  Pass if ≥ 90 % of pairs resolved at native remain resolved at the candidate.
  Why d_native/4 and d_native/2: peaks and pairs are measured at nucleus scale, not on texture.
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
- Exception, documented: `scripts/build_cache.py` reads the test TIFs to write the test cache, and
  reads the test npz files back for format checks (shape, dtype, image count, scene structure,
  NaN, SHA-256). No test pixel statistic is reported or used for any choice.
- `scripts/evaluate_test.py` saves one row per test image (model, scene_id, count, blur, prediction)
  to `results/test_predictions/`. Paired ratios and residuals are computed from those rows, so no
  test image is loaded again.

## 10. Carbon tracking
- Every compute script runs inside `tracked_run()` (src/carbon.py): OfflineEmissionsTracker,
  country_iso_code = "TUR", measure_power_secs = 5, stopped in a finally block.
  (OfflineEmissionsTracker with country_iso_code="TUR" already worked in scripts/check_env.py.)
- Run folder `runs/<YYYYMMDD-HHMMSS>_<category>_<model>_<hash4>/` with emissions.csv, config.json, metrics.json.
  Categories: env, preprocess, analysis, baseline, search, train, eval, measure. Status: ok / failed.
- short_run = duration < 3 × measure_power_secs → reported as "below measurement resolution".
- Project total = sum over `runs/index.csv`, failed runs included. Legacy `_env_check` row added without re-running.
- The first run of scripts/data_inventory.py was untracked; it is re-run once under the helper.
- Every run, including size checks and self-tests, runs inside `tracked_run()`.
- A run is any execution of a project script, or any code that loads data or builds a model.
  Git commands, shell one-liners that load no data, and reading or editing log files are not runs.
- Runs that were not tracked are added to `runs/index.csv` with `append_index_row`: energy and
  emissions stay empty, duration is approximate, and the notes column says "untracked, not measured".
  The project total includes their duration but no energy for them.

## 11. Training, measurement and reporting

### Decisions and reasons
- Own CNN: design B, 4 blocks 16-32-64-64, avg-pool after blocks 1-3, GAP, linear. The
  depthwise-separable variant (blocks 2-4) is the 2nd ablation.
  Reason: It is small and simple, I can compute every layer by hand,
  and its last layer sees an area about 6.5 nucleus diameters wide.
- Seeds: own CNN and MobileNetV3-Small with 3 seeds (42, 43, 44) on val; ResNet-18 with 1 seed (42).
  Seed 42 is the final model for each test run, fixed now.
  Reason: Repeating the small models is cheap, but ResNet-18 is about 11 times more expensive
  per step, so I run it only once to save energy.
- Budget: max 3,000 steps with the early-stopping rule below.
  Reason: 1,500 steps may be too short for a model trained from scratch, and early stopping
  will stop it sooner if it stops improving.
- "CNN beats brightness" = the 95% paired scene-bootstrap CI of MAE_cnn / MAE_brightness on
  test_seen lies entirely below 1; the energy ratio is reported next to it. Energy ratio = gross
  energy per 1,000 predictions on CPU, for both models. Training energy is reported as absolute
  values, with no ratio.
  Reason: The test set has only 100 scenes, so a small difference can be just noise; I only
  call it a win if the whole interval is below 1.
- The acceptance rule of section 8 stays as the course defines it. Every model is also compared
  with the brightness baseline (error and energy).

### 11.1 Models
- Own CNN, input 1 x 96 x 128. Block = 3x3 conv (padding 1, no bias), BatchNorm, ReLU.
  Blocks 16-32-64-64, 2x2 average pooling after blocks 1-3, GAP, linear to 1 output.
  60,465 parameters, 37,158,976 MACs, receptive field 38 px at the last conv.
- Standard models: ResNet-18 and MobileNetV3-Small, ImageNet weights (IMAGENET1K_V1), stock
  architecture, same input and normalisation as the own CNN.
  Conv1 weights summed over RGB (section 6). Last linear layer replaced by 1 output.
  MobileNet classifier dropout set to 0. All layers trained with one LR; BatchNorm in train mode.
- Every model: the final linear layer starts with all weights 0 and bias 0.5005, so every model
  starts by predicting the training mean (the mean baseline). Other new layers use the PyTorch
  default initialisation. (rules-v2.1)
- ImageNet weights: one-time download inside `tracked_run` (category env), recorded in the README
  with file hashes. Their pre-training footprint is discussed qualitatively in the report.

### 11.2 Training (identical for every model)
- Loss L1 on count / 100. AdamW, weight decay 1e-4 on all parameters.
- Cosine LR from the chosen value to 0 over 3,000 steps, no warm-up.
- Batch size 32, drop_last. Data held as tensors on the GPU, no workers.
- Mixed precision off, except the one measured run in 11.5.
- cudnn.deterministic = True, cudnn.benchmark = False. Python, NumPy, torch and CUDA seeds all fixed.

### 11.3 Early stopping (identical for every model)
- Evaluate val MAE in cells, in eval mode, every 150 steps.
- Improvement = val MAE ≤ best − 0.02 cells. An improvement saves the checkpoint and resets
  the counter; anything else adds 1 to the counter.
- Stop at the first evaluation with step ≥ 1,500 and counter ≥ 6, otherwise at step 3,000.
- The saved checkpoint is the model. Evaluations count as part of the run.

### 11.4 LR search
- Grid 1e-4, 3e-4, 1e-3, 3e-3, 300 steps each, full train set, seed 42, cosine over 300 steps.
- Each trial is its own tracked run, category search.
- Choice: lowest val MAE at step 300; a tie goes to the lower LR.
- If the best LR is on the edge of the grid, one more value beyond it (3e-5 below, 1e-2 above),
  for any model. Same choice rule.
- Ablations and the mixed-precision runs reuse the LR of their parent model.

### 11.5 Ablations and efficiency runs (val only, seed 42, own CNN unless stated)
- Resolution: same network at 256x192.
- Depthwise-separable: blocks 2-4 become 3x3 depthwise, BN, ReLU, 1x1, BN, ReLU.
  8,449 parameters, 6,475,840 MACs.
- Mixed precision: ResNet-18, seed 42, same LR, same training rules.
- Noise reference for that comparison: one ResNet-18 repeat without mixed precision, 600 steps,
  seed 42, same LR. The mixed-precision comparison uses energy per step.
- Reported without extra training: caching and early stopping.
- Quantization, pruning and distillation are not used.

### 11.6 Failed runs
- A crash from a technical cause may be repeated with the same seed; both runs stay in the index.
- A model that trains badly is not replaced. Seed 42 stays the final model, and the budget stays
  3,000 steps.

### 11.7 Measurement
- MACs: `torch.utils.flop_counter.FlopCounterMode`, 2 flops = 1 MAC. BN and pooling count as 0.
- Latency: eval mode, no_grad, batch size 1, on GPU and CPU, on val images. 200 warm-up passes,
  then 5 repeats of 1,000 timed passes; median and p95. torch.cuda.synchronize() before each
  GPU timer read. CPU thread count fixed.
- Energy per 1,000 predictions: on val images, category measure, on CPU for every model including
  brightness, and on GPU for the CNNs. Loop of at least 60 s, 3 repeats, after a 60 s idle
  measurement. Gross and net of idle are both reported; the energy ratio uses CPU gross.

### 11.8 Reporting
- Footprint three ways: final training run (seed 42); training incl. LR search (seed 42 plus that
  model's trials); project total (`runs/index.csv`, all seeds, ablations and failed runs).
- Maximum planned training is 34,200 steps: LR search 3,600 (+300 per model if the edge rule
  applies), 7 final runs 21,000, resolution and depthwise-separable ablations 6,000,
  mixed-precision run 3,000, noise reference 600.
- Each CNN's ratio to brightness is reported separately, with its CI. test_unseen ratios are a
  diagnostic only.
- Residuals by count are reported for every model, on val for all models and on test for final models.
- Val predictions per image are saved for every model. Mean and brightness get theirs from one
  more tracked run of `scripts/baselines.py`, to `results/baselines/val_predictions.csv`.
- Val spread over seeds is reported for the own CNN and MobileNetV3-Small. ResNet-18 has none.

Known limitations:
- Early stopping may rarely fire: it cannot stop before step 1,500, and under cosine decay the error
  usually keeps improving late. A stop at step 2,000 still has about 25 % of the starting LR, so the
  model misses its best low-LR phase.
- "About 11 times more expensive per step" is a MACs figure (424.9 M vs 37.16 M). Real GPU energy
  per step does not scale exactly with MACs. ResNet-18 has one seed, so its result may not be typical.
- Three CNNs are each compared with brightness, with no correction for multiple comparisons, so
  one could win by chance.
- Choosing the LR from 300 steps favours fast starters, such as pretrained models and higher LRs.
  A 3,000-step run might prefer a lower LR.
- Ablations have one seed. A difference smaller than the spread over the 3 own-CNN seeds is called
  "no clear difference".
