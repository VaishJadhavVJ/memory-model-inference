"""Rank the 16 candidate models against a set of observations.

Usage: python3 scripts/infer.py OBSERVATIONS.csv

OBSERVATIONS.csv has columns test, observed (yes/no). Predictions come from results/predictions.csv.
For each candidate:
  contradictions = tests observed but forbidden by the candidate -> candidate is eliminated
  mismatches     = tests allowed by the candidate but not observed (soft evidence)
Writes <OBSERVATIONS>_inference.csv next to the input with all 16 candidates, survivors first,
fewest mismatches first, and prints the survivors.
"""
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_predictions():
    """{model: {test: "A" or "F"}} from results/predictions.csv."""
    with open(ROOT / "results" / "predictions.csv", newline="") as f:
        return {row.pop("model"): row for row in csv.DictReader(f)}


def load_observations(path):
    """{test: True if observed} from a CSV with columns test, observed (yes/no)."""
    observed = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            value = row["observed"].strip().lower()
            if value not in ("yes", "no"):
                raise SystemExit(f"{path}: observed must be yes or no, got {row['observed']!r} for {row['test']}")
            observed[row["test"]] = value == "yes"
    return observed


def infer(predictions, observed):
    """One row per candidate, sorted by (contradictions, mismatches), so survivors come first."""
    rows = []
    for name, predicted in predictions.items():
        if not name.startswith("cand_"):
            continue
        contradictions = [test for test, seen in observed.items() if seen and predicted[test] == "F"]
        mismatches = [test for test, seen in observed.items() if not seen and predicted[test] == "A"]
        rows.append({
            "candidate": name,
            "survives": "no" if contradictions else "yes",
            "contradictions": len(contradictions),
            "contradicted_by": " ".join(contradictions),
            "mismatches": len(mismatches),
            "mismatched_tests": " ".join(mismatches),
        })
    rows.sort(key=lambda row: (row["contradictions"], row["mismatches"]))  # stable: ties keep file order
    return rows


def run(obs_path):
    """Infer from one observations file, write <name>_inference.csv next to it, print the survivors."""
    predictions = load_predictions()
    observed = load_observations(obs_path)
    tests = list(next(iter(predictions.values())))
    unknown = sorted(set(observed) - set(tests))
    if unknown:
        raise SystemExit(f"{obs_path}: tests not in predictions.csv: {unknown}")
    missing = [test for test in tests if test not in observed]

    rows = infer(predictions, observed)
    out_path = obs_path.with_name(obs_path.stem + "_inference.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    survivors = [row for row in rows if row["survives"] == "yes"]
    print(f"{os.path.relpath(obs_path)}: {len(survivors)} of {len(rows)} candidates survive")
    if missing:
        print(f"  no observation for {missing}; these tests are ignored")
    for row in survivors:
        print(f"  {row['candidate']}  mismatches={row['mismatches']}  {row['mismatched_tests']}")
    print(f"  wrote {os.path.relpath(out_path)}")
    return rows


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    run(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
