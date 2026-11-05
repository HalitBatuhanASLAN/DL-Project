# Session log: cache and baselines

| Field | Value |
| --- | --- |
| Date | 2026-11-05, from about 22:53 (UTC+3) |
| Tool | Claude Code, Code tab of the Claude desktop app, on Windows 11 |
| Model | Claude Opus 5.5 (`claude-opus-5-5`), auto permission mode |
| Prompt | `ai_log/prompts/2026-11-05_05_cache_baselines.md` |
| Commits | `9d2b339` notes; `13df177` metrics.py; `c9a5f27` build_cache.py; `cd0b694` baselines.py; `077a8e3` results |
| Tag | `cache-v1` -> `077a8e3` |

## Goal

Build the image cache at both resolutions and run the two baselines on val. No model code and
no training.

## Steps

1. Read the rules, `rules.json` and the decision files.
2. Compared the root notes with the `ai_log/` copies: the root versions only add lines. Moved them
   (overwrite) and committed.
3. Wrote `src/metrics.py`, committed, ran the self-test: PASS.
4. Wrote `scripts/build_cache.py`, committed, ran it.
5. Wrote `scripts/baselines.py`, committed, ran it.
6. Committed results and run folders, tagged `cache-v1`, pushed. Stopped.

## Commands

```bash
.venv/Scripts/python.exe -m src.metrics
.venv/Scripts/python.exe scripts/build_cache.py
.venv/Scripts/python.exe scripts/baselines.py
git add results runs && git commit
git tag -a cache-v1 -m "..."
git push origin main cache-v1
```

## Key outputs

### Checks

- `src.metrics` self-test: PASS.
- `build_cache.py`: 41 of 41 PASS (5 checks on each of 8 files, plus train mean target = 50.05).
- `baselines.py`: analytic test_seen MAE of the mean baseline 25.8500, expected 25.85: PASS.

### Cache (w1, F1, F26, F39, F48; PIL BOX; uint8)

| Split | Images | 128x96 (bytes) | 256x192 (bytes) |
| --- | --- | --- | --- |
| train | 1200 | 14,804,196 | 59,040,996 |
| val | 400 | 4,935,396 | 19,680,996 |
| test_seen | 400 | 4,935,396 | 19,680,996 |
| test_unseen | 400 | 4,933,796 | 19,679,396 |

Total 140.8 MiB. The npz files are ignored by git; `results/cache_manifest.json` holds their
SHA-256.

### Normalisation stats (x = (u8/255 - mean) / std, train pixels)

| Resolution | Mean | Std |
| --- | --- | --- |
| 128x96 | 0.066356 | 0.133375 |
| 256x192 | 0.066537 | 0.135162 |

### Baselines on val (128x96, 400 images, 100 scenes, B = 10,000, seed 42)

| Model | MAE [95 % CI] | RMSE [95 % CI] | R2 [95 % CI] |
| --- | --- | --- | --- |
| Mean | 25.85 [22.82, 28.81] | 29.96 [27.14, 32.56] | 0.0000 [-0.0542, -0.00001] |
| Brightness | 1.081 [0.932, 1.230] | 1.395 [1.218, 1.558] | 0.9978 [0.9971, 0.9984] |

| Blur | Mean MAE [95 % CI] | Brightness MAE [95 % CI] |
| --- | --- | --- |
| F1 | 25.85 [22.82, 28.81] | 0.904 [0.750, 1.064] |
| F26 | 25.85 [22.82, 28.81] | 1.020 [0.868, 1.171] |
| F39 | 25.85 [22.82, 28.81] | 1.149 [0.975, 1.326] |
| F48 | 25.85 [22.82, 28.81] | 1.250 [1.055, 1.450] |

Brightness fit on train: a = -3.225273, b = 3.148495, train R2 = 0.9976.

### Energy per run

| Run | Script | Duration (s) | Energy (kWh) | Emissions (kg) | short_run |
| --- | --- | --- | --- | --- | --- |
| `20261105-225640_preprocess_none_851d` | build_cache.py | 13.88 | 0.00013109 | 0.00006090 | True |
| `20261105-225713_baseline_mean_and_brightness_6ea7` | baselines.py | 10.64 | 0.00010721 | 0.00004981 | True |

Both are below measurement resolution (section 10, limit 15 s). Neither failed. Project total over
`runs/index.csv`, 11 rows: 0.002647 kWh, 296.1 s.

## Findings for review

1. The brightness baseline is far better than anything the rules anticipate: val MAE 1.08 cells and
   R2 0.998, from one number per image. Train R2 0.9976 and val R2 0.9978 agree, so this is not
   overfitting, and the feature can hold no label. Count is close to total intensity in this data.
2. Consequence for section 8: the acceptance rule compares MAE_own with MAE_best and 0.60 x MAE_mean
   = 15.51 cells. An own CNN at 15 cells would pass the second condition while being 14 times worse
   than the brightness line, so that condition is close to empty here. Brightness is not part of the
   rule. Nothing was changed; any change needs a new tagged version, and it should be decided before
   training (`rules-v2` is the natural place).
3. Consequence for the question of the project: a CNN has about 1 cell of error left to gain. The
   resolution and blur ablations may show little, since the mean of an image hardly changes with
   either.
4. The brightness MAE rises with every blur level, 0.90 to 1.25, but the intervals overlap. Blur
   barely hurts this feature.
5. Section 9 says only `scripts/evaluate_test.py` loads test arrays, and its documented exception
   covers check F only. `build_cache.py` reads the test TIFs and reads the test npz files back for
   shape, dtype, label and NaN checks. It prints no test pixel statistic and makes no choice from
   them, but the rule text does not cover it. This needs a line in the next rule version.
6. Mean baseline, by construction: val has the same 20 counts as train in equal numbers, so the
   prediction equals the val mean, R2 is exactly 0 and MAE is exactly 25.85, the same as test_seen.
   Each blur level has the same labels, so all four rows are identical. The R2 point lies just above
   its interval, because any resample shifts the mean and can only lower R2. The MAE interval
   reflects the mix of counts drawn, not any uncertainty of the model.
7. The "no NaN" check cannot fail on uint8 pixels; it means something for the labels only.
8. Intercept a = -3.23 means the line predicts about 0 cells at a mean pixel value of 1.02. Residuals
   by count were not looked at (not requested), so a possible curve at high counts is unknown.

## Differences from the prompt

- The self-test of `src/metrics.py` was not run inside `tracked_run` (the prompt asked for it on
  items 2 and 3 only). It reads no data and took about 1 s, with no row in `runs/index.csv`.
- `results/baselines_val_per_blur.csv` also has CIs and RMSE and R2 per blur level (the prompt
  asked for MAE per blur level). Section 8 applies the same procedure to all reported metrics.
- `baselines.py` checks the SHA-256 of each cache file against the manifest before use. Its loader
  refuses any split other than train and val.
- `baselines_val.json` also holds `train_mean`, and `brightness_params.json` also holds the train R2.
- `build_cache.py` stops on any raw image that is not 520x696 uint8 (section 1). It reads each
  check from the file on disk, not from memory. Files use uncompressed `np.savez`.
- Bootstrap B, seed and CI are read from `configs/rules.json`, not repeated in the code.
- This log and the prompt file were committed after the tag, as in the earlier sessions.

## Problems and solutions

None. No run failed and no script needed a second attempt.

## Left open

- `ai_log/report_notes.txt` and `ai_log/ai_journal_notes.md` do not yet record this result.
- Findings 2 and 5 need a decision before training.
- No model code was written and no training was run, as instructed.
