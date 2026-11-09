"""Check results/predictions.csv against what the 16 candidates should predict,
and check Phase 1 inference against the expected best survivor for each simulated truth.

Prints PASS/FAIL per expectation and exits with status 1 if any fail. Run scripts/predict.py first.
"""
from infer import infer, load_predictions
from phase1 import simulate

COHERENCE = ["CoRR", "CoRW", "CoWR", "CoWW"]
PIN = {"WR": "SB", "WW": "2+2W", "RW": "LB", "RR": "IRIW"}  # should be F exactly when the flag is 1
PHASE1 = {  # truth: (unique best surviving candidate, its mismatched tests)
    "sc": ("cand_WW1_WR1_RR1_RW1", []),
    "tso": ("cand_WW1_WR0_RR1_RW1", []),
    "aarch64": ("cand_WW0_WR0_RR0_RW0", ["IRIW+addrs", "LB+datas"]),
    "ra": ("cand_WW0_WR0_RR0_RW1", ["MP", "S", "WRC"]),
    "sra": ("cand_WW1_WR0_RR0_RW1", ["MP", "WRC"]),
}


def flags(name):
    """cand_WW1_WR0_RR1_RW1 -> {"WW": True, "WR": False, "RR": True, "RW": True}"""
    return {part[:2]: part[2] == "1" for part in name.split("_")[1:]}


def main():
    table = load_predictions()
    cands = {name: row for name, row in table.items() if name.startswith("cand_")}

    checks = [
        ("16 candidates", [] if len(cands) == 16 else [f"found {len(cands)}"]),
        ("cand_WW1_WR1_RR1_RW1 matches sc",
         [t for t, v in table["sc"].items() if table["cand_WW1_WR1_RR1_RW1"][t] != v]),
        ("cand_WW1_WR0_RR1_RW1 matches tso",
         [t for t, v in table["tso"].items() if table["cand_WW1_WR0_RR1_RW1"][t] != v]),
        ("coherence tests F for every candidate",
         [f"{n}:{t}" for n, row in cands.items() for t in COHERENCE if row[t] != "F"]),
        ("no ties between candidates",
         [n for n, row in cands.items() if list(cands.values()).count(row) > 1]),
    ]
    for pair, test in PIN.items():
        checks.append((f"{test} is F exactly when {pair[0]}->{pair[1]} is preserved",
                       [n for n, row in cands.items() if (row[test] == "F") != flags(n)[pair]]))
    checks.append(("LB+datas = LB and IRIW+addrs = IRIW for every candidate",
                   [n for n, row in cands.items()
                    if row["LB+datas"] != row["LB"] or row["IRIW+addrs"] != row["IRIW"]]))

    for truth, (best, mismatched) in PHASE1.items():
        survivors = [row for row in infer(table, simulate(table, truth)) if row["survives"] == "yes"]
        fewest = survivors[0]["mismatches"] if survivors else None
        got = [(row["candidate"], sorted(row["mismatched_tests"].split()))
               for row in survivors if row["mismatches"] == fewest]
        checks.append((f"Phase 1 {truth}: unique best {best}, mismatches {mismatched}",
                       [] if got == [(best, sorted(mismatched))] else [f"got {got}"]))

    for label, failures in checks:
        print(("PASS  " if not failures else "FAIL  ") + label + ("" if not failures else f": {failures}"))
    if any(failures for _, failures in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
