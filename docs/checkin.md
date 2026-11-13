# Vaishnavi Jadhav (vjadh4@uic.edu), CS 554 project check-in, November 12, 2026

## 1. Goal

I want to infer the memory model of an Apple M4 by running litmus tests on it as a black box and
comparing the results with known models. The two questions are whether the M4 in Arm mode is as weak
as the Arm spec allows, and whether its hardware TSO mode matches x86-TSO.

## 2. Progress

**Test suite.** I have 13 AArch64 litmus tests. Nine are classic shapes generated with diyone7 (SB,
MP, LB, 2+2W, S, WRC, IRIW, LB+datas, IRIW+addrs). Four are coherence tests (CoRR, CoWR, CoRW, CoWW).
To check the suite, I wrote none.cat, a model with no axioms. Every test is allowed under it. So every
weak outcome is reachable, and each "forbidden" verdict comes from a model's rules, not a broken test.

**Models.** I wrote 6 baseline models as herd7 .cat files: none, RLX (coherence only), RA, SRA, TSO
and SC. herd7's built-in aarch64 model is the Arm reference. A script generates 16 candidate models
from 4 yes/no flags: is program order kept for W->W, W->R, R->R and R->W pairs? In names like
WW1_WR0_RR1_RW1, 1 means the order is kept. The all-1 candidate matches my SC model and WW1_WR0_RR1_RW1
matches my TSO model on all 13 tests.

**Inference rules.** herd7 says whether each candidate allows (A) or forbids (F) each weak outcome.
litmus7 says whether the hardware showed it.
- Observed but forbidden by a candidate: the candidate is eliminated (hard evidence).
- Allowed but never observed: counted as a mismatch (soft evidence).
- Surviving candidates are ranked by mismatch count.

**Phase 1: simulated data.** I used a known model as the "hardware": a test counts as observed
exactly when that model allows it.

| Truth | Survivors | Best candidate | Mismatches |
|---|---|---|---|
| SC | 16 | WW1_WR1_RR1_RW1 | 0 |
| TSO | 8 | WW1_WR0_RR1_RW1 | 0 |
| aarch64 | 1 | WW0_WR0_RR0_RW0 | 2: IRIW+addrs, LB+datas |
| RA | 2 | WW0_WR0_RR0_RW1 | 3: MP, S, WRC |
| SRA | 4 | WW1_WR0_RR0_RW1 | 2: MP, WRC |

SC and TSO are recovered exactly. The other three lie outside the candidate space, and their leftover
mismatches show what it cannot express: dependencies (aarch64) and causality without one global write
order (RA, SRA).

**Phase 2: first run on the M4 in Arm mode.** I ran natively on macOS with litmus7, 20M to 50M runs
per test. For every test, litmus7's hash matched herd7's, so the hardware ran the tests herd7 analysed.

| Test | aarch64 | Seen on M4 | Weak / total |
|---|---|---|---|
| SB | A | yes | 2255 / 50M |
| MP | A | yes | 456 / 50M |
| 2+2W | A | yes | 126 / 50M |
| S | A | yes | 29 / 50M |
| WRC | A | yes | 106 / 30M |
| IRIW | A | yes | 31177 / 20M |
| LB | A | **no** | 0 / 50M |
| LB+datas, IRIW+addrs, CoRR, CoRW, CoWR, CoWW | F | no | 0 in each (20M to 50M runs) |

Nothing the M4 showed is forbidden by the Arm model. The one gap is LB: Arm allows it, but it never
appeared in 50M runs.

**Inference result.** 2 of 16 candidates survive. The best fit is WW0_WR0_RR0_RW1, which keeps only
R->W order. Its one mismatch, IRIW+addrs, is a dependency effect. The fully relaxed candidate comes
second with 3 mismatches. This matches the prediction in my proposal (Oct 23) that the M4 in Arm mode
keeps R->W order, based on Y. Khayet and A. Morrison, "Arm Weak Memory Consistency on Apple Silicon:
What Is It Good For?", ASPLOS 2026. For now this is soft evidence: 0 in 50M could also mean the
outcome is allowed but rare.

## 3. Problems and how I handled them

- diyone7 wrote wrong final conditions for some one-location tests, so CoRW and CoWW came out allowed
  even under SC. I kept diy's code, fixed only the final condition of CoWR, CoRW and CoWW, and kept
  diy's original condition in a header line of each file.
- herd7 reports success even when a model fails to load. My scripts stop with an error when herd7's
  result line is missing. herd7 also loads its own sc.cat and tso.cat unless given a full path, so the
  scripts always pass full paths.
- The macOS compiler setup failed twice: the Xcode license was never accepted, and the linker could
  not read the newest SDK. I used the Command Line Tools and the matching SDK through two shell
  variables. I did not change any system settings.
- macOS cannot pin threads to cores, so test threads may run on performance or efficiency cores. I
  recorded this as a limitation of the native runs.
- Phase 1 showed that some models lie outside the candidate space, so zero mismatches is not always
  possible. I now require zero mismatches only for SC and TSO and read leftover mismatches as findings.

## 4. Next steps

- LB stress test: run LB for many more iterations and with other litmus7 settings, to strengthen or
  overturn the R->W result.
- TSO mode: run the suite on the M4 in TSO mode inside an Ubuntu ARM64 VM (UTM) with the TSOEnabler
  kernel module, and compare with x86-TSO.
- Android: run the suite on a Samsung S25 Ultra through Termux (stretch goal).
- Final writeup, due December 4.

## 5. Key files

- `tests/`: the 13 litmus tests.
- `models/baselines/`: the 6 baseline models.
- `models/candidates/`: the 16 generated candidate models.
- `scripts/`: Python scripts (standard library only) for predictions, inference, checks and log parsing.
- `results/`: herd7 predictions, Phase 1 results, raw M4 logs and the M4 inference output.
- `docs/`: the proposal and this check-in.

## 6. Questions for you

1. Scope. Is Phase 3 (TSO mode) plus the current results enough for the final, or should I go
   deeper? I am considering two extensions and would value your view on which is more useful:
   (a) an operational model of the inferred M4 model, written as a small OCaml program that
   enumerates all executions of each litmus test, checked against herd7's axiomatic predictions
   on all 13 tests, plus a paper proof that SB, 2+2W, LB and IRIW each pin down exactly one
   ordering flag; or
   (b) repeating the hardware runs on a non-Apple Arm core (Samsung S25 Ultra, Qualcomm Oryon).
2. Evidence from absence. LB was never observed in 50M runs. Is it reasonable to report this
   with a statistical bound (0 in N runs gives a 95% upper bound of about 3/N on the per-run
   rate), or would you treat it differently?

## 7. AI use

I used Claude for planning and Claude Code for setup and scripts.
