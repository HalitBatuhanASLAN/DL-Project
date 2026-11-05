# Session log: training infrastructure

| Field | Value |
| --- | --- |
| Date | 2026-11-05, from about 23:25 (UTC+3) |
| Tool | Claude Code, Code tab of the Claude desktop app, on Windows 11 |
| Model | Claude Opus 5.5 (`claude-opus-5-5`), auto permission mode |
| Prompts | `ai_log/prompts/2026-11-05_06_training_infra.md` |
| Commits | `0063f55` to `ca7a15e`, then this log |
| Tag | `infra-v1` -> `ca7a15e` |

## Goal

Write the model, training, search, test and measurement code, download the ImageNet weights after
approval, and smoke-test training. No LR search, no real training, no test run.

## Steps

1. Moved the two notes files into `ai_log/`. The root copies held every line of the old ones.
2. Added `src/data.py`, extended `scripts/baselines.py` and `tracked_run`, ran the baselines.
3. Added `src/models.py`. Asked before downloading, with exact sizes from HEAD requests.
4. Added and ran `scripts/download_weights.py`; put the SHA-256 hashes in the README.
5. Added and ran `scripts/layer_table.py`.
6. Added `scripts/train.py` and `scripts/lr_search.py`.
7. Added `scripts/evaluate_test.py` and `scripts/measure.py`. Compiled, not run.
8. Ran three smoke tests, tagged, pushed.

## Commands

```bash
.venv/Scripts/python.exe scripts/baselines.py          # twice, see "Problems and solutions"
.venv/Scripts/python.exe scripts/download_weights.py
.venv/Scripts/python.exe scripts/layer_table.py        # twice, see "Differences from the prompt"
.venv/Scripts/python.exe scripts/train.py --model <m> --seed 42 --lr 1e-3 --resolution 128x96 --max-steps 20 --eval-every 10 --category env --notes "smoke test"
git tag -a infra-v1 -m "..."
git push origin main infra-v1
```

## Key outputs

### Baselines

Equal to cache-v1: mean MAE 25.8500, brightness MAE 1.0806 [0.9323, 1.2297]. 400 rows per model.
The MAE recomputed from the saved rows gives the same two numbers.

### Layer table: 25 of 25 checks PASS

| Model | Params | MACs 128x96 | MACs 256x192 | RF |
| --- | --- | --- | --- | --- |
| Own CNN | 60,465 | 37,158,976 | 148,635,712 | 38 |
| Own CNN depthwise | 8,449 | 6,475,840 | 25,903,168 | 38 |
| ResNet-18 | 11,170,753 | 424,870,400 | 1,699,480,064 | - |
| MobileNetV3-Small | 1,518,593 | 13,496,576 | 50,837,504 | - |

For both own models the hand formulas agree with `sum(p.numel())` and `FlopCounterMode`.

### Weights

| File | Bytes | SHA-256 |
| --- | --- | --- |
| `resnet18-f37072fd.pth` | 46,830,571 | `f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec` |
| `mobilenet_v3_small-047dcff4.pth` | 10,306,551 | `047dcff4addef86ea5bc2eff13c9614dc11f47ab1160d0a71a25e7db994f4e1f` |

### Smoke tests (20 steps, lr 1e-3, seed 42, 128x96, eval at steps 10 and 20)

Train loss is on count / 100, as the mean of steps 1-10 and of steps 11-20.

| Model | Train loss | Val MAE | Peak allocated / reserved | Median step |
| --- | --- | --- | --- | --- |
| own_cnn | 0.115 -> 0.072 | 21.7 -> 18.4 | 200 / 286 MiB | 10.0 ms |
| resnet18 | 1.308 -> 0.424 | 70.6 -> 56.8 | 445 / 494 MiB | 35.8 ms |
| mobilenet_v3_small | 0.357 -> 0.305 | 59.5 -> 50.4 | 235 / 244 MiB | 29.6 ms |

Peak is the PyTorch counter of the run, 12 % of the 4 GB limit at most.

### Energy per step

Every run lasted 1.6 to 2.2 s, under the 15 s limit, so each is `short_run` and "below measurement
resolution" (section 10). Two figures, neither of them a measurement of sustained training:

| Model | Run energy | Mean power | A: energy / 20 | B: power x median step |
| --- | --- | --- | --- | --- |
| own_cnn | 19.3e-6 kWh | 43.3 W | 0.97e-6 kWh | 0.12e-6 kWh |
| resnet18 | 28.7e-6 kWh | 47.2 W | 1.43e-6 kWh | 0.47e-6 kWh |
| mobilenet_v3_small | 23.0e-6 kWh | 40.3 W | 1.15e-6 kWh | 0.33e-6 kWh |

A is too high, because it charges startup to the 20 steps (loading, and a first step of 0.6 to
0.9 s). B uses the mean power of a run that was mostly startup, so sustained GPU load may be higher.

### Estimate for the planned 34,200 steps

Steps by model: own CNN 10,200; own CNN at 256x192 3,000; depthwise 3,000; ResNet-18 7,800;
MobileNetV3-Small 10,200. Two guesses, because these variants were not run: a 256x192 step takes
4 own-CNN steps, and a depthwise step takes 1.

- Time: about 14 min of training steps plus under 1 min of evaluations, so about 15 min.
- Energy: about 0.010 kWh (B) to 0.047 kWh (A), or about 5 to 22 g CO2 at 0.4647 kg/kWh.

The first LR-search trials will replace these figures with real ones.

### Energy of this session

Project total in `runs/index.csv` is now 0.003328 kWh, 1.55 g CO2, up from 0.002647 kWh.

## Findings for review

1. MobileNetV3-Small has 36 % of the MACs of the own CNN but takes about 3 times longer per step,
   close to ResNet-18. MACs are a poor guide to GPU time here.
2. ResNet-18 starts far from the mean target: loss 1.31 means 131 cells, despite the output bias.
   The new linear layer has default weights over large features. This is what section 11.1 says,
   and the loss falls quickly.
3. Val MAE of both pretrained models is still worse than the mean baseline (25.85) after 20 steps.
   Likely reason, not tested: their BatchNorm running statistics still come from ImageNet, and
   MobileNet's momentum is 0.01 (only 18 % replaced after 20 steps, 95 % after 300). Worth keeping
   in mind when reading the 300-step LR search.

## Differences from the prompt and the rules

- Rules files are unchanged (`git diff rules-v2 -- docs configs splits` is empty).
- Paths disagree: the prompt says `results/val_predictions/`, sections 11.8 and `rules.json` say
  `results/baselines/val_predictions.csv`. The same rows were written to both. CNN predictions go to
  `results/val_predictions/<run_id>.csv`.
- `src/carbon.py`: `tracked_run` gained a `notes` argument, and now keeps what a script wrote to
  `metrics.json`. Before, it overwrote that file.
- New files not in the prompt: `src/data.py` (`load_cache` moved here so several scripts share it)
  and `scripts/download_weights.py`.
- Weights are in `checkpoints/hub/checkpoints/`, not the user cache, so they stay inside `Project/`.
- `train.py` also accepts category env, `--eval-every` and `--notes`, needed by the smoke test.
- The cosine schedule always runs over `--max-steps`. So the 600-step noise reference of section
  11.5 will decay over 600 steps. It is compared on energy per step only.
- Section 9 details I chose: the log row is written before a test file opens, so a crash still
  counts as a use. An ablation variant also needs `--force --reason`. Predictions are per split:
  `<model>_<resolution>_<split>_run<k>.csv`.
- `measure.py`: 4 CPU threads is my value, the rules only say "fixed". It needs `--checkpoint` for a
  CNN, and also measures brightness latency on CPU.
- `layer_table.py` ran twice. The second run removed warnings and fixed floats such as 38.0. In
  `model_tables.md` the empty cells of the standard models show "nan", cosmetic only.
- The log name uses number 06, which `2026-11-05_06_rules_v2` already has, as the prompt asked.

## Problems and solutions

`scripts/baselines.py` ran twice, though the prompt says once. A scripted edit to the file failed
to insert the block that writes the predictions, without any error, so the first run
(`20261105-233130`) gave the right metrics and no prediction files. I fixed the block with a checked
edit, committed it, and ran again (`20261105-233219`). Both runs are in the index and their metrics
are identical.

## Left open

- `evaluate_test.py` and `measure.py` are compiled but have never run, as asked.
- Never executed: `--amp`, `own_cnn_ds` in training, 256x192 in training, and `lr_search.py` itself.
- Determinism was not tested: no run has been repeated with the same seed.
- `ai_log/report_notes.txt` and `ai_log/ai_journal_notes.md` do not record this session.
