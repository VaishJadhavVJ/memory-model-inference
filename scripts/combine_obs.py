"""Combine observation CSVs (from hw_obs.py) of repeated runs of the same tests.

Usage: python3 scripts/combine_obs.py OUT.csv RUN1.csv RUN2.csv [...]

Prints each test's weak/total per run. If every run agrees on observed yes/no for every test,
writes OUT.csv with the weak and total counts summed. Otherwise lists the disagreements and
writes nothing.
"""
import csv
import sys


def load(path):
    """{test: (weak, total)} from a CSV with columns test, observed, weak, total."""
    with open(path, newline="") as f:
        return {row["test"]: (int(row["weak"]), int(row["total"])) for row in csv.DictReader(f)}


def main():
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    out_path, paths = sys.argv[1], sys.argv[2:]
    runs = [load(path) for path in paths]
    tests = list(runs[0])
    if any(list(run) != tests for run in runs):
        raise SystemExit("The runs do not contain the same tests")

    disagree = []
    for test in tests:
        counts = [run[test] for run in runs]
        seen = {weak > 0 for weak, _ in counts}
        print(f"{test:<16}" + "".join(f"{weak:>8} / {total:<10}" for weak, total in counts)
              + ("  <-- seen in some runs only" if len(seen) > 1 else ""))
        if len(seen) > 1:
            disagree.append(test)
    if disagree:
        raise SystemExit(f"Runs disagree on seen/never for {disagree}; {out_path} not written")

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["test", "observed", "weak", "total"])
        for test in tests:
            weak = sum(run[test][0] for run in runs)
            total = sum(run[test][1] for run in runs)
            writer.writerow([test, "yes" if weak > 0 else "no", weak, total])
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
