# Session log: housekeeping and visual checks

| Field | Value |
| --- | --- |
| Date | 2026-11-05, from about 22:30 (UTC+3) |
| Tool | Claude Code, Code tab of the Claude desktop app, on Windows 11 |
| Model | Claude Opus 5.5 (`claude-opus-5-5`), auto permission mode |
| Prompt | `ai_log/prompts/2026-11-05_03_housekeeping_visual_checks.md` |
| Commits | `18f3403` housekeeping; `4df88ec` check_stain.py and helpers; `8aafc98` check_resolution.py; `76197fa` check_blur.py; `c0995a1` results and run folders |
| Tags | `data-v1` -> `c0995a1` |

## Goal

Finish the housekeeping left over from session 02, then run the pre-registered visual checks
(stain, file sanity, resolution, blur) and record their decisions. No cache and no baseline.

## Steps

1. Read `docs/decision_rules.md`, `configs/rules.json`, `src/`, `scripts/make_split.py`, and the
   notes.
2. Part A: compared old and new notes (the old ones hold nothing that is lost), moved both into
   `ai_log/`, added root `.gitattributes`, added the missing row, committed and pushed.
3. Added helpers to `src/common.py`. `read_training_image()` refuses any non-train image, so
   checks A, 1, 2 and B1 cannot read a test file by accident.
4. Wrote, committed and pushed each script, then ran it. Each run's `config.json` records the
   commit that contains its code (verified: `4df88ec`, `8aafc98`, `76197fa`).
5. Looked at every figure after its run, before going on.
6. Committed results and run folders, tagged `data-v1`, pushed. Stopped there.

## Commands

```bash
git add scripts/check_stain.py src/common.py && git commit && git push origin main
.venv/Scripts/python.exe scripts/check_stain.py
git add scripts/check_resolution.py && git commit && git push origin main
.venv/Scripts/python.exe scripts/check_resolution.py
git add scripts/check_blur.py && git commit && git push origin main
.venv/Scripts/python.exe scripts/check_blur.py
git add results runs && git commit
git tag -a data-v1 -m "..."
git push origin main data-v1
```

## Key outputs

### Check F (all 19,200 files, aggregate only): PASS

0 of 19,200 files differ from 520x696 uint8.

| Stain | Split | Files | Min | Max | Mean | Mean of medians | % at 0 | % at 255 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| w1 | train | 4800 | 0 | 255 | 16.94 | 2.42 | 4.60 | 0.00000006 |
| w1 | val | 1600 | 0 | 251 | 16.85 | 2.41 | 4.59 | 0 |
| w1 | test_seen | 1600 | 0 | 254 | 16.97 | 2.45 | 4.58 | 0 |
| w1 | test_unseen | 1600 | 0 | 253 | 17.72 | 2.47 | 4.51 | 0 |
| w2 | train | 4800 | 0 | 243 | 53.07 | 39.59 | 4.58 | 0 |
| w2 | val | 1600 | 0 | 244 | 52.82 | 38.94 | 4.59 | 0 |
| w2 | test_seen | 1600 | 0 | 242 | 53.22 | 39.58 | 4.55 | 0 |
| w2 | test_unseen | 1600 | 0 | 239 | 55.60 | 42.13 | 4.36 | 0 |

### Check A (C1 F1, samples 1 and 4): nuclei = w1, conflict with the documentation

Rule: containment >= 0.90 and area ratio <= 0.70, in both samples.

| Sample | Area w1 | Area w2 | Containment w1 in w2 | Ratio w1/w2 | Containment w2 in w1 | Ratio w2/w1 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 742 | 2424 | 1.000 | 0.306 | 0.306 | 3.267 |
| 4 | 791 | 3187 | 1.000 | 0.248 | 0.248 | 4.029 |

w1 PASS, w2 FAIL. The rule says "w1 passes -> nuclei = w1, conflict reported", which is not a
stop. `stain_overlay.png` agrees: w1 is the small blob, w2 the large body around it.

### Check 1 (C1 F1, samples 1, 4, 7, 8, 10, stain w1)

Diameters 30.74, 31.74, 32.94, 31.74, 31.74 px; d_native (median) = 31.74 px. Limit 3.0 px.

| Candidate | Factor | Diameter (px) | Check 1 |
| --- | --- | --- | --- |
| 128x96 | 5.4375 | 5.84 | PASS |
| 256x192 | 2.71875 | 11.67 | PASS |
| 348x260 | 2.0 | 15.87 | PASS |

### Check 2 (C100 F1, same samples, stain w1)

Window 15 px. Peaks per image 164, 154, 157, 160, 185. 540 pairs, 299 resolved at native.
Pair distance min/median/max 8.2 / 20.8 / 89.0 px. Limit: retention >= 0.90.

| Candidate | Kept of 299 | Retention | Check 2 |
| --- | --- | --- | --- |
| 128x96 | 188 | 0.6288 | FAIL |
| 256x192 | 258 | 0.8629 | FAIL (borderline) |
| 348x260 | 269 | 0.8997 | FAIL (borderline, 1 pair short of 270) |

Decision: no candidate passes both, so main 348x260, ablation 256x192, as reported by the rule.

### Check B1 (s01 x 20 seen counts, stain w1, 348x260, sigma 7.934 px)

| F | 1 | 4 | 7 | 10 | 14 | 17 | 20 | 23 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D(F) | 0.0000 | 0.0067 | 0.0056 | 0.0167 | 0.0295 | 0.0309 | 0.0494 | 0.0639 |

| F | 26 | 29 | 32 | 35 | 39 | 42 | 45 | 48 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D(F) | 0.0839 | 0.0861 | 0.1065 | 0.1238 | 0.1459 | 0.1703 | 0.1743 | 0.2032 |

K = ceil(0.2032 / 0.20) + 1 = 3, clipped to 4. Targets 0, 0.0677, 0.1355, 0.2032.
Decision: blur levels F1, F23, F39, F48.

### Energy per run

| Run | Script | Duration (s) | Energy (kWh) | Emissions (kg) | short_run |
| --- | --- | --- | --- | --- | --- |
| `20261105-223456_analysis_none_35e5` | check_stain.py | 218.87 | 0.00177949 | 0.00082673 | False |
| `20261105-223943_analysis_none_005b` | check_resolution.py | 1.95 | 0.00002318 | 0.00001077 | True |
| `20261105-224059_analysis_none_17c5` | check_blur.py | 3.35 | 0.00003392 | 0.00001576 | True |

The two short runs are below measurement resolution (section 10). No run failed. Project total
over `runs/index.csv`, 7 rows: 0.002381 kWh.

## Findings for review

1. Stain: the documented identity (w2 = nuclei) is wrong for this data. All later steps use w1.
2. Check 2 measures mostly texture inside nuclei, not separation between nuclei. C100 images
   gave 154-185 peaks for 100 nuclei; 80 % of pairs are closer than one nucleus diameter. In
   `peaks_c100.png` the lost pairs lie inside single nuclei. Diagnostic from
   `resolution_pairs.csv`, not a decision, on native-resolved pairs at least d_native apart
   (109 pairs): retention 128x96 0.954, 256x192 0.991, 348x260 1.000. The filter is crude, since
   touching nuclei can also be closer than d_native. Under such a pair definition 128x96 would
   pass, but the frozen rule was applied unchanged. Any change needs a new tagged rule version
   with a reason (decision_rules.md, header). 348x260 has about 9.8 times the pixels of 128x96.
3. D(F48) = 0.20, while section 5 expected 0.6-1.0. K comes from the lower clip, not from the
   curve. The high-pass sigma equals the nucleus radius, so blob-scale structure stays in hp().

## Differences from the prompt

- "Sheet C" is not defined in section 4 or in `rules.json`. I used the "resolution sheet (native
  / 256x192 / 128x96)" from `report_notes.txt`, plus 348x260: C100 full, C100 crop and C1 crop of
  training sample 1. It takes no part in any decision.
- Exact values of the synthetic test were not available inside `Project/`, so the rounded ones
  were used. `emissions_kg` is left empty (not given), `start_time` is the date only, `short_run`
  is True, `run_id` is `synthetic_helper_test_20261105`.
- The prompt gives status "ok" for that row. Session 02's log describes the test as the failure
  path (a deliberate RuntimeError). "ok" was used as instructed.
- Check F computes more than the list in section 9 (median, % at 0 and 255), as the prompt asks.
  It is still aggregate only.
- Script commits were also pushed before running (the prompt asks only for the commit).
- Extra outputs: `peaks_c100.png`, `resolution_pairs.csv`, `blur_similarity.csv`,
  `blur_strip.png`, `file_sanity.csv`.
- Choices the rules leave open: 4-connectivity (scipy default) for components; `mode="nearest"`
  for sampling at the image edge; F1 and F48 reserved first, then middle targets filled in order;
  no merging of equal neighbouring maxima (closest peaks are 8.2 px apart, so none occurred).
- `choose()` in `check_resolution.py` has an unused first argument. Left as is, so the committed
  code stays the code that ran.

## Problems and solutions

- The first attempt to write the files through one long Bash heredoc failed with a shell parse
  error, before any command ran (checked with `git status`). Solved by using the file tools.
- `scikit-image` is not installed; not needed, since `otsu()` exists and scipy gives the rest.

## Left open

- Decide whether to keep 348x260 or issue a new tagged rule version for check 2. Blur levels
  depend on the resolution, so check B1 would need a re-run, and `data-v1` a successor.
- `ai_log/report_notes.txt` still says stain "w2 = nuclei, confirmed by the overlay check" as the
  plan; it needs the real result.
- Cache and baselines were not started, as instructed.
