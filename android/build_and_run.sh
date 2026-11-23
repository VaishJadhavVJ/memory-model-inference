#!/bin/sh
# Build and run the litmus tests on an Android phone inside Termux (no root needed).
# Usage: sh build_and_run.sh        (see README_RUN.txt)
# Writes results_<model>_<date>.txt: phone details first, then the output of every test.
cd "$(dirname "$0")" || exit 1

for tool in clang make; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "$tool is not installed. Install it with:  pkg install clang make"
        exit 1
    fi
done

NCPU=$(nproc)                      # cores this app may use; each binary sees the same number
SIZE=100000                        # iterations per run (-s), as on the M4
TARGET=${TARGET:-10000000}         # aim for at least this many executions per test

MODEL=$(getprop ro.product.model 2>/dev/null)
[ -n "$MODEL" ] || MODEL=unknown
OUT="results_$(printf %s "$MODEL" | tr -c 'A-Za-z0-9' '_')_$(date +%Y%m%d_%H%M).txt"

# The test sources are the .c files that define N, the number of threads.
TESTS=$(grep -l '^#define N ' *.c | sed 's/\.c$//')
COUNT=$(echo "$TESTS" | wc -l | tr -d ' ')

echo "Building $COUNT tests (this can take a few minutes)..."
if ! make -j "$NCPU" $(for t in $TESTS; do printf '%s.exe ' "$t"; done) >build.log 2>&1; then
    tail -n 20 build.log
    echo "Build failed. The full log is in build.log."
    exit 1
fi

{
    echo "=== uname -a"; uname -a
    echo "=== getprop ro.product.model"; getprop ro.product.model
    echo "=== getprop ro.soc.model"; getprop ro.soc.model
    echo "=== cat /proc/cpuinfo"; cat /proc/cpuinfo
    echo "=== settings: nproc=$NCPU size=$SIZE target=$TARGET date=$(date)"
} >"$OUT" 2>&1

i=0
for t in $TESTS; do
    i=$((i + 1))
    N=$(sed -n 's/^#define N \([0-9]*\)$/\1/p' "$t.c")
    COPIES=$((NCPU / N)); [ "$COPIES" -ge 1 ] || COPIES=1      # copies of the test run at once
    RUNS=$(( (TARGET + SIZE * COPIES - 1) / (SIZE * COPIES) ))  # runs x size x copies >= target
    echo "[$i/$COUNT] $t: $N threads, $COPIES copies, $RUNS runs"
    ./"$t.exe" -q -a "$NCPU" -s "$SIZE" -r "$RUNS" >run.tmp 2>&1
    if ! grep -q '^Observation ' run.tmp; then
        # Pinning a thread to a core can be refused (e.g. if Android limits the app's cores).
        echo "    could not pin threads to cores, running again without pinning"
        { echo "=== NOTE: $t failed with thread pinning, output:"; cat run.tmp
          echo "=== NOTE: $t rerun without pinning (-i 0)"; } >>"$OUT"
        ./"$t.exe" -q -a "$NCPU" -s "$SIZE" -r "$RUNS" -i 0 >run.tmp 2>&1
    fi
    cat run.tmp >>"$OUT"
done
rm -f run.tmp

if [ -d "$HOME/storage/downloads" ]; then
    cp "$OUT" "$HOME/storage/downloads/" && echo "Copied $OUT to your Downloads folder."
fi
echo "Done. Results: $(pwd)/$OUT"
