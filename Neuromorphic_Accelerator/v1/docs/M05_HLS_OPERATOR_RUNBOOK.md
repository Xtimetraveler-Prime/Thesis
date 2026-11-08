> **LATEST FIFTH-TOP STATUS (after 2026-11-08 operator PASS):** Initial rolling-wheel genuine Vitis 2025.2 CSim **PASS** (0 errors, exit 0; `neuromorphic_v1_m05_rolling_csim_20261108T185457Z_144435`). The *source was subsequently changed* to bound startup wheel-memory clears to admitted neuron IDs, with a 2→1→2 consecutive-run HLS testbench regression. This revised rolling source has **native CI verification only**; rerun **genuine CSim and HLS synthesis together** with `bash hls/m05_stream_eval/run_m05_offline_hls.sh --rolling --synth` (cumulative stages, new evidence folder), then inspect top `m05_rolling_replay_csynth.rpt` before any `--rolling --cosim`. The previous fourth integrated co-sim report shows **Pass**, latency min/avg/max **8463/10572/16396 cycles**, interval **8489/11300/16416 cycles**, total **42363 cycles**, **NOT physical network throughput**. More at [rolling design and exact report requests](M05_ROLLING_WHEEL_DESIGN_2026_11_08.md).
>
> **LATEST 2026-11-08:** The *fourth* **integrated 8-tick** HLS top now also has a genuine Vitis 2025.2 CSim + HLS csynth + XSim C/RTL cosim **PASS** on the operator workstation. HLS estimates: 8.002 ns / 5,914 LUT / 3,122 FF / 6 DSP / 74 BRAM18K; top-level latency unknown. The original cosim report remains available locally but **not yet analyzed for transaction latency**. See [original evidence path and scope](M05_ROLLING_WHEEL_DESIGN_2026_11_08.md). A *fifth*, separate [rolling-wheel candidate](../hls/m05_rolling/m05_rolling.cpp) is now native-tested only, with 72 M05 +91 accepted = **163 native tests** and five native-compiled benches; real Vitis proof **not yet obtained**. The prior commands/status sections below are historical for earlier IPs.
>
> **NEXT operator Vitis gate for new rolling top** (after pulling branch, with Vitis 2025.2 sourced and no board operations): `bash hls/m05_stream_eval/run_m05_offline_hls.sh --rolling --csim`. Stop on first failure; preserve the fresh `Thesis_Evidence` path. Only after this PASS consider `--rolling --synth`, resource inspection and `--rolling --cosim`. The new rolling wheel admits delays **1–8** and runs up to **64 ticks** (not continuous); late errors invalidate prior speculative trace rows. [Contract](M05_ROLLING_WHEEL_DESIGN_2026_11_08.md).

# M05 Vitis HLS 2025.2 offline operator verification (KV260/K26, NO BOARD)

**Current scope:** Three independent, project-owned **HLS-oriented C++ candidate IPs** in `Neuromorphic_Accelerator/v1/hls/`: `m05_stream_eval` (stateless per-neuron update), `m05_stateful_service` (persistent 1,024-row neural state/config memory with exact-once per-ID/tick guard), and `m05_event_accumulator` (signed i64 per-neuron coalescing, 4,096 individual contributions/tick with SEALED readout and sticky overflow). They are **not yet joined into a complete PL scheduler**. On 2026-11-08 the **operator** ran and reported genuine Vitis HLS CSim, HLS synthesis, and XSim C/RTL co-simulation **PASS for all three standalone tops**, with reports and evidence paths cataloged in [the real HLS evidence summary](M05_REAL_HLS_RESULTS_2026_11_08.md). The assistant has not run Vitis locally; there has been no integrated simulator or physical KV260 action.

This runbook uses Vitis HLS **2025.2** and K26 part **`xck26-sfvc784-2LV-c`** with a **10 ns requested clock, 12% uncertainty**. These are goals, not achieved timing/area. Original source and reports live in new exclusive-create directories under `$HOME/Thesis_Evidence`, never tracked/overwritten in Git. Do NOT run old v3 JTAG/DDR scripts. No Vivado Hardware Manager/device programming here.

> **LATEST PASS STATUS (after the originally failed attempts):** The three retried genuine CSim benches **all passed**, three individual RTL syntheses **all passed**, and three individual XSim C/RTL cosimulations **all passed** on the operator's Vitis 2025.2 installation. See [exact original evidence directories, resources and scope](M05_REAL_HLS_RESULTS_2026_11_08.md). The older failure diagnosis below is historical and explains the corrected absolute-path generator. **Do not confuse independent IP PASS with a completed M05 on-chip event scheduler.**
>
> **Next engineering work:** PL event routing/scheduling and state/accumulator integration, full-system temporal parity. OOC implementation is optional and does not substitute for an integrated RTL bench.

## 2026-11-08 real HLS failure and fix — review before rerunning

The operator ran all three **genuine** Vitis v2025.2 Csim commands on M05 source commit `6f5ca78a`; **all three failed** with `HLS 200-2001` (source and testbench not found) then `HLS 200-627` (no C testbench). This occurred because Vitis changed into the external `Thesis_Evidence` directory before resolving project-relative `syn.file`, `tb.file` and `-I` paths. The Vitis logs also confirmed `syn.output.format` is **deprecated** and should be `package.output.format`. Those failures prove **a configuration defect**, not faulty neural arithmetic; **no neuron logic reached Vitis CSim**. Preserve all three old failure folders unchanged. See [original failure analysis](M05_HLS_CSIM_FAILURE_2026_11_08.md).

**Fix on the same branch:** each new run generates and saves `hls_effective_config.cfg` beside its original evidence logs, containing verified **absolute** paths for every C++ source, testbench, and include directory. All Csim, synthesis, cosim and OOC commands now receive this effective config. The helper refuses a missing file or overwriting another run's config. `package.output.format=rtl` is used. The local mock-Vitis regression exercises the exact *directory change* and tests all 3 tops; it is **not genuine HLS evidence**.

After pulling the new branch, check:

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m05_hls*.py' -v
```

The three genuine `--csim` commands in section C are **the next required operator validation**. Start with the stream top; stop at the first failure, upload the new original log and `hls_effective_config.cfg`. Do not proceed to synthesis until ALL three genuine Csim logs pass.

## New M05 integrated finite-horizon IP — fourth top, not covered by prior genuine HLS PASS

The first connected **PL-oriented** scheduler + LIF datapath is now source-staged at [`m05_integrated_replay`](../hls/m05_integrated/m05_integrated.cpp). A single run has resident synapses and state, 8 future-tick aggregate buckets, recurrent positive delays, a 4096-individual-deliveries-per-tick cap, output buffer with failure suppression, and complete ticks without host orchestration. **12 new native test methods PASS; no genuine Vitis tool results exist yet for THIS new top.** [Detailed contract](M05_INTEGRATED_FINITE_HORIZON_DESIGN.md).

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m05*.py' -v  # expect 60
# Source your installed Vitis 2025.2 if needed, then:
export HLS_PART=xck26-sfvc784-2LV-c
bash hls/m05_stream_eval/run_m05_offline_hls.sh --integrated --csim
# AFTER successful genuine integrated CSim ONLY:
bash hls/m05_stream_eval/run_m05_offline_hls.sh --integrated --synth
# AFTER successful synthesis and resource inspection ONLY:
bash hls/m05_stream_eval/run_m05_offline_hls.sh --integrated --cosim
```

Stop and send the new `01_csim.log`/`02_csynth.log`/`03_cosim.log` on the first failing stage. Do not claim the prior standalone co-sims establish integrated RTL equivalence. This is a bounded finite-run prototype: **continuous temporal queueing, live backpressure and physical placement remain open**.

## A. Prepare VS Code Ubuntu terminal

```bash
cd ~/Git/Thesis
git status --short                   # check for uncommitted work; preserve it
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip || \
  git switch --track origin/agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1

python3 --version
g++ --version
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m05*.py' -v
python3 -m unittest discover -s tests -p 'test_m04*.py' -q
python3 -m unittest discover -s tests -p 'test_m03*.py' -q
python3 -m unittest discover -s tests -p 'test_m02*.py' -q
python3 -m unittest discover -s tests -p 'test_m01*.py' -q
```

Expected source-only count **60 M05 + 22 M04 + 28 M03 + 21 M02 + 20 M01 = 151 named unittest methods**; there are additional randomized subcases. Four staged Vitis bench files are also compiled and executed **natively** by CI, but that is not Vitis Csim or C/RTL evidence.

## B. Load Vitis 2025.2 tools (example; adjust INSTALL_ROOT)

Find your real `settings64.sh` using your system's Vitis installation location. Do **not** copy the placeholder literally:

```bash
# EXAMPLE if your installation is /tools/Xilinx/Vitis/2025.2:
source /tools/Xilinx/Vitis/2025.2/settings64.sh

# Verify commands are actually available in THIS terminal
command -v vitis-run
command -v v++
vitis-run --version
v++ --version
echo "$XILINX_VITIS"
pwd  # should end in Neuromorphic_Accelerator/v1
```

If Vitis is installed at `/opt/Xilinx/Vitis/2025.2`, change the source path accordingly. `vivado -version` is optional; no board access is needed. If either Vitis executable is missing, stop, share your tool path/version output, and do not claim an HLS PASS.

## C. Phase 1 — **Genuine** Vitis C simulation, one independent top at a time

The repository script performs **real** `vitis-run --mode hls --csim`, checks Vitis 2025.2/part/source config, generates `hls_effective_config.cfg` with absolute paths for all design/testbench files and headers, and writes originals to a newly created `$HOME/Thesis_Evidence` folder. It **does not** silently run a Python substitute.

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
export HLS_PART=xck26-sfvc784-2LV-c

# C++ stateless neuron evaluator: M02 correctness + AXIS candidate
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stream --csim

# Persistent on-chip 1K neuron state/config store candidate
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stateful --csim

# Exact signed event accumulator and seal/overflow contract
bash hls/m05_stream_eval/run_m05_offline_hls.sh --accumulator --csim
```

**Stop if a command exits nonzero.** Keep its original evidence folder, including `01_csim.log`, `result.txt`, `source_sha256.txt`, `tool_version.txt` and `commit.txt`. Share that failure before continuing. All 3 Csim results should show the individual testbench PASS and tool process success; a native `g++` PASS is insufficient.

For the first review, sending only the outputs from these **three Csim commands** is ideal. Actual synthesis may expose interface and arithmetic restrictions that we must resolve.

## D. Phase 2 — HLS synthesis (only after Csim passes)

Each command creates a **fresh** evidence folder, reruns its C simulation and then executes the AMD documented `v++ -c --mode hls` flow.

```bash
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stream --synth
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stateful --synth
bash hls/m05_stream_eval/run_m05_offline_hls.sh --accumulator --synth
```

**Required assessment (each top separately):** report actual **estimated clock period, requested 10ns, achieved loop II, min/max latency, LUTs, FFs, DSPs, BRAM_18K/BRAM_36K, URAM** and complete tool warning/error list. A `PIPELINE II=1` pragma is *only a directive*. For stateful/accumulator tops, confirm that RAM binding actually inferred BRAM rather than treating the entire array as registers or eliminating it. If synthesis fails, capture the error and do **not** assume the design meets M05. No LUT/throughput speedup claims should be made from C++ test times.

## E. Phase 3 — C/RTL co-simulation (only after successful synthesis)

Commands each rerun Csim and synthesis in a new evidence folder and then execute **`vitis-run --mode hls --cosim`**:

```bash
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stream --cosim
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stateful --cosim
bash hls/m05_stream_eval/run_m05_offline_hls.sh --accumulator --cosim
```

Require all expected response values, correct order, invalid/duplicate handling and no unexpected deadlock. **Check both testbench PASS and actual RTL cosimulation summary PASS**; the testbench itself can pass natively while the RTL sim fails. If the HLS interface protocol introduces TLAST/framing, wide struct packing, ap_ctrl_hs start/done or backpressure limitations, capture original wave/log and revise source; do not silently waive those issues.

## F. Optional Phase 4 — Offline OOC Vivado implementation

This is **NOT** board programming, and **NOT** integrated system-level routed timing. Only after C/RTL co-sim success, if you choose to evaluate single-IP place/route:

```bash
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stream --impl
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stateful --impl
bash hls/m05_stream_eval/run_m05_offline_hls.sh --accumulator --impl
```

Each `--impl` run independently repeats Csim, synthesis and C/RTL cosim first. Report **OOC WNS, target clock, resource utilization, tool version/part** separately from HLS estimates, and always label them "isolated IP OOC", **not a complete accelerator or physical KV260 result**.

## G. Evidence collection and how to share results

Every command prints a new directory like:
`$HOME/Thesis_Evidence/neuromorphic_v1_m05_stream_csim_YYYYMMDDTHHMMSSZ_PID`

To list your original runs:

```bash
find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
  -name 'neuromorphic_v1_m05_*' -print | sort
```

Pick a single folder of interest and **substitute its actual path** (do not guess it):

```bash
export M05_RUN="$HOME/Thesis_Evidence/PASTE_ACTUAL_FOLDER_NAME_HERE"
cat "$M05_RUN/commit.txt"
cat "$M05_RUN/top.txt"
cat "$M05_RUN/part.txt"
cat "$M05_RUN/tool_version.txt"
cat "$M05_RUN/mode.txt"
cat "$M05_RUN/result.txt"
cat "$M05_RUN/report_paths.txt"
cat "$M05_RUN/report_sha256.txt"
cat "$M05_RUN/log_sha256.txt"
find "$M05_RUN" -type f \( -name '*_csynth.rpt' \
  -o -name '*cosim*.rpt' -o -name 'syn_report*.xml' \) -print
```

**Send:** the terminal summary and any **complete original** `01_csim.log`, `02_csynth.log`, `03_cosim.log`, or `04_ooc_impl.log` actually produced. For completed synthesis, share the complete `*_csynth.rpt` (or its actual report filename) and `report_paths.txt`. For errors, paste the first error **plus preceding warnings and source/line context**, not only the last `ERROR:` line. Include the `commit.txt`, `source_sha256.txt`, `hls_effective_config.cfg`, and `effective_config_sha256.txt` so we can confirm exactly which source and resolved paths Vitis received. You can upload selected logs/report files; entire build directories/bitstreams are unnecessary.

**Safety:** do not give me private credentials or machine-specific tokens, and do not perform JTAG or DDR writes. Retain failed evidence unchanged and rerun in a new directory after any source correction.

## H. Honest gate interpretation and next engineering choices

Passing all three independent HLS cores at Csim/csynth/cosim would **advance M05.1 and the standalone subcomponents of M05.2/M05.3/M05.4**. It would **not yet close M05** because there is currently no integrated PL event router/positive-delay scheduling FIFO/ready-valid backpressure test between the three cores, no end-to-end hardware tick barrier, and no physical state-cache residency controller. The *host* scheduler continues to provide those semantics today.

Next system-level work must integrate the three components and enforce exactly-once evaluation, zero/bias/nonzero-voltage wakeups, all delayed self/parallel synapses, full W16 current coalescing, 4,096 cap with sticky invalid-run handling, and no partial publication on overflow. Only a **full end-to-end** simulation against accepted M02 traces and a reproducible hardware-resource/performance report can satisfy final M05. Until then, **M05 stays OPEN / draft PR #79 UNMERGED**. Physical KV260 deployment requires separate explicit authorization.

### Official 2025.2 tool basis

- AMD UG1399 `vitis-run --mode hls --csim`, `v++ -c --mode hls`, `vitis-run --mode hls --cosim`, and `--impl`: https://docs.amd.com/r/2025.2-English/ug1399-vitis-hls/vitis-v-and-vitis-run-Commands
- 2025.2 HLS config keys/flow: https://docs.amd.com/r/2025.2-English/ug1399-vitis-hls/HLS-Config-File-Commands
- HLS internal RAM binding: https://docs.amd.com/r/2025.2-English/ug1399-vitis-hls/pragma-HLS-bind_storage
- AXIS stream interface semantics: https://docs.amd.com/r/2025.2-English/ug1399-vitis-hls/Interfaces-for-Vitis-Kernel-Flow
