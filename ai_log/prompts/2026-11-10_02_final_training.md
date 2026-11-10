# Prompt: final training, ablations, post-hoc BN diagnostic

Date: 2026-11-10. Given verbatim to Claude Code (Claude Opus 5.5, `claude-opus-5-5`).
The text below is unchanged.

````text
Context: CSE655 project, repo = current folder. Read docs/decision_rules.md (rules-v2.1) and
configs/rules.json fully first and follow them exactly. Windows, .venv, install nothing, do not
search outside Project/. Commit every script BEFORE running it. Every run inside tracked_run.
Keep code simple and commented (exam). Record your model name and version in the session log.
Every run must log power_source "AC"; if not, stop and tell me.

1. Final training runs (section 11, chosen LRs from results/lr_search/*.json, max 3,000 steps,
   early stopping exactly as 11.3, category "train"), in this order:
   - own_cnn seeds 42, 43, 44 (lr 3e-3)
   - mobilenet_v3_small seeds 42, 43, 44 (lr 3e-3)
   - resnet18 seed 42 (lr 1e-3)
   After these 7 runs: commit, tag train-v1, push.

2. Ablations and efficiency runs (section 11.5, val only, seed 42, parent LR):
   - own_cnn at 256x192
   - own_cnn_ds (depthwise-separable) at 128x96
   - resnet18 with AMP (mixed precision)
   - resnet18 noise reference: 600 steps, no AMP
   Commit, tag ablation-v1, push.

3. Post-hoc diagnostic (NOT pre-registered, NOT used for any choice; category "analysis",
   notes "post-hoc BN diagnostic"): for the mobilenet_v3_small seed-42 checkpoint, recompute
   BatchNorm running statistics with one pass over the TRAIN cache in train mode, no gradient,
   no weight change; then report val MAE before and after. Do the same for own_cnn and resnet18
   seed 42 for comparison. Do not save the recalibrated weights as a final model.
   Commit, push.

STOP. Do NOT run measure.py or evaluate_test.py.

Session log: ai_log/prompts and ai_log/sessions, 2026-11-10_02_final_training.

Summary:
- Table for every run: model, seed, resolution, LR, stop step (early stop or 3,000), best val MAE,
  RMSE, R2, duration, energy (Wh), short_run.
- Seed spread (mean and min-max of best val MAE) for own_cnn and mobilenet_v3_small.
- Which models beat brightness on val (1.08)? (val only; the real decision is on test.)
- Ablations: val MAE and energy vs the own_cnn seed-42 run, and whether the difference is larger
  than the own_cnn seed spread.
- AMP vs noise reference: energy per step and time per step.
- BN diagnostic: val MAE before/after per model.
- Project total energy and CO2 so far. Anything unexpected (NaN, swings, memory).
````
