# CS 554 final project: reverse-engineering hardware memory models

## Goal
Infer the memory model of an Apple M4 from black-box litmus testing and compare it with known models.
Questions: (1) Is the M4 in Arm mode as weak as the Arm spec allows? (2) Does its hardware TSO mode match x86-TSO?
Check-in due ~Nov 13. Final due Dec 4.

## Method
- herd7 predicts, for each (model, test), whether the weak outcome is Allowed or Forbidden.
- litmus7 runs the same tests on hardware and records whether the weak outcome was Observed.
- Candidates: 16 models from 4 yes/no flags: is program order preserved for W->W, W->R, R->R, R->W
  pairs (different locations, dependencies ignored)?
- Baselines: SC, TSO, RA, SRA, RLX (our own .cat files) plus herd7's built-in AArch64 model.
- Inference rules:
  - Observed on hardware but Forbidden by a candidate: candidate eliminated (hard evidence).
  - Allowed by a candidate but never observed: not eliminated, counted as a mismatch (soft evidence).
  - Survivors ranked by mismatch count. In Phase 1 (simulated, ground truth known) require zero mismatches.

## Phases
1. Validate on herd7-simulated observations (SC, TSO, RA).
2. Apple M4, Arm mode.
3. Apple M4, TSO mode, inside an Ubuntu ARM64 VM (UTM) with the TSOEnabler kernel module. Later.
Stretch: Samsung S25 Ultra via Termux; LDAR/STLR tests; operational model.

## Layout
tests/               .litmus files
models/baselines/    sc.cat tso.cat ra.cat sra.cat rlx.cat
models/candidates/   16 generated .cat files
scripts/             Python, standard library only
results/             CSVs and raw logs
notes.md             lab notebook

## Rules
- Graded coursework: I must understand and defend everything. After writing a .cat file or script,
  explain it in plain language (line by line for .cat files). Prefer simple, readable code.
- If a result disagrees with my expectation, do NOT edit models or tests to force a match.
  Explain which side is wrong and why, then ask me.
- Append every step to notes.md: date, commands, results, problems hit.
- Commit after each working step with a clear message.
- Never change macOS security settings, disable SIP, or install kernel extensions on macOS.
- Ask before installing anything not via Homebrew, opam, or pip.
- opam tools need `eval $(opam env)` in each shell first.
- Repo: github.com/VaishJadhavVJ/memory-model-inference (private). Push after every commit.