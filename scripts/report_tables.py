"""Write the final report's LaTeX tables (docs/report/tables/) from the result CSVs.

Usage: python3 scripts/report_tables.py
Rerun after new results (e.g. more S25 runs): docs/report/main.tex \\input{}s these files, so every
number in the tables comes from results/. Also copies the files the report shows (one RMEM
screenshot, two example files) into docs/report/, so the folder can be uploaded to Overleaf as is.
"""
import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
REPORT = ROOT / "docs" / "report"
TABLES = REPORT / "tables"

PHASE1 = {"sc": "SC", "tso": "TSO", "aarch64": "Arm (aarch64.cat)", "ra": "RA", "sra": "SRA"}
SHAPES = ["MP", "SB", "LB", "2+2W", "S", "WRC", "IRIW"]
M4_FIT, S25_FIT = "cand_WW0_WR0_RR0_RW1", "cand_WW1_WR0_RR0_RW1"
# Flat was run by hand in the RMEM web interface, so its results are not in a CSV (notes.md, 2026-11-23).
FLAT = {"LB": "A", "LB+datas": "F", "IRIW": "A", "IRIW+addrs": "F", "MP": "A"}


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def by_model(path):
    """{model: {test: "A"/"F"}} from a predictions CSV."""
    return {row.pop("model"): row for row in read(path)}


def by_test(path):
    return {row["test"]: row for row in read(path)}


def tt(text):
    return r"\texttt{" + text.replace("_", r"\_") + "}"


def runs(n):
    return f"{n // 1_000_000}M" if n % 1_000_000 == 0 else f"{n:,}"


def count(row):
    """weak / total, e.g. "2,255 / 50M"."""
    return f"{int(row['weak']):,} / {runs(int(row['total']))}"


def write(name, colspec, header, body):
    """A booktabs tabular; captions and labels live in main.tex."""
    lines = [r"\begin{tabular}{" + colspec + "}", r"\toprule", " & ".join(header) + r" \\", r"\midrule"]
    for row in body:
        lines.append(r"\midrule" if row is None else " & ".join(row) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", ""]
    (TABLES / name).write_text("\n".join(lines))


def wide(name, predictions):
    """Models as rows, tests as rotated column headers (appendix)."""
    tests = list(next(iter(predictions.values())))
    header = ["Model"] + [r"\rotatebox{90}{" + test + "}" for test in tests]
    write(name, "l" + "c" * len(tests), header,
          [[tt(model)] + [row[test] for test in tests] for model, row in predictions.items()])


def main():
    TABLES.mkdir(parents=True, exist_ok=True)
    pred = by_model(RESULTS / "predictions.csv")
    pred_ra = by_model(RESULTS / "predictions_ra.csv")
    m4, s25 = by_test(RESULTS / "obs_m4_arm.csv"), by_test(RESULTS / "obs_s25.csv")
    m4_ra, s25_ra = by_test(RESULTS / "obs_m4_ra.csv"), by_test(RESULTS / "obs_s25_ra.csv")
    tests = sorted(pred["aarch64"])

    body = []
    for truth, label in PHASE1.items():
        rows = read(RESULTS / "phase1" / f"{truth}_inference.csv")
        survivors = [row for row in rows if row["survives"] == "yes"]
        best = survivors[0]
        mism = best["mismatched_tests"].split()
        body.append([label, str(len(survivors)), tt(best["candidate"]),
                     str(len(mism)) + (": " + ", ".join(mism) if mism else "")])
    write("phase1.tex", "llll", ["Truth", "Survivors", "Best candidate (unique)", "Mismatches"], body)

    write("hw.tex", "lcrr", ["Test", "aarch64.cat", "M4 (weak / runs)", "S25 (weak / runs)"],
          [[test, pred["aarch64"][test], count(m4[test]), count(s25[test])] for test in tests])

    body = []
    for chip, path in [("M4", "obs_m4_arm_inference.csv"), ("S25", "obs_s25_inference.csv")]:
        if body:
            body.append(None)
        for row in read(RESULTS / path):
            if row["survives"] == "yes":
                body.append([chip, tt(row["candidate"]), row["mismatches"],
                             ", ".join(row["mismatched_tests"].split()) or "none"])
    write("survivors.tex", "lllp{0.38\\linewidth}",
          ["Chip", "Surviving candidate", "Mismatches", "Mismatched tests"], body)

    order = [f"{shape}+rel+{kind}" for kind in ("acq", "acqpc") for shape in SHAPES]
    write("ra.tex", "lccccccrr",
          ["Test", "aarch64", "RA", "SRA", "TSO", "SC", "", "M4 (weak / runs)", "S25 (weak / runs)"],
          [[test] + [pred_ra[m][test] for m in ("aarch64", "ra", "sra", "tso", "sc")] + ["",
           count(m4_ra[test]), count(s25_ra[test])] for test in order])

    write("flat.tex", "lcccc",
          ["Test", "Machine 0001 (M4 fit)", "Machine 1001 (S25 fit)", "aarch64.cat", "Flat (RMEM)"],
          [[test, pred[M4_FIT][test], pred[S25_FIT][test], pred["aarch64"][test], FLAT[test]] for test in FLAT])

    wide("pred_full.tex", pred)
    wide("pred_ra_full.tex", pred_ra)

    checks = read(RESULTS / "opmodel_check.csv")
    (TABLES / "numbers.tex").write_text(
        f"\\newcommand{{\\OpMatch}}{{{sum(row['match'] == 'yes' for row in checks)}}}\n"
        f"\\newcommand{{\\OpPairs}}{{{len(checks)}}}\n"
        f"\\newcommand{{\\OpStates}}{{{sum(int(row['herd_states']) for row in checks):,}}}\n")

    (REPORT / "figures").mkdir(exist_ok=True)
    (REPORT / "code").mkdir(exist_ok=True)
    shutil.copy(ROOT / "docs" / "figures" / "rmem" / "flat_LB+datas.png", REPORT / "figures" / "flat_LB_datas.png")
    shutil.copy(ROOT / "tests" / "LB.litmus", REPORT / "code" / "LB.litmus")
    shutil.copy(ROOT / "models" / "candidates" / f"{M4_FIT}.cat", REPORT / "code" / f"{M4_FIT}.cat")
    print(f"wrote {len(list(TABLES.glob('*.tex')))} files to {TABLES.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
