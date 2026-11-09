"""Phase 1: validate inference on simulated observations whose ground truth is known.

For each truth model, a test counts as observed exactly when herd7 says the model allows it (A).
Writes results/phase1/<truth>.csv (observations) and runs infer.py on it (<truth>_inference.csv).
"""
import csv

from infer import ROOT, load_predictions, run

TRUTHS = ["sc", "tso", "aarch64", "ra", "sra"]


def simulate(predictions, truth):
    """{test: True if observed}, where observed means the truth model allows the test."""
    return {test: verdict == "A" for test, verdict in predictions[truth].items()}


def main():
    predictions = load_predictions()
    out_dir = ROOT / "results" / "phase1"
    out_dir.mkdir(exist_ok=True)
    for truth in TRUTHS:
        path = out_dir / f"{truth}.csv"
        with open(path, "w", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(["test", "observed"])
            for test, seen in simulate(predictions, truth).items():
                writer.writerow([test, "yes" if seen else "no"])
        run(path)


if __name__ == "__main__":
    main()
