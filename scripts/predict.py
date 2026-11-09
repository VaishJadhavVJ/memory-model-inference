"""Run herd7 for every model (6 baselines, herd7's aarch64.cat, 16 candidates) on every test.

Saves results/predictions.csv (rows = models, columns = tests, values A/F) and prints the table.
Needs herd7 on PATH: run `eval $(opam env)` first.
"""
import csv
from pathlib import Path

from run_baselines import MODELS, ROOT, VERDICT, observe


def main():
    tests = sorted((ROOT / "tests").glob("*.litmus"), key=lambda path: path.stem)
    # MODELS holds our baselines as full paths plus "aarch64.cat"; candidates are full paths too
    models = list(MODELS.values()) + sorted((ROOT / "models" / "candidates").glob("*.cat"))

    header = ["model"] + [test.stem for test in tests]
    rows = []
    for model in models:
        verdicts = [VERDICT[observe(model, test)[0]] for test in tests]
        rows.append([Path(model).stem] + verdicts)

    with open(ROOT / "results" / "predictions.csv", "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)

    widths = [max(len(row[i]) for row in [header] + rows) + 1 for i in range(len(header))]
    for row in [header] + rows:
        print("".join(cell.ljust(width) for cell, width in zip(row, widths)))


if __name__ == "__main__":
    main()
