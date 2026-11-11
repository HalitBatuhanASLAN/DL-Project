# Session log: figures, own_cnn diagnostics, summary table

| Field | Value |
| --- | --- |
| Date | 2026-11-11, about 19:12 to 19:25 (UTC+3) |
| Tool | Claude Code, Code tab of the Claude desktop app, on Windows 11 |
| Model | Claude Opus 5.5 (`claude-opus-5-5`), auto permission mode |
| Prompts | `ai_log/prompts/2026-11-11_01_figures_and_diagnostics.md` |
| Commits | `0d27f05` (prompt) to `412628e` (outputs), then this log |
| Tags | `analysis-v1` -> the commit of this log |
| Power | Every run's `config.json` says `power_source: "AC"` (5 of 5 runs) |

## Goal

Report figures (spec 3.5 main figure plus 4 others), post-hoc val-only diagnostics on why own_cnn
failed acceptance, and `results/summary.md` with every number the report cites and its source.
`evaluate_test.py` was not run, and no test image was loaded. Test numbers come only from the saved
rows in `results/test_predictions/` via `results/results.csv`, `results/test_mae_by_blur.csv` and
`results/test_residuals_by_count.csv` (written by `scripts/results.py` in the previous session).

## Scripts (each committed before it ran)

| Script | Commit | Reads | Writes |
| --- | --- | --- | --- |
| `scripts/diagnostics.py` | `ea78760` | `runs/<7 final training runs>/eval_log.csv, metrics.json`, `results/val_predictions/<run>.csv` | `results/diagnostics/` |
| `scripts/figures.py` | `ea78760`, then fixes `64a7b40`, `522805c`, `ce4ecae` | `results/results.csv`, test CSVs above, `runs/index.csv`, run folders | `results/figures/` |
| `scripts/summary.py` | `a23eb87` | all of the above, `results/results_summary.json`, `results/baselines_val.json` | `results/summary.md` |

## Commands

```bash
.venv/Scripts/python.exe scripts/diagnostics.py
.venv/Scripts/python.exe scripts/figures.py     # three times, see Problems
.venv/Scripts/python.exe scripts/summary.py
```

## Runs (all category analysis, all ok, all short_run)

| Run | Script | Wh |
| --- | --- | --- |
| `20261111-191657_analysis_own_cnn_53ec` | diagnostics.py | 0.0208 |
| `20261111-191709_analysis_all_final_1852` | figures.py (1st, labels collided) | 0.0289 |
| `20261111-191817_analysis_all_final_1852` | figures.py (2nd, labels still collided) | 0.0268 |
| `20261111-191902_analysis_all_final_1852` | figures.py (3rd, final) | 0.0310 |
| `20261111-192031_analysis_all_final_0b23` | summary.py | 0.00001 |

This session: 5 runs, 0.108 Wh, 0.050 g CO2eq. Project total after this session (`runs/index.csv`,
108 rows, 1 failed): 32.56 Wh, 15.13 g CO2eq.

## Figures (`results/figures/`, PNG 300 dpi + PDF each)

1. `mae_vs_co2_training`: MAE (log) vs kg CO2eq, training incl. LR search (log). Final models as
   filled circles (test_seen MAE); val-only variants as open triangles, labelled "(val)", legend
   "val MAE (val-only variant, no test run)". Pareto front over test points only: brightness.
2. `mae_vs_co2_project`: the same with x = project CO2 per model. Pareto front: mean, brightness.
3. `val_curves`: val MAE every 150 steps, 7 final-training runs, log y, star = saved checkpoint,
   brightness val MAE as a reference line.
4. `test_mae_by_blur`: test_seen MAE per blur level (brightness and the 3 CNNs).
5. `residual_by_count`: mean test residual per count, one panel per model; seen counts as dots,
   held-out counts (14, 40, 66, 91, test_unseen) as open squares.
6. `energy_per_1000`: CPU gross Wh per 1,000 predictions, log y, 5 final models.

`main_points.csv` lists every point of figures 1-2 with its source file.

## Diagnostics (val only, post-hoc, not pre-registered; `results/diagnostics/`)

a) Saved checkpoint vs median val MAE of the last 5 evaluations:

| Run | Best val MAE (step) | Median last 5 | Ratio |
| --- | --- | --- | --- |
| own_cnn seed 42 | 1.356 (1350) | 1.857 (steps 1650-2250) | 1.37 |
| own_cnn seed 43 | 1.234 (1050) | 2.660 | 2.16 |
| own_cnn seed 44 | 1.027 (3000) | 1.163 | 1.13 |
| mobilenet_v3_small seed 42 | 1.513 (2550) | 1.588 (steps 2400-3000) | 1.05 |
| mobilenet_v3_small seed 43 | 1.514 (2250) | 1.627 | 1.07 |
| mobilenet_v3_small seed 44 | 1.348 (2400) | 1.485 | 1.10 |
| resnet18 seed 42 | 2.047 (900) | 2.324 | 1.14 |

b) Mean signed val residual (prediction - count) and val MAE after removing it (offset fitted and
measured on the same val images, so optimistic; never applied to test):

| Run | Mean residual | Counts with positive mean (of 20) | Val MAE -> after |
| --- | --- | --- | --- |
| own_cnn seed 42 | +0.761 | 16 | 1.356 -> 1.108 |
| own_cnn seed 43 | -0.190 | 8 | 1.234 -> 1.250 |
| own_cnn seed 44 | -0.369 | 6 | 1.027 -> 1.002 |
| mobilenet_v3_small seed 42 | -0.195 | 11 | 1.513 -> 1.524 |
| mobilenet_v3_small seed 43 | -0.222 | 9 | 1.514 -> 1.500 |
| mobilenet_v3_small seed 44 | -0.481 | 8 | 1.348 -> 1.339 |
| resnet18 seed 42 | +0.286 | 12 | 2.047 -> 2.009 |

c) own_cnn val MAE per blur level:

| Seed | F1 | F26 | F39 | F48 |
| --- | --- | --- | --- | --- |
| 42 | 1.332 | 1.294 | 1.354 | 1.442 |
| 43 | 1.236 | 1.280 | 1.237 | 1.182 |
| 44 | 1.024 | 1.004 | 1.029 | 1.051 |

## Observations (numbers only)

- own_cnn seed 42 was saved at step 1350, between a 1.961 and a 3.498 evaluation; the median of
  its last 5 evaluations (1.857) is 37 % above the saved value. For mobilenet_v3_small seed 42 the
  gap is 5 %.
- own_cnn seed 42 has a positive val offset (+0.761, 16 of 20 counts); the other two own_cnn seeds
  and all mobilenet seeds have negative offsets. On test_seen the previous session found a positive
  own_cnn residual at 19 of 20 seen counts.
- own_cnn seed 42 val MAE rises from F26 (1.294) to F48 (1.442), the same direction as on test_seen
  (1.454 -> 1.776). Seed 43 falls from F1 to F48; seed 44 is nearly flat.
- Val spread over seeds: own_cnn 1.205 +- 0.166 (1.027-1.356), mobilenet_v3_small
  1.458 +- 0.095 (1.348-1.514). Seed 42 is the worst own_cnn seed on val.
- Of all trained runs, only own_cnn seed 44 (val 1.027) is below the brightness val MAE (1.081).
  No variant has a test number.
- Brightness is on the Pareto front in both versions: no CNN has a lower test_seen MAE.
- ResNet-18 AMP: 0.417 mWh per step vs 0.606-0.608 for FP32 (noise reference and final run).

## Differences from the prompt

- Diagnostics a) and b) are computed for all 7 final-training runs, not only seed 42 of own_cnn and
  mobilenet; the extra rows show the spread over seeds.
- Main figure x for val-only variants: their own training run + the parent's LR search (the only
  runs that belong to them), the same in both versions. A final model's project CO2 already
  contains its seed 43/44 runs, so in the project version the variants sit left of their parent.
  Stated in a note under the figure.
- Main figure x for baselines: training = the baseline run that wrote the current parameters
  (`20261105-233219`, commit `b56eaaf`); project = `results.csv` project value + all three
  `mean_and_brightness` runs (shared, counted for both).
- Both axes of the main figure are log scale (the mean baseline at 25.85 would otherwise squash the
  others). The mean baseline is left out of the blur and residual figures (constant 25.85 and
  50.05 - count); the titles say so.
- The energy bar chart uses a log y-axis as asked; bar length on a log axis depends on where the
  axis starts, so the value labels on the bars are the numbers to read.

## Problems and solutions

- Main figure, first run: point labels collided in the 5e-4 to 1e-3 kg cluster, and a Pareto front
  of one point drew no visible line. Fix `64a7b40` (label offsets, a ring on front points, legend
  below the plot); that commit did not compile (line break inside a string), so nothing ran; fixed in
  `522805c`. Second run: labels still collided. Fix `ce4ecae` (labels of the cluster moved up with
  leader lines, separate offsets per version). Third run is final. All three runs are in the index.
- In the final main figures two leader lines pass through a neighbouring label (mobilenet s43/s44).
  The figures are readable; not changed further, to avoid another run.
