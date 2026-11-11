# Prompt: figures and own_cnn diagnostics

Date: 2026-11-11. Given verbatim to Claude Code (Claude Opus 5.5, `claude-opus-5-5`). The text
below is unchanged.

````text
Context: CSE655 project, repo = current folder. Read docs/decision_rules.md (rules-v2.1) and
configs/rules.json first. Windows, .venv, install nothing, do not search outside Project/.
Commit every script BEFORE running it. Every run inside tracked_run (category "analysis").
Keep code simple and commented (exam). Record your model name and version in the session log.
Do NOT run evaluate_test.py and do NOT load any test image. Use only saved predictions,
run folders and val data.

1. Main figure (spec 3.5): test_seen MAE (y) vs kg CO2eq (x, LOG scale), one point per model or
   configuration: the 5 final models plus the val-only variants (own_cnn seeds 43/44, mobilenet
   seeds 43/44, 256x192, depthwise, resnet18 AMP) shown with a different marker and labelled
   "val MAE" so test and val points are never mixed silently. Mark the Pareto front (test points
   only). Make two versions: x = training CO2 incl. LR search, and x = project CO2 per model.
   Save PNG (300 dpi) + PDF to results/figures/.
2. Other figures for the report: val MAE curves over steps for the 7 final-training runs
   (shows the spikes); test_seen MAE per blur level per model; mean residual by count per model
   (seen and unseen counts marked); bar chart of energy per 1,000 predictions (CPU gross, log scale).
3. "Why did own_cnn fail" - val-only diagnostics, results in results/diagnostics/:
   a) For own_cnn seed 42: val MAE at the best checkpoint vs. the median val MAE of the last
      5 evaluations (how lucky was the selected checkpoint?). Same for mobilenet seed 42.
   b) Mean signed residual on val for own_cnn seed 42 and mobilenet seed 42 (is the systematic
      offset already visible on val?), and val MAE after subtracting that mean offset
      (diagnostic only, never applied to test).
   c) own_cnn val MAE per blur level for seeds 42/43/44.
4. Write results/summary.md: one table with every number the report will cite (test, val, energy,
   CO2, latency, acceptance, beats-brightness), each with the file it comes from.
Commit all, tag analysis-v1, push.

Session log: ai_log/prompts and ai_log/sessions, 2026-11-11_01_figures_and_diagnostics.
Summary: list of figures, the diagnostic numbers, and anything unexpected.
````
