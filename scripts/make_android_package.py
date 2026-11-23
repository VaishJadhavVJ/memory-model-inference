"""Build the Android test package: build/android/ and build/android_tests.zip.

Usage: python3 scripts/make_android_package.py
Runs litmus7 on tests/*.litmus and tests/ra/*.litmus, adds android/build_and_run.sh and
android/README_RUN.txt, and zips the folder. The phone compiles and runs the tests itself in
Termux (see android/README_RUN.txt). Both are build outputs: build/ is not tracked by git.
Needs litmus7 on PATH: run `eval $(opam env)` first.
"""
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "android"
ZIP = ROOT / "build" / "android_tests.zip"

LITMUS_OPTS = [
    "-os", "android8",          # Linux kernel with Android's C library; pins threads via gettid()
    "-affinity", "random",      # pin each thread to its own core, shuffled again at every run
    "-mem", "direct", "-st", "1",  # memory settings of the M4 runs (litmus7's M1.cfg)
    "-s", "100k",               # 100,000 iterations per run; build_and_run.sh picks -r per test
    "-gcc", "clang",            # Termux has clang, not gcc
    "-ccopts", "-O2 -march=armv8.2-a+rcpc",  # +rcpc lets clang assemble LDAPR (tests/ra)
]


def main():
    tests = sorted((ROOT / "tests").glob("*.litmus")) + sorted((ROOT / "tests" / "ra").glob("*.litmus"))
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    subprocess.run(["litmus7", *LITMUS_OPTS, "-o", str(OUT), *map(str, tests)], check=True)
    # litmus7 can exit 0 after skipping a test, so count the generated test sources
    made = [path for path in OUT.glob("*.c") if "\n#define N " in path.read_text()]
    if len(made) != len(tests):
        raise SystemExit(f"litmus7 made {len(made)} test sources for {len(tests)} tests")
    for name in ("build_and_run.sh", "README_RUN.txt"):
        shutil.copy(ROOT / "android" / name, OUT / name)

    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(OUT.iterdir()):
            z.write(path, f"android_tests/{path.name}")
    print(f"{len(tests)} tests -> {OUT.relative_to(ROOT)}/ and {ZIP.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
