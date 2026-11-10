# Session log: rules-v2.1, init check, reproducibility check, LR search

| Field | Value |
| --- | --- |
| Date | 2026-11-10, about 22:50 to 23:15 (UTC+3) |
| Tool | Claude Code, Code tab of the Claude desktop app, on Windows 11 |
| Model | Claude Opus 5.5 (`claude-opus-5-5`), auto permission mode |
| Prompts | `ai_log/prompts/2026-11-10_01_rules_v2_1_and_lr_search.md` |
| Commits | `f232c01` to `7a2029e`, then this log |
| Tags | `rules-v2.1` -> `ad5e266`, `infra-v1.1` -> `2857f88`, `search-v1` -> `7a2029e` |
| Power | Every run's `config.json` says `power_source: "AC"` (25 of 25 runs) |

## Goal

Implement rules-v2.1 (zero output weights), check it, then do the reproducibility check and the
LR search of section 11.4. No final training.

## Steps

1. Prompt 1, step 0: tags `rules-v2.1` and `infra-v1.1` did not exist (locally or on origin),
   and no init check had run. Stopped and reported, as the prompt said. No changes.
   The notes files were already in `ai_log/`, not in the root, so nothing to move.
2. Prompt 2, Part A: committed the notes (`f232c01`). Updated section 11.1, added
   "Changes from rules-v2", `rules.json` version and `output_weight_init` (`ad5e266`), tagged
   `rules-v2.1`, pushed.
3. `src/models.py`: `build_model` sets the head weights to 0 and the bias to 0.5005; an assert
   checks that `rules.json` says `"zeros"` (`37fc91c`).
4. Added `scripts/init_check.py` (`61c6afb`), ran it: 4 of 4 PASS. Committed, tagged
   `infra-v1.1`, pushed (`2857f88`).
5. Added `scripts/repro_check.py`, committed, ran it: bit-identical.
6. LR search for own_cnn, mobilenet_v3_small, resnet18 (in that order) with the committed
   `scripts/lr_search.py`. Committed, tagged `search-v1`, pushed (`7a2029e`).

## Commands

```bash
.venv/Scripts/python.exe scripts/init_check.py
.venv/Scripts/python.exe scripts/repro_check.py
.venv/Scripts/python.exe scripts/lr_search.py --model own_cnn
.venv/Scripts/python.exe scripts/lr_search.py --model mobilenet_v3_small
.venv/Scripts/python.exe scripts/lr_search.py --model resnet18
git tag -a rules-v2.1 / infra-v1.1 / search-v1; git push origin main <tag>
```

## Key outputs

### Init check (`results/init_check.json`), PASS = |MAE - 25.85| <= 0.01, head weights 0, grad > 0

| Model | Val MAE step 0 | Prediction (cells) | Head weight grad norm | Result |
| --- | --- | --- | --- | --- |
| own_cnn | 25.8500 | 50.05 for all 400 | 1.469 | PASS |
| own_cnn_ds | 25.8500 | 50.05 for all 400 | 2.390 | PASS |
| resnet18 | 25.8500 | 50.05 for all 400 | 19.43 | PASS |
| mobilenet_v3_small | 25.8500 | 50.05 for all 400 | 5.706 | PASS |

The forward/backward batch is the first 32 train images. They all have the same count (train
loss 49.05 cells for every model), so the check shows the gradient exists, not that it is typical.

### Reproducibility (`results/repro_check.json`)

own_cnn, seed 42, lr 1e-3, 150 steps, twice: val MAE 2.376905293166638 both times; every tensor
of the two checkpoints is bit-identical (largest difference 0.0). With 150 steps the only
evaluation is at step 150, so the checkpoint holds the final weights.

### LR search (`results/lr_search/<model>.json`), val MAE at step 300 (cells)

| Model | 1e-4 | 3e-4 | 1e-3 | 3e-3 | 1e-2 (edge) | Chosen | Edge rule |
| --- | --- | --- | --- | --- | --- | --- | --- |
| own_cnn | 2.674 | 2.147 | 1.710 | **1.548** | 1.907 | 3e-3 | fired (1e-2 worse) |
| mobilenet_v3_small | 9.133 | 7.293 | 7.105 | **4.096** | 6.190 | 3e-3 | fired (1e-2 worse) |
| resnet18 | 2.065 | 2.239 | **1.718** | 3.292 | - | 1e-3 | no |

Search steps: 14 trials x 300 = 4,200 (planned 3,600 + 300 per edge rule).

### Time and energy per trial (300 steps)

| Model | Duration per trial | Median step | Energy per trial | Per step | Short run |
| --- | --- | --- | --- | --- | --- |
| own_cnn | 3.2-4.5 s | 10-14 ms | 0.058-0.062 Wh | ~0.20 mWh | all 5 |
| mobilenet_v3_small | 8.0-8.4 s | 23-25 ms | 0.097-0.107 Wh | ~0.33 mWh | all 5 |
| resnet18 | 14.7-16.2 s | 46-50 ms | 0.187-0.199 Wh | ~0.64 mWh | 3e-4 only (14.7 s) |

Session total (25 runs): 129 s, 0.00170 kWh, 0.79 g CO2. Project total: 496 s, 0.00503 kWh, 2.34 g.

## Observations

- Short-run energy is not proportional to time: own_cnn trials of 3.2 s and 4.5 s both read about
  0.06 Wh (implied 50-70 W), while ResNet-18 reads about 45 W. Only the three ResNet-18 trials
  over 15 s are above measurement resolution.
- Val MAE at step 150 swings a lot (ResNet-18 lr 1e-3: 13.65 at step 150, 1.72 at step 300;
  MobileNet lr 1e-2: 28.42 at step 150, above the mean baseline 25.85). Eval-mode BatchNorm with
  running statistics that still lag behind the weights at high LR is the likely cause. At step 300
  (LR near 0) every trial is far below the mean baseline.
- MobileNetV3-Small is clearly worse than the other two (best 4.10 vs 1.55 / 1.72), although its
  training loss at step 300 (~4 cells, train mode, with flips) is similar. The val/train gap
  points to the same BatchNorm effect, but this was not checked.
- After 300 steps no CNN is better than the brightness baseline on val (1.08).
- Step times are higher than in the infra-v1 smoke tests (ResNet-18 46-50 ms vs 36 ms,
  MobileNet 23-25 ms vs 30 ms); the smoke-test medians came from only 20 steps.
- No NaN loss. GPU peak reserved memory 244-508 MiB (at most 12% of 4 GB).

## Differences from the prompt

- Prompt 1 named the log `2026-11-10_01_lr_search`; prompt 2 replaced it with this name.
- The notes commit "Update notes: rules-v2.1 decision" contains the ResNet-18 ~131-cell
  observation (Entry O) but no explicit statement of the zero-weight decision; the decision text
  and reason are in `docs/decision_rules.md` ("Changes from rules-v2").
- The reproducibility comparison ran as a third tracked run (env, "reproducibility check,
  compare"), because it loads the checkpoints.

## Problems and solutions

- My first command to edit the rules files was a malformed shell heredoc and changed nothing
  (checked with `git status`). Redone with a small edit script in the scratchpad. No run was
  affected.
