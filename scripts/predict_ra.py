"""Run herd7 on the release/acquire tests in tests/ra/ with aarch64.cat, ra.cat, sra.cat, tso.cat, sc.cat.

Saves results/predictions_ra.csv (rows = models, columns = tests, values A/F) and prints the table.
Only aarch64.cat reads the STLR/LDAR/LDAPR annotations. Our own models ignore them and treat every
access alike, so under ra.cat every access is release/acquire: that is theoretical RA.
Needs herd7 on PATH: run `eval $(opam env)` first.
"""
from predict import predict
from run_baselines import MODELS, ROOT


def main():
    tests = sorted((ROOT / "tests" / "ra").glob("*.litmus"), key=lambda path: path.stem)
    models = [MODELS[name] for name in ("Arm", "RA", "SRA", "TSO", "SC")]
    predict(tests, models, ROOT / "results" / "predictions_ra.csv")


if __name__ == "__main__":
    main()
