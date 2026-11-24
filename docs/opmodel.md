# Operational model of the inferred M4 model (candidate 0001)

Our candidates are axiomatic: they accept or reject a whole execution at once. This file describes the
same models as a machine that runs a test one step at a time. Picture a shared whiteboard. Every thread
writes on it and reads from it, and every thread keeps a to-do list of its unfinished instructions.

## State
- Memory: one shared whiteboard holding the current value of every location (all start at 0). When a
  thread writes, every other thread sees the new value at the same moment. So the model is multi-copy
  atomic: there is never a moment when one thread sees a write and another does not.
- Each thread: its registers (all start at 0) and its to-do list, the unfinished instructions in
  program order. At the start the to-do list is the whole program.

## Parameters
The same 4 yes/no flags as the 16 candidates (`cand_WW?_WR?_RR?_RW?`). Each flag says whether an
instruction must stay behind an earlier unfinished instruction of a given kind, at a different location:
- W->W: a store stays behind an earlier unfinished store.
- W->R: a load stays behind an earlier unfinished store.
- R->R: a load stays behind an earlier unfinished load.
- R->W: a store stays behind an earlier unfinished load.

"Candidate 0001" is `cand_WW0_WR0_RR0_RW1`: only R->W is kept. It is the M4's best fit.

## Steps
At each step, pick any thread and any instruction on its to-do list that is allowed to go now, perform
it, and cross it off. Repeat until every to-do list is empty.

1. Load rule: a thread may perform any unfinished load, reading the location's current value from the
   whiteboard into the register, unless an earlier unfinished instruction in the same thread
   - touches the same location, or
   - is a load and R->R is set, or a store and W->R is set.
2. Store rule: a thread may perform any unfinished store, writing its value on the whiteboard, unless an
   earlier unfinished instruction in the same thread
   - touches the same location, or
   - is a store and W->W is set, or a load and R->W is set.

The same-location condition is what keeps every candidate coherent (the `uniproc` axiom): a thread's
accesses to one location always happen in program order.

No store forwarding: a real CPU can let a thread read its own store before other threads see it, but
here such a load waits until the store is on the whiteboard. This changes nothing for our 13 tests,
because the only thread that reads a location it wrote itself is P0 of CoWR, and that test uses a single
location.

## Final outcome
When every to-do list is empty, write down the final values of the registers and locations named in the
test's condition. Doing this for every possible order of steps gives the set of final states the model
allows. The weak outcome is allowed exactly when it is in that set.

`scripts/opmodel.py` explores every order for all 16 flag settings on all 13 tests. For every pair, the
set of final states is identical to the one herd7 lists for the matching candidate .cat file (208 of 208
pairs, `results/opmodel_check.csv`).

Two limits, neither of which shows up in our tests:
- Dependencies are ignored, as in the candidates, so LB+datas behaves like LB and IRIW+addrs like IRIW.
- The machine puts all accesses, including same-location pairs and reads of a thread's own stores, into
  one order. The candidates check same-location order (`uniproc`) and the cross-thread order (`global`)
  separately, so they can be weaker on tests that mix a thread's repeated accesses to one location with
  other locations. None of our 13 tests does.

## Hand simulations
All four use candidate 0001: only R->W is kept.

### SB (expected: allowed)
Program: P0 does `x = 1` then `X3 = y`. P1 does `y = 1` then `X3 = x`.
Weak outcome: `0:X3=0 /\ 1:X3=0`.

| Step | Thread | Instruction | Why it may go now | Whiteboard after |
|---|---|---|---|---|
| 1 | P0 | `X3 = y`, reads 0 | the earlier store is to x, not y, and W->R is off | x=0, y=0 |
| 2 | P1 | `X3 = x`, reads 0 | same reason | x=0, y=0 |
| 3 | P0 | `x = 1` | nothing earlier is unfinished | x=1, y=0 |
| 4 | P1 | `y = 1` | nothing earlier is unfinished | x=1, y=1 |

Final: `0:X3=0; 1:X3=0`. The weak outcome is reached, so SB is allowed.

### LB (expected: forbidden), and why it's impossible
Program: P0 does `X1 = x` then `y = 1`. P1 does `X1 = y` then `x = 1`.
Weak outcome: `0:X1=1 /\ 1:X1=1`.

R->W is on, so each thread's store must wait until its own load is done. Follow what the weak outcome
needs:
1. P0's load reads 1, so P1's `x = 1` was performed before it.
2. P1's `x = 1` waits for P1's load, so P1's load was performed earlier still.
3. P1's load reads 1, so P0's `y = 1` was performed before it.
4. P0's `y = 1` waits for P0's load.

So P0's load would have to happen before itself. No order of steps can do that, so LB is forbidden.
(With R->W off, as in candidate 0000, both stores can go first and LB is allowed.)

### MP (expected: allowed)
Program: P0 does `x = 1` then `y = 1`. P1 does `X1 = y` then `X3 = x`.
Weak outcome: `1:X1=1 /\ 1:X3=0`.

| Step | Thread | Instruction | Why it may go now | Whiteboard after |
|---|---|---|---|---|
| 1 | P0 | `y = 1` | the earlier store is to x, not y, and W->W is off | x=0, y=1 |
| 2 | P1 | `X1 = y`, reads 1 | nothing earlier is unfinished | x=0, y=1 |
| 3 | P1 | `X3 = x`, reads 0 | nothing earlier is unfinished | x=0, y=1 |
| 4 | P0 | `x = 1` | nothing earlier is unfinished | x=1, y=1 |

Final: `1:X1=1; 1:X3=0`. The weak outcome is reached, so MP is allowed.

### CoRR (expected: forbidden)
Program: P0 does `x = 1`. P1 does `X1 = x` then `X2 = x`.
Weak outcome: `1:X1=1 /\ 1:X2=0`.

Both of P1's loads touch x, so the second must wait for the first (the same-location condition; no flag
is involved). If the first load reads 1, P0's `x = 1` is already on the whiteboard, and nothing ever
writes 0 again. The second load comes later, so it also reads 1. `X2 = 0` cannot happen, so CoRR is
forbidden. This holds for all 16 flag settings, matching herd7's F for every candidate.
