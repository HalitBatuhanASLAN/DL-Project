# Prompt: rules freeze, carbon helper, frozen split

Date: 2026-11-05. Given verbatim to Claude Code (claude-opus-5-5). The text below is unchanged.

````text
Context: CSE655 "green CNN regression" project, repo at the current folder (Project/).
Windows, PowerShell, Python 3.11, .venv. Everything in the repo is in English.
The data-preparation design is frozen in docs/decision_rules.md and configs/rules.json.
Read both files fully before doing anything. Follow them exactly; if something in them is
unclear or impossible, stop and ask instead of improvising.

Scope of this session (stop after step 6; do NOT run any visual check, cache or baseline):

0. Three files are in the Project/ root. Move them (move, not copy):
   - decision_rules.md -> docs/decision_rules.md   (create docs/)
   - rules.json        -> configs/rules.json        (create configs/)
   - ai_journal_notes.md -> ai_log/ai_journal_notes.md (overwrite the old one)
   Show me the folder listing afterwards.

1. Commit and tag the rules.
   - Check that .gitignore ignores data/ but NOT runs/, results/, splits/, docs/, configs/.
   - Add scipy to requirements.txt with the exact installed version (it is already installed
     as a dependency of scikit-learn; do not install anything new).
   - Commit docs/decision_rules.md, configs/rules.json and requirements.txt:
     "Freeze data-preparation rules (rules-v1)". Create git tag rules-v1. Push commit and tag.

2. Write src/common.py: paths, load_rules() (reads configs/rules.json), read_tif(),
   resize_box() (PIL Image.Resampling.BOX), otsu() (numpy, 256-bin histogram),
   sha256(). Only what is listed; short and commented.

3. Write src/carbon.py exactly as in section 10 of decision_rules.md:
   - tracked_run(category, model, config) context manager using OfflineEmissionsTracker
     (country_iso_code="TUR", measure_power_secs=5, output_dir = the run folder).
   - run_id = YYYYMMDD-HHMMSS_<category>_<model>_<hash4 of config>.
   - On enter: create runs/<run_id>/, write config.json (args, seed, git commit, hashes of
     configs/rules.json and splits file if present, torch/CUDA/codecarbon versions, GPU name,
     AC/battery status if available).
   - On exit, in a finally block: stop tracker, write metrics.json (status ok/failed with
     exception type and message, duration, energy kWh, emissions kg, short_run flag),
     append one row to runs/index.csv, re-raise any exception.
   - append_index_row() for adding a row without a tracker.
   Then add the legacy row for runs/_env_check/ with append_index_row() (category env,
   values copied from its emissions.csv, notes "legacy format, pre-helper, not re-run").

4. Re-run scripts/data_inventory.py once under tracked_run(category="analysis", model="none").
   Change the script only as much as needed to wrap its main() in tracked_run.
   Compare the new results/data_inventory.txt with the committed one and report whether
   they are identical (they should be). This run also tests the carbon helper.

5. Write scripts/make_split.py exactly as in section 2 of decision_rules.md, wrapped in
   tracked_run(category="preprocess", model="none"):
   - numpy.random.default_rng(42).permutation(numpy.arange(1, 26)) -> 15/5/5 samples.
   - held-out counts 14, 40, 66, 91 -> test_unseen (all 25 samples).
   - Output splits/splits.csv (all 19,200 images: relative_path, count, blur, sample, stain,
     scene_id, split) and splits/splits.sha256; results/split_summary.csv.
   - Built-in checks that must all pass, printed as PASS/FAIL:
     a) no scene appears in two splits; b) scene counts train 300 / val 100 / test_seen 100 /
     test_unseen 100; c) held-out counts appear only in test_unseen; d) every split x count x
     blur x stain cell has the same number of images within each split.
   - Print the sample permutation and which samples went to train/val/test.

6. Show me git status, then commit everything from steps 2-5 (src/, scripts/, splits/,
   results/, runs/) with message "Carbon helper, tracked inventory re-run, frozen split
   (split-v1)", tag split-v1, push commit and tag.

Session log (do this last, in the same commit or a follow-up commit):
- Save this prompt verbatim to ai_log/prompts/2026-11-05_02_rules_carbon_split.md
- Write ai_log/sessions/2026-11-05_02_rules_carbon_split.md: date, tool/model, goal, steps,
  commands, key outputs (energy of each tracked run, split check results, permutation),
  anything you did beyond or differently from this prompt, problems and solutions.

Constraints:
- Use only installed packages (numpy, scipy, pillow, pandas, codecarbon, torch). Install nothing.
- Do not read or display any image pixels in this session except inside the inventory re-run.
- Do not search the computer outside Project/.
- Keep the code simple and commented; I must explain every line in an exam.

At the end, give me a plain-text summary: tags created, files added, the sample permutation
and split assignment, all PASS/FAIL results, energy and duration of each tracked run,
and anything unexpected.
````
