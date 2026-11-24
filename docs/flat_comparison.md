# Our operational model vs Arm's Flat model

Flat is the operational model of the Armv8 architecture by Pulte, Flur, Deacon, French, Sarkar and
Sewell ("Simplifying ARM Concurrency: Multicopy-atomic Axiomatic and Operational Models for ARMv8",
POPL 2018). The rmem tool implements it. This file compares Flat with our "shared whiteboard" machine
(docs/opmodel.md) on our 13 tests.

## Status: Flat results still to be run by hand
rmem could not be installed on this Mac. Its opam package (rmem 0.1) needs `lwt` 4.5.0 or older, which
only builds on OCaml older than 4.12, and opam does not offer OCaml older than 4.12 on Apple Silicon. So
the "Arm" column below uses herd7's `aarch64.cat`, Arm's axiomatic model. The paper develops Flat
together with Arm's axiomatic model, so we expect Flat to give the same answers on these tests. The hand
runs at the end of this file check that for the five tests where it matters most.

## Results on the 13 tests
A = weak outcome allowed, F = forbidden. Bold = differs from the Arm column. The machine columns equal
the axiomatic candidates with the same flags: `scripts/opmodel.py` found identical final states for all
16 candidates on all 13 tests. Hardware columns: weak outcomes / runs (S25: two runs of 10M combined).

| Test | Machine 0001 (M4 fit) | Machine 1001 (S25 fit) | Arm: aarch64.cat (Flat stand-in) | M4 | S25 |
|---|---|---|---|---|---|
| 2+2W | A | **F** | A | 126 / 50M | 0 / 20M |
| CoRR | F | F | F | 0 / 50M | 0 / 20M |
| CoRW | F | F | F | 0 / 50M | 0 / 20M |
| CoWR | F | F | F | 0 / 50M | 0 / 20M |
| CoWW | F | F | F | 0 / 30M | 0 / 20M |
| IRIW | A | A | A | 31177 / 20M | 88090 / 20M |
| IRIW+addrs | **A** | **A** | F | 0 / 20M | 0 / 20M |
| LB | **F** | **F** | A | 0 / 50M | 0 / 20M |
| LB+datas | F | F | F | 0 / 50M | 0 / 20M |
| MP | A | A | A | 456 / 50M | 6 / 20M |
| S | A | **F** | A | 29 / 50M | 0 / 20M |
| SB | A | A | A | 2255 / 50M | 35 / 20M |
| WRC | A | A | A | 106 / 30M | 2228 / 20M |

Machine 0001 keeps only R->W order. Machine 1001 keeps W->W and R->W.

## Which tests differ, and why
- **LB (both machines forbid, Arm allows).** Our R->W rule makes a store wait until every earlier load
  in its thread is done. Flat has no such rule: a store to a different location may reach memory before
  an earlier load has read, as long as the store does not depend on it. Neither phone nor the M4 ever
  showed LB, which is why the inference picked R->W.
- **LB+datas (all forbid, for different reasons).** Flat forbids it because the store's value is computed
  from the load's value, so the store cannot happen until the load has read. Our machines forbid it only
  because of the R->W rule; they would forbid it even without the data dependency.
- **IRIW+addrs (both machines allow, Arm forbids).** Each reader's second load uses an address computed
  from its first load's value. Flat tracks this, so the second load cannot read before the first. With
  one shared memory, the two readers must then agree on the order of the two writes. Our machines ignore
  dependencies and treat it as plain IRIW, where the loads may go in either order. This is the leftover
  mismatch in every inference so far.
- **2+2W and S (machine 1001 forbids, Arm allows).** 1001 keeps W->W, so a thread's two stores reach
  memory in program order. Flat lets stores to different locations reach memory in either order. The M4
  showed both tests; the S25 showed neither in 20M runs.

## What Flat models that our machine does not
- **Out-of-order and speculative execution.** Flat keeps, per thread, a tree of instruction instances.
  It can fetch and start instructions past a branch before knowing which way the branch goes.
- **Dependencies.** Flat runs the real instruction semantics, including register reads and writes. An
  instruction can only use a value once the instruction producing it has finished, so address, data and
  control dependencies come out naturally. Our machine has no registers in addresses or values: every
  address and stored value is a constant.
- **Restarts and discards.** If a load read too early and an earlier access to the same address later
  shows that value was wrong, Flat restarts that load and the instructions that used its value.
  Instructions on a wrongly predicted branch are thrown away. Our machine never undoes a step.
- **Store forwarding.** Flat lets a load read a value from an earlier store in its own thread before that
  store reaches memory. Our machine makes the load wait (docs/opmodel.md explains why this does not
  affect our tests).
- **Barriers and other instructions.** Flat covers DMB, ISB, acquire/release (LDAR, STLR, LDAPR),
  exclusives and more. Our machine only has plain loads and stores.

## What they share
- **One flat memory.** In both, memory is a single map from locations to values. A store that reaches
  memory is seen by every other thread at the same moment, so both models are multi-copy atomic.
- **Out-of-order access to different locations, in-order access to the same location.** Both let a
  thread's accesses to different locations reach memory out of program order, and both keep a thread's
  accesses to one location in order (coherence). Our 4 flags are a coarse version of Flat's rules about
  when an access may go ahead of earlier ones.

## Running the Flat model by hand (RMEM web interface)
1. Open http://www.cl.cam.ac.uk/users/pes20/rmem (it redirects to
   https://www.cl.cam.ac.uk/~sf502/regressions/rmem/).
2. Click **Model** in the top bar. Under **Storage model**, select **Flat**. Leave every other option as
   it is and close the dialog with **OK**.
3. Click **Load litmus**. In the "Load litmus test" dialog, click **Load from file...** and choose
   `tests/LB.litmus` from this repo. (Or open the file, copy all of it into the box under "or enter a test
   below:", and click **OK**.) If rmem rejects the diyone7 header lines (`Generator=`, `Prefetch=`,
   `Com=`, `Orig=`), paste the test instead and delete those lines first.
4. Click **Search** in the top bar and choose **Search exhaustively**. Confirm the warning about stack
   overflow (these tests are small).
5. Read the result in the console. It lists the final states found. The weak outcome is allowed exactly
   when the state in the test's `exists` line is among them. If it prints an `Observation` line, as herd7
   does, `Sometimes` means allowed and `Never` means forbidden.
6. Repeat steps 3 to 5 for `LB+datas`, `IRIW`, `IRIW+addrs` and `MP`, checking under **Model** that Flat is
   still selected.

| Test | aarch64.cat | Flat (RMEM web) |
|---|---|---|
| LB | A | to do |
| LB+datas | F | to do |
| IRIW | A | to do |
| IRIW+addrs | F | to do |
| MP | A | to do |
