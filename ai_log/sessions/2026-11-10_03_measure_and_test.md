# Session log: measurement, test runs, results

| Field | Value |
| --- | --- |
| Date | 2026-11-11, about 18:25 to 19:10 (UTC+3) |
| Tool | Claude Code, Code tab of the Claude desktop app, on Windows 11 |
| Model | Claude Opus 5.5 (`claude-opus-5-5`), auto permission mode |
| Prompts | `ai_log/prompts/2026-11-10_03_measure_and_test.md` |
| Commits | `adf6819` (prompt) to `c9cba58`, then this log |
| Tags | `test-v1` -> `c9cba58` |
| Power | Every run's `config.json` says `power_source: "AC"` (44 of 44 runs) |

## Goal

Pre-test checks, section 11.7 measurement, one section 9 test run per final model, results table,
acceptance (section 8) and "beats brightness" (section 11). No plots.

## Step 1: pre-test checks (no runs; all PASS)

- a) `scripts/train.py` draws shuffled batches: `batch_indices()` (lines 59-64) calls
  `torch.randperm(n_images, generator=generator)` at the start of every pass over the train set and
  drops the last incomplete batch; the generator is `torch.Generator(device).manual_seed(seed)`
  (line 117), and `set_seeds()` (lines 49-56) fixes the Python, NumPy, torch and CUDA seeds. The
  unshuffled order existed only in the first pass of `bn_diagnostic.py`.
- b) Final models (all seed 42, 128x96, `rules-v2.1`, training run config `power_source` AC):

| Model | Artifact | SHA-256 |
| --- | --- | --- |
| mean | `results/baselines_val.json` (train_mean 50.05) | `cc3ffe418fd8594094245fcedb324940bcb90767f9d564806214976404b6187e` |
| brightness | `results/baselines/brightness_params.json` (a -3.2253, b 3.1485) | `25d3f2676af12377cd2d8fe2439268e4b561b1f528f737a297ad85ca349e713d` |
| own_cnn | `checkpoints/20261110-231256_train_own_cnn_73cc.pt` (best step 1350) | `11677411374c0eaaef0ed5c445b773934a9be23dda0153f86b6dc4093fcda105` |
| mobilenet_v3_small | `checkpoints/20261110-231518_train_mobilenet_v3_small_c673.pt` (best step 2550) | `126b2595deee06c50e44da08a02952261035f8091d7ff4575c2628b4be384cbb` |
| resnet18 | `checkpoints/20261110-232008_train_resnet18_c1c4.pt` (best step 900) | `525edb4a5a38895f336a94cca049bc288a502d4c3f712a355db81b6bfca86639` |

- c) `results/test_log.csv` and `results/test_predictions/` did not exist, and `runs/index.csv`
  had no `eval` run. Only `evaluate_test.py` calls `read_cache()` on a test split; every other
  script uses `load_train_or_val()`. The other readers of test files are the documented section 9
  exceptions, `check_stain.py` (check F, aggregate statistics) and `build_cache.py`, plus
  `data_inventory.py` (5 random file summaries, before the split existed, section 2).

## Commands

```bash
.venv/Scripts/python.exe scripts/measure.py --model mean|brightness
.venv/Scripts/python.exe scripts/measure.py --model own_cnn|mobilenet_v3_small|resnet18 --checkpoint checkpoints/<seed-42 run>.pt
.venv/Scripts/python.exe scripts/evaluate_test.py --model mean   # then brightness, own_cnn, mobilenet_v3_small, resnet18 (with --checkpoint)
.venv/Scripts/python.exe scripts/results.py                     # twice, see Problems
```

## Key outputs

### Measurement (val images, 4 CPU threads, median over repeats)

| Model | CPU ms med / p95 | GPU ms med / p95 | CPU gross Wh/1000 | CPU net | GPU gross Wh/1000 | GPU net | Idle W |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mean | 0.0005 / 0.0005 | - | 0.000028 | 0.000003 | - | - | 30.9 |
| brightness | 0.0294 / 0.0658 | - | 0.000345 | -0.000009 | - | - | 35.4 |
| own_cnn | 1.98 / 2.57 | 0.84 / 1.22 | 0.0205 | 0.0024 | 0.0084 | 0.0009 | 30.9 |
| mobilenet_v3_small | 8.33 / 9.59 | 6.00 / 7.44 | 0.0837 | 0.0169 | 0.0597 | 0.0093 | 28.2 |
| resnet18 | 13.70 / 15.28 | 3.15 / 3.90 | 0.1422 | 0.0303 | 0.0334 | 0.0116 | 28.4 |

### Results table (`results/results.csv`, test_seen, 95 % scene-bootstrap CI)

| Model | Params | MFLOPs/img | MAE | RMSE | R2 | Size MB |
| --- | --- | --- | --- | --- | --- | --- |
| mean | 1 | 0 | 25.85 [22.82, 28.81] | 29.96 [27.14, 32.56] | 0.000 [-0.054, -0.000] | - |
| brightness | 2 | 0.0123 | 1.142 [0.967, 1.330] | 1.532 [1.312, 1.742] | 0.9974 [0.9963, 0.9981] | 0.0003 |
| own_cnn | 60,465 | 74.32 | 1.569 [1.374, 1.777] | 1.915 [1.659, 2.171] | 0.9959 [0.9944, 0.9970] | 0.253 |
| mobilenet_v3_small | 1,518,593 | 26.99 | 1.249 [1.065, 1.443] | 1.608 [1.388, 1.826] | 0.9971 [0.9959, 0.9980] | 6.22 |
| resnet18 | 11,170,753 | 849.74 | 1.951 [1.694, 2.237] | 2.473 [2.098, 2.900] | 0.9932 [0.9898, 0.9953] | 44.77 |

| Model | Train kWh (seed 42) | Train g CO2eq | Train + LR search g | Project g (by model name) |
| --- | --- | --- | --- | --- |
| mean | - | - | - | 1.073 |
| brightness | - | - | - | 1.088 |
| own_cnn | 0.000439 | 0.204 | 0.343 | 3.191 |
| mobilenet_v3_small | 0.000989 | 0.459 | 0.692 | 3.738 |
| resnet18 | 0.001095 | 0.509 | 0.865 | 4.185 |

### Acceptance (section 8, point estimates): FAIL

- MAE_own 1.569; MAE_best 1.249 (mobilenet_v3_small); 1.15 x MAE_best = 1.436 -> fail.
- MAE_mean 25.85; 0.60 x MAE_mean = 15.51 -> pass.
- Paired MAE_own / MAE_best = 1.256 [1.065, 1.486].

### Beats brightness (section 11, test_seen, paired): none

| CNN | MAE / MAE_brightness | Beats? | CPU gross energy ratio | test_unseen ratio (diagnostic) |
| --- | --- | --- | --- | --- |
| own_cnn | 1.374 [1.216, 1.558] | no | 59.5 | 1.191 [1.030, 1.373] |
| mobilenet_v3_small | 1.093 [0.927, 1.291] | no | 242.3 | 1.319 [1.124, 1.550] |
| resnet18 | 1.708 [1.410, 2.085] | no | 411.5 | 1.854 [1.572, 2.215] |

### test_unseen MAE (diagnostic only)

mean 25.75 [23.15, 28.31]; brightness 1.147 [0.979, 1.322]; own_cnn 1.366 [1.174, 1.569];
mobilenet_v3_small 1.513 [1.257, 1.788]; resnet18 2.127 [1.834, 2.430].

### MAE per blur level (`results/test_mae_by_blur.csv`)

| Split | Model | F1 | F26 | F39 | F48 |
| --- | --- | --- | --- | --- | --- |
| test_seen | brightness | 1.242 | 1.096 | 1.096 | 1.136 |
| test_seen | own_cnn | 1.429 | 1.454 | 1.618 | 1.776 |
| test_seen | mobilenet_v3_small | 1.319 | 1.204 | 1.238 | 1.235 |
| test_seen | resnet18 | 2.104 | 1.904 | 1.895 | 1.903 |
| test_unseen | brightness | 1.056 | 1.089 | 1.178 | 1.266 |
| test_unseen | own_cnn | 1.351 | 1.325 | 1.356 | 1.433 |
| test_unseen | mobilenet_v3_small | 1.599 | 1.484 | 1.503 | 1.468 |
| test_unseen | resnet18 | 2.219 | 2.037 | 2.087 | 2.165 |

Mean baseline: 25.85 (seen) and 25.75 (unseen) at every level. Residuals by count are in
`results/test_residuals_by_count.csv`.

### Energy

This session: 44 runs (measure 37, eval 5, analysis 2), 19.34 Wh, 8.99 g CO2eq; measurement alone
18.83 Wh. Project total (`runs/index.csv`, 103 rows, 1 failed): 3,159 s, 32.45 Wh, 15.08 g CO2eq.

## Observations (numbers only)

- Val -> test_seen MAE: own_cnn 1.356 -> 1.569; mobilenet_v3_small 1.513 -> 1.249; resnet18
  2.047 -> 1.951; brightness 1.081 -> 1.142.
- own_cnn has a positive mean residual at 19 of 20 seen counts and at all 4 unseen counts.
- own_cnn test_seen MAE rises from F1 (1.429) to F48 (1.776).
- Brightness CPU net energy is negative (-0.000009 Wh/1000): its idle measurement (35.4 W) was
  higher than the power during its loops.
- The mean baseline's latency (0.0005 ms) times a Python call that returns a constant.
- 4 measure runs are short_run (the latency runs of mean, brightness, and own_cnn CPU and GPU).
- The results.py metrics equal the evaluate_test.py metrics to about 1e-7 (CSV rounding of predictions).

## Differences from the prompt

- `measure.py` did not support the mean baseline. I added it (CPU only, returns the train mean)
  and committed it before running (`8bd4a07`).
- Latency on GPU only for the 3 CNNs (baselines CPU only), as section 11.7 sets for energy.
- Baselines: params and FLOPs counted by hand (mean 1 / 0; brightness 2 / 12,291), no training run,
  model size = parameter file (none for mean). "Project g per model" = runs whose `model` column
  equals the model name; the shared `mean_and_brightness` baseline runs are in neither row.
- Model size = checkpoint file size (state dict plus a small config dict), MB = 10^6 bytes.

## Problems and solutions

- The first `results.py` run left the GPU latency and energy columns empty, because `measure.py` stores them
  under `"cuda"`. Fixed (`c1b2bfa`) and re-ran; both analysis runs are in the index. Neither run
  loaded a test image.
