# Session log: rules freeze, carbon helper, frozen split

| Field | Value |
| --- | --- |
| Date | 2026-11-05, from about 22:10 (UTC+3) |
| Tool | Claude Code, Code tab of the Claude desktop app, on Windows 11 |
| Model | Claude Opus 5.5 (`claude-opus-5-5`), auto permission mode |
| Prompt | `ai_log/prompts/2026-11-05_02_rules_carbon_split.md` |
| Commits | `2bdd08b` Freeze data-preparation rules (rules-v1); `b5bc7ae` Carbon helper, tracked inventory re-run, frozen split (split-v1) |
| Tags | `rules-v1` -> `2bdd08b`; `split-v1` -> `b5bc7ae` |

## Goal

Freeze the data-preparation rules, build the carbon tracking helper, re-run the inventory
under it, and create the frozen split. No visual check, cache or baseline was run.

## Steps

1. Read `decision_rules.md` and `rules.json` fully before changing anything. Cross-checked by
   hand: seen-count mean 50.05 and test_seen mean-baseline MAE 25.85 both follow from the counts.
2. Moved the three root files to `docs/`, `configs/`, `ai_log/`.
3. Confirmed with `git check-ignore` that only `data/` is ignored among the six paths.
4. Added `scipy==1.17.1` to `requirements.txt`, committed the three files, tagged `rules-v1`, pushed.
5. Wrote `src/common.py` and `src/carbon.py`.
6. Tested them on synthetic data in the scratchpad, including the failure path.
7. Added the legacy `_env_check` row to `runs/index.csv`.
8. Wrapped `scripts/data_inventory.py` in `main()` and re-ran it under `tracked_run`.
9. Wrote and ran `scripts/make_split.py`; re-checked the result with a separate snippet.
10. Showed `git status`, committed, tagged `split-v1`, pushed.

## Commands

```bash
mkdir -p docs configs
mv decision_rules.md docs/decision_rules.md
mv rules.json configs/rules.json
mv -f ai_journal_notes.md ai_log/ai_journal_notes.md
git check-ignore -v data/ runs/ results/ splits/ docs/ configs/
git add docs/decision_rules.md configs/rules.json requirements.txt
git commit -m "Freeze data-preparation rules (rules-v1)"
git tag rules-v1
git push origin main
git push origin rules-v1
.venv/Scripts/python.exe <scratchpad>/test_helpers.py <scratchpad>
.venv/Scripts/python.exe scripts/data_inventory.py
.venv/Scripts/python.exe scripts/make_split.py
git add src/ scripts/ splits/ results/ runs/
git commit -m "Carbon helper, tracked inventory re-run, frozen split (split-v1)"
git tag split-v1
git push origin main
git push origin split-v1
```

The legacy row was added once with a short inline Python snippet that read
`runs/_env_check/emissions.csv` and called `append_index_row()`. It is not a saved script.

## Key outputs

Carbon (`runs/index.csv`):

| Run | Category | Status | Duration (s) | Energy (kWh) | Emissions (kg CO2e) | short_run |
| --- | --- | --- | --- | --- | --- | --- |
| `_env_check` (legacy) | env | ok | 10.18 | 0.000188 | 0.0000875 | True |
| `20261105-221607_analysis_none_21b5` | analysis | ok | 34.01 | 0.000353 | 0.000164 | False |
| `20261105-221700_preprocess_none_fc37` | preprocess | ok | 0.41 | 0.00000358 | 0.00000166 | True |

`short_run` True means "below measurement resolution" (section 10).

Inventory re-run: content identical to the committed `results/data_inventory.txt`, compared
byte for byte after normalising line endings. The working file (CRLF) was also byte-identical
to its pre-run state, and git shows no change.

Split:

```text
Sample permutation (seed 42): [16, 17, 20, 21, 10, 8, 18, 25, 7, 11, 4, 1, 22, 19, 13, 6, 12, 15, 24, 3, 5, 23, 2, 14, 9]
Train samples    : [16, 17, 20, 21, 10, 8, 18, 25, 7, 11, 4, 1, 22, 19, 13]
Val samples      : [6, 12, 15, 24, 3]
Test samples     : [5, 23, 2, 14, 9]
Held-out counts  : [14, 40, 66, 91]
PASS  a) no scene appears in two splits
PASS  b) scene counts {'test_seen': 100, 'test_unseen': 100, 'train': 300, 'val': 100}
PASS  c) held-out counts only in test_unseen
PASS  d) cells balanced within each split
```

| Split | Scenes | Images | Images per cell |
| --- | --- | --- | --- |
| train | 300 | 9,600 | 15 |
| val | 100 | 3,200 | 5 |
| test_seen | 100 | 3,200 | 5 |
| test_unseen | 100 | 3,200 | 25 |

`splits/splits.csv` SHA-256: `43fee5789616aa731391b037575ed58695cdcc80cab4aa19bdf73f6b400a3690`.
The blob committed to git has the same hash. A separate check confirmed the per-split sample
sets, train mean 50.05 and test_seen mean-baseline MAE 25.85.

## Differences from the prompt

- `scripts/data_inventory.py` had no `main()`; all its code ran at module level. Added `main()`
  and indented the whole body. Without whitespace the diff is 12 added lines: `import sys`,
  the `sys.path` line, the `tracked_run` import, `def main():`, and the `__main__` block.
- Added `splits/.gitattributes` (not requested). See Problems.
- `config.json` has one extra field, `command` (`sys.argv`). `runs/index.csv` columns were not
  specified; chose run_id, start_time, category, model, status, duration_s, energy_kwh,
  emissions_kg, short_run, notes. `notes` holds the exception type for a failed run.
- `otsu()` also accepts float images, with bins over min..max, because section 4 applies Otsu to
  a smoothed image. It returns the centre of the best bin. A constant image raises ValueError.
- AC/battery status uses `ctypes` and the Windows `GetSystemPowerStatus` call. `psutil` is
  installed but is not on the allowed list or in `requirements.txt`.
- `make_split.py` writes its outputs only after all four checks pass.
- `splits.csv` is read from file names under `rules.json` `data.raw_dir`, not from
  `data/bbbc005_index.csv`, so the split does not depend on an ignored file.
- One extra `tracked_run` was executed by the scratchpad test (failure path, a `RuntimeError`
  on purpose) with `RUNS_DIR` redirected to the scratchpad: 0.15 s, 1.7e-8 kWh. It is not in
  `runs/index.csv`. The same test ran `read_tif` on a synthetic TIF. No real image was read
  outside the inventory re-run.
- Used the Bash tool (Git Bash) for commands rather than PowerShell.
- Commit messages carry a `Co-Authored-By` trailer, as in earlier commits.

## Problems and solutions

- `core.autocrlf` is `true`, so git would change the line endings of `splits.csv` on checkout
  and break `splits.sha256`. Solved by writing LF on every system and adding
  `splits/.gitattributes` with `-text` for both files, so they are stored byte for byte.

## Left open

- `ai_log/report_notes.txt` was already deleted in the working tree when the session started, and
  `docs/decision_rules.md` cites it (provenance paragraph). The deletion was not committed, so the
  file remains in git at both tags.
- `ai_log/ai_journal_notes.md` (moved in step 0) is modified but uncommitted: no step listed it.
  The old copy was already deleted when the session started, so the move overwrote nothing on disk.
- `configs/rules.json` has no `-text` rule, so a future checkout may turn it into CRLF and change
  `rules_sha256` in `config.json`. Its content would stay the same.
- `git_commit` in both `config.json` files is `2bdd08b`, because the helper and scripts were
  committed after the runs that used them.
