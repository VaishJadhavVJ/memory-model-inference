"""Operational "shared whiteboard" machine for the 16 candidates, checked against herd7 (docs/opmodel.md).

Usage: python3 scripts/opmodel.py

For every candidate (4 flags) and every test in TESTS, explores every order of steps of the machine
and collects the final states over the variables in the test's condition. Compares that set with the
full list of final states herd7 prints for the candidate's .cat file, writes results/opmodel_check.csv,
and exits with status 1 on any mismatch. Needs herd7 on PATH: run `eval $(opam env)` first.
"""
import csv
import itertools
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAIRS = ["WW", "WR", "RR", "RW"]  # flag order, as in the candidate names cand_WW?_WR?_RR?_RW?

# The 13 tests in tests/, written by hand from the .litmus files.
# Each thread is its instructions in program order:
#   ("W", location, value)     store a constant (the MOV that sets the value is folded in)
#   ("R", location, register)  load into a register
# The second item lists the variables in the test's condition, named as herd7 prints them.
# LB+datas and IRIW+addrs keep only their loads and stores: the machine ignores dependencies, like the
# candidates. The data-dependent store value is a constant (W1 EOR W1 = 0, plus 1 = 1) and the
# address-dependent load reads y (offset W1 EOR W1 = 0), so nothing else changes.
TESTS = {
    "2+2W": ([[("W", "x", 2), ("W", "y", 1)],
              [("W", "y", 2), ("W", "x", 1)]], ["[x]", "[y]"]),
    "CoRR": ([[("W", "x", 1)],
              [("R", "x", "X1"), ("R", "x", "X2")]], ["1:X1", "1:X2"]),
    "CoRW": ([[("W", "x", 2)],
              [("R", "x", "X1"), ("W", "x", 1)]], ["[x]", "1:X1"]),
    "CoWR": ([[("W", "x", 2), ("R", "x", "X2")],
              [("W", "x", 1)]], ["[x]", "0:X2"]),
    "CoWW": ([[("R", "x", "X0"), ("R", "x", "X2"), ("R", "x", "X3")],
              [("W", "x", 3), ("W", "x", 1)],
              [("W", "x", 2)]], ["0:X0", "0:X2", "0:X3"]),
    "IRIW": ([[("W", "x", 1)],
              [("R", "x", "X1"), ("R", "y", "X3")],
              [("W", "y", 1)],
              [("R", "y", "X1"), ("R", "x", "X3")]], ["1:X1", "1:X3", "3:X1", "3:X3"]),
    "IRIW+addrs": ([[("W", "x", 1)],
                    [("R", "x", "X1"), ("R", "y", "X3")],
                    [("W", "y", 1)],
                    [("R", "y", "X1"), ("R", "x", "X3")]], ["1:X1", "1:X3", "3:X1", "3:X3"]),
    "LB": ([[("R", "x", "X1"), ("W", "y", 1)],
            [("R", "y", "X1"), ("W", "x", 1)]], ["0:X1", "1:X1"]),
    "LB+datas": ([[("R", "x", "X1"), ("W", "y", 1)],
                  [("R", "y", "X1"), ("W", "x", 1)]], ["0:X1", "1:X1"]),
    "MP": ([[("W", "x", 1), ("W", "y", 1)],
            [("R", "y", "X1"), ("R", "x", "X3")]], ["1:X1", "1:X3"]),
    "S": ([[("W", "x", 2), ("W", "y", 1)],
           [("R", "y", "X1"), ("W", "x", 1)]], ["[x]", "1:X1"]),
    "SB": ([[("W", "x", 1), ("R", "y", "X3")],
            [("W", "y", 1), ("R", "x", "X3")]], ["0:X3", "1:X3"]),
    "WRC": ([[("W", "x", 1)],
             [("R", "x", "X1"), ("W", "y", 1)],
             [("R", "y", "X1"), ("R", "x", "X3")]], ["1:X1", "2:X1", "2:X3"]),
}


def may_perform(unfinished, k, flags):
    """May the k-th unfinished instruction of a thread perform now?

    No, if an earlier unfinished instruction touches the same location, or if the flag for the pair
    (earlier kind, this kind) is set, e.g. "WR" for a load behind an unfinished store.
    """
    kind, loc, _ = unfinished[k]
    return all(loc != earlier_loc and not flags[earlier_kind + kind]
               for earlier_kind, earlier_loc, _ in unfinished[:k])


def perform(state, t, k):
    """The state after thread t performs its k-th unfinished instruction."""
    memory, registers, unfinished = (dict(state[0]), dict(state[1]), state[2])
    kind, loc, arg = unfinished[t][k]
    if kind == "W":
        memory[loc] = arg                            # visible to every thread at once
    else:
        registers[f"{t}:{arg}"] = memory.get(loc, 0)  # locations start at 0
    rest = unfinished[t][:k] + unfinished[t][k + 1:]
    unfinished = unfinished[:t] + (rest,) + unfinished[t + 1:]
    return (tuple(sorted(memory.items())), tuple(sorted(registers.items())), unfinished)


def final_states(test, flags):
    """Every reachable final state, each a frozenset of "var=value" strings over the condition's variables."""
    threads, shown = TESTS[test]
    start = ((), (), tuple(tuple(thread) for thread in threads))
    seen, todo, finals = set(), [start], set()
    while todo:  # depth-first search over all orders of steps; `seen` skips states already explored
        state = todo.pop()
        if state in seen:
            continue
        seen.add(state)
        if not any(state[2]):  # every thread has finished
            memory, registers = dict(state[0]), dict(state[1])
            finals.add(frozenset(f"{var}={memory.get(var[1:-1], 0) if var.startswith('[') else registers.get(var, 0)}"
                                 for var in shown))
            continue
        for t, unfinished in enumerate(state[2]):
            for k in range(len(unfinished)):
                if may_perform(unfinished, k, flags):
                    todo.append(perform(state, t, k))
    return finals


def herd_states(model, test):
    """The final states herd7 lists for a test, in the same form as final_states()."""
    out = subprocess.run(["herd7", "-model", str(model), str(test)], capture_output=True, text=True).stdout
    lines = out.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("States ")]
    if not starts:  # herd7 exits 0 even when a model fails to load
        raise SystemExit(f"No States line from: herd7 -model {model} {test}\n{out}")
    i = starts[0]
    count = int(lines[i].split()[1])
    return {frozenset(part.strip() for part in line.split(";") if part.strip())
            for line in lines[i + 1:i + 1 + count]}


def show(states):
    """States as sorted text, one state per '|'-separated item."""
    return " | ".join(sorted("; ".join(sorted(state)) for state in states))


def main():
    rows, mismatches = [], []
    for bits in itertools.product([0, 1], repeat=len(PAIRS)):
        name = "cand_" + "_".join(f"{pair}{bit}" for pair, bit in zip(PAIRS, bits))
        flags = dict(zip(PAIRS, map(bool, bits)))
        for test in TESTS:
            machine = final_states(test, flags)
            herd = herd_states(ROOT / "models" / "candidates" / f"{name}.cat", ROOT / "tests" / f"{test}.litmus")
            same = machine == herd
            rows.append({"candidate": name, "test": test, "herd_states": len(herd),
                         "machine_states": len(machine), "match": "yes" if same else "no",
                         "only_herd": show(herd - machine), "only_machine": show(machine - herd)})
            if not same:
                mismatches.append(rows[-1])

    with open(ROOT / "results" / "opmodel_check.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows) - len(mismatches)} of {len(rows)} (candidate, test) pairs have identical final states")
    for row in mismatches:
        print(f"MISMATCH {row['candidate']} {row['test']}: only herd7 [{row['only_herd']}], "
              f"only machine [{row['only_machine']}]")
    print("wrote results/opmodel_check.csv")
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
