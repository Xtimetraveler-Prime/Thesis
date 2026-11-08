# M05 evaluation-engine evolution — hardware-verified optimization ledger

**Maintainer contract:** append a new row whenever the scheduler, LIF arithmetic, memory layout, admission limit, kernel I/O contract, or testbench changes. Tie each observation to **the exact Git commit and local Vitis evidence directory**, keep raw logs outside Git in `~/Thesis_Evidence`, and distinguish native/CSim/synthesis/XSim/OOC/place-and-route/board proof. This is the canonical evaluation-engine historical record; the roadmap is a condensed milestone status. No dates/result lines should silently overwrite earlier measurements.

**Last updated:** 2026-11-08. **Branch:** `agent/neuromorphic-accelerator-v1-m05-sparse-onchip`, draft PR #79, UNMERGED. K26 device `xck26-sfvc784-2LV-c`, Vitis HLS 2025.2, 10 ns requested clock. All HLS source snapshots except the newest documentation/audit script are preserved as commits in this branch; historic `Loihi_Digital_Twin/v3` stays frozen.

## A. Why the engine evolved

| Phase | Architectural decision | New capability | Quantified limitation / tradeoff |
| --- | --- | --- | --- |
| Standalone M05 components | Independent streaming scalar LIF, stateful 1,024-neuron RAM service, signed event accumulator | Proved reusable neuron math, storage inference and event admission in separate synthesizeable interfaces | **Not** a fused neural engine or a sum-of-area resource claim |
| Fused finite-horizon `m05_integrated_replay` | One HLS top loads neurons and synapses, schedules positive-delay recurrent events, advances logical ticks autonomously and **doesn't emit until entire run succeeds** | 1–8 ticks, max 1024 neurons / 4096 edges / 4096 deliveries/tick, direct M04 exact LIF semantics | Full eight-tick temporal current memory and eight-tick trace memory retained per call; `ap_start` resets on each run; generated logic is not physically validated |
| Rolling signed-i64 `m05_rolling_replay` | Replace per-run trace buffer with per-tick scratch/output; reuse 8 temporal wheel slots `t % 8`; ordered external ingress | Up to **64 ticks** per run at constant future-current memory size; full sparse/touch/count semantics | New **delay 1–8 only**, sorted input precondition; earlier tick rows become provisional until final status, requiring host to drain concurrently and discard all on late failure |
| Scoped wheel initialization | Initialize only `8 × neuron_count` active temporal cells instead of unconditional `8 × 1024`; test 2→1→2 successive runs | Reduces initial memory-clear work for small networks | Allocated BRAM width and depth unchanged; actual speedup unmeasured, and HLS loop schedule/top-level II remain variable |
| Signed-i32 current wheel | Prove 4096 arrivals/tick of signed W16 terms fit exact signed28 range; store wheel in **signed32** but retain signed64 M04 request semantics | Halves current-wheel physical bits; exact +134213632 / −134217728 legal extremes passed native **and actual C/RTL cosim** | 14 BRAM18K block reduction observed; no absolute runtime speedup established; any larger future delivery bound/term width invalidates proof |
| M05.5 host trace commit gate | Stage and validate streamed tick rows, expose to caller only after `ap_done` and final status==0, abort on error/timeout | Fail-closed publication at **host model** level; 65,536 max rows; model stall/rollback tests | CPU-only; not a synthesized AXIS sink, DMA, PS interface, RTL `TREADY` stall proof or actual hardware reset/retry |
| Evidence audit & comparison discipline (new) | Parse local Vitis reports, retain exact commit/source/testbench hashes, display synthesis/XSim separately | Reproducible comparisons and explicit warnings for changed testbenches | No new RTL optimization; user still must run real Vitis/physical tools; parsing a text report is not independent timing verification |

## B. Direct HLS top-level comparison (not physical utilization)

All values below are from **real operator-run Vitis 2025.2 HLS synthesis** on K26. The estimate is a reported HLS clock-period estimate, **not** placed-and-routed actual clock.

| Version | Verified source Git commit | Max ticks | Max recurrent delay | BRAM18K | LUT | FF | DSP | Estimated clock period |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Fused i64 finite-horizon | `6850593a7416e1b6d4e8185e58925c157237098b` (source as integrated HLS evidence; verify original `commit.txt`) | 8 | Any positive; beyond horizon dropped | **74** | **5,914** | **3,122** | **6** | **8.002 ns** |
| Rolling signed-i64, scoped initialization | `984f5baf45ce771e94e1e8b2947e1ef27ccc6d58` (synthesis) / `03c3fbc5f8866c44510ff67d2cce8151988fa4d7` (C/RTL, identical rolling kernel source) | 64 | 8 | **53** | **10,083** | **8,459** | **2** | **8.244 ns** |
| Rolling signed-i32, same LIF semantics | `827f719778472da39ffa294b431ee848fe360529` (synthesis) / `07913bbf925e5cd1ffc0d84dd6f9d5b4c2ee519a` (C/RTL, identical rolling kernel source) | 64 | 8 | **39** | **9,956** | **8,346** | **2** | **8.256 ns** |

**Important commit-provenance qualification:** the original **integrated synthesis `commit.txt` was not pasted with its full report** into this conversation; the entry identifies a known early integrated-source commit, but it is **not guaranteed to be the exact original synthesized checkout** until the operator reads `commit.txt`. The two rolling synth and cosim commits are directly supplied in operator reports, and the `m05_rolling.cpp` Git blob SHA was verified unchanged between each pair. Do not claim that any report used a different SHA than its `commit.txt`.

**Resource changes:**
- Fused→rolling i64: **−21 BRAM18K (74→53)**, **+4,169 LUT (5,914→10,083)**, **+5,337 FF (3,122→8,459)**, **−4 DSP (6→2)**. The architectures have different run-length/delay constraints, so this is a Pareto comparison, not proof of universally superior throughput or features.
- Rolling i64→rolling i32: **−14 BRAM18K (53→39, −26.4%)**. All 14 blocks came from `current_U` changing **30→16 BRAM18K** (8,192 words ×64→×32 bits); LUT **10,083→9,956** (−127), FF **8,459→8,346** (−113), DSP **2 unchanged**. Estimated clock **8.244→8.256 ns (+0.012 ns)**, both below the 10 ns requested target.
- Fused→i32 rolling: **−35 BRAM18K (74→39, −47.3%)**, with the known increase in LUT/FF, shorter supported maximum delay and provisional output tradeoff.

## C. Genuine XSim C/RTL transaction reports

These report **whole-testbench transaction latencies**. They differ in network sizes, event counts and transaction count. **Never divide or compare averages as a per-neuron or per-tick speedup.** The C/RTL report is not physical board throughput. All runs used the nominal 10 ns simulated clock.

| Top/version | C/RTL evidence provenance | Testbench transactions | Latency min/avg/max (cycles) | Interval min/avg/max (cycles) | Testbench total (cycles) | Verified |
| --- | --- | ---: | --- | --- | ---: | --- |
| Fused i64 8-tick | `~/Thesis_Evidence/neuromorphic_v1_m05_integrated_cosim_20261108T164737Z_86835` | Unconfirmed individual count; report has cumulative transactions | 8463 / 10572 / 16396 | 8489 / 11300 / 16416 | 42363 | Verilog PASS, post-check PASS |
| Rolling i64 | Operator-supplied successful cosim at `03c3fbc5f8866c44510ff67d2cce8151988fa4d7` | **8** | 265 / 3616 / 16492 | 285 / 3919 / 16512 | 29077 | Verilog PASS, 8/8 post-check PASS |
| Rolling i32 | `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_cosim_20261108T194952Z_176120`, commit `07913bbf925e5cd1ffc0d84dd6f9d5b4c2ee519a` | **10** | **265 / 6328 / 17225** | **285 / 6869 / 17248** | **63463** | Verilog PASS, 10/10 post-check PASS |

The **i32 rolling** testbench additionally covers a full 64-tick independently calculated dense trace; 4096 × +32767 events at one tick; 4096 × −32768 at another; 4096 delayed recurrent parallel synapses; 2→1→2 network-size restart; late overflow/ordering errors. Hence the larger average is **not evidence** the arithmetic optimization slowed the engine.

## D. Evidence locations and reproducible local audit

Raw Vitis reports, timestamps, CSim/synthesis/XSim stage logs and original hashes remain exclusively in operator-local `~/Thesis_Evidence`, **not the repository**:

- Integrated CSim: `neuromorphic_v1_m05_integrated_csim_20261108T161418Z_84650`
- Integrated synthesis: `neuromorphic_v1_m05_integrated_synth_20261108T164348Z_85611`
- Integrated XSim C/RTL: `neuromorphic_v1_m05_integrated_cosim_20261108T164737Z_86835`
- Rolling i64 synth: use original `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_synth_*` directory with commit `984f5baf45ce771e94e1e8b2947e1ef27ccc6d58` (do not assume latest wildcard picks an old version).
- Rolling i32 synth: `neuromorphic_v1_m05_rolling_synth_20261108T193909Z_169727`
- Rolling i32 cosim: `neuromorphic_v1_m05_rolling_cosim_20261108T194952Z_176120`
- Rolling i64 cosim: operator's earlier evidence folder, inspect original `commit.txt` for identity.

New Python audit: [`scripts/m05_hls_evidence_audit.py`](../scripts/m05_hls_evidence_audit.py). It accepts **one or more original rolling synth/cosim evidence directories**, rejects explicit nonzero exit status, wrong top/target, malformed report, or XSim Pass without matching finish log, and displays source/TB hashes when present. It does **not** modify original logs and includes **11 synthetic-fixture tests** to protect the parser.

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
python3 scripts/m05_hls_evidence_audit.py --markdown --evidence \
  "$HOME/Thesis_Evidence/neuromorphic_v1_m05_rolling_synth_20261108T193909Z_169727" \
  "$HOME/Thesis_Evidence/neuromorphic_v1_m05_rolling_cosim_20261108T194952Z_176120"
```

If both original `source_sha256.txt` manifests are present, compare testbench hashes to decide whether per-case HLS co-sim timing comparisons are remotely meaningful. Even identical testbench code hashes do NOT prove identical datasets or injected stalls unless workload manifests and seeds are also fixed.

## E. Genuine post-route OOC feasibility — 2026-11-08

**New operator result received after the i32 C/RTL PASS: actual offline Vivado 2025.2 out-of-context implementation PASS.** This is the first **placed-and-routed hardware-design estimate** in the M05 evaluation-engine evolution, NOT a result measured on a physical FPGA.

- **Original evidence:** `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_impl_20261108T200432Z_186026`, checkout commit **`334ca0ee78c2651019d72101f23f253b62396aed`**, `exit_status=0`. The `m05_rolling.cpp` kernel remains identical to the earlier i32 HLS/XSim-verified source. `--rolling --impl` ran cumulative genuine CSim, HLS synthesis, XSim and Vivado implementation; only the **impl and routed summary** were quoted in this operator reply, so don't manufacture any unquoted per-stage results.
- Vivado `export_impl.rpt`: **required 10.000 ns**, **achieved after place-and-route 6.503 ns**, **WNS +3.497081 ns**, **WHS +0.055000 ns**, **TPWS 0.000000 ns**, **0 unrouted nets**. `CP achieved post-synthesis: 4.963 ns`; route-induced change is expected and **not a physical throughput figure**.
- **Post-implementation resources:** **6,257 LUT, 6,887 FF, 35 BRAM, 2 DSP, 0 URAM, 162 SRL, 1,215 CLB**. This area is a different compilation stage and shouldn't be presented as though it were the HLS 9,956 LUT / 8,346 FF / 39 BRAM estimate. The achieved utilization reports were for the K26 stand-alone **out-of-context** HLS IP; the PS, clocks/reset, shell, interconnect, DMA, DDR, and board constraints are not incorporated.
- Tool reported **zero critical warnings/errors** and failfast design metrics **all OK**, with 2 other warnings not enumerated in the pasted log. Actual routed path-detail and timing summary files exist under `work/hls/impl/verilog/report/` and `work/hls/impl/verilog/project.runs/impl_1/`; inspect them before claiming all specific interface paths are constrained.

### Synthesis-vs-placement results for the SAME optimized i32 rolling kernel

| Gate | Clock metric | LUT | FF | BRAM18K | DSP |
|---|---|---:|---:|---:|---:|
| Vitis HLS synthesis estimate | 8.256 ns estimated | 9,956 | 8,346 | 39 | 2 |
| Vivado OOC **routed** implementation | **6.503 ns achieved** (10 ns required) | **6,257** | **6,887** | **35** | **2** |

### Interpretation and next gate

This demonstrates a technically credible **routed neuromorphic evaluation-engine IP** on the target FPGA family with useful resource headroom. It does **not** establish a viable PS/AXI integration, physical input stream feed, sustained throughput, or reliable backpressure. The next new test must drive actual synthesized Verilog **`trace_TREADY` stalls** and **input `TVALID` gaps**, asserting data/VALID stability and complete handshake-ordered trace. The verified kernel will not be edited for this gate. A dedicated offline XSim testbench/launcher is located at [`rtl_stress/tb_m05_rolling_axis_stress.sv`](../hls/m05_rolling/rtl_stress/tb_m05_rolling_axis_stress.sv) and [`scripts/run_m05_rolling_rtl_stress.sh`](../scripts/run_m05_rolling_rtl_stress.sh); **Genuine direct RTL stress result PENDING operator execution**, not equivalent to prior Vitis HLS co-sim.

### M05.6 first genuine direct XSim attempt — testbench compilation failure (2026-11-08)

**Operator attempted direct generated-RTL AXIS stall test** using known routed kernel evidence `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_impl_20261108T200432Z_186026`, testbench checkout `c6ac13e114037db513c21af82175595ef540244b`, new evidence `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_20261108T203112Z_209004`: `exit_status=1`. Tool successfully derived *real generated IP* AXI-Lite offsets from `work/hls/.autopilot/db/driver/src/xm05_rolling_replay_hw.h`, and `xvlog` analyzed all generated Verilog. **Xvlog rejected the NEW SystemVerilog testbench at line 305**, `[VRFC 10-4982] syntax error near '"trace=24; ...' `. Cause: two adjacent `$display` format strings were written on consecutive lines as C-style implicit concatenation, which is not valid SystemVerilog syntax. **No XSim elaboration or RTL handshake simulation occurred**; this is NOT a DUT algorithm, routed timing or AXIS ready/valid failure.

**Fix:** keep the verified `m05_rolling.cpp` kernel, original implementation evidence and AXI register map unchanged; rewrite the one `$display` to contain one format literal in `hls/m05_rolling/rtl_stress/tb_m05_rolling_axis_stress.sv`; add native regression `test_no_adjacent_format_string_literals_in_xvlog_stressbench`. The repaired source must be retested by actual `xvlog → xelab → xsim` on operator's machine before M05.6 can be declared PASS. Native/static CI is NOT proof the simulator can elaborate the generated IP. Preserve both old failure and future new evidence directories.

### M05.6 completed directed output-backpressure RTL test (2026-11-08)

Operator reran the direct generated-Verilog testbench with the repaired format
string, using **unchanged** signed32 HLS source previously verified by routed
out-of-context implementation. Original test evidence
`~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_20261108T203635Z_212333`
ended **`exit_status=0`**: `xvlog` analyzed generated HDL and bench,
`xelab` built `m05_rolling_axis_stress_snapshot`, and XSim verified the
exact **24-row** trace for a two-neuron/12-tick delay-8 recurrence. Actual
`trace_TREADY` stalls: **188 cycles**, verified stable VALID/TDATA and
order, final status 0. The test inserted **1,162 input-valid gap cycles**
but recorded **N/S/E input stall cycles 0/0/0**; therefore this is direct
**output** AXIS-backpressure proof only, not full duplex or randomized stall
coverage. The result is simulated RTL, not physical PS/PL/DMA timing.

**Caveat exposed by this real run:** XSim printed warnings that Vitis
generated `./m05_rolling_replay_*.dat` initialization files could not be
opened from the new simulator working directory. These did not make the 24-row
test fail but may leave RAM uninitialized in wider workloads. Follow-on source
development added `scripts/m05_rtl_meminit.py` to stage only original
tool-generated RAM images from the existing `--impl` evidence, preserving
original source SHA256 and failing closed on missing/conflicting assets. No
dummy `.dat` contents are permitted. The new stressbench primes input VALID
before start and checks stable incoming TVALID/TDATA under genuine TREADY
stalls, requiring >=10 input-stall cycles. Native regressions cover asset
provenance and signal assertions; **new strengthened direct RTL XSim run
NOT YET PERFORMED**. Both the earlier failed syntax attempt and this first
passed output-stall run remain distinct evidence entries.

### M05.6 input-stall coverage miss; M05.7 separates the genuine-proof baseline (2026-11-08)

**Operator's new genuine XSim result:** `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_20261108T205357Z_221064`, `exit_status=1`. Strict RAM-init staging successfully copied **11 exact generated .dat files** with SHA256 provenance; no previous missing-RAM warning. Actual generated RTL `xvlog` and `xelab` PASS; XSim ran to **12170 ns** but stopped at **`Fatal: RTL_STRESS_FAIL no meaningful incoming AXIS backpressure`** (bench line 345). This happens after the existing 24-row output/status assertions; **there is no reported spike, membrane-voltage, trace-order or routed timing fault**. The 2-neuron, 1-edge, 1-event source contains too few prestart packets to force a measured `TVALID && !TREADY` inbound stall. XSim itself may print `exit 0` after SystemVerilog `$fatal`; the runner was correct to mark the run FAILED due to absent required final PASS marker.

**Design review and regression-preserving response:**
- Return the original `tb_m05_rolling_axis_stress.sv` to Git blob SHA `c2831bc2953b41066ac4ba83afb75fdeda13c15a`, the exact original **real XSim PASS** source (24 rows, 188 output stalls). Do **not** retroactively mark the earlier output-only verified test failed.
- Create **separate** `tb_m05_rolling_axis_ingress_stress.sv`: 64 input-neuron packets, 12 ticks, **768 golden trace rows**, 1 delay-8 recurrent edge, 1 external event, 300 prestart cycles, explicit input VALID/TDATA hold checks, **>=10 real inbound stalls required**, original output TREADY stall monitor retained. This is a **NEW testbench**, so its RTL result is **PENDING**.
- New runner optional `--ingress` selects the separate simulator module, keeps per-test mode plus SHA256 manifest in fresh `~/Thesis_Evidence`, fails on `Fatal: RTL_STRESS_FAIL` even when XSim exits zero, and keeps the 11 generated .dat asset gate for both test modes.
- The previously established **signed32 evaluation kernel** `m05_rolling.cpp` (Git blob `e5443aa87dcc8819ee8aa680b6ca105facc1aced`), HLS CSim, XSim C/RTL post-check and genuine 6.503 ns post-route 35-BRAM OOC proof are **unchanged**; changes involve only testbenches and verification tooling.
- [M05.7 runbook](M05_INGRESS_BACKPRESSURE_GATE_2026_11_08.md) contains failure triage, reproducible old-vs-new tests and commands. If 64 inputs still do not stall, inspect actual Vitis-generated regslice/FIFO depth and READY waveform. Don't silently reduce the required 10-cycle input stall threshold, alter HLS kernel to force a test PASS, or infer a hardware issue from a test-coverage miss.

### M05.7 verified bidirectional directed AXIS stall gate (2026-11-08)

Operator ran the **64-neuron direct generated-Verilog XSim ingress** scenario,
source checkout `809f6f7aa2add553708e93e9741b69e28b2d263c` (or its
identical bench SHA), evidence directory
`~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_20261108T210506Z_227783`,
`exit_status=0`, `stress_mode=ingress`. Genuine Vitis HLS 2025.2
generated RTL: `xvlog` PASS, `xelab` PASS, `xsim` **PASS**.
The 11 genuine RAM-init `.dat` files were staged with checksum manifest
(no missing-file warnings). Exact XSim output:

```text
INFO: M05 ingress prestart accepted N/S/E=2/1/1; stalls N/S/E=283/0/0; pending neurons_TVALID=1 neurons_TREADY=0
PASS: M05 REAL RTL AXIS INGRESS stall stress N=64 E=1 S=1 T=12; trace=768; stalled_output_cycles=7573;ingress_gap_cycles=16762; input_stalls N/S/E=312/0/0; final_status=0
```

The two-synapse/single-event baseline is unchanged and earlier output test
also PASS (24/24 rows, 188 output stalls). Current new hardware evidence
therefore demonstrates **actual neuron-side READY backpressure plus trace
output READY backpressure under one directed workload**, with 768 exact
ordered output records and final status 0. The synapse and external ports
each only supplied one packet and did **not** experience measured input
stall: do NOT infer saturation of those independent channels. Simulated
handshake counts are neither physical device throughput nor a speedup
against the eight-tick integrated kernel.

### M05.8 next verification — late-error transactional RTL discard (pending)

With input/output directed stalls confirmed, the next failure-mode risk
is **prematurely committing speculative trace** before completion. The
kernel streams tick0..3 even if tick4 detects an invalid late external
event: three external packets (tick0/+5→neuron0, tick4/+5→neuron0,
then OUT-OF-ORDER tick3/+5→neuron0) trigger
`M05_ROLL_BAD_EXTERNAL=4` only after 4×2 = **8 valid provisional rows**
(including a real t0 neuron0 spike). New separately compiled direct
generated-RTL testbench:
[`tb_m05_rolling_axis_late_error.sv`](../hls/m05_rolling/rtl_stress/tb_m05_rolling_axis_late_error.sv).
A new `--late-error` selector in
[`run_m05_rolling_rtl_stress.sh`](../scripts/run_m05_rolling_rtl_stress.sh)
reuses unchanged prior genuine 6.503 ns routed OOC HLS IP. It asserts
ordered partial trace, output TREADY stalls, final AXI-Lite status4 and
no extra records. A separate
[`m05_rtl_transaction_replay.py`](../scripts/m05_rtl_transaction_replay.py)
parses the new run's **actual** XSim provisional beat transcript into
existing native `RollingTraceCommitGate`, verifies **0 accepted rows**
after status4, and saves `05_trace_commit.log`.

**This new M05.8 generated-RTL XSim case is NOT YET operator verified.**
The native replay tests rely on SYNTHETIC logs, not a real kernel. The
unchanged signed32 evaluation source and previously verified physical
OOC clock/resource estimates remain exactly as recorded above. M05 open,
draft PR #79 unmerged. [M05.8 detailed runbook and commands](M05_LATE_ERROR_TRANSACTION_GATE_2026_11_08.md).

## F. Next controlled experiments / acceptance gates

1. **ACHIEVED:** i32 rolling engine genuine CSim, HLS synthesis, C/RTL XSim and **Vivado OOC place-and-route** at required 10 ns, achieved 6.503ns. All observed results have documented exact commits/versions and operator-original evidence paths; the evaluation kernel remains unchanged.
2. **CURRENT USER GATE (experimental):** directly compile the generated HLS RTL and [dedicated handshake stress test](M05_AXIS_RTL_STALL_TEST_2026_11_08.md) in Vivado 2025.2 XSim. The new native test prep tools/bench are not yet a real RTL PASS. Force `trace_TREADY` stalls, input `TVALID` gaps, verify stable payload and ordering under stalls and final status after concurrent draining. Preserve new original `Thesis_Evidence` logs even on failure.
3. **NEXT:** expand direct RTL backpressure to multiple seeds, multiple logical runs and malformed/late-error packets; then design a full PS/PL DMA/AXI-Lite concurrent output drain using the native [transactional receiver](M05_TRACE_COMMIT_GATE_2026_11_08.md), including timeout recovery.
4. **LATER:** continuous state-preserving event scheduling beyond 64 ticks, >8 synaptic delay support, and controlled same-workload latency/throughput benchmarks. Require owner acceptance before merging M05 or programming physical FPGA.

**Safety and provenance:** no branch merge, no physical JTAG programming or PS/DDR operations, no invented latencies. **All original evidence folders including older v2 physical logs are preserved unchanged.**
