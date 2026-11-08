# M05 — Independent native PC verification (NO BOARD / no toolchain required)

**Status:** M05 in progress on `agent/neuromorphic-accelerator-v1-m05-sparse-onchip` (draft PR #79). Do not merge until user-native verification **and** explicit approval. User previously accepted M01–M04. M05 is not accepted. No JTAG, AXI/PS-DDR writes, FPGA programming or physical operations are authorized.

## 1. Fetch exact new branch in VS Code Ubuntu terminal

```bash
cd ~/Git/Thesis
git status --short
# Preserve any existing uncommitted work; do not discard it to switch branches.
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip || \
  git switch --track origin/agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD
git status --short
cd Neuromorphic_Accelerator/v1
python3 --version
g++ --version
```

Source-only tests compile the **actual native C++ streaming batch kernel** with `g++` and launch it from a Python timestep/event worklist. The host fallback for `hls::stream` is a `std::queue` functional test shim, not a hardware FIFO. Ensure the Git branch is the M05 branch and the working tree is clean before recording evidence.

## 2. Run all source and numerical regressions

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m05*.py' -v
python3 -m unittest discover -s tests -p 'test_m04*.py' -q
python3 -m unittest discover -s tests -p 'test_m03*.py' -q
python3 -m unittest discover -s tests -p 'test_m02*.py' -q
python3 -m unittest discover -s tests -p 'test_m01*.py' -q
```

Expected: **17 M05 + 22 M04 + 28 M03 + 21 M02 + 20 M01 = 108 named unittest methods**, all PASS. One M05 method loops over 12 deterministic recurrent-network subcases. Native C++ compilation or malformed replies fail; no external GPU, MNIST TEST, Vitis, Vivado or KV260 is needed.

## 2a. Optional native-only smoke of the separate HLS Csim testbench

This compiles the staged HLS vector testbench with `g++`, **not Vitis HLS**. It is an extra testbench-consistency gate, not additional PL proof.

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
mkdir -p "$HOME/Thesis_Evidence"
# Use a new uniquely named output path; do not reuse original test binaries.
SMOKE_DIR="$(mktemp -d "$HOME/Thesis_Evidence/m05_hls_tb_native_XXXXXXXX")"
g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic \\
  -Wno-unknown-pragmas \\
  hls/m04_lif_eval/m04_eval.cpp \\
  hls/m05_stream_eval/m05_stream.cpp \\
  hls/m05_stream_eval/m05_hls_csim_tb.cpp \\
  -o "$SMOKE_DIR/m05_hls_tb_host"
"$SMOKE_DIR/m05_hls_tb_host"
sha256sum "$SMOKE_DIR/m05_hls_tb_host" \\
  hls/m05_stream_eval/m05_hls_csim_tb.cpp
```

Expected: `PASS: M05 isolated stream C simulation oracle vectors` **from a native host executable**, not from Vitis HLS. Preserve any output artifacts; do not execute old v3 hardware scripts.

## 3. Optional immutable original PC evidence

Run **once per new directory**; do not reuse or overwrite any prior evidence or report. This stores native/CI-independent logs, source commit and hashes outside the repository.

```bash
set -euo pipefail
set -C
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
mkdir -p "$HOME/Thesis_Evidence"
export M05_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
export M05_EVIDENCE="$HOME/Thesis_Evidence/neuromorphic_accel_v1_m05_pc_${M05_UTC}_$$"
mkdir "$M05_EVIDENCE" || exit 1

git rev-parse HEAD > "$M05_EVIDENCE/source_head.txt"
python3 --version > "$M05_EVIDENCE/python_version.txt" 2>&1
g++ --version > "$M05_EVIDENCE/gpp_version.txt" 2>&1
sha256sum \
  hls/m04_lif_eval/m04_eval.hpp \
  hls/m04_lif_eval/m04_eval.cpp \
  hls/m05_stream_eval/m05_stream.hpp \
  hls/m05_stream_eval/m05_stream.cpp \
  hls/m05_stream_eval/m05_stream_host_cli.cpp \
  hls/m05_stream_eval/m05_hls_config.cfg \
  hls/m05_stream_eval/m05_hls_csim_tb.cpp \
  src/neuromorphic_accelerator_v1/m05_host_runtime.py \
  tests/test_m05_stream.py \
  docs/M05_ENGINE_V3_COMPARISON.md \
  docs/M05_TESTS_EXPLAINED.md \
  > "$M05_EVIDENCE/source_sha256.txt"

python3 -m unittest discover -s tests -p 'test_m05*.py' -v \
  2>&1 | tee "$M05_EVIDENCE/m05_original_native_tests.log"
python3 -m unittest discover -s tests -p 'test_m04*.py' -q \
  2>&1 | tee "$M05_EVIDENCE/m04_original_regression.log"
python3 -m unittest discover -s tests -p 'test_m03*.py' -q \
  2>&1 | tee "$M05_EVIDENCE/m03_original_regression.log"
python3 -m unittest discover -s tests -p 'test_m02*.py' -q \
  2>&1 | tee "$M05_EVIDENCE/m02_original_regression.log"
python3 -m unittest discover -s tests -p 'test_m01*.py' -q \
  2>&1 | tee "$M05_EVIDENCE/m01_original_regression.log"

sha256sum "$M05_EVIDENCE"/*.log "$M05_EVIDENCE/source_sha256.txt" \
  "$M05_EVIDENCE/source_head.txt" > "$M05_EVIDENCE/evidence_sha256.txt"
cat "$M05_EVIDENCE/source_head.txt"
cat "$M05_EVIDENCE/evidence_sha256.txt"
git status --short
```

If a test fails, **preserve the failed original evidence unchanged** and start a *new* evidence directory for a rerun. CI source checkout and operator-native PC results are separate evidence.

## 4. Optional genuine offline Vitis HLS exploration — not JTAG

This step is **optional**, and has **NOT BEEN RUN by the development agent** because no installed Vitis HLS is available. It requires an appropriate Vitis/Vivado 2025.2 installation and the exact K26 part; no board connection required. Source Vitis settings first with your local installation path, then:

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
export HLS_PART=xck26-sfvc784-2LV-c
# Vitis C-simulation only:
bash hls/m05_stream_eval/run_m05_offline_hls.sh

# Later, if the C simulation succeeds and you elect offline synthesis:
bash hls/m05_stream_eval/run_m05_offline_hls.sh --synth

# Only with a verified synthesizable top and Vitis simulator:
bash hls/m05_stream_eval/run_m05_offline_hls.sh --cosim
```

The runner rejects missing/wrong-version tools, uses a new exclusive-create `$HOME/Thesis_Evidence` output directory, records source SHA and report paths, never touches old v3 staging scripts, and does **not** connect to the KV260. Synthesis success would produce **estimates**, not real post-route timing or actual observed FPGA inference. If Vitis fails, keep the original logs for diagnosis; do not fabricate a PASS.

## 5. What to report for your verification

Report the current branch HEAD SHA; M05 native count/PASS or any failing method; prior regression counts; original log/evidence SHA hashes if generated. For genuine offline HLS runs, separately share actual Vitis version, selected part, command, original Csim/synthesis/cosim logs, report SHA and estimated II/latency/LUT/FF/BRAM/URAM/DSP if present.

**Scientific boundary:** this work does not prove a full on-chip event scheduler, physically bounded FIFO or actual neuron-state BRAM; it does not show DDR virtualization, acceleration, power savings or Loihi/YANA silicon equivalence. M05 remains open and unmerged until the user explicitly authorizes closure. See [M05 source comparison](M05_ENGINE_V3_COMPARISON.md) and [test explanations](M05_TESTS_EXPLAINED.md).
