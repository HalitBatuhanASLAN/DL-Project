# CSE655 Term Project — AI Journal Notes (raw material)
Last update: 2026-11-05
Purpose: collect facts for the final AI Usage Report. Do not paste this file as-is;
the final report must be written in my own voice, AI text marked as quotations.

## Required format (to follow in the final report)
From the CSE655 spec (AI Usage Report, 2-5 pages):
- Tools used: name, version, what each was used for
- Log of key interactions: what I asked, what came back, what I kept / changed / rejected
- At least 3 concrete cases where the AI was wrong, incomplete or misleading, and how I caught/fixed them
- Verification methods (tests, shape checks, hand calculations, docs comparison)
- Short assessment; full chat exports/links attached as appendix
Per-entry template (instructor's format from a previous course, CSE341):
Entry # | Date | Phase | AI tool (+version) | Goal | Prompt (verbatim) | Response (key part) |
Accepted | Rejected/Modified | Errors caught (how detected, what if not caught) | Reflection (2-3 sentences)
Rules: real dates only, no backfilling, never invent AI errors.

## Tools so far
- Claude (claude.ai, project chat, Claude Opus 5.5): spec analysis, dataset selection, planning, setup review
- Claude (claude.ai, separate chat; model not shown in share): dataset selection
- Gemini 3.6 Flash (gemini.google.com): dataset selection
- ChatGPT (chatgpt.com; model not shown, "thinking" mode): dataset selection
- Claude Desktop: local environment setup (CUDA torch, env check script, repo files)

## Chat links (appendix)
- Gemini: https://share.gemini.google/luuknxEZ0bfa (created 2026-11-04 20:51)
- ChatGPT: https://chatgpt.com/share/6aecb395-27c0-83eb-926f-bf6d4b88a8d7 (2026-11-04 ~20:54)
- Claude (separate): https://claude.ai/share/41fdf8fa-e2a5-4a5f-a6b7-985901012a1c (2026-11-04 ~20:50)
- Claude (project chat): export TODO

---

## Entry A — 2026-11-04 — Understanding the spec
- Phase: Planning | Tool: Claude (project chat)
- Goal: understand what the project asks for.
- Prompt (TR): "Ödev dosyasını incele ve ne istendiğini anlat bana"
  (EN: "Review the assignment file and explain what is asked.")
- Response (summary): section-by-section explanation of tasks 3.1-3.5, acceptance rule
  (MAE_own <= 1.15 x MAE_best AND <= 0.6 x MAE_mean), grading, deliverables, exam; advice to
  log CodeCarbon from the first run.
- Accepted: overall structure. Verified against the PDF myself.
- Errors: none found.

## Entry B — 2026-11-04 20:51 — Dataset selection (Gemini 3.6 Flash)
- Phase: Design (dataset) | Tool: Gemini 3.6 Flash
- Prompt (TR, verbatim): "Detaylıca raporu incele sonrasında beni en az yoracak ve her anlamda en
  rahat kolay ve güzel sonucu alacağımız quiz-rapor-implementasyon aşaması vs vs veri seti önerileri ver"
  (EN: "Review the spec in detail, then suggest datasets that will be least tiring and easiest
  across the exam, report and implementation.")
- Response (key part): recommended UTKFace (3,000-image subset); simple 3-4 block CNN + GAP;
  ResNet-18 + MobileNetV3; claimed own CNN with MAE ~6-7 "satisfies the condition without
  hesitation"; listed three example "AI errors" to write in the report; suggested torchinfo
  generates the layer table including receptive field.
- Follow-ups: I pasted Claude's BBBC005 analysis ("buna ne diyorsun") -> Gemini fully agreed;
  then asked for criticism and a final decision -> BBBC005.
- Errors caught:
  1. Self-contradictory arithmetic: said MAE 6-7 passes the 1.15x rule, later computed
     1.15 x 4.5 = 5.17 (so 6-7 fails). Caught by doing the arithmetic.
  2. Suggested ready-made "AI error" examples to put in the report (e.g. "AI forgot stride
     in receptive field"). These never happened -> writing them would be fabrication.
     Rejected; spec requires real cases.
  3. Claimed torchinfo summary produces the layer table; torchinfo gives shapes/params,
     not receptive field. RF must be computed by hand/own code.
  4. Unverified specifics: "cell is ~5x5 px", "UTKFace has 128x128 crops", "100/100".
  5. Sycophancy: switched from "UTKFace is best" to "I'd sign under BBBC005" as soon as
     another AI's answer was pasted, without new evidence.
- Accepted: general CNN shape idea (Conv-BN-ReLU-Pool + GAP), single ablation idea.
- Reflection: TODO (my own words).

## Entry C — 2026-11-04 20:54 — Dataset selection (ChatGPT)
- Phase: Design (dataset) | Tool: ChatGPT (thinking mode; 44 s / 14 s / 19 s; model name not shown)
- Note: answers are not rendered on the share page; extracted from the page source on 2026-11-05.
- Prompt 1 (TR, verbatim): same as Entry B ("Detaylıca raporu incele ... veri seti önerileri ver"), spec PDF attached.
- Response 1 (key part): long plan; grading table correct (10/20/15/25/10/10/10). Candidates only
  UTKFace (1st), PetFinder Pawpularity ("easiest data prep", but "risky"), BIWI head pose.
  Did NOT consider BBBC005 although the spec lists synthetic cell counting. Plan: Custom CNN +
  ResNet-18 + MobileNetV3-Small, 128x128, Huber, AdamW, max 25 epochs, seed 42, Colab first,
  "use the whole dataset if possible", 96 vs 128 ablation. Good points: warned that UTKFace may
  contain the same person in several photos (identity leakage) and that the 3 AI errors must
  NOT be invented.
- Prompt 2: pasted the project-chat BBBC005 analysis + "buna ne diyorsun" ("what do you think").
- Response 2 (key part): moved BBBC005 to 1st; flagged split leakage (keep same well/condition in
  one split); claimed the BBBC005 page has no "CC0" label, only a copyright-waiver sentence, so
  "do not write CC0 in the report"; noted segmentation ground truth exists for 1,200 images only
  (not needed for counting); proposed a feasibility pilot before full training.
- Prompt 3: "Eleştiriler olabilirsin, son karar olarak sence en mantıklısı hangisi"
  ("You can criticize; as a final decision, which is most sensible?")
- Response 3 (switched to English): final = BBBC005; risks: (1) leakage, (2) baseline may be
  stronger than expected — do not assume uniform counts, compute it, (3) synthetic data limits
  claims (no claim about real lab images). Config: "full dataset of 19,200 images", ResNet18 +
  MobileNetV3-Small pretrained, 128x128, error analysis by count/blur/stain.
- Errors / suboptimal:
  1. Initial candidate list missed the one dataset type the spec itself suggests (synthetic cell
     counting) and still listed Pawpularity, whose target is nearly unpredictable from images.
  2. CC0 claim: official BBBC005 page shows "Copyright: CC0" with the waiver text (seen in my
     search on 2026-11-04) -> ChatGPT's "no CC0 label" correction looks wrong. TODO: re-check page
     once more before writing the report; quote the page's own sentence to be safe.
  3. "Use all 19,200 images" sounds like 19,200 independent samples, but they are renderings of far
     fewer unique scenes (blur levels x stains) -> misleading about data diversity; also conflicts
     with the low-CO2 goal and with its own earlier "don't download/train everything first".
  4. Mild sycophancy: switched to BBBC005 right after a pasted answer, but (unlike Gemini) gave
     new reasons and reservations.
- Accepted: feasibility pilot idea; error analysis by count/blur/stain; "synthetic data limits
  claims" for the limitations section; compute real baseline instead of assuming.

## Entry D — 2026-11-04 ~20:50 — Dataset selection (Claude, separate chat)
- Phase: Design (dataset) | Tool: Claude (separate chat)
- Prompt (TR, verbatim): "Bu proje için bana en rahat olacak, en rahat quizde sınavda kendimi
  sunabileceğim, en rahat yapılabilecek şekilde veri seti önerileri ver"
- Response (key part): UTKFace first (64x64/96x96 subset); dSprites and BBBC005 as backups;
  "bias analysis fills the 10-point part"; "verify BBBC005 license yourself"; "download from Kaggle".
- Follow-up 1: pasted the project-chat critique. Claude then:
  - correctly flagged that the pasted text's "I verified it in the previous message" was not
    something it had done (it was from a different chat);
  - checked the official page: BBBC005 is CC0, 19,200 files, 1.8 GB, 696x520;
  - admitted its "bias = 10 points" claim was wrong;
  - raised DATA LEAKAGE: the same simulated plate exists at several blur levels and two stains,
    so a random split puts versions of the same scene into train and test -> must split by
    group (cell count + sample id).
- Follow-up 2 (final decision): BBBC005, with grouped split as the one hard requirement.
- Errors caught: "bias = 10 points" (spec check), unverified license advice.
- Accepted: grouped split requirement (to verify on real file names in Stage 1);
  suggestion of one stain + few blur levels subset.

## Entry E — 2026-11-04 — Dataset comparison (Claude, project chat)
- Phase: Design (dataset) | Tool: Claude (project chat)
- Prompts: asked for easiest datasets with license links; then pasted Entry D's first answer:
  "bu ve benzeri yanıtlar hep ilk sıraya face koydu, tekrardan gözden geçir ve değerlendirme yapalım".
- Response: BBBC005 first (CC0 verified), UTKFace second; Pawpularity rejected (baseline RMSE
  ~20.7 vs good ~16.8 -> 0.6x rule infeasible); criteria table; dSprites pitfalls.
- Errors caught (in this assistant's own answer): did NOT mention the leakage risk between
  blur/stain versions of the same scene, although it recommended selecting blur-level subsets.
  Caught by cross-checking with another AI (Entry D). If missed: optimistic test MAE and a
  likely exam question I could not defend.
- Accepted: BBBC005 decision, 128x128 working resolution idea, 64 vs 128 ablation idea.

## Entry F — 2026-11-04/05 — Environment setup (Claude project chat + Claude Desktop)
- Phase: Implementation (setup) | Tools: Claude (project chat), Claude Desktop
- What happened: project chat gave setup commands (venv, pip install torch ...). On Windows
  this installed the CPU-only torch 2.15.0 (126.7 MB wheel). Project chat detected it from the
  wheel size in my pip log, then wrote an English prompt for Claude Desktop.
- Claude Desktop: found driver supports max CUDA 12.4 while torch 2.15 ships only CUDA 13.x
  builds -> installed torch 2.6.0+cu124; wrote scripts/check_env.py (CodeCarbon smoke test),
  .gitignore, requirements.txt (torch pinned without +cu124 so pip -r works), README setup.
- Verified: torch.cuda.is_available() = True; RTX 3050 Ti Laptop (4 GB); CodeCarbon measured
  GPU via NVML; git status excluded .venv/ and data/.
- Errors / suboptimal: the first generic pip command (no CUDA index URL) was suboptimal for a
  local Windows GPU machine -> caught by checking wheel size / CUDA flag.
- Accepted: all setup files as is.

---
## Candidate "AI was wrong" cases for the report (real, verified)
1. Gemini: MAE 6-7 "passes" the 1.15x rule — contradicted by its own later arithmetic.
2. Gemini: proposed fabricated AI-error examples for the report (integrity risk).
3. Claude (separate chat): "bias analysis = separate 10 points" — wrong per spec.
4. Claude (project chat): missed data leakage across blur/stain versions — caught by Entry D.
5. Gemini/torchinfo: receptive field claim.
6. Setup: generic pip command gave CPU-only torch on Windows.
7. ChatGPT: "no CC0 label on BBBC005 page" (to re-verify) and "use all 19,200 images" (ignores
   that they are renderings of fewer unique scenes).
8. ChatGPT: first answer never considered BBBC005; listed Pawpularity.
Cross-model observation: with the same first prompt, Gemini, ChatGPT and the separate Claude chat
all ranked UTKFace first; only the project chat ranked BBBC005 first. All three later switched to
BBBC005 after seeing that analysis. Two (Claude separate, ChatGPT) independently raised the
leakage issue that the project chat missed.

## TODO
- Export of the project chat (this conversation) for the appendix.
- Reflections in my own words for each entry.
