# Prompts: training infrastructure

Date: 2026-11-05. Given verbatim to Claude Code (claude-opus-5-5). The text below is unchanged.
One prompt, plus the answer to the weight-download question.

## Prompt 1

````text
Context: CSE655 project, repo = current folder. Read docs/decision_rules.md (rules-v2, all
sections, especially 6, 9, 10, 11) and configs/rules.json fully first; follow them exactly.
Windows, .venv, do not search outside Project/. Install nothing. Commit every script BEFORE
running it. Every run inside tracked_run. Keep code simple and commented: I must explain every
line in an exam.

0. Move report_notes.txt and ai_journal_notes.md from the Project/ root into ai_log/ (overwrite).
   Commit.

1. Baselines val predictions (rules 11.8, point 10): extend scripts/baselines.py to save one row
   per val image (model, scene_id, count, blur, prediction) to results/val_predictions/ for the
   mean and brightness baselines. Run it once (tracked, category "baseline"). Numbers must equal
   the cache-v1 results (MAE 25.85 and 1.08).

2. src/models.py:
   - OwnCNN (section 11.1) and its depthwise-separable variant (section 11.5).
   - build_standard(name): ResNet-18 / MobileNetV3-Small, IMAGENET1K_V1 weights, conv1 summed over
     RGB to 1 channel, last linear -> 1 output, MobileNet dropout 0.
   - Output bias 0.5005 for every model.
3. ImageNet weights: ASK ME before downloading (show file names and sizes). After I approve,
   download them once inside tracked_run (category "env"), record SHA-256 hashes in the README.
4. scripts/layer_table.py (tracked, category "measure"): per-layer table for OwnCNN and the
   depthwise variant at 128x96 and 256x192: output shape, params, receptive field, jump, MACs;
   totals; cross-check total MACs with FlopCounterMode and params with sum(p.numel()).
   Must reproduce 60,465 params / 37,158,976 MACs / RF 38 and 8,449 / 6,475,840.
   Also params and MACs for ResNet-18 and MobileNetV3-Small. Save CSV + Markdown to
   results/model_tables/.
5. scripts/train.py: one training run as in sections 11.2-11.4 and 11.6 (args: model, seed, lr,
   resolution, max_steps, amp, category "train" or "search"). Data from the cache (train + val
   only, refuse test files), flips as in section 6, cosine LR, L1, AdamW, early stopping exactly
   as 11.3, best checkpoint saved to checkpoints/ (git-ignored), per-eval log CSV
   (step, train loss, val MAE, lr, elapsed) in the run folder, val predictions of the best
   checkpoint saved per image, metrics.json with best val MAE/RMSE/R2, stop step, steps run.
6. scripts/lr_search.py: runs the grid of section 11.4 for one model by calling train.py logic,
   each trial its own tracked run (category "search"), applies the choice and edge rule, writes
   results/lr_search/<model>.json.
7. scripts/evaluate_test.py (write and commit, DO NOT RUN): section 9 exactly; refuses a second
   run per model without --force --reason; writes results/test_predictions/ and test_log.csv.
8. scripts/measure.py (write and commit, DO NOT RUN yet): latency and energy per 1,000
   predictions as section 11.7.
9. Smoke test: train.py with own_cnn, seed 42, lr 1e-3, max_steps 20, eval every 10 steps, at
   128x96, category "env", notes "smoke test". Also 20 steps for resnet18 and mobilenet_v3_small
   (only if weights are approved). Report: did loss go down, GPU memory peak, time per step,
   energy per step per model. Do NOT run the LR search or any real training.
10. Commit all, tag infra-v1, push. Session log as usual: ai_log/prompts and ai_log/sessions,
    2026-11-05_06_training_infra.

Summary: layer table check (PASS/FAIL against the numbers above), smoke-test numbers per model,
GPU memory peak (4 GB limit!), time and energy per step per model, estimated total time and
energy for the planned 34,200 steps, anything unexpected or anything you changed from the rules.
````

## Answer to the download question

Asked with the two file names, sizes and source. Answer: "Approve both".
