# Prompts: rules-v2.1, init check, reproducibility check and LR search

Date: 2026-11-10. Given verbatim to Claude Code (Claude Opus 5.5, `claude-opus-5-5`).
The text below is unchanged. Two prompts: the first stopped at step 0 because the tags
rules-v2.1 and infra-v1.1 did not exist; the second added Part A and repeated the rest.

## Prompt 1

````text
Context: CSE655 project, repo = current folder. Read docs/decision_rules.md and
configs/rules.json fully first and follow them exactly. Windows, .venv, install nothing,
do not search outside Project/. Commit every script BEFORE running it. Every run inside
tracked_run. Keep code simple and commented (exam). Record in the session log which AI model
you are (name and version as shown to you).

Conditions for every run in this session: laptop on AC power, fixed power plan, no heavy apps.
Check the AC status that tracked_run logs; if it says battery, stop and tell me.

STEP 0 - state check (no runs):
- Show git log --oneline -8 and git tag. Confirm tags rules-v2.1 and infra-v1.1 exist and that
  the init check gave val MAE 25.85 for all 4 models with a non-zero head gradient.
- If rules-v2.1 or infra-v1.1 is missing, STOP and tell me what is missing. Do nothing else.
- If report_notes.txt or ai_journal_notes.md are in the Project/ root, move them into ai_log/
  (overwrite) and commit.

STEP 1 - reproducibility check (category "env", notes "reproducibility check"):
- Run own_cnn, seed 42, lr 1e-3, 150 steps, twice. Compare val MAE and the final weights.
  Report whether they are bit-identical; if not, report the largest difference.

STEP 2 - LR search (section 11.4), in this order: own_cnn, mobilenet_v3_small, resnet18.
- Each trial is its own tracked run (category "search"). Apply the choice rule and edge rule
  exactly. Write results/lr_search/<model>.json.
- After all three: commit, tag search-v1, push.

STOP after step 2. Do not start final training.

Session log as usual: ai_log/prompts and ai_log/sessions, 2026-11-10_01_lr_search.

Summary:
- Step 0 result.
- Reproducibility: identical or not, largest difference.
- For each model: val MAE at step 300 for every LR, chosen LR, whether the edge rule fired.
- Measured time and energy per trial and per step for each model (these are the first runs
  above measurement resolution if they last > 15 s; say which are still short runs).
- Updated estimate of time and energy for the remaining training (section 11 plan).
- Anything unexpected, and anything that looks like a bug (e.g. a model getting worse than the
  mean baseline, NaN loss, GPU memory near 4 GB).
````

## Prompt 2

````text
The rules-v2.1 session was never run. Do it now in this session, then continue.

PART A - rules-v2.1 (decided on 2026-11-05, before any LR search or real training):
1. Commit the uncommitted changes in ai_log/report_notes.txt and ai_log/ai_journal_notes.md
   ("Update notes: rules-v2.1 decision"). They already contain the decision.
2. Rule change: the final linear layer's WEIGHTS are initialised to zero for every model
   (own_cnn, own_cnn_ds, resnet18, mobilenet_v3_small); the bias stays 0.5005.
   Reason (mine, verbatim): "Every model then starts by predicting the training mean, which is
   exactly the mean baseline, so no model wastes its first steps. ResNet-18 started at about
   131 cells error with the default head initialisation. The same rule for all models keeps
   the comparison fair."
   Update section 11.1 of docs/decision_rules.md and configs/rules.json
   ("output_weight_init": "zeros", version "rules-v2.1"), add a "Changes from rules-v2" note with
   the smoke-test observation and the fact that the decision was recorded on 2026-11-05 but
   implemented on 2026-11-10 (no training happened in between). Commit, tag rules-v2.1, push.
3. Implement it in src/models.py. Commit.
4. Init check (tracked, category "env", notes "init check, no training"): for all 4 models,
   build, no training, val MAE in eval mode at step 0 (expected 25.85 each), plus one
   forward + backward pass to check the head weight gradient is non-zero. PASS/FAIL per model.
   Commit results, tag infra-v1.1, push.

GATE: if all 4 models PASS, continue with STEP 1 (reproducibility check) and STEP 2 (LR search)
from my previous message, exactly as written. If any model FAILS, stop and report.

Session log: one log covering both parts, 2026-11-10_01_rules_v2_1_and_lr_search, including
your model name and version.
````
