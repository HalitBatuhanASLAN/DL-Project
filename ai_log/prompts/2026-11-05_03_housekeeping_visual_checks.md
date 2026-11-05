# Prompt: housekeeping and visual checks

Date: 2026-11-05. Given verbatim to Claude Code (claude-opus-5-5). The text below is unchanged.

````text
Context: CSE655 project, repo = current folder (Project/). Read docs/decision_rules.md and
configs/rules.json fully first and follow them exactly. Windows, .venv, install nothing,
do not search outside Project/. Keep code simple and commented (exam).

PART A - housekeeping (one commit, before anything else):
1. Move report_notes.txt and ai_journal_notes.md from the Project/ root into ai_log/
   (overwrite the old ones).
2. Add configs/rules.json and docs/decision_rules.md to splits/.gitattributes-style protection:
   create a root .gitattributes that keeps *.json, *.csv and *.md in configs/, docs/, splits/
   byte-for-byte (no CRLF conversion). Keep the existing splits/.gitattributes working.
3. The synthetic helper test from the last session consumed energy but is not in
   runs/index.csv. Add one row with append_index_row(): category "env", model "none",
   status "ok", energy 1.7e-8 kWh, duration 0.15 s, notes "synthetic helper test of
   2026-11-05, run folder not kept". If you have the exact values, use them.
4. Commit and push: "Housekeeping: notes, line-ending protection, missing run row".
New rule from now on: commit every script BEFORE running it, so config.json records the
commit that actually contains the code.

PART B - visual checks (sections 3, 4 and 5 of decision_rules.md). Use only the training
scenes defined there, except check F (aggregate statistics only, documented exception).
Each script: committed first, then run inside tracked_run(category="analysis", model="none"),
writes its decision file to results/decisions/ and its figures/CSVs to results/visual_check/.
Each script refuses to run if the previous decision file is missing.

1. scripts/check_stain.py: check A (rule in section 3) + check F (all 19,200 files: shape,
   dtype, and per stain x split: min/max/mean, mean of per-image medians, % pixels at 0 and 255).
   Output results/decisions/stain.json with the nuclei stain and all measured numbers.
   If the rule says "stop", stop and report; do not continue to step 2.
2. scripts/check_resolution.py: checks 1 and 2 + sheet C (section 4).
   Output results/decisions/resolution.json (main and ablation resolution, all numbers).
3. scripts/check_blur.py: check B1 (section 5) with the high-pass metric.
   Output results/decisions/blur_levels.json (D(F) for all 16 levels, K, chosen levels).
4. Commit all results and run folders; tag data-v1; push.

STOP after Part B. Do not build the cache and do not run baselines.

Session log (last): save this prompt verbatim to
ai_log/prompts/2026-11-05_03_housekeeping_visual_checks.md and write
ai_log/sessions/2026-11-05_03_housekeeping_visual_checks.md (date, tool/model, goal, steps,
commands, key outputs, energy per run, anything beyond or different from the prompt,
problems and solutions). Commit and push.

At the end, give me a plain-text summary with, for each check: the measured numbers, the
rule threshold, PASS/FAIL, and the resulting decision (nuclei stain, main + ablation
resolution, chosen blur levels and K). List every figure file produced, energy and duration
of each run, and anything unexpected. If any number is borderline (within 10% of a
threshold), say so explicitly.
````
