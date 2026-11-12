"""Turn a litmus7 log into an observations CSV for infer.py, checking each test's hash against herd7.

Usage: python3 scripts/hw_obs.py LOG OUT.csv
Example: python3 scripts/hw_obs.py results/hw/m4_arm/run.log results/obs_m4_arm.csv

The hash summarises a test's initial state and code. If litmus7's hash equals herd7's hash for
the same file, the hardware ran exactly the test that herd7 analysed.
Writes columns: test, observed (yes/no), weak (runs that showed the weak outcome), total (all runs).
Stops without writing if a hash differs or a test in tests/ has no result in the log.
Needs herd7 on PATH: run `eval $(opam env)` first.
"""
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def herd_hash(test):
    """The Hash= value herd7 prints for tests/<test>.litmus (the model does not affect it)."""
    path = ROOT / "tests" / f"{test}.litmus"
    out = subprocess.run(["herd7", str(path)], capture_output=True, text=True)
    for line in out.stdout.splitlines():
        if line.startswith("Hash="):
            return line[len("Hash="):]
    raise SystemExit(f"No Hash line from herd7 for {path}\n{out.stdout}{out.stderr}")


def parse_log(path):
    """{test: (hash, weak, total)} from a litmus7 log.

    In each test's block, litmus7 prints Hash=... and then
    Observation <test> <Never|Sometimes|Always> <positive> <negative>.
    """
    results, last_hash = {}, None
    for line in Path(path).read_text().splitlines():
        if line.startswith("Hash="):
            last_hash = line[len("Hash="):]
        elif line.startswith("Observation "):
            _, test, _, positive, negative = line.split()
            if last_hash is None:
                raise SystemExit(f"{path}: no Hash line before the Observation line of {test}")
            results[test] = (last_hash, int(positive), int(positive) + int(negative))
            last_hash = None
    return results


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    log, out_path = sys.argv[1], Path(sys.argv[2])
    results = parse_log(log)
    tests = sorted(path.stem for path in (ROOT / "tests").glob("*.litmus"))
    missing = [test for test in tests if test not in results]
    if missing:
        raise SystemExit(f"{log}: no result for {missing}")

    rows, different = [], []
    for test in tests:
        litmus_hash, weak, total = results[test]
        same = litmus_hash == herd_hash(test)
        print(f"{test:<12} hash {litmus_hash} {'matches herd7' if same else 'DIFFERS from herd7'}"
              f"  weak {weak:>6} of {total}")
        if not same:
            different.append(test)
        rows.append([test, "yes" if weak > 0 else "no", weak, total])
    if different:
        raise SystemExit(f"Hash mismatch for {different}; {out_path} not written")

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["test", "observed", "weak", "total"])
        writer.writerows(rows)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
