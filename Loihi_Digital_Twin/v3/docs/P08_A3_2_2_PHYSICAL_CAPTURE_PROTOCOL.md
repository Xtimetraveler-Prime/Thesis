# P08-A3.2.2 — Dual-variant 1,024-image KV260 capture protocol

**Status (2026-10-18 project timeline): USER ATTESTED A3.2.2 PHYSICAL FIRST A2.1/A2.2 1,024-IMAGE PAIR AND A3.2.1 INDEPENDENT ORACLE/TIMING INTEGRITY PASS. Paired median A53 full-service difference +0.0168 ms; further repeated trials remain A3.2.3.** Previous **A3.1** pilot completed physical parity and timing telemetry; the fixed 16-image pilot remains immutable. **A3.2.1** offline 1,024-image paired analyzer passed user-local native tests. No power characterization.

**Result update:** The user reports all A3.2.2 native tests passed after the guarded test fixture correction, both true-original first1024 offline preflights passed, and the separate KV260 physical A2.1/A2.2 captures plus original independent packed-oracle paired report PASS. See [numerical paired physical measurements](P08_A3_2_2_PHYSICAL_RESULTS.md). The procedure below remains the authoritative reproduction/safety protocol, not an instruction to overwrite the accepted first pair.

## 1. Goal and unchanged research foundations

Capture **one** independent original-order, first-1,024 **TRAIN-derived validation** session per fixed firmware version; independently replay the original P07 packed-integer neural oracle for **all 1,024 × 26 output ticks and the selected 26 × 42 full physical trace**, then validate A53 timing sidecars. Retain both independent datasets for the already user-accepted [A3.2.1 offline paired analysis](P08_A3_2_PAIRED_LATENCY_PROTOCOL.md). A3.2.2 itself does **not** claim replicated timing confidence or instruction-only instrumentation overhead.

- A2.1 **baseline**, image-only timing: pinned original ELF SHA256 `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`. User-original Vitis build directory `/tmp/v3_p08_a2_build_20261018T193149Z`, ELF `vitis_workspace/p08_a2_board.elf`.
- A2.2 **detail**, image and 26-tick timing: pinned original ELF SHA256 `87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361`. User-original Vitis build directory `/tmp/v3_p08_a2_2_build_20261018T200133Z`, ELF `vitis_workspace/p08_a2_2_board.elf`.
- Both: routed P03.2c XSA SHA256 `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`, immutable 512KiB master SHA256 `9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955`, unchanged P03/P07 fabric/HLS and checkpoint.
- Exactly one shared frozen 1,024-image stage from `scripts/p07_a4_2_prepare.py --validation-first 1024 --trace-index 1023`. No new official MNIST TEST opening, replay or training. Host-only labels are used for sample provenance **not** the spike encoder/FPGA inference.
- Raw timestamps: ARM `CNTVCT_EL0` and each physical run's observed `CNTFRQ_EL0`. PL dispatch cycles are *another* hardware clock domain; do **not** convert PL cycles into seconds using `CNTFRQ`. Primary external references and precise callback boundaries remain in [A2.2 Timing Methods](P08_A2_2_TIMING_METHODS.md).

## 2. Newly implemented software (each run independent)

- `scripts/run_p08_a3_2_1024.sh`: ONE controlled mode `P08_A3_2_VARIANT=A2_1` or `A2_2`. Denies unrecognized modes. SHA/ELF/Vitis build-manifest checks and byte-exact original staged firmware sources for **that exact mode** are performed before any hardware command.
- `scripts/p08_a3_2_single_check.py`: OFFLINE consumer of actual captured original P07 numerical journal, selected full trace, and image timing sidecar; with A2.2 also consumes the 3MiB CRC-protected per-tick telemetry. Requires the original frozen independent P07 oracle PASS *first*. The A2.2 path also checks every external event count versus the accepted spike encoder, routed packet totals and final drain, as well as all tick-to-image PL cycles.
- `tests/test_p08_a3_2_capture.py`: negative tests for missing consent, wrong mode, existing evidence directory, absent pinned source, forbidden sample populations, neural-oracle failure and variant-specific 1,024-image telemetry. Tests have **not yet** been user-run for these new files; nothing here touches the FPGA.
- Existing `scripts/p08_a3_2_pair_check.py`: previously accepted A3.2.1 postprocess tool; **not** a physical launcher. Requires independently verified A2.1 and A2.2 captures from distinct fresh directories.

## A3.2.2 initial local test fixture correction (2026-10-18)

The user ran the new A3.2.2 native tests and reported four failures: both firmware variants of the missing-consent test and both firmware variants of the offline-missing-artifacts test. These are **negative test fixture failures**, **not a physical KV260 runtime failure**. The initial `env_for(tmp_path)` fixture pointed `P08_A3_2_STAGE_DIR` at `tmp_path` and `P08_A3_2_RUN_DIR` at `tmp_path/not-created`. Therefore the evidence target was **inside the protected immutable stage**, and the unchanged runner correctly rejected it before the tests reached their intended consent/artifact guards.

Corrected `tests/test_p08_a3_2_capture.py` now creates a distinct sibling `tmp_path/stage`, leaving `tmp_path/not-created` as a valid non-overlapping evidence path. Six additional negative tests explicitly ensure **both firmware modes** still reject evidence nested inside stage, build, or route-report locations, even when physical consent variables are present. **No change** was made to the production `scripts/run_p08_a3_2_1024.sh` or to frozen P03/P07/P08 C sources, original bitstreams or prior physical evidence.

The complete native suite **must be rerun** after this correction; no renewed PASS or physical launch is claimed.

## 3. Native gates (NO physical board / NEVER substitute for JTAG evidence)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-a-physical-baseline
git pull --ff-only origin agent/v3-p08-a-physical-baseline
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q \
  tests/test_p08_a3_2_capture.py tests/test_p08_a3_2_analysis.py \
  tests/test_p08_a3_1_pilot.py tests/test_p08_a2_2_ticks.py \
  tests/test_p08_a2_timing.py \
  tests/test_p07_a4_official.py tests/test_p07_a4_fault.py

bash -n scripts/run_p08_a3_2_1024.sh
python -m py_compile scripts/p08_a3_2_single_check.py scripts/p08_a3_2_pair_check.py \
  src/loihi_twin_v2/p08_a3_2_analysis.py
```

**Stop if anything fails.** This run has no remote CI attestation yet; all test evidence must come from local execution. Do **not** schedule/execute a board run until native gates pass.

## 4. Stage original first-1,024 validation images once — offline

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
mkdir -p "$HOME/Thesis_Evidence"
export P08_A3_2_STAGE_DIR="$HOME/Thesis_Evidence/p08_a3_2_stage1024_$(date -u +%Y%m%dT%H%M%SZ)"
PYTHONPATH="$PWD/src" python scripts/p07_a4_2_prepare.py \
  --validation-first 1024 --trace-index 1023 --out "$P08_A3_2_STAGE_DIR"
PYTHONPATH="$PWD/src" python scripts/p07_a4_2_check.py \
  --stage-dir "$P08_A3_2_STAGE_DIR"
```

If an **identical accepted** stage already exists, point `P08_A3_2_STAGE_DIR` to it; **never overwrite or regenerate it in place**. The run script independently loads canonical TRAIN, authenticates the accepted 50k/10k split and checkpoint, matches all 1,024 index/label/image bytes, validates descriptor CRC/stream origin and trace index 1023. `P07_A4_OFFICIAL_TEST=SEALED` is a workload exclusion for P08, not a change to accepted historical P07 TEST.

## 5. Offline hardware/artifact preflight — one mode at a time

With Vitis/Vivado 2025.2 environment loaded when appropriate, keep **`P03_DIAG_REPORTS` at your actual accepted route-report directory**; it is not contained in this document and must not be guessed. Set the original built candidate directories:

```bash
export P08_A2_BUILD_DIR=/tmp/v3_p08_a2_build_20261018T193149Z
export P08_A2_2_BUILD_DIR=/tmp/v3_p08_a2_2_build_20261018T200133Z
: "${P03_DIAG_REPORTS:?Set your accepted P03.2c routed-report directory}"
```

**A2.1 first example:**

```bash
export P08_A3_2_VARIANT=A2_1
export P08_A3_2_RUN_DIR="$HOME/Thesis_Evidence/p08_a3_2_A2_1_1024_$(date -u +%Y%m%dT%H%M%SZ)"
P08_A3_2_PREFLIGHT_ONLY=YES bash scripts/run_p08_a3_2_1024.sh
```

Expected offline success (no physical files written, no JTAG or DDR):

```text
P07_A4_2A_STAGING_CHECK_PASS=1
P08_A3_2_2_ORIGINAL_TRAIN_FIRST1024_PREFLIGHT_PASS=1
P08_A3_2_2_ELF_DDR_ISOLATION_PASS=1
P08_A3_2_2_OFFLINE_PREFLIGHT_PASS=1
P08_A3_2_2_PHYSICAL_VARIANT=A2_1
P08_A3_2_2_KV260_LATENCY=NOT_RUN
```

Repeat the same commands only after switching to `P08_A3_2_VARIANT=A2_2` and using a **different new `P08_A3_2_RUN_DIR`**. Do **not** choose a directory within Git, or reuse a previous physical folder. The offline preflight checks that its selected Vitis build sources match the unmodified source files; **firmware rebuilding is NOT part of A3.2.2.** If your /tmp original build was deleted, stop and reconcile its absence rather than copying or substituting an untracked ELF.

## 6. Separate physical KV260 capture — only after user-run offline/native PASS

**Dangerous:** `scripts/run_p08_a3_2_1024.sh` will program the accepted PL design, control the Cortex-A53 and overwrite reserved physical DDR `0x40000000..0x43FFFFFF`. Any booted Linux system on KV260 may own this memory. Do **not** access hardware under Linux or attempt to resume a paused Linux kernel. Before **every** separate run physically reboot the KV260 into the accepted **dedicated JTAG-only bare-metal state**; reboot again afterward even on failure. No A3.2 KV260 run has been authorized/attempted automatically by development tools.

After the complete offline preflight for the **specific exact `P08_A3_2_VARIANT` / `P08_A3_2_RUN_DIR`** succeeds, and *only after* the reboot and your separate authorization of DDR overwriting, execute:

```bash
unset P08_A3_2_PREFLIGHT_ONLY
export P08_A3_2_CONFIRM_JTAG_ONLY=YES
export P08_A3_2_CONFIRM_DDR_OVERWRITE=YES
export P08_A3_2_CONFIRM_TRAIN_VALIDATION_ONLY=YES

bash scripts/run_p08_a3_2_1024.sh
```

Both physical paths follow accepted original P03 PS-width diagnosis → original P07 6-region staged DDR readback and SHA pins → route bitstream program → autonomous A53 single dataset session → **original P07 numerical packed replay** → corresponding P08 telemetry validation. Distinct raw captures: A2.1 stores neural journal (1MiB), selected full neural trace (64KiB), image timing (1MiB); A2.2 adds tick timing (3MiB). Both record `physical_identity.txt` with `firmware_variant=A2_1/A2_2`, the pinned SHA256, `scope=TRAIN_DERIVED_VALIDATION_FIRST_1024`, trace index 1023; both retain logs, partial readbacks on faults and hashes. Each run refuses overwrite. Selected first1024 stage reused unchanged.

Only a successful original oracle *and* CRC/time/counter validation permits:

```text
P08_A3_2_2_ORIGINAL_P07_1024_PACKED_ORACLE_PASS=1
P08_A3_2_2_SINGLE_RUN_TIMING_CRC_PASS=1
P08_A3_2_2_SINGLE_1024_PHYSICAL_CAPTURE_PASS=1
P08_A3_2_2_SINGLE_1024_FULL_PHYSICAL_GATE_PASS=1
P08_A3_2_2_PAIRED_BASELINE=NOT_YET_RUN
```

On any failure, preserve the entire run directory (including `attempt_exit_status.txt`, `available_output_sha256.txt`, logs and raw readbacks), investigate and **do not** claim a physical benchmark.

## 7. Paired comparison only once BOTH verified individual run folders exist

```bash
# Run from v3 root on host AFTER TWO independent original oracles pass.
PYTHONPATH="$PWD/src" python scripts/p08_a3_2_pair_check.py \
  --stage-dir "$P08_A3_2_STAGE_DIR" \
  --a21-run-dir "/absolute/path/to/verified_A2_1_run" \
  --a22-run-dir "/absolute/path/to/verified_A2_2_run" \
  --a21-elf "$P08_A2_BUILD_DIR/vitis_workspace/p08_a2_board.elf" \
  --a22-elf "$P08_A2_2_BUILD_DIR/vitis_workspace/p08_a2_2_board.elf" \
  --report "/absolute/new/untracked/path/to/paired_report.json"
```

The pair CLI reruns both original P07 1,024-image packed oracles again and rejects mismatched frame indices, trace identity, A53 frequencies, PL cycles, original event schedules/packet routes or bad CRC. The report includes **frame-paired** `A2.2 - A2.1` service milliseconds and per-stage distributions. It does **not** claim replication or noise confidence from one pair. A3.2.3 (pending user gate) will define and aggregate physically repeated pairs.

## 8. Measurement provenance and limitations

The runner is a narrowed extension of the **user-physically-accepted A3.1** original physical pilot sequence, not a new neural algorithm. The accepted `scripts/p07_a4_2_verify.py` and `vivado/p07_a4_xsdb_prepare.tcl` are authoritative for original packed replay/byte-exact DDR staging. Timing and counter semantics and source references are documented in [A2.2 Timing Methods](P08_A2_2_TIMING_METHODS.md), including Arm Generic Timer behavior and AMD Vitis HLS UG1399 configured/achieved clock cautions.

`CNTFRQ_EL0=99,999,001 Hz` was observed on the **A3.1** board run only; do **not** force that value into future runs. Do **not** interpret 26 hardware PL dispatch-cycle sums as A53 elapsed time. Do **not** combine separate stage medians to estimate full-image latency. **Power and energy remain expressly DEFERRED.**
