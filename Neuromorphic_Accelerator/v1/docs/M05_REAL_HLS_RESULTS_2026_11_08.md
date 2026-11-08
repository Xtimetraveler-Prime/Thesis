> **New 2026-11-08 results after prior summary:** operator supplied the *fourth integrated top's* full C/RTL co-sim reports: Verilog **PASS**; simulated latency **min 8,463 / avg 10,572 / max 16,396 cycles**; initiation interval **min 8,489 / avg 11,300 / max 16,416 cycles**; total simulator execution **42,363 cycles**. At requested 10ns clock the average transaction corresponds to **105.72 µs**; NOT measured FPGA inference throughput. Both `work/hls/sim/report/m05_integrated_replay_cosim.rpt` and `work/reports/hls_cosim.rpt` show the same row. The *fifth rolling candidate* initial source also achieved **genuine Vitis CSim PASS** at `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_csim_20261108T185457Z_144435`, testbench PASS and exit 0. Its git SHA was **not pasted**. A **later rolling source change** bounds RAM initialization to active neurons and adds 2→1→2 CSim regression; new `--rolling --synth` first reruns CSim. **Rolling synthesis/RTL cosim NOT reported**. All raw tool artifacts remain outside Git.

> **NEW integrated real-tool result, 2026-11-08:** Operator confirmed **Vitis 2025.2 HLS CSim PASS**, **csynth PASS** (top HLS estimated 8.002 ns, 5,914 LUT / 3,122 FF / 6 DSP / 74 BRAM18K), and **XSim C/RTL cosim PASS** for the *fourth* top `m05_integrated_replay`. Original paths: `~/Thesis_Evidence/neuromorphic_v1_m05_integrated_csim_20261108T161418Z_84650`; `~/Thesis_Evidence/neuromorphic_v1_m05_integrated_synth_20261108T164348Z_85611`; `~/Thesis_Evidence/neuromorphic_v1_m05_integrated_cosim_20261108T164737Z_86835`. C/RTL console explicitly states `[COSIM 212-1000] *** C/RTL co-simulation finished: PASS ***`, oracle postcheck PASS and `exit_status=0`. **Full per-transaction timing report still unreviewed:** `work/hls/sim/report/m05_integrated_replay_cosim.rpt` and `work/reports/hls_cosim.rpt`. These results do NOT prove AXIS backpressure, physical timing or continuous operation. [New rolling follow-on](M05_ROLLING_WHEEL_DESIGN_2026_11_08.md) is **native-only** pending genuine Vitis; do not inherit the integrated top's RTL PASS. Originals remain outside Git as requested.

# M05: real Vitis HLS 2025.2 operator evidence — isolated IP gates (2026-11-08)

**Status:** Operator-provided Vitis outputs substantiate **PASS** for each of three **standalone** HLS C simulations, HLS C syntheses, and XSim C/RTL co-simulations. **The integrated M05 on-chip event-driven engine is NOT implemented or accepted.** M05 remains OPEN; PR #79 remains DRAFT / UNMERGED; no hardware-board/PS/DDR actions have been performed.

## Source and evidence provenance

- Vitis `2025.2` build `6295257`, K26 `xck26-sfvc784-2LV-c`, Vivado IP flow, requested clock `10.00 ns`, uncertainty `1.20 ns`.
- Operator CSim logs explicitly identify git SHA `ffaef8bea32f222f11f0553aca8f929e258bb804`. Subsequent standalone synthesis and C/RTL evidence has been reported in the same development sequence. **Full original `commit.txt`, `source_sha256.txt`, effective config hashes and `03_cosim.log` were not uploaded with the provided terminal excerpts**; verification of byte-for-byte provenance still requires those originals if a formal evidence package is needed.
- **Previous three genuine CSim path failures** at `6f5ca78a` are preserved and analyzed separately in [original failure record](M05_HLS_CSIM_FAILURE_2026_11_08.md). The corrected effective HLS configs generated absolute source/testbench/include paths and all three later genuine CSim benches passed with exit 0.
- Top-level synth reports supplied as terminal pasted text and reviewed; inner pipeline submodule utilization must NOT be substituted for the top-level totals.

| Top | Genuine Vitis CSim | Standalone C synthesis | Genuine XSim C/RTL co-simulation | Original evidence directories (under `~/Thesis_Evidence/`) |
| --- | --- | --- | --- | --- |
| `m05_stream_eval` | **PASS**, oracle vectors, 0 errors, exit 0 | **PASS**, RTL generated, exit 0 | **PASS** `[COSIM 212-1000]`, xsim C post-check PASS, exit 0 | `neuromorphic_v1_m05_stream_csim_20261108T073238Z_65236`; `neuromorphic_v1_m05_stream_synth_20261108T073719Z_67061`; `neuromorphic_v1_m05_stream_cosim_20261108T074438Z_70342` |
| `m05_stateful_service` | **PASS**, oracle vectors, 0 errors, exit 0 | **PASS**, RTL generated, exit 0 | **PASS** `[COSIM 212-1000]`, xsim C post-check PASS, exit 0 | `neuromorphic_v1_m05_stateful_csim_20261108T073303Z_65857`; `neuromorphic_v1_m05_stateful_synth_20261108T073948Z_68134`; `neuromorphic_v1_m05_stateful_cosim_20261108T074813Z_72797` |
| `m05_event_accumulator` | **PASS**, oracle vectors, 0 errors, exit 0 | **PASS**, RTL generated, exit 0 | **PASS** `[COSIM 212-1000]`, xsim C post-check PASS, exit 0 | `neuromorphic_v1_m05_accumulator_csim_20261108T073318Z_66424`; `neuromorphic_v1_m05_accumulator_synth_20261108T074033Z_69176`; `neuromorphic_v1_m05_accumulator_cosim_20261108T075205Z_75152` |

## Top-level HLS synthesis estimates (NOT placed/routed timing or complete accelerator utilization)

| Top | Estimated clock period | Estimated Fmax (from synth console) | LUT | FF | DSP | BRAM18K | URAM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `m05_stream_eval` | 8.170 ns | 122.40 MHz | 9,267 | 12,945 | 4 | 0 | 0 |
| `m05_stateful_service` | 8.305 ns | 120.41 MHz | 3,208 | 2,401 | 4 | 10 | 0 |
| `m05_event_accumulator` | 3.559 ns | 280.98 MHz | 1,076 | 842 | 0 | 5 | 0 |
| **Arithmetic sum of separate tops (NOT actual integrated fit)** | — | — | **13,551** | **16,188** | **8** | **15** | **0** |

Device availability per standalone top-level reports: **117,120 LUT; 234,240 FF; 1,248 DSP; 288 BRAM18K; 64 URAM**. Sum is **11.6% LUT, 6.9% FF, 0.6% DSP, 5.2% BRAM18K** of nominal whole K26 capacity **before** memory/event router, future delay queue, synaptic routing, AXI infrastructure, synchronization, integration, and optimization. Separate standalone estimates cannot prove coexistence, wiring, placed resources, achievable system timing, or bandwidth.

### Memory specifics

- Stateful top: **10 BRAM18K blocks**. Seven 1,024-row arrays: W16 `voltages`, `biases`, `thresholds`, `resets` each 1 block; u64 `last_tick` 4 blocks; `initialized` and `processed` bit arrays each 1. HLS RTL console explicitly reported voltage, bias and tick block-RAM mappings; top-level report confirms all seven arrays, not just pragmas.
- Accumulator top: **5 BRAM18K blocks**. Signed-i64 `sums` uses 4; 1-bit `touched` uses 1, both 1,024 rows. Not host RAM.
- Stream top: zero BRAM; its 64-bit signed divider hardware is costly. Pipeline submodule report attributes **6,607 LUT and 8,651 FF** to the `sdiv_64ns_33ns_64_68_1` instance, substantial relative to 9,267 top-level LUT and 12,945 FF.

### Timing, throughput and architecture caveats

- **Stream inner loop:** target II=1, **achieved II=1**, depth 69. At 100 MHz and steady streaming without backpressure, loop scheduling suggests up to 100 million neuron updates/s at its loop interface. **NOT achieved system throughput**. Top-level stream IP is not a continuously free-running engine: top level has min–max latency 1–1095 cycles and reported top-level interval 2–1096 cycles for count-dependent batches.
- **Stateful top** and **accumulator top** are NOT fully pipelined command services. Their top-level reports show latency **1–1,054,722 cycles** (maximum configured batch) and interval **2–1,054,723 cycles**, with up-to-1024 command outer loops not pipelined. Their separate CLEAR initialization subloops have II=1 but that does **not** mean 1 command per clock.
- **Stateful `m04_eval_one`:** 1–67-cycle non-pipelined submodule; synthesis generated sequential divider `sdiv_64ns_33ns_64_68_seq_1`. Distinct from the stream loop's 69-stage pipelined divider. Integration must decide on ONE neuron-evaluation datapath or justify duplicate arithmetic and bottleneck.
- HLS estimated Fmax and loop II are not physical routed timing, measured FPGA power, wall-clock live inference or end-to-end event scheduler throughput; nor is `ap_ctrl_hs`/AXIS packaging proof of integrated ready-valid/backpressure or full tick barrier correctness.
- User's three XSim post-check excerpts each explicitly contain `[COSIM 212-1000] *** C/RTL co-simulation finished: PASS ***`, testbench PASS and exit code 0. No reported failures. Standalone vectors do not cover a stitched accelerator or future-delay positive-delay recurrent queue.

## Next M05 development gate

Develop a **single integrated, synthesizable on-chip event scheduler and neuron processing service** (either new unified top or explicit validated IP interconnect). Avoid simply wiring the three independent command streams without a controller. Implement bounded positive-delay event FIFO/buckets and synapse fanout, delivery fan-in/touch bits, exact signed-i64 summation before evaluation, all-tick barrier, 1,024-state BRAM read/commit hazards, self/parallel recurrences, autonomous/bias/zero-state sparse rules, a 4,096-*individual-deliveries* per-tick cap with sticky invalid-run/abort, output spike ordering, ready/valid backpressure and no partial result publication. Compare full voltage/spike/event traces against independent M02 dense and event models plus M03 scheduler. Verify integrated CSim → C synthesis → C/RTL co-simulation, then consider OOC implementation and ultimately a separate user-authorized hardware-board gate.

**No need to rerun already-passing independent tops solely to continue source-level integration.** For a thesis-grade archival bundle, obtain original `result.txt`, `commit.txt`, `source_sha256.txt`, `effective_config_sha256.txt`, `03_cosim.log`, `report_paths.txt` and `*_cosim.rpt` from each of the three *cosim* evidence directories, plus already-supplied top-level synthesis reports, preserving all originals unchanged. If a report isn't produced, record that fact rather than inventing it.
