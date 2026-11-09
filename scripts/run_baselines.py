"""Run herd7 with every baseline model on every test in tests/.

Saves results/baselines.csv and prints a table: A = allowed (Sometimes/Always), F = forbidden (Never).
Needs herd7 on PATH: run `eval $(opam env)` first.
"""
import csv
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINES = ROOT / "models" / "baselines"

# Column name -> model passed to herd7 -model. Our files use full paths, because a bare
# "sc.cat" or "tso.cat" would load herd7's built-in file of the same name instead.
MODELS = {
    "None": BASELINES / "none.cat",
    "RLX": BASELINES / "rlx.cat",
    "RA": BASELINES / "ra.cat",
    "SRA": BASELINES / "sra.cat",
    "TSO": BASELINES / "tso.cat",
    "SC": BASELINES / "sc.cat",
    "Arm": "aarch64.cat",  # herd7's built-in model, its default for AArch64 tests
}
VERDICT = {"Sometimes": "A", "Always": "A", "Never": "F"}


def observe(model, test):
    """Run herd7 once and return (observation, positive, negative) from its Observation line."""
    out = subprocess.run(["herd7", "-model", str(model), str(test)], capture_output=True, text=True)
    for line in out.stdout.splitlines():
        if line.startswith("Observation "):
            _, _, observation, positive, negative = line.split()
            return observation, int(positive), int(negative)
    # herd7 exits 0 even when a model fails to load, so a missing line is the only sign of trouble
    raise SystemExit(f"No Observation line from: herd7 -model {model} {test}\n{out.stdout}{out.stderr}")


def main():
    tests = sorted((ROOT / "tests").glob("*.litmus"), key=lambda path: path.stem)
    rows = []
    for test in tests:
        for name, model in MODELS.items():
            observation, positive, negative = observe(model, test)
            rows.append({"test": test.stem, "model": name, "observation": observation,
                         "positive": positive, "negative": negative, "verdict": VERDICT[observation]})

    with open(ROOT / "results" / "baselines.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"{'Test':<12}" + "".join(f"{name:<5}" for name in MODELS))
    for test in tests:
        verdicts = [row["verdict"] for row in rows if row["test"] == test.stem]
        print(f"{test.stem:<12}" + "".join(f"{v:<5}" for v in verdicts))


if __name__ == "__main__":
    main()
