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
