# Memory Model Inference

CS 554 final project. We infer the memory model of an Apple M4 by black-box litmus testing:
herd7 predicts whether each weak outcome is allowed or forbidden under a set of candidate models,
litmus7 runs the same tests on the hardware, and candidates that forbid an observed outcome are
eliminated. The goals are to see whether the M4 in Arm mode is as weak as the Arm spec allows,
and whether its hardware TSO mode matches x86-TSO.

## Layout

```
tests/               .litmus files
models/baselines/    sc.cat tso.cat ra.cat sra.cat rlx.cat
models/candidates/   16 generated .cat files
scripts/             Python, standard library only
results/             CSVs and raw logs
notes.md             lab notebook
build/               litmus7 output (not tracked)
```

Requires herdtools7 (`opam install herdtools7`, then `eval $(opam env)`).

Status: in progress
