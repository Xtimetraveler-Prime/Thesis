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

## F. Next controlled experiments / acceptance gates


1. **Already achieved:** i32 rolling engine genuine CSim, HLS synthesis and C/RTL XSim PASS; source immutable until next explicit hardware experiment.
2. **Next offline hardware-feasibility gate:** attempt Vivado **out-of-context HLS IP implementation** using existing safe runner `--rolling --impl` (cumulative CSim+synth+cosim+OOC implementation), then inspect actual implementation clock/BRAM/LUT/FF reports. This is an offline device-family placement/routing experiment, **not** an actual full KV260 shell/PS/DDR integration or board measurement. If the report doesn't provide routed timing, say so.
3. **Separately planned:** a real AXIS ready/valid stall monitor/testbench attached to generated RTL that deliberately deasserts `trace_TREADY` and delays ingress `TVALID`, checks stable payloads/ordering/no drop/duplicate, bounded stalled run completion and final status. The current XSim HLS co-sim provides functional trace confirmation but its UVM config showed zero transfer latency; **not a guaranteed randomized-backpressure test**.
4. **Separately planned:** a full PS/PL transport integration adapting the native [transactional receiver](M05_TRACE_COMMIT_GATE_2026_11_08.md) to a real concurrently draining trace DMA, AXI-Lite `ap_done` + final `return` register, timeout/reset/retry, and evidence of fail-closed output. Physical hardware operations only with explicit operator permission.
5. **Later M05:** continuous state-preserving scheduler beyond 64 ticks, generalized >8 delays without unbounded future buckets, throughput/neuron-event-per-cycle benchmark on identical workloads, and merged milestone only after owner acceptance.

**Safety and provenance:** no branch merge, no physical JTAG programming or PS/DDR operations, no invented latencies. **All original evidence folders including older v2 physical logs are preserved unchanged.**
