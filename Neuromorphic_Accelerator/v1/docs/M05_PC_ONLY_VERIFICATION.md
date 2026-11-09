> **2026-11-09 M05 ACCEPTANCE / M06 HANDOFF:** M05 is accepted at the original bounded FPGA-targeted on-chip neural HLS/RTL simulation scope, not full physically programmed integrated PS/DDR operation. The signed32 rolling HLS CSim/synth/10-transaction XSim and M05.11c shell/controller genuine XSim independent 256-bit trace replay/counters pass; all current HLS/shell/testbench Git blob SHAs match the original owner-accepted sources. See [M05 acceptance review and deferred DDR/AXI gate](M05_ACCEPTANCE_REVIEW_2026_11_09.md). Once final source+docs CI is 5/5 green and PR #79 is merged, start new M06 branch from merged main. **No need to run old D4.2–D4.4 read-only probe to accept the M05 on-chip prototype.** Its original 63 unresolved AXI warnings remain M06 problems to investigate *before* claiming functioning 256→128 DDR transfers. No board/JTAG/DDR write authorization. Earlier M05-pending commands below are historic.

> **LATEST M05.12d.4 combined owner verification, 2026-11-09 UTC:** Accepted genuine owner D4.1b original evidence at ~/Thesis_Evidence/neuromorphic_v1_m05_12d4_readonly_bd_20261109T154700Z_yG0IsT, original checkout 541cc1742c3d20493af381999366d94cf0cfa4a3, intentional exit3 and original 23/11 control/memory interface readback. **Do not rerun D3 or D4.1b just to start.** Pull current PR #79 research branch, compileall + all M01–M05 native tests + focused D4 tests, source Vivado 2025.2, then run **one** bash scripts/run_m05_12d4_protocol_gate.sh "$IP_D3" "$D4_OLD" "$D4_BD", with the exact three accepted original evidence paths defined at [one-run D4.2–D4.4 runbook](M05_12D4_PROTOCOL_GATE_2026_11_09.md). New unique owner folder contains genuine-original 64-warning D4.2 readback/11-pair risk, Vivado read-only sim_1/mem_sc model file discovery (not functional XSim), 382 original generated file pre/post SHA check, D4.4 truthful M05 exit audit and all logs. **exit 3** = all original proofs preserved but generated SmartConnect AXI protocol still BLOCKED; exit 2 = genuine error/corruption. Never force USER widths, overwrite negative evidence, use FPGA board/JTAG/physical DDR, synth, generate bitstream, merge, or start M06.

> **M05.12d.4 D4.1b safe offline original owner procedure, 2026-11-09 UTC:** The owner accepted previous D4.1 original hash inventory exit3 for 64 warnings. Pull current research branch; run python3 -m compileall -q src scripts tests, python3 -m unittest discover -s tests -p 'test_m05_12d4*.py' -v, all M01–M05 regressions, and bash -n scripts/run_m05_12d4_readonly_bd_probe.sh. Source genuine Vivado 2025.2 if necessary, check vivado -version, export IP_D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ" and D4_OLD="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d4_warning_inventory_20261109T152119Z_jBQsxu", then bash scripts/run_m05_12d4_readonly_bd_probe.sh "$IP_D3" "$D4_OLD". It uses a fresh original D4.1b evidence folder and genuine open_project -read_only, produces static node hints, actual 23 interface property readbacks, original 11-net correlation, source SHAs before/after and independent report. **Exit3** means original readback captured but AXI semantics still BLOCKED; **exit2** means original input/tool check failure. Never rerun accepted D3 just to start, overwrite a failed owner folder, touch physical DDR/board or generate deployment bitstreams. See [exact commands](M05_12D4_READONLY_BD_PROPERTIES_2026_11_09.md).

> **NEW D4.1 offline-only host procedure (2026-11-09 UTC):** After pulling current branch, run python3 -m compileall -q src scripts tests, then python3 -m unittest discover -s tests -p 'test_m05_12d4*.py' -v. Run the older M05/M01–M04 regressions as listed below. For genuine D3 provenance inspection only (NO Vivado tool run), set IP_D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ" and run bash scripts/run_m05_12d4_warning_inventory.sh "$IP_D3". This creates NEW original D4 evidence and intentionally returns **exit code 3** with JSON when original hashes pass but unresolved warnings block protocol sign-off; 2 is invalid evidence. Preserve all original D3 folders. See [D4.1 runbook](M05_12D4_WARNING_INVENTORY_2026_11_09.md). Native/CI and actual original evidence are separately classified.

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

Expected: **48 M05 + 22 M04 + 28 M03 + 21 M02 + 20 M01 = 139 named unittest methods**, all PASS. Seeded recurrent-network methods include 12 streaming, 8 state-memory and 6 accumulator test subcases; these do not increase the number of named methods. Native C++ compilation or malformed replies fail; no external GPU, MNIST TEST, Vitis, Vivado or KV260 is needed.

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
  tests/test_m05_stateful.py \
  tests/test_m05_accumulator.py \
  tests/test_m05_hls_setup.py \
  tests/test_m05_hls_path_regression.py \
  hls/m05_stream_eval/prepare_hls_config.py \
  hls/m05_stateful/m05_stateful.hpp \
  hls/m05_stateful/m05_stateful.cpp \
  hls/m05_stateful/m05_stateful_csim_tb.cpp \
  hls/m05_stateful/m05_stateful_hls_config.cfg \
  hls/m05_accumulator/m05_accumulator.hpp \
  hls/m05_accumulator/m05_accumulator.cpp \
  hls/m05_accumulator/m05_accum_csim_tb.cpp \
  hls/m05_accumulator/m05_accum_hls_config.cfg \
  hls/m05_stream_eval/run_m05_offline_hls.sh \
  docs/M05_HLS_OPERATOR_RUNBOOK.md \
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

### HLS path regression (after the operator's first failed Vitis runs)

The first three **genuine** 2025.2 Csim calls all failed before compilation due to **missing source/testbench paths** after Vitis changed directory to the external evidence folder. This is fixed by generating an absolute-path `hls_effective_config.cfg` for each new run, and switching to non-deprecated `package.output.format=rtl`. Check the three dedicated host-only path tests:

```bash
python3 -m unittest discover -s tests -p 'test_m05_hls_path_regression.py' -v
```

All three must pass locally. They simulate Vitis' CWD changes using a **STUB**, not actual HLS, so the next step is to rerun true Csim. Preserve the original failed logs unchanged; see [failure analysis](M05_HLS_CSIM_FAILURE_2026_11_08.md) and [operator runbook](M05_HLS_OPERATOR_RUNBOOK.md).

## 4. Genuine offline Vitis HLS verification for THREE independent tops — not JTAG

**The project assistant cannot run Vitis HLS in this execution environment.** All real C-simulation, synthesis, and C/RTL co-simulation work remains **NOT RUN** until the operator runs it. Follow the comprehensive, tool-checked [M05_HLS_OPERATOR_RUNBOOK.md](M05_HLS_OPERATOR_RUNBOOK.md), which contains version checks, full commands, fresh source/report hashes, stage-by-stage pass criteria, OOC implementation and exact artifacts to share.

After sourcing YOUR Vitis 2025.2 `settings64.sh`, from `Neuromorphic_Accelerator/v1`, start with **three isolated genuine Csim runs**:

```bash
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stream --csim
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stateful --csim
bash hls/m05_stream_eval/run_m05_offline_hls.sh --accumulator --csim
```

Only after each Csim passes:

```bash
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stream --synth
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stateful --synth
bash hls/m05_stream_eval/run_m05_offline_hls.sh --accumulator --synth
```

`--cosim` performs Csim + synth + RTL co-sim; `--impl` further performs **offline OOC**, not an actual KV260 deployment. Each invocation creates its own exclusive evidence directory outside Git and preserves failures. **The three successful isolated IPs would still NOT constitute a connected M05 event-driven accelerator.**

## 5. What to report for your verification

Report the current branch HEAD SHA; M05 native count/PASS or any failing method; prior regression counts; original log/evidence SHA hashes if generated. For genuine offline HLS runs, separately share actual Vitis version, selected part, command, original Csim/synthesis/cosim logs, report SHA and estimated II/latency/LUT/FF/BRAM/URAM/DSP if present.

**Scientific boundary:** this work includes HLS-oriented C++ candidates for local BRAM and exact per-tick accumulation, but native tests do not prove inferred BRAM, full on-chip event routing, a physically bounded future FIFO, global barrier or RTL flow; it does not show DDR virtualization, acceleration, power savings or Loihi/YANA silicon equivalence. M05 remains open and unmerged until the user explicitly authorizes closure. See [M05 source comparison](M05_ENGINE_V3_COMPARISON.md) and [test explanations](M05_TESTS_EXPLAINED.md).
