# Prompt: figures v2 (KirazNet labels, linear y) and savings

Date: 2026-11-11. Given verbatim to Claude Code (Claude Opus 5.5, `claude-opus-5-5`). The text
below is unchanged.

````text
Context: CSE655 project, repo = current folder. Read docs/decision_rules.md first. Windows, .venv,
install nothing, do not search outside Project/. Commit every script BEFORE running it. Every run
inside tracked_run (category "analysis"). Do NOT run evaluate_test.py and do NOT load any test image.
Record your model name and version in the session log.

1. Naming: in all report figures, label own_cnn as "KirazNet" and own_cnn_ds as "KirazNet-Lite"
   (code, run folders and CSV keys stay unchanged).
2. Re-plot results/figures/mae_vs_co2_training: remove the mean baseline (state "mean baseline MAE
   25.85, not shown" in the title), LINEAR y axis, log x axis, fix the overlapping mobilenet s43/s44
   labels. Re-plot mae_vs_co2_project with ONLY the 5 test points (final models + brightness;
   mean removed the same way). Re-plot val_curves, residual_by_count, test_mae_by_blur and
   energy_per_1000 with the new labels only. PDF + PNG as before.
3. scripts/savings.py: (a) early stopping: for every training run that stopped before 3,000 steps,
   steps not run x that run's measured energy per step -> Wh and g CO2eq saved, plus the total;
   (b) caching: one tracked run that reads the 1,200 TRAIN TIFs from data/raw and resizes them
   (as build_cache does) vs one tracked run that loads the train cache; report time and energy of
   each, and the saving per training run if TIFs were decoded every epoch (number of epochs from the
   seed-42 KirazNet run). Write results/savings.json and add the rows to results/summary.md.
4. Also add to results/summary.md: Wh and steps run for the two ablations, the AMP run and the
   noise reference, and energy per step for each (so the report's ablation table has a source).
5. Commit all, tag analysis-v2, push.
Session log: ai_log/prompts and ai_log/sessions, 2026-11-11_02_figures_v2_and_savings.
Summary: list of re-plotted figures, the savings numbers, the new summary rows.
````
