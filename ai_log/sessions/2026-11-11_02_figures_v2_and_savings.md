# Session log: figures v2 (KirazNet labels) and savings

| Field | Value |
| --- | --- |
| Date | 2026-11-11, about 19:50 to 20:00 (UTC+3) |
| Tool | Claude Code, Code tab of the Claude desktop app, on Windows 11 |
| Model | Claude Opus 5.5 (`claude-opus-5-5`), auto permission mode |
| Prompts | `ai_log/prompts/2026-11-11_02_figures_v2_and_savings.md` |
| Commits | `f87544f` (figures.py v2 + prompt) to `8f5988b` (summary outputs), then this log |
| Tags | `analysis-v2` -> the commit of this log |
| Power | Every run's `config.json` says `power_source: "AC"` (6 of 6 runs) |

## Goal

Rename the own models in the report figures (own_cnn -> "KirazNet", own_cnn_ds -> "KirazNet-Lite";
code, run folders and CSV keys unchanged), re-plot the main figures without the mean baseline on a
linear y axis, quantify the energy saved by early stopping and by the image cache, and add the
ablation-table and savings numbers to `results/summary.md`. `evaluate_test.py` was not run and no
test image or test cache file was loaded. The caching measurement reads only the 1,200 train TIFs
and the train cache.

## Scripts (each committed before it ran)

| Script | Commit | Reads | Writes |
| --- | --- | --- | --- |
| `scripts/figures.py` (v2) | `f87544f`, fix `3475643` | as before (saved results, run folders) | `results/figures/` |
| `scripts/savings.py` (new) | `224c3ee` | run folders, `splits/splits.csv`, 1,200 train TIFs in `data/raw`, `data/cache/train_128x96.npz` | `results/savings.json` |
| `scripts/summary.py` | `2255c6a` | as before + `results/savings.json` | `results/summary.md` |

## Commands

```bash
.venv/Scripts/python.exe scripts/figures.py     # twice, see Problems
.venv/Scripts/python.exe scripts/savings.py
.venv/Scripts/python.exe scripts/summary.py
```

## Runs (all category analysis, all ok, all short_run)

| Run | Script | s | Wh |
| --- | --- | --- | --- |
| `20261111-195316_analysis_all_final_917c` | figures.py (1st, see Problems) | 2.72 | 0.0257 |
| `20261111-195358_analysis_all_final_917c` | figures.py (2nd, final) | 2.69 | 0.0357 |
| `20261111-195521_analysis_none_4dee` | savings.py: decode + resize 1,200 train TIFs | 11.54 | 0.1283 |
| `20261111-195537_analysis_none_3016` | savings.py: load train cache | 0.10 | 0.0075 |
| `20261111-195540_analysis_all_final_ea6e` | savings.py: arithmetic, writes savings.json | 0.04 | 0.00002 |
| `20261111-195616_analysis_all_final_0b23` | summary.py | 0.07 | 0.00001 |

This session: 6 runs, 0.197 Wh, 0.092 g CO2eq. Project total after this session (`runs/index.csv`,
114 rows, 1 failed): 32.76 Wh, 15.22 g CO2eq.

## Figures re-plotted (`results/figures/`, PNG 300 dpi + PDF each)

1. `mae_vs_co2_training`: mean baseline not drawn; title says "(mean baseline MAE 25.85, not
   shown)". y linear (MAE in cells), x log. Labels KirazNet / KirazNet s43 / s44 / 256x192 /
   KirazNet-Lite. The mobilenet s43 label now sits above its point and the KirazNet 256x192
   label left of its point; no label overlaps. Pareto front: brightness.
2. `mae_vs_co2_project`: only the test points, without the mean (brightness, KirazNet, mobilenet,
   resnet18 = 4 points; the 5th final model, mean, is named in the title). Linear y, log x.
   Pareto front: brightness (it was "mean, brightness" in v1, when the mean was drawn).
3. `val_curves`, `test_mae_by_blur`, `residual_by_count`, `energy_per_1000`: only the labels
   changed (own_cnn -> KirazNet). Same data, scales and layout as v1.

`results/figures/main_points.csv` is byte-identical to v1 (keys own_cnn, own_cnn s43, ...).

## Savings (`results/savings.json`)

Early stopping: 5 training runs stopped before 3,000 steps. Energy per step = whole run energy /
steps run (start-up and val evaluations included).

| Run | Steps run | Not run | Wh saved | g CO2eq saved |
| --- | --- | --- | --- | --- |
| own_cnn (KirazNet) seed 42 | 2,250 | 750 | 0.146 | 0.068 |
| own_cnn seed 43 | 1,950 | 1,050 | 0.189 | 0.088 |
| resnet18 seed 42 | 1,800 | 1,200 | 0.730 | 0.339 |
| own_cnn 256x192 (ablation) | 1,500 | 1,500 | 0.873 | 0.406 |
| own_cnn_ds (KirazNet-Lite) | 1,650 | 1,350 | 0.238 | 0.110 |
| Total | | 5,850 | 2.18 | 1.01 |

Caching (128x96):
- decode + resize 1,200 train TIFs: 11.5 s, 0.128 Wh, 0.060 g CO2eq.
- load the train cache: 0.10 s, 0.0075 Wh, 0.0035 g CO2eq.
- seed-42 KirazNet run: 2,250 steps / 37 batches per epoch = 60.8 epochs -> 61 decoded passes.
- Decoding every epoch instead of loading the cache once would cost about 7.82 Wh, 3.63 g CO2eq
  and 704 s more per training run (the whole training run used 0.44 Wh and 28 s).
- Building the cache once (all 4 splits, both resolutions, run `20261105-225640`): 0.131 Wh, 13.9 s.

## New rows in `results/summary.md`

Appended at the end, so rows 1-132 keep their numbers. Rows 96-97 (project total) and 107-108
(Pareto front, now from the v2 figures run) changed value.

- 133-136, ablation table (sec. 11.5), Wh / steps run / mWh per step: 256x192 0.873 / 1,500 /
  0.582; depthwise-separable 0.290 / 1,650 / 0.176; resnet18 AMP 1.25 / 3,000 / 0.417; resnet18
  FP32 noise reference 0.364 / 600 / 0.606.
- 137-142, savings: early stopping (per run and total, as in the table above).
- 143-147, savings: caching (decode run, cache-load run, epochs, saving per training run, cache
  build cost).

## Problems

- figures.py v2, first run: `main_points.csv` used the figure-label dict, so its label key for
  own_cnn became "KirazNet" (the prompt says CSV keys stay unchanged). The project figure's x tick
  labels also repeated (e.g. "2e-03" twice, one-digit rounding on a range under one decade), and
  the brightness label touched its Pareto ring. Fixed in `3475643` (separate KEY dict, ticks with 2
  digits, brightness label offset) and re-run; the first run stays in the index.

## Limitations

- Both caching runs are short_run (< 15 s, section 10): their energy is below the measurement
  resolution and only an estimate. The cache-load energy (0.0075 Wh in 0.1 s) is clearly dominated
  by the tracker's 5 s sampling, so it is an overestimate; the saving is dominated by the decode run.
- Decoding every epoch is a counterfactual: later epochs would partly hit the OS file cache, so the
  7.8 Wh saving per run is an upper-end estimate. The decode run itself may already have been
  partly warm (build_cache read 4,800 TIFs in 13.9 s; this run read 1,200 in 11.5 s).
- Early-stopping savings assume the steps not run would have cost the run's average energy per step.
