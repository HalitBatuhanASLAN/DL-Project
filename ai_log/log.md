# AI log: index

Everything about how AI tools were used in this project. The AI usage report (`report/ai_usage_report.tex`)
is written from these files. All code sessions used Claude Code (Code tab of the Claude desktop app,
Windows 11), model Claude Opus 5.5 (`claude-opus-5-5`).

## Files and folders

| Path | Contents |
| --- | --- |
| `log.md` | This index |
| `ai_journal_notes.md` | Raw notes for the AI usage report: the required report format, and journal entries on the planning chats (dataset choice, decision rules, carbon accounting) with prompts, answers, what was kept or rejected, and errors caught. Last updated 2026-11-05 |
| `report_notes.txt` | Running project notes for the main report: dataset selection and rejected candidates, design decisions and their reasons. Last updated 2026-11-05 |
| `prompts/` | The prompts the author gave to Claude Code, verbatim, one file per code session |
| `sessions/` | One session log per code session, written by the agent at the end: goal, steps, exact commands, runs (energy, CO2eq), commits and tags, problems, deviations from the prompt, limitations |
| `transcripts/` | Masked Markdown transcripts of code sessions (messages complete, tool outputs as excerpts, unrelated personal data masked) |
| `transcripts/raw/` | Raw `.jsonl` session files, kept on the author's computer only (git-ignored, never committed) |

## Code sessions

The prompt and the session log of a session have the same file name in `prompts/` and `sessions/`.

| Session | Topic | Tag(s) | Transcript |
| --- | --- | --- | --- |
| `2026-11-05_01_data_inventory` | BBBC005 extraction and data inventory | - | yes (snapshot to 20:45, see below) |
| `2026-11-05_02_rules_carbon_split` | Rules freeze, CodeCarbon helper, frozen split | `rules-v1`, `split-v1` | no |
| `2026-11-05_03_housekeeping_visual_checks` | Stain, resolution and blur checks | `data-v1` | no |
| `2026-11-05_04_rules_v1_1` | Check 2 at nucleus scale | `rules-v1.1`, `data-v2` | no |
| `2026-11-05_05_cache_baselines` | Image cache, mean and brightness baselines | `cache-v1` | no |
| `2026-11-05_06_rules_v2` | Training rules frozen before any training | `rules-v2` | no |
| `2026-11-05_06_training_infra` | Models, train/search/test/measure code, weights, smoke tests | `infra-v1` | no |
| `2026-11-10_01_rules_v2_1_and_lr_search` | Zero-init head, init and reproducibility checks, LR search | `rules-v2.1`, `infra-v1.1`, `search-v1` | no |
| `2026-11-10_02_final_training` | Final training (7 runs), ablations, BN diagnostic | `train-v1`, `ablation-v1` | no |
| `2026-11-10_03_measure_and_test` | Latency/energy measurement, one test run per model, results | `test-v1` | no |
| `2026-11-11_01_figures_and_diagnostics` | Report figures, own_cnn val diagnostics, summary table | `analysis-v1` | no |
| `2026-11-11_02_figures_v2_and_savings` | KirazNet labels, early-stopping and cache savings | `analysis-v2` | no |
| `2026-11-11_03_repo_docs` | Report sources moved to `report/`, README, this index | - | no (session log only) |

## Not in this folder

- The environment setup session was a remote claude.ai session. Its transcript is on claude.ai
  (see the share links in the appendix of the AI usage report), not here.
- Planning chats about the dataset and the rules are summarised in `ai_journal_notes.md`. Their full
  exports are linked in the AI usage report.

## Transcript status

Only `transcripts/2026-11-05_01_data_inventory.md` exists so far. It was made from a copy of the raw file
taken at 20:45:30 on 2026-11-05, so it stops partway through the logging task at the end of that session.
The complete raw files of all code sessions are stored by Claude Code outside the repository. The masked
transcripts of the other sessions still need to be generated from them (see
`sessions/2026-11-11_03_repo_docs.md`).
