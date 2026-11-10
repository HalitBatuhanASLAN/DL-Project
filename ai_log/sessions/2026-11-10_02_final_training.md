# Session log: final training, ablations, post-hoc BN diagnostic

| Field | Value |
| --- | --- |
| Date | 2026-11-10, about 23:10 to 23:35 (UTC+3) |
| Tool | Claude Code, Code tab of the Claude desktop app, on Windows 11 |
| Model | Claude Opus 5.5 (`claude-opus-5-5`), auto permission mode |
| Prompts | `ai_log/prompts/2026-11-10_02_final_training.md` |
| Commits | `d13683c` (prompt) to `4221033`, then this log |
| Tags | `train-v1` -> `4a894ce`, `ablation-v1` -> `b974746` |
| Power | Every run's `config.json` says `power_source: "AC"` (17 of 17 runs), checked after each run |

## Goal

Section 11 final training (7 runs), section 11.5 ablations and efficiency runs (4 runs), and a
post-hoc BatchNorm diagnostic that is not pre-registered and is not used for any choice.
measure.py and evaluate_test.py were not run; no test file was opened.

## Commands

```bash
# 1. Final training, category train (scripts/train.py unchanged since infra-v1)
.venv/Scripts/python.exe scripts/train.py --model own_cnn --seed 42|43|44 --lr 3e-3 --category train
.venv/Scripts/python.exe scripts/train.py --model mobilenet_v3_small --seed 42|43|44 --lr 3e-3 --category train
.venv/Scripts/python.exe scripts/train.py --model resnet18 --seed 42 --lr 1e-3 --category train
# 2. Ablations / efficiency, seed 42, parent LR, category train (no "ablation" category exists)
.venv/Scripts/python.exe scripts/train.py --model own_cnn --lr 3e-3 --resolution 256x192
.venv/Scripts/python.exe scripts/train.py --model own_cnn_ds --lr 3e-3 --resolution 128x96
.venv/Scripts/python.exe scripts/train.py --model resnet18 --lr 1e-3 --amp
.venv/Scripts/python.exe scripts/train.py --model resnet18 --lr 1e-3 --max-steps 600
# 3. Post-hoc diagnostic, category analysis (scripts/bn_diagnostic.py, new)
.venv/Scripts/python.exe scripts/bn_diagnostic.py --checkpoint checkpoints/<seed-42 run>.pt [--order cache]
```

## Key outputs

### All runs (val, 400 images; brightness baseline MAE 1.08, mean baseline 25.85)

| Run | Model | Seed | Res. | LR | Stop step | Best at | Best val MAE | RMSE | R2 | Duration | Energy | short_run |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 231256_..._73cc | own_cnn | 42 | 128x96 | 3e-3 | 2250 (early) | 1350 | 1.356 | 1.625 | 0.9971 | 28.4 s | 0.439 Wh | no |
| 231341_..._be25 | own_cnn | 43 | 128x96 | 3e-3 | 1950 (early) | 1050 | 1.234 | 1.605 | 0.9971 | 27.3 s | 0.352 Wh | no |
| 231422_..._1c4d | own_cnn | 44 | 128x96 | 3e-3 | 3000 | 3000 | 1.027 | 1.438 | 0.9977 | 43.2 s | 0.541 Wh | no |
| 231518_..._c673 | mobilenet_v3_small | 42 | 128x96 | 3e-3 | 3000 | 2550 | 1.513 | 2.050 | 0.9953 | 90.0 s | 0.989 Wh | no |
| 231701_..._d8bb | mobilenet_v3_small | 43 | 128x96 | 3e-3 | 3000 | 2250 | 1.514 | 1.906 | 0.9960 | 80.2 s | 0.898 Wh | no |
| 231834_..._88b5 | mobilenet_v3_small | 44 | 128x96 | 3e-3 | 3000 | 2400 | 1.348 | 1.776 | 0.9965 | 81.3 s | 0.910 Wh | no |
| 232008_..._c1c4 | resnet18 | 42 | 128x96 | 1e-3 | 1800 (early) | 900 | 2.047 | 2.482 | 0.9931 | 94.6 s | 1.095 Wh | no |
| 232222_..._a201 | own_cnn (ablation) | 42 | 256x192 | 3e-3 | 1500 (early) | 600 | 1.462 | 1.874 | 0.9961 | 73.9 s | 0.873 Wh | no |
| 232352_..._13c9 | own_cnn_ds (ablation) | 42 | 128x96 | 3e-3 | 1650 (early) | 750 | 1.651 | 2.067 | 0.9952 | 23.2 s | 0.290 Wh | no |
| 232429_..._0845 | resnet18 AMP | 42 | 128x96 | 1e-3 | 3000 | 2700 | 1.543 | 1.937 | 0.9958 | 109.8 s | 1.250 Wh | no |
| 232634_..._8658 | resnet18 noise ref. | 42 | 128x96 | 1e-3 | 600 (budget) | 600 | 1.762 | 2.243 | 0.9944 | 31.6 s | 0.364 Wh | no |

Every run: `best_val_mae` after reloading the checkpoint equals the value when it was saved.

### Seed spread (best val MAE)

| Model | Mean | Min - max | Range |
| --- | --- | --- | --- |
| own_cnn | 1.206 | 1.027 - 1.356 | 0.328 |
| mobilenet_v3_small | 1.458 | 1.348 - 1.514 | 0.166 |

### Brightness (val 1.08)

No final (seed-42) model beats it on val: own_cnn 1.356, mobilenet_v3_small 1.513, resnet18 2.047.
Of all 11 runs, only own_cnn seed 44 (1.027) is below 1.08, and seed 44 is not a final model
(section 11). Val only; the decision is on test_seen.

### Ablations vs own_cnn seed 42 (1.356, 0.439 Wh)

| Variant | Val MAE | Diff | Energy | Energy ratio | vs seed range 0.328 |
| --- | --- | --- | --- | --- | --- |
| 256x192 | 1.462 | +0.106 | 0.873 Wh | 1.99x | smaller: no clear difference |
| depthwise-separable | 1.651 | +0.295 | 0.290 Wh | 0.66x | smaller (close): no clear difference |

### AMP vs no AMP (ResNet-18, seed 42, lr 1e-3; energy and time include evaluations)

| Run | Steps | Energy per step | Time per step (duration/steps) | Median train step | Peak reserved |
| --- | --- | --- | --- | --- | --- |
| AMP | 3000 | 0.417 mWh | 36.6 ms | 34.8 ms | 390 MiB |
| no AMP, noise reference | 600 | 0.606 mWh | 52.6 ms | 50.2 ms | 494 MiB |
| no AMP, final run | 1800 | 0.608 mWh | 52.6 ms | 50.3 ms | 494 MiB |

The two no-AMP runs differ by 0.3 % per step; AMP uses about 31 % less energy and 30 % less
time per step.

### Post-hoc BN diagnostic (NOT pre-registered, NOT used for any choice; weights not saved)

| Model (seed 42) | BN layers | Val MAE before | After, cache order | After, shuffled (seed 42) |
| --- | --- | --- | --- | --- |
| own_cnn | 4 | 1.356 | 5.672 | 1.307 |
| mobilenet_v3_small | 34 | 1.513 | 33.43 | 1.643 |
| resnet18 | 20 | 2.047 | 120.7 | 2.889 |

All 6 runs: weights unchanged (checked with `torch.equal`), "before" equals the run's best val MAE.
Shuffled batches hold 10-19 different counts (mean 15.8).

### Energy

This session: 17 runs, 691 s, 8.08 Wh, 3.75 g CO2 (train 683 s / 8.00 Wh; analysis 7 s / 0.08 Wh).
Project total (`runs/index.csv`, 59 rows, 1 failed): 1,187 s, 13.11 Wh, 6.09 g CO2.
Training steps run this session: 18,000 final + 6,750 ablation/efficiency = 24,750 (planned max 30,600).

## Observations

- Val MAE swings strongly between evaluations at high LR: own_cnn s42 18.93 at step 900,
  own_cnn_ds 18.85 at 900, own_cnn 256x192 13.76 at 900, own_cnn s43 12.71 at 600. Train loss
  does not jump at the same steps. The best checkpoints of the own CNNs come from these noisy
  middle evaluations (steps 600-1350); 4 of 5 own-CNN runs stopped early.
- ResNet-18 early-stopped at 1800 (best at 900, 2.047), while the AMP run went to 3000 and reached
  1.543 at step 2700. The difference comes from the stopping rule on noisy val, not from AMP:
  the no-AMP run had already stopped before its low-LR phase (the known limitation in section 11).
- The 600-step noise reference has a cosine schedule over 600 steps (train.py sets T_max to the
  step budget), so its val MAE (1.762) is not comparable to a 3000-step run; only energy and
  time per step are used, as section 11.5 says.
- BN diagnostic: with shuffled batches, recomputed statistics do not help mobilenet_v3_small
  (worse by 0.13) or resnet18 (worse by 0.84); own_cnn improves by 0.05. Lagging running
  statistics do not explain MobileNet's gap in this test.
- No NaN in any log. GPU peak reserved memory at most 1,056 MiB (own_cnn 256x192), 26 % of 4 GB.

## Differences from the prompt

- No `ablation` category exists (section 10), so the 4 ablation/efficiency runs use category
  `train` with notes "ablation: ..." / "efficiency: ...".
- BN diagnostic ran twice per model (6 analysis runs instead of 3); see below.

## Problems and solutions

- The first BN diagnostic pass used the train cache in cache order and made every model far
  worse (MobileNet 1.51 -> 33.4, ResNet-18 2.05 -> 120.7). The cache is grouped by scene, so a
  batch of 32 holds images of one count (the init check found this for the first batch), and
  the average of within-batch variances misses the variance between counts. This is a flaw of
  my diagnostic, not a BN finding. Kept as `results/bn_diagnostic/*_cache.json` (commit
  `da34f51`); added `--order shuffled` (one fixed permutation, seed 42) and a count of distinct
  counts per batch, committed (`528ce01`), and re-ran. The cache-order pass did not record the
  per-batch count diversity, so the one-count-per-batch claim is only checked for the first batch.
