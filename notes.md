# Lab notebook

## 2026-10-31 — Project setup, herdtools7 install, first herd7 run

**Layout.** Created `tests/`, `models/baselines/`, `models/candidates/`, `scripts/`, `results/`
(empty ones hold a `.gitkeep` so git tracks them). `git init`, `.gitignore` for `__pycache__/`, `*.py[cod]`.

**Install** (machine: Apple M4, arm64, macOS, Homebrew 7.0.6):
```
brew install opam                 # opam 2.6.1
opam init -y --no-setup           # default switch; --no-setup = default "No" to editing ~/.zshrc
eval $(opam env)                  # needed in every new shell
opam install -y herdtools7        # herdtools7 7.58
herd7 -version; litmus7 -version; diyone7 -version   # all print 7.58
```
- Problem/quirk: `opam init` built OCaml 5.5.2, then `opam install herdtools7` downgraded the switch
  to OCaml 5.4.1 because herdtools7 7.58 does not yet support 5.5. Not an error; install succeeded.
- No shell profile was modified, so `eval $(opam env)` is required before using herd7 etc.

**First test.** `tests/SB.litmus` (store buffering: each thread writes its own location, then reads the other's).
```
herd7 tests/SB.litmus            # default AArch64 model = aarch64.cat
```
Result: 4 final states, condition `0:X2=0 /\ 1:X2=0` reachable →
`Observation SB Sometimes 1 3` (1 execution satisfies it, 3 don't). Arm allows the weak SB outcome.
Same result with explicit `-model aarch64.cat` (same Hash `dca0cdb9…`).

Contrast (herd's built-in `sc.cat`, not our own baseline yet): `herd7 -model sc.cat tests/SB.litmus` →
3 states, `Observation SB Never 0 3`. SC forbids both reads returning 0, as expected.

Note to self: the first output line `Test SB Allowed` only says the test uses `exists`
(it asks "is this allowed?"); it is NOT the verdict. The verdict is `Ok`/`No` and the Observation line.

## 2026-10-31 — GitHub repo

- `gh auth status`: logged in as VaishJadhavVJ (scopes include `repo`).
- Checked what litmus7 generates (`litmus7 -o <dir> tests/SB.litmus`, then `make`): C sources,
  Makefile, run.sh, plus `*.exe`, `*.o`, `*.t` after compiling. Convention: litmus7 output goes in
  `build/`, which is gitignored along with `*.exe`, `*.o`, `*.t`, `.DS_Store`, Python caches.
  Verified with `git check-ignore` that .litmus, .cat, .py, .csv, logs and notes.md stay tracked.
- Added README.md.
- `gh repo create memory-model-inference --private --source=. --push`
  → https://github.com/VaishJadhavVJ/memory-model-inference (private)

## 2026-10-31 — Baseline models, diy-generated tests, herd7 runner

**Models** in `models/baselines/` (all `include "cos.cat"` to enumerate coherence orders `co` and derive `fr`):
- `sc.cat`: `acyclic po | rf | co | fr`
- `tso.cat`: uniproc `acyclic po-loc | rf | co | fr`; global `acyclic ppo | rfe | co | fr`, ppo = po minus W->R
- `rlx.cat`: `acyclic po-loc | rf | co | fr` only
- `ra.cat`: hb = `(po | rf)+`; `acyclic hb`; `irreflexive hb ; (rf | co | fr)+`
- `sra.cat`: ra.cat's axioms + `acyclic po | rf | co`

**Tests** (replaces the hand-written SB; diyone7's SB is the same test with registers renamed):
```
cd tests && diyone7 -arch AArch64 -name SB PodWR Fre PodWR Fre    # etc. for MP LB 2+2W S WRC IRIW LB+datas IRIW+addrs
```
**Runner:** `python3 scripts/run_baselines.py` → `results/baselines.csv` (test, model, observation, positive, negative, verdict).

**Result:** all 54 cells (9 tests x 6 models) match the expected table. 0 disagreements.
```
Test        RLX  RA   SRA  TSO  SC   Arm
2+2W        A    A    F    F    F    A
IRIW        A    A    A    F    F    A
IRIW+addrs  A    A    A    F    F    F
LB          A    F    F    F    F    A
LB+datas    A    F    F    F    F    F
MP          A    F    F    F    F    A
S           A    F    F    F    F    A
SB          A    A    A    A    F    A
WRC         A    F    F    F    F    A
```
Cross-check: our sc.cat and rlx.cat give the same Observation as herd's built-in sc.cat and uniproc.cat on all 9 tests.

**Problems hit:**
- `diyone7 -name X` writes `X.litmus` into the current directory (prints nothing), so run it inside `tests/`.
- `include "ra.cat"` in sra.cat failed: herd7 looks for includes in the cwd and its own lib dir, not next to
  the model file. Fixed by copying RA's 3 lines into sra.cat so each model file stands alone.
- herd7 exits 0 even when a model fails to load (it just prints the error, no Observation line).
  The runner therefore stops with an error if the Observation line is missing.
- Our sc.cat/tso.cat share names with herd's built-ins; `herd7 -model sc.cat` from the project root loads
  herd's. Always pass the path (`models/baselines/sc.cat`).

**Limitation to fix later:** no test here touches a single location only, so rlx.cat's coherence axiom never
forbids anything in this suite (RLX = A everywhere). Add coherence tests (CoRR, CoWR, ...) to exercise it.

## 2026-10-31 — Coherence tests (CoRR, CoWR, CoRW, CoWW): diyone7 problem

Goal: add single-location tests so rlx.cat's coherence axiom is actually exercised; expect F under every model.

- `diyone7` refuses one-location cycles ("Unique location") unless given `-oneloc`.
  Single-thread cycles (`PosWR Fri`, `PosRW Rfi`, `PosWW Coi`) fail with `CannotNormalise("find_start")`:
  diy needs at least one external edge. `PosWW Coe Coe` also needs `-obs accept` (adds an observer thread).
- Cycles tried: CoRR `Rfe PosRR Fre`, CoWR `PosWR Fre Coe`, CoRW `Rfe PosRW Coe`, CoWW `PosWW Coe Coe`.
- **Problem:** with `-oneloc`, diy writes a wrong final condition whenever the cycle has a co edge. Write values
  are assigned correctly along co, but the condition lists writes in cycle order instead of co order
  (with one location the cycle wraps around, so the two differ). herd7 results (scratchpad copies):

  | test | condition | RLX RA SRA TSO SC Arm |
  |---|---|---|
  | CoRR (diy) | `1:X1=1 /\ 1:X2=0` | all Never |
  | CoWR (diy) | `[x]=1 /\ 0:X2=0` | all Never (reading 0 after own write is forbidden anyway; `[x]=1` does not match the cycle) |
  | CoWR (fixed) | `[x]=2 /\ 0:X2=0` | all Never |
  | CoRW (diy) | `[x]=1 /\ 1:X1=2` | all **Sometimes**: plain SC run (P0 x=2; P1 reads 2; P1 x=1) |
  | CoRW (fixed) | `[x]=2 /\ 1:X1=2` | all Never |
  | CoWW (diy) | `0:X0=3 /\ 0:X2=1 /\ 0:X3=2` | all **Sometimes**: observer sees P1's own order 3,1,2 |
  | CoWW (fixed) | `0:X0=1 /\ 0:X2=2 /\ 0:X3=3` | all Never |

  Verdict: the models are right; diy's CoRW/CoWW conditions are wrong. `-obs accept|force`,
  `-cond observe|unicond`, `-optcoherence` all keep the wrong order. The opam package ships no Co* tests.
- Nothing added to `tests/` yet (CLAUDE.md: explain and ask before editing tests).

## 2026-11-01 — Coherence tests added

Decision (mine): keep diy's code, rewrite only the `exists` line of CoWR/CoRW/CoWW to follow the cycle's co order.
```
cd tests
diyone7 -arch AArch64 -oneloc -name CoRR Rfe PosRR Fre
diyone7 -arch AArch64 -oneloc -name CoWR PosWR Fre Coe
diyone7 -arch AArch64 -oneloc -name CoRW Rfe PosRW Coe
diyone7 -arch AArch64 -oneloc -obs accept -name CoWW PosWW Coe Coe
```
Then edited by hand (CoRR untouched). Each edited file has a `Fix=` header line with diy's original condition:
- CoWR: `[x]=1 /\ 0:X2=0` → `[x]=2 /\ 0:X2=0`
- CoRW: `[x]=1 /\ 1:X1=2` → `[x]=2 /\ 1:X1=2`
- CoWW: `0:X0=3 /\ 0:X2=1 /\ 0:X3=2` → `0:X0=1 /\ 0:X2=2 /\ 0:X3=3`

Checked herd7 and litmus7 both parse the files with the extra `Fix=` line.

`python3 scripts/run_baselines.py`: all 24 new cells (4 tests x 6 models) are F, as expected.
The 9 earlier tests' rows in results/baselines.csv are unchanged. RLX's coherence axiom is now exercised.

Quirk: results/baselines.csv has `\r\n` line endings (Python csv default), so shell tools see `F\r`;
strip with `tr -d '\r'` before awk/grep on the last column.

## 2026-11-08 — none.cat sanity baseline, LF line endings in CSV

- `run_baselines.py`: CSV now written with `lineterminator="\n"` (was `\r\n`). Checked: 0 `\r` in the file.
- Added `models/baselines/none.cat`: only `include "cos.cat"`, no axioms. herd7 still enumerates every rf and
  every co per location, then accepts all of them. Added as first column "None".
- Checked that `cos.cat` → `cos-no-opt.cat` → `cross.cat` contain only definitions, no checks.
  herd7's `-optace` (default `iico`) could in principle prune candidates early; `-optace false` gives identical
  counts on CoRR/CoWR/CoRW/CoWW (1 3, 1 5, 1 5, 6 378), so nothing is pruned before the model.
- Result: all 13 tests are A under none.cat. In particular CoWR, CoRW, CoWW (edited conditions) are reachable,
  so their F under every other model comes from the models' coherence axioms, not from an impossible condition.
  All earlier cells unchanged.
```
Test        None RLX  RA   SRA  TSO  SC   Arm
2+2W        A    A    A    F    F    F    A
CoRR        A    F    F    F    F    F    F
CoRW        A    F    F    F    F    F    F
CoWR        A    F    F    F    F    F    F
CoWW        A    F    F    F    F    F    F
IRIW        A    A    A    A    F    F    A
IRIW+addrs  A    A    A    A    F    F    F
LB          A    A    F    F    F    F    A
LB+datas    A    A    F    F    F    F    F
MP          A    A    F    F    F    F    A
S           A    A    F    F    F    F    A
SB          A    A    A    A    A    F    A
WRC         A    A    F    F    F    F    A
```

## 2026-11-08 — 16 candidate models, predictions table, expectation checks

**Generator:** `python3 scripts/gen_candidates.py` writes `models/candidates/cand_WW?_WR?_RR?_RW?.cat` (16 files).
Same shape as tso.cat (uniproc axiom + `acyclic ppo | rfe | co | fr as global`); only `let ppo = ...` changes:
the union of `(po & (A * B))` for each preserved pair, or `0` (cat's empty relation) if none is preserved.

**Sanity checks (step 2), full Observation line incl. execution counts, all 13 tests:**
- `sc.cat` vs `cand_WW1_WR1_RR1_RW1`: 13/13 identical. PASS
- `tso.cat` vs `cand_WW1_WR0_RR1_RW1`: 13/13 identical (its ppo line is word-for-word tso.cat's). PASS

**Predictions:** `python3 scripts/predict.py` → `results/predictions.csv` (23 models x 13 tests, A/F).
Reuses `observe()`, `VERDICT` and the baseline list `MODELS` from run_baselines.py. ~2 s.
```
model                2+2W CoRR CoRW CoWR CoWW IRIW IRIW+addrs LB LB+datas MP S SB WRC
none                 A    A    A    A    A    A    A          A  A        A  A A  A
rlx                  A    F    F    F    F    A    A          A  A        A  A A  A
ra                   A    F    F    F    F    A    A          F  F        F  F A  F
sra                  F    F    F    F    F    A    A          F  F        F  F A  F
tso                  F    F    F    F    F    F    F          F  F        F  F A  F
sc                   F    F    F    F    F    F    F          F  F        F  F F  F
aarch64              A    F    F    F    F    A    F          A  F        A  A A  A
cand_WW0_WR0_RR0_RW0 A    F    F    F    F    A    A          A  A        A  A A  A
cand_WW0_WR0_RR0_RW1 A    F    F    F    F    A    A          F  F        A  A A  A
cand_WW0_WR0_RR1_RW0 A    F    F    F    F    F    F          A  A        A  A A  A
cand_WW0_WR0_RR1_RW1 A    F    F    F    F    F    F          F  F        A  A A  F
cand_WW0_WR1_RR0_RW0 A    F    F    F    F    A    A          A  A        A  A F  A
cand_WW0_WR1_RR0_RW1 A    F    F    F    F    A    A          F  F        A  A F  A
cand_WW0_WR1_RR1_RW0 A    F    F    F    F    F    F          A  A        A  A F  A
cand_WW0_WR1_RR1_RW1 A    F    F    F    F    F    F          F  F        A  A F  F
cand_WW1_WR0_RR0_RW0 F    F    F    F    F    A    A          A  A        A  A A  A
cand_WW1_WR0_RR0_RW1 F    F    F    F    F    A    A          F  F        A  F A  A
cand_WW1_WR0_RR1_RW0 F    F    F    F    F    F    F          A  A        F  A A  A
cand_WW1_WR0_RR1_RW1 F    F    F    F    F    F    F          F  F        F  F A  F
cand_WW1_WR1_RR0_RW0 F    F    F    F    F    A    A          A  A        A  A F  A
cand_WW1_WR1_RR0_RW1 F    F    F    F    F    A    A          F  F        A  F F  A
cand_WW1_WR1_RR1_RW0 F    F    F    F    F    F    F          A  A        F  A F  A
cand_WW1_WR1_RR1_RW1 F    F    F    F    F    F    F          F  F        F  F F  F
```
**Expectation checks (step 4):** `python3 scripts/check_predictions.py` (reads the CSV, exit 1 on any FAIL).
All PASS: 16 candidates; SC/TSO matches; coherence tests F for every candidate; no ties; SB/2+2W/LB/IRIW are F
exactly when W->R/W->W/R->W/R->R is preserved; LB+datas = LB and IRIW+addrs = IRIW for every candidate.
Checked the checker: flipping one SB cell in a temp copy of the CSV gives FAIL on the pin and tie checks, exit 1.

**Observations:**
- `cand_WW0_WR0_RR0_RW0` = `rlx` on every test. Expected in general: with ppo = 0 the global axiom is
  `acyclic rfe | co | fr`, and any such cycle is already a uniproc cycle, so the candidate is just coherence.
- The two-pair tests come out as conjunctions: MP F iff W->W and R->R; S iff W->W and R->W; WRC iff R->R and R->W.
- aarch64 differs from cand_0000/rlx only on LB+datas and IRIW+addrs (dependencies), which no candidate can express.

## 2026-11-08 — Inference script and Phase 1 validation

- `scripts/infer.py OBS.csv` (OBS has columns `test, observed` = yes/no; predictions from results/predictions.csv).
  Per candidate: contradictions = observed but F (eliminated), mismatches = A but not observed (listed by name).
  Writes `OBS_inference.csv` next to the input (all 16, sorted by contradictions then mismatches, so survivors
  come first) and prints the survivors. Rejects observed values other than yes/no and unknown test names.
- `scripts/phase1.py`: for truth in sc, tso, aarch64, ra, sra, writes `results/phase1/<truth>.csv` with
  observed = yes exactly where herd7 says the truth allows the test (A), then runs infer.py on it.
- `scripts/check_predictions.py`: added one check per truth (unique best survivor + its mismatched tests).
  All 15 checks PASS. Checked a wrong expectation gives FAIL, and a bad `observed` value is rejected.

### Phase 1 summary (for check-in)

Simulated observations: a test is "observed" exactly when the ground-truth model allows it.

| Truth | Survivors | Best candidate (unique) | Mismatches |
|---|---|---|---|
| sc | 16 | WW1_WR1_RR1_RW1 | 0 |
| tso | 8 | WW1_WR0_RR1_RW1 | 0 |
| aarch64 | 1 | WW0_WR0_RR0_RW0 | 2: IRIW+addrs, LB+datas |
| ra | 2 | WW0_WR0_RR0_RW1 | 3: MP, S, WRC |
| sra | 4 | WW1_WR0_RR0_RW1 | 2: MP, WRC |

All five rows match the expected table.

**SC and TSO are recovered exactly.** Both lie inside the candidate space; inference picks the right candidate
uniquely with 0 mismatches, and the runner-up is at least 1 mismatch behind (for SC, the TSO candidate, off by SB).
So the 13 tests and the inference rules separate the models we can express.

**aarch64, RA and SRA lie outside the candidate space.** Their leftover mismatches are not a search failure: each
one is forced, because an observed test switches off the flag that would forbid it. What they point to:

- **aarch64 → dependencies.** Arm allows every plain shape (SB, MP, LB, 2+2W, S, WRC, IRIW), so only the fully
  relaxed candidate survives. Arm still forbids LB+datas and IRIW+addrs: a data dependency orders R->W and an
  address dependency orders R->R. Candidates ignore dependencies, so none can forbid LB+datas while allowing LB.
  Fix: add dependency-aware flags (e.g. "R->W preserved when data-dependent", "R->R when address-dependent").
- **RA → causality without a single global order.** RA forbids MP, S, WRC (once you read a value, you also see
  everything that happened before its write: hb = (po | rf)+), but allows IRIW, 2+2W and SB. In our space MP needs
  W->W and R->R, S needs W->W and R->W, WRC needs R->R and R->W. Observing 2+2W forces W->W off and observing IRIW
  forces R->R off, so MP, S and WRC must stay allowed. The root cause: our candidates put co and fr in one global
  order (multi-copy atomic), so preserving R->R forbids both MP and IRIW. RA is not multi-copy atomic: two readers
  can disagree on the order of independent writes, yet causal chains through rf are still respected.
- **SRA → same as RA, minus S.** SRA also orders writes consistently with hb (`acyclic po | rf | co`), which
  forbids 2+2W and S; W->W + R->W captures that, so S is no longer a mismatch. MP and WRC remain, for the same
  reason as RA: SRA still allows IRIW, which forces R->R off.

**For Phase 2:** zero mismatches can only be expected if the hardware lies inside the space. Leftover mismatches on
the dependency tests would point to dependency ordering (expected for an Arm core); MP/WRC-style mismatches
alongside an observed IRIW would point to a non-multi-copy-atomic, causality-based model. On hardware, "not
observed" may also mean "allowed but rare", so mismatches stay soft evidence and need enough litmus7 iterations.

## 2026-11-08 — Phase 1 rule in CLAUDE.md

Changed the Phase 1 inference rule in CLAUDE.md: zero mismatches is required only for truths inside the
candidate space (SC, TSO). For truths outside it (aarch64, RA, SRA), the leftover mismatches show what the
candidate space cannot express. This matches the Phase 1 results above; no code or results changed.
Follow-up: the rule now starts with "In Phase 1," so it is scoped to Phase 1, and the Phases list names all five
simulated truths (SC, TSO, RA, SRA, aarch64).

## 2026-11-11 — Phase 2: first hardware run, Apple M4 in Arm mode (native macOS)

Step 0 (my predictions table for the M4) skipped at my request; it does not exist yet, so the comparison
with my own predictions is still to do.

**Toolchain problems (fixed with two shell variables only, no system settings changed):**
- `gcc` is Xcode.app's clang, whose license was never accepted ("You have not agreed to the Xcode license
  agreements"). Accepting it needs `sudo xcodebuild -license`; left alone. Used the separate Command Line
  Tools instead: `export DEVELOPER_DIR=/Library/Developer/CommandLineTools`.
- Linking then failed: `ld: tapi error: malformed file ... MacOSX27.0.sdk/usr/lib/libSystem.B.tbd: unknown
  architecture arm64e.x1-macos`. clang picked the newest SDK (27.0), which is newer than the CLT 26.6
  linker understands. Fixed with the SDK matching the tools and macOS 26.6:
  `export SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk`.

**litmus7 options** (litmus7 7.58):
- `-mach M1`: litmus7's bundled MacBook M1 config (`$(litmus7 -libdir)/M1.cfg`): `os = Mac` (target macOS),
  `affinity = none` (macOS has no call to pin a thread to a core), `memory = direct` (threads access the test
  locations directly, not through pointers), `stride = 1` (threads walk the array of test instances one
  slot at a time). Its size/run/avail values are overridden by the options below.
- `-a 10`: the M4 has 10 cores (4 P + 6 E). litmus7 runs floor(10 / threads) copies of a test at once:
  5 for 2-thread tests, 3 for 3-thread tests (CoWW, WRC), 2 for 4-thread tests (IRIW, IRIW+addrs).
- `-s 100k -r 10`: litmus7's own defaults (100,000 iterations per run, 10 runs), compiled in. Executions
  per test = s x r x copies.
- `-o build/m4_arm`: write C files, Makefile and run.sh there instead of running immediately (build/ is
  gitignored). run.sh passes its arguments to every test binary.
- **No thread pinning: the OS scheduler decides, so test threads may land on P or E cores, and this can change
  between runs.**

**Commands:**
```
eval $(opam env)
export DEVELOPER_DIR=/Library/Developer/CommandLineTools
export SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk
litmus7 -mach M1 -a 10 -s 100k -r 10 -o build/m4_arm tests/*.litmus
cd build/m4_arm && make -j 8
sh run.sh > ../../results/hw/m4_arm/small.log          # small run: 2M-5M executions per test, 3.8 s
sh run.sh -r 100 > ../../results/hw/m4_arm/run.log     # real run: 20M-50M executions per test, 16 s
cd ../..
python3 scripts/hw_obs.py results/hw/m4_arm/run.log results/obs_m4_arm.csv
python3 scripts/infer.py results/obs_m4_arm.csv
```

**New script `scripts/hw_obs.py LOG OUT.csv`:** reads each test's `Hash=` and `Observation` lines from a
litmus7 log, runs herd7 on the same tests/ file and compares hashes (stops, writing nothing, if one differs
or a test is missing), and writes `test, observed, weak, total`. Checked by editing one hash in a copy of
the log: it reports "DIFFERS", exits 1 and writes no CSV.

**Hash check:** all 13 litmus7 hashes equal herd7's, so the hardware ran exactly the tests herd7 analysed.

**Results (real run) vs herd7 aarch64:**

| Test | aarch64 | M4 observed | weak / total |
|---|---|---|---|
| 2+2W | A | yes | 126 / 50M |
| CoRR | F | no | 0 / 50M |
| CoRW | F | no | 0 / 50M |
| CoWR | F | no | 0 / 50M |
| CoWW | F | no | 0 / 30M |
| IRIW | A | yes | 31177 / 20M |
| IRIW+addrs | F | no | 0 / 20M |
| LB | A | **no** | 0 / 50M |
| LB+datas | F | no | 0 / 50M |
| MP | A | yes | 456 / 50M |
| S | A | yes | 29 / 50M |
| SB | A | yes | 2255 / 50M |
| WRC | A | yes | 106 / 30M |

The small run gave the same yes/no on all 13 tests (LB also 0 there).

**Nothing observed that aarch64 forbids** (no contradiction with the Arm model). The only difference: LB is
allowed by aarch64 but was never observed in 50M runs.

**Inference** (`results/obs_m4_arm_inference.csv`): 2 of 16 candidates survive.
- `cand_WW0_WR0_RR0_RW1` (only R->W preserved): 0 contradictions, 1 mismatch (IRIW+addrs).
- `cand_WW0_WR0_RR0_RW0` (fully relaxed): 0 contradictions, 3 mismatches (IRIW+addrs, LB, LB+datas).
Every other candidate is eliminated by an observed test (SB kills W->R, 2+2W kills W->W, IRIW kills R->R).

**Reading:**
- The M4 shows every weak behaviour aarch64 allows on these tests except LB. Best fit: "Arm without
  load->store reordering", i.e. a later store never becomes visible before an earlier load has read.
  This is soft evidence: 0 in 50M could also mean "allowed but very rare".
- The leftover IRIW+addrs mismatch is the dependency effect seen in Phase 1 for aarch64: with an address
  dependency between the two reads, IRIW disappears. Plain IRIW shows up only because the readers' loads are
  reordered, which is consistent with Arm's multi-copy atomicity.
- Preliminary answer to question (1): on these 13 tests the M4 is not as weak as the Arm spec allows (no LB).

**Next:** fill in my predictions table and compare; run LB with many more iterations and other `-a`/stride
settings to strengthen (or overturn) the LB result.
