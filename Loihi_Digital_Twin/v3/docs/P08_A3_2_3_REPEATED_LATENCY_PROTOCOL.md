# P08-A3.2.3 — Repeated paired physical latency characterization

**Status (2026-10-18 project timeline): ALL THREE ORIGINAL KV260 PAIRED PHYSICAL RUNS COMPLETED AND FINAL DESCRIPTIVE THREE-PAIR RESULTS USER-REPORTED. Matched ordinary-image A2.2−A2.1 median differences +16.840, +25.400 and +29.710 µs; mean +23.984 µs, between-pair SD 6.551 µs. Original final three-pair file/explicit aggregate PASS marker not independently provided in chat; no CI or raw evidence re-inspection. P08-A3.2.3 USER-ATTESTED LATENCY REPEATS COMPLETE; OVERALL P08-A REQUIRES A5 CPU COMPARATOR AND REPORT.** Do not merge or claim a statistical reference without user approval. Power/energy deferred.

**Final result update:** The last A2.1→A2.2 Pair 3 also passed the original dual-oracle paired timing checker as reported by the user. Final 3-pair host report excerpt: A2.1 medians **35.7023, 35.6946, 35.6696 ms**, A2.2 medians **35.7234, 35.7163, 35.7220 ms**, paired median differences **+16.840, +25.400, +29.710 µs**, between-pair mean **+23.984 µs** (sample SD **6.551 µs**), fixed-image delta-range median **24.730 µs** and p95 **73.541 µs**. Read the [full source-qualified final measurement report](P08_A3_2_3_FINAL_PHYSICAL_REPEAT_RESULTS.md). Original result/runner code unchanged; all commands below are **historical reproduction instructions, NOT remaining physical tasks**. No extra FPGA runs are required for repeat study; P08-A5 CPU comparator remains open.

## 1. Previously accepted first pair (locked data)

The user reported **1,024 original-order TRAIN-derived validation images**, A2.1 and A2.2 separately executed on the KV260 and original P07 packed-neural validation passed for both, paired timing integrity PASS. The 1,023 ordinary image rows (trace frame 1023 excluded) yielded:

| Measurement | A2.1 | A2.2 | Frame-paired A2.2 − A2.1 |
| --- | ---: | ---: | ---: |
| Median service (ms) | 35.7023 | 35.7234 | **+0.0168** |
| P95 (ms) | 41.9667 | 41.9800 | +0.0744 |
| Min (ms) | 27.8371 | 27.8020 | −0.0435 |
| Max (ms) | 48.8564 | 48.8689 | +0.0822 |
| Sample stdev (ms) | 3.3939 | 3.3937 | 0.0240 |

Both separate A53 CNTFRQ readings were **99,999,001 Hz**. This small first-pair median delta is a **measured A53 frame-service difference** affected by run/order effects, not a calibrated isolated cost of each additional timer sample. The exact user-reported results, firmware pins and source paths are preserved in [A3.2.2 first-pair report](P08_A3_2_2_PHYSICAL_RESULTS.md). Original first16 pilot is recorded separately.

**New Pair 2 acceptance:** The user executed the reversed order A2.2 → A2.1, accepted both independent 1,024-image original P07 packed-oracle/timing gates, and reported A2.1 median **35.6946 ms**, A2.2 median **35.7163 ms**, and same-frame paired median **+0.0254 ms / +25.4 µs** (paired nearest-rank p95 **+0.0827 ms**, range **−0.0428 to +0.0909 ms**, stdev **0.0255 ms**). Both A53 CNTFRQ values: **99,999,001 Hz**. Details: [Pair 2 exact observations](P08_A3_2_3_PAIR2_RESULTS.md). Its A2.1 evidence folder and paired report filename were not posted. Do not guess either path. Both Pair 1 and Pair 2 JSON reports are immutable inputs for the final aggregate.

The first pair is **one hardware session per firmware**, NOT repeated sampling. Do not re-run or overwrite its directories, logs or JSON. The original accepted **first1024 TRAIN-only stage**, last selected 26×42 full trace at 1023, and existing frozen built firmware binaries remain unchanged throughout P08-A3.2.3.

## 2. Predeclared second/third pair order and study scope

For three independently rebooted pairs (six physical sessions, including the already executed pair):

| Pair | First physically run | Second physically run | State |
| --- | --- | --- | --- |
| 1 | A2.1 | A2.2 | **USER PHYSICAL PASS**, 1,024-image per-version |
| 2 | **A2.2** | **A2.1** | **USER-ATTESTED PHYSICAL PASS**; 1023 ordinary-image matched median delta **+25.4 µs**, p95 **+82.7 µs** |
| 3 | **A2.1** | **A2.2** | **USER-ATTESTED PHYSICAL PASS**; final paired median **+29.710 µs** |

This AB/BA/AB ordering is **partially counterbalanced**, not a randomized or blinded design. Preserve chronological time, device reboot and environment notes in each untracked physical evidence folder; do not infer a controlled thermal/clock relationship without actual evidence. Do not describe the 3 × 1,023 ordinary observations per mode as 3,069 independent samples—the same **1,023 ordinary images** are measured repeatedly. The **one** full trace image per 1,024-image run is excluded from ordinary service distributions.

One physical run at a time; reboot to dedicated **JTAG-only bare-metal state** before *and* after every session. No Linux ownership of reserved DDR. Every runner invocation overwrites `0x40000000–0x43FFFFFF`. Never automate several physical sessions in a loop because independent reboot/ownership confirmation is mandatory. Do not open or rerun official MNIST TEST. Power and energy deferred.

## 3. New A3.2.3 host aggregator

Files added:
- `src/loihi_twin_v2/p08_a3_2_repeats.py` — fail-closed pure Python three-pair aggregation, enforcing the same original dataset descriptor/raw pixel/manifest SHA256 for each pair, exact original A2.1/A2.2 ELF pins, full 1,024 per-image arrays with internally consistent deltas and nearest-rank p95, original dual-oracle/physical-timing PASS flags, separate physical run directories and **distinct** 1MiB/3MiB physical timing sidecar hashes. No physical board access.
- `scripts/p08_a3_2_repeat_check.py` — offline CLI `--pair-reports pair1.json pair2.json pair3.json --report new.json`. Must pass three independently accepted A3.2.1 paired reports; one pair or duplicated report is rejected. Writes a new no-overwrite results manifest.
- `tests/test_p08_a3_2_repeats.py` — synthetic-only native tests of three-repetition accounting, wrong counts, reused physical files, source staging drift, forged delta and a mismatched summary.
- Existing physical `scripts/run_p08_a3_2_1024.sh`, original P07 oracle, A2.1 and A2.2 binaries and Vivado bitstream **unchanged**.

The aggregator reports 3 run-pair medians, between-pair median-delta distribution with only **n=3**, distribution of the fixed-image three-run mean deltas across **1,023 image identities**, per-image range of three deltas, preserved per-pair absolute and delta vectors, original evidence/report SHA256s, per-run counter rates and **explicit small-n limitations**. It does *not* calculate a confidence interval as if all 3 × 1,023 values were independent, does *not* causally attribute the difference solely to instrumentation, and cannot independently prove the historical run order from the timing buffers alone. The source A3.2.1 pair verifier already proved original packed P07 neural parity for **both** runs before creating each report; the aggregator binds report-provided evidence hashes but does not rerun that expensive full oracle a fourth time.

## 4. Native verification first (NO hardware)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-a-physical-baseline
git pull --ff-only origin agent/v3-p08-a-physical-baseline
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q \
  tests/test_p08_a3_2_repeats.py \
  tests/test_p08_a3_2_capture.py tests/test_p08_a3_2_analysis.py \
  tests/test_p08_a3_1_pilot.py tests/test_p08_a2_2_ticks.py \
  tests/test_p08_a2_timing.py tests/test_p07_a4_official.py tests/test_p07_a4_fault.py

python -m py_compile scripts/p08_a3_2_repeat_check.py \
  src/loihi_twin_v2/p08_a3_2_repeats.py
bash -n scripts/run_p08_a3_2_1024.sh
```

**Stop if any test fails; no source CI/native pass for A3.2.3 is asserted yet.** No Vitis build required: physical binaries are immutable and SHA-pinned.

## 5. Repeat-pair capture commands (operator-controlled separate boots)

**Historical reproduction note:** all three physical pairs, including the final A2.1 → A2.2 Pair 3, have been user-completed. The JTAG sections below record how the accepted measurements were obtained; **do not rerun or overwrite** any original session. The only optional remaining A3 action is independent file-level sealing of the existing summary and raw evidence; **A5 CPU software baseline is the next research stage.** For each Pair 3 session use a fresh output directory and independently reboot into JTAG-only bare-metal with no Linux ownership of the reserved DDR range.


Set original accepted paths (the user previously posted the stage/build locations, but **not** the first paired report filename):

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
source ~/Git/Thesis/.venv-p08/bin/activate
export P08_A3_2_STAGE_DIR=/home/dna/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z
export P08_A2_BUILD_DIR=/tmp/v3_p08_a2_build_20261018T193149Z
export P08_A2_2_BUILD_DIR=/tmp/v3_p08_a2_2_build_20261018T200133Z
: "${P03_DIAG_REPORTS:?Restore actual accepted P03.2c routed report path}"
PYTHONPATH="$PWD/src" python scripts/p07_a4_2_check.py --stage-dir "$P08_A3_2_STAGE_DIR"
```

**Pair 2 first run: A2.2 (reverse order)**. Select a **NEW evidence path**:

```bash
export P08_A3_2_VARIANT=A2_2
export P08_A3_2_PAIR2_A22_DIR="$HOME/Thesis_Evidence/p08_a3_2_pair2_A2_2_$(date -u +%Y%m%dT%H%M%SZ)"
export P08_A3_2_RUN_DIR="$P08_A3_2_PAIR2_A22_DIR"
P08_A3_2_PREFLIGHT_ONLY=YES bash scripts/run_p08_a3_2_1024.sh
```

Only if offline preflight passes, physically reboot to dedicated JTAG-only bare metal with **NO** running KV260 Linux DDR owner; explicitly authorize overwrite and run (the following call **WILL** program the FPGA and overwrite reserved DDR):

```bash
unset P08_A3_2_PREFLIGHT_ONLY
export P08_A3_2_CONFIRM_JTAG_ONLY=YES
export P08_A3_2_CONFIRM_DDR_OVERWRITE=YES
export P08_A3_2_CONFIRM_TRAIN_VALIDATION_ONLY=YES
bash scripts/run_p08_a3_2_1024.sh
cat "$P08_A3_2_RUN_DIR/attempt_exit_status.txt"
sha256sum --check "$P08_A3_2_RUN_DIR/physical_output_sha256.txt"
unset P08_A3_2_CONFIRM_JTAG_ONLY P08_A3_2_CONFIRM_DDR_OVERWRITE P08_A3_2_CONFIRM_TRAIN_VALIDATION_ONLY
```

Require **`P08_A3_2_2_SINGLE_1024_FULL_PHYSICAL_GATE_PASS=1`**, script exit status zero and all hashes OK; preserve failure evidence. Reboot the KV260 after every attempt, never resume halted Linux.

**Pair 2 second run: A2.1** (ONLY after reboot). New evidence directory and fresh offline preflight:

```bash
export P08_A3_2_VARIANT=A2_1
export P08_A3_2_PAIR2_A21_DIR="$HOME/Thesis_Evidence/p08_a3_2_pair2_A2_1_$(date -u +%Y%m%dT%H%M%SZ)"
export P08_A3_2_RUN_DIR="$P08_A3_2_PAIR2_A21_DIR"
P08_A3_2_PREFLIGHT_ONLY=YES bash scripts/run_p08_a3_2_1024.sh
```

Only after this second preflight and **another separate JTAG-only reboot + new physical consent**, run the same consent/runner/exit/checksum commands as above. Again reboot afterward. Never reuse the A2.2 run directory.

Run original paired host verifier ONLY after both separate 1,024-image oracle/telemetry physical captures pass:

```bash
export P08_A3_2_PAIR2_REPORT="$HOME/Thesis_Evidence/p08_a3_2_pair2_report_$(date -u +%Y%m%dT%H%M%SZ).json"
PYTHONPATH="$PWD/src" python scripts/p08_a3_2_pair_check.py \
  --stage-dir "$P08_A3_2_STAGE_DIR" \
  --a21-run-dir "$P08_A3_2_PAIR2_A21_DIR" \
  --a22-run-dir "$P08_A3_2_PAIR2_A22_DIR" \
  --a21-elf "$P08_A2_BUILD_DIR/vitis_workspace/p08_a2_board.elf" \
  --a22-elf "$P08_A2_2_BUILD_DIR/vitis_workspace/p08_a2_2_board.elf" \
  --report "$P08_A3_2_PAIR2_REPORT"
```

Expected `P08_A3_2_1024_BOTH_ORACLES_EXACT=1`, `P08_A3_2_1024_PAIRED_LATENCY_SINGLE_PAIR_PASS=1`. This is still **not** a repeated baseline.

For **pair 3**, use exactly the same method but order **A2.1 then A2.2**, completely fresh session/output folders, and a new `P08_A3_2_PAIR3_REPORT`. Each run again needs offline preflight, independent reboot and newly entered three consents. Do not change any acceptance pins, stage bytes, frozen firmware or Vivado XSA. **Do not run all four remaining physical sessions in a single shell loop.**

## 6. Aggregate once three complete paired reports exist

Identify the existing original paired report filename **from the user's actual untracked output**, not from a guessed timestamp. E.g. list candidate files:

```bash
find "$HOME/Thesis_Evidence" -maxdepth 1 -type f -name 'p08_a3_2_pair_*.json' -print
```

Choose its exact verified path as `P08_A3_2_PAIR1_REPORT` (do not overwrite). After pair2 and pair3 are accepted:

```bash
export P08_A3_2_REPEAT_REPORT="$HOME/Thesis_Evidence/p08_a3_2_three_pair_summary_$(date -u +%Y%m%dT%H%M%SZ).json"
PYTHONPATH="$PWD/src" python scripts/p08_a3_2_repeat_check.py \
  --pair-reports "$P08_A3_2_PAIR1_REPORT" \
                 "$P08_A3_2_PAIR2_REPORT" \
                 "$P08_A3_2_PAIR3_REPORT" \
  --report "$P08_A3_2_REPEAT_REPORT"
```

Expected markers: `P08_A3_2_3_DISTINCT_PHYSICAL_SESSIONS=6`, `P08_A3_2_3_SAME_ORIGINAL_TRAIN_FIRST1024_PASS=1`, `P08_A3_2_3_THREE_PAIRED_LATENCY_AGGREGATION_PASS=1`, `P08_A3_2_3_RESULT_SCOPE=DESCRIPTIVE_REPEATED_PILOT`. The report's three physical delta medians and fixed-image spread are the quantities to inspect. If run-order effects are notable or between-pair variability overwhelms delta, do not overclaim overhead calibration.

**Completed experiment:** no new physical A3.2 runs or firmware rebuilds are necessary. Any future repetition requires a new user-controlled study plan and distinct JTAG-only consent; do not run these historical operator commands merely to claim closure. Only P08-A5 CPU comparator / final report and user approval remain for full P08-A milestone closure (power/energy deferred).
