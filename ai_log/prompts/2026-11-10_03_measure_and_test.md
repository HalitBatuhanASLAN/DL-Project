# Prompt: measurement, test runs, results

Date: 2026-11-11 (session name 2026-11-10_03 as given in the prompt). Given verbatim to Claude Code
(Claude Opus 5.5, `claude-opus-5-5`). The text below is unchanged.

````text
Context: CSE655 project, repo = current folder. Read docs/decision_rules.md (rules-v2.1) and
configs/rules.json fully first and follow them exactly. Windows, .venv, install nothing, do not
search outside Project/. Commit every script BEFORE running it. Every run inside tracked_run.
Keep code simple and commented (exam). Record your model name and version in the session log.
Every run must log power_source "AC"; if not, stop and tell me.

STEP 1 - pre-test checks (read code and files only; no runs):
a) Confirm that train.py draws shuffled batches from the train cache (show the lines and the
   seeding). The BN diagnostic bug came from an unshuffled cache, so I want this verified.
b) Confirm the 5 final models and their artifacts exist: mean baseline, brightness baseline
   (results/baselines/brightness_params.json), own_cnn seed 42, mobilenet_v3_small seed 42,
   resnet18 seed 42 (best checkpoints). Show paths and SHA-256 of each checkpoint.
c) Confirm evaluate_test.py has never been run (results/test_log.csv absent or empty) and that no
   other script opens test files.
If any check fails, STOP and report. Do not fix anything without asking me.

STEP 2 - measure.py (section 11.7, val images, category "measure"):
latency (GPU and CPU, batch 1, median and p95) and energy per 1,000 predictions (CPU gross for
all 5 final models incl. brightness; GPU gross and net for the 3 CNNs). Also model file size (MB)
and params / MACs from results/model_tables/. Commit outputs.

STEP 3 - evaluate_test.py, exactly ONE run per final model, in this order: mean, brightness,
own_cnn, mobilenet_v3_small, resnet18. No --force. If any run crashes, STOP and report; do not
re-run without asking me.

STEP 4 - results (category "analysis", from the saved test predictions only, no test images
loaded again):
- results/results.csv with the spec table columns: model, params, MFLOPs/img, test_seen MAE,
  RMSE, R2 (with scene-bootstrap 95% CIs), train kWh, train kg CO2eq (final seed-42 run),
  training incl. LR search kg CO2eq, project kg CO2eq per model, ms/img (GPU and CPU),
  energy per 1,000 predictions, model size MB.
- Acceptance (section 8): MAE_own <= 1.15 x MAE_best and MAE_own <= 0.60 x MAE_mean, point
  estimates; plus the paired bootstrap CI of MAE_own / MAE_best.
- "Beats brightness" for each CNN (section 11): paired CI of MAE_cnn / MAE_brightness on test_seen.
- test_unseen MAE per model (diagnostic only).
- MAE per blur level and residuals by count per model (CSV).
Commit all, tag test-v1, push. STOP: no plots yet.

Session log: ai_log/prompts and ai_log/sessions, 2026-11-10_03_measure_and_test.

Summary: step 1 results; measurement table; the full results table; acceptance PASS/FAIL with the
numbers; beats-brightness verdict per CNN with CIs; test_unseen numbers; MAE per blur level;
anything unexpected. Do not interpret beyond the numbers.
````
