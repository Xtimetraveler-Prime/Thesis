# M05 rolling temporal wheel — native-tested follow-on to the genuine-Vitis-verified finite-run engine

> **LATEST 2026-11-08 ROLLING HLS SYNTHESIS — user-provided original report, scoped to source commit `984f5baf45ce771e94e1e8b2947e1ef27ccc6d58`:** Genuine Vitis HLS 2025.2, target K26 (`xck26-sfvc784-2LV-c`), **exit_status=0**. Clock **10ns requested / 8.244ns HLS estimated** (1.20ns uncertainty). HLS area: **53 BRAM18K / 288, 10,083 LUT / 117,120, 8,459 FF / 234,240, 2 DSP / 1,248, 0 URAM**. Its future-current `current_U` alone occupies **30 BRAM18K** of 53; per-tick scratch state is resident BRAM as intended. Top-level latency/II **unknown (`?`)**, and a reported initialization-loop theoretical maximum `34,359,738,362` cycles is **not** a measured run; don't infer throughput from it. Warning `HLS 200-448` says **loop lower-bound II=2 from competing reads of single-port `bias`**, not that the whole engine achieves global II=2; reset is synchronous active low. All claims are HLS estimates, **not placed/routed clock, timing closure or physical throughput**. Memory compare against earlier eight-tick integrated top: **74→53 BRAM18K (-21)**, LUT **5,914→10,083 (+4,169)**, FF **3,122→8,459 (+5,337)**, DSP **6→2**, clock estimate **8.002→8.244ns**. The earlier integrated run is **8 ticks** vs rolling **64 ticks**, and their testbench workloads are not cycle-per-tick equivalent. No rolling C/RTL co-simulation result yet.
>
> **NEW SOURCE-PRESERVING TEST COVERAGE:** Following synthesis, only [`m05_rolling_csim_tb.cpp`](../hls/m05_rolling/m05_rolling_csim_tb.cpp) and [`test_m05_rolling.py`](../tests/test_m05_rolling.py) were extended—not the actual synthesized [`m05_rolling.cpp`](../hls/m05_rolling/m05_rolling.cpp). GitHub blob SHA **`5065bb5babad38e4f6685be34c77189be6a9e426`** is identical on synthesis commit and the updated branch. New RTL-ready CSim bench now independently computes every neuron state, spike, evaluated-bit and delivery count of a **64-tick** two-neuron signed recurrent network (including delay-8 self/parallel recurrence, last-tick zero event), and tests a **late out-of-order external input** causing BAD_EXTERNAL after speculative prefix emissions. Python adds 2 named native tests for full 64-tick M02/M03 oracle parity and the 1,024-neuron boundary. Native CI **74 M05 + 91 M01–M04 = 165 methods PASS**; **five** HLS CSim bench source executables compiled/executed NATIVELY in CI. **No actual Vitis CSim/RTL yet for the strengthened bench**, so next gate is **cumulative `--rolling --cosim`** which first reruns genuine CSim and synthesis before XSim. Original original roll-synth source/config/results remain in external `Thesis_Evidence`, no Git reports.

> **2026-11-08 NEW OPERATOR REPORT + SOURCE REVISION:** Genuine **rolling** `m05_rolling_replay` Vitis 2025.2 **CSim PASS**, zero errors, exit 0 on the operator machine at `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_csim_20261108T185457Z_144435`. That run is evidence for the then-current rolling source; **its exact `commit.txt` is not supplied**. No genuine rolling RTL synthesis/C-RTL co-simulation has been reported. After that pass, source was **modified** to reduce per-invocation BRAM initialization from 8×1024 physical entries to 8×`neuron_count` admitted entries, while still clearing the active slot before its delay-8 aliases are routed. The HLS CSim bench now checks **2 → 1 → 2 network sizes across consecutive invocations**, ensuring no prior-epoch RAM visibility. These changes require **new genuine Vitis CSim** before treating the optimized source as hardware-validated; the cumulative `--rolling --synth` command reruns CSim and then synthesizes only if it passes. No routed timing, whole-network throughput, backpressure proof or board execution yet.
>
> **Integrated RTL latency report now reviewed:** `m05_integrated_replay_cosim.rpt` and `work/reports/hls_cosim.rpt` show the SAME Verilog `Pass` record: **latency min 8463 / avg 10572 / max 16396 cycles**, **interval min 8489 / avg 11300 / max 16416 cycles**, **total simulation 42363 cycles**. With the configured 10ns simulation clock those are respectively latency **84.63 / 105.72 / 163.96 µs**, interval **84.89 / 113.0 / 164.16 µs**, and total **423.63 µs** for that testbench sequence. These are simulation transactions with different test cases; **not** achieved physical K26 network throughput or a fair rolling-versus-integrated benchmark. Previous integrated HLS synth's **8,194-cycle** init subloop (8×1024) motivates but does NOT demonstrate any achieved rolling speedup.

**Branch:** `agent/neuromorphic-accelerator-v1-m05-sparse-onchip` (draft PR #79; **NOT MERGED**). No KV260/JTAG/DDR/physical action authorized.

## Established previous verification vs new work

The previously developed `m05_integrated_replay` finite-horizon (1–8 ticks) **PASSED genuine Vitis HLS 2025.2 CSim, synthesis and XSim C/RTL co-simulation** on the operator workstation, K26 `xck26-sfvc784-2LV-c` / 10ns requested target. Original user evidence:
- CSim `~/Thesis_Evidence/neuromorphic_v1_m05_integrated_csim_20261108T161418Z_84650`: `SIM 211-1`, zero errors, return 0.
- Synthesis `~/Thesis_Evidence/neuromorphic_v1_m05_integrated_synth_20261108T164348Z_85611`: top `m05_integrated_replay_csynth.rpt`, 8.002ns **HLS-estimated** clock period, 5,914 LUT, 3,122 FF, 6 DSP, 74 BRAM18K / 288 device total. Unknown top-level end-to-end latency. No place/route timing.
- C/RTL cosim `~/Thesis_Evidence/neuromorphic_v1_m05_integrated_cosim_20261108T164737Z_86835`: **`[COSIM 212-1000] *** C/RTL co-simulation finished: PASS ***`**, C postcheck golden vectors PASS, exit 0. Original `work/hls/sim/report/m05_integrated_replay_cosim.rpt` and `work/reports/hls_cosim.rpt` were subsequently provided and reviewed: Verilog PASS, latency 8463/10572/16396 cycles min/avg/max at 10ns. These are testbench simulation transactions, not physical throughput.
- The full reports remain in operator-local `Thesis_Evidence`, **not tracked by Git**. This document is evidence metadata, not a substitute for those original log hashes.

**NEW work after this PASS**: an alternative fifth top, `m05_rolling_replay` in [m05_rolling.cpp](../hls/m05_rolling/m05_rolling.cpp). Its earlier source has genuine operator Vitis **CSim PASS**, but the newly optimized rolling source requires repeat CSim; **no rolling HLS synthesis, XSim RTL co-simulation or physical-fabric validation** has been reported. The prior integrated PASS does not transfer automatically.

## What changes relative to the eight-tick full-trace-buffered prototype?

| Property | Existing `m05_integrated_replay` | NEW `m05_rolling_replay` |
| --- | --- | --- |
| Absolute run limit | 8 ticks | **64 ticks per invocation** (explicit provisional bound) |
| Future-event allocation | Full `[8][1024]` bucket bank, indexed by absolute tick | **Eight reusable slots**, each `[1024]`, addressed by `tick % 8` |
| Allowed recurrent delays | Any positive uint64 (future > end discarded) | **1–8 ticks only** (reject delay 0 or >8) |
| External inputs | Arbitrary tick ordering; preloaded before evaluation | **Sorted nondecreasing by tick**, one-event lookahead on AXIS input |
| Event semantics | Signed i64 aggregate + independent touched/count per tick | **Same M02 semantics**, 4096 individual contributions/tick including zero/cancel |
| Synapses | Self + parallel, linked-list fanout | Same, with compact one-byte stored delays |
| Trace buffering | All 8-tick trace rows resident, no output on ANY run failure | Only ONE tick of temporary trace in resident RAM; after that tick's fanout checks it may stream to AXIS |
| Late error rule | Empty output on any failure | **Earlier tick records may have been emitted; a nonzero FINAL status invalidates the ENTIRE run/prefix** |
| Hardware evidence | Real Vitis CSim/synth/cosim PASS, 74 BRAM18K HLS estimate | **Only native/source checks so far**; resource utilization TBD |
| Remaining | True continuous engine + PS integration/backpressure | Continuous >64 tick epoch, delayed events >8, safe consumer status protocol + real hardware validation |

This is a **rolling temporal-bucket / current-sum wheel**, not a FIFO preserving individual event packets. Individual count/touch metadata ensure legal additive M02 behavior and overflow semantics. Do not call it an asynchronous physical chip.

### Read/compute/free/fanout/commit order

For each logical tick `t`, the active physical slot is `s = t % 8`:

1. Accept sorted external contributions for `t`, mixed with previously queued recurrent contributions in `s`. Reject malformed/backward IDs/timestamps/weights and a 4097th delivery.
2. Evaluate every eligible neuron exactly once in ascending ID order, using its **old state and the whole signed i64 aggregate**. Eligible iff nonzero prior voltage, nonzero bias, or **touched** (even zero/canceled input). Share accepted M04/M02 scalar LIF function. Stage this tick's poststate/spikes in scratch.
3. Save `delivery_count[s]` for trace counters. **Clear all current-slot sums and touch flags before recurrence**. This is essential for delay==8: `t+8` aliases `s`.
4. For every spike, traverse outgoing linked-list edges and add signed W16 terms to `(t+delay)%8` if in run horizon. Only delays 1..8 are admitted, so no collision with a *still outstanding* distinct future tick. Reject future 4097th arrival; do not emit any trace row for the **faulting** tick.
5. Emit this tick's voltage/spike/evaluated/count records after its fanout checks pass. These are provisional until final `ap_done` and status==0. If later overflow/error occurs, the consumer **MUST discard all received rows** as invalid; do not interpret them as a successful partial network. A host sink that waits for `ap_done` *before consuming trace* can deadlock a backpressured AXI stream; concurrent draining and subsequent final-status validation are required, subject to future real protocol testing.

**Not yet proven:** real AXIS backpressure, stall/restart handshake, fanout hazard under pipeline optimization, physical timing/resource mapping, stream ordering across an FPGA host transport, abort signaling without final status/timeout, and on-chip state continuation across runs. All incoming packets must be supplied when demanded, or the HLS IP will stall waiting on AXIS. This prototype resets state and wheel at the beginning of each invocation and deliberately excludes >8 delay. It does **not** close M05.

## New source/test locations

- [Rolling top contract](../hls/m05_rolling/m05_rolling.hpp) and [HLS-oriented C++ implementation](../hls/m05_rolling/m05_rolling.cpp)
- [Strict native-only framed CLI](../hls/m05_rolling/m05_rolling_host_cli.cpp) — publishes **zero accepted rows on nonzero final status**, modeling mandatory consumer discard
- [Vitis-ready HLS CSim vectors](../hls/m05_rolling/m05_rolling_csim_tb.cpp) — check **tick 0→8→16 wheel wrap**, 4096 recurrent contributions plus one external causing a **late** 4097th event, and fresh-run reinitialization.
- [12 native M02/M03 oracle tests](../tests/test_m05_rolling.py) — full 24–40 tick state/spike/sparse/delivery trace parity, negative/canceling/zero signed inputs, ordered ingress, long recurrence, 4096/4097 boundary, delay rejection, output fault policy, and 12 seeded 30-tick recurrent networks.
- [Vitis 2025.2 K26 config](../hls/m05_rolling/m05_rolling_hls_config.cfg); same evidence-local absolute-path generator and runner now select `--rolling`. Fifth candidate not yet genuine-tool proven.

## Operator verification, in order

Pull the updated branch and first run native regression tests (expect 72 M05 + 91 M01–M04 = **163 named native tests**):

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
cd Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m05*.py' -v
```

Then, in a terminal with the **actual Vitis 2025.2** environment sourced and `vitis-run` available:

```bash
export HLS_PART=xck26-sfvc784-2LV-c
bash hls/m05_stream_eval/run_m05_offline_hls.sh --rolling --csim
```

STOP if the new fifth-top CSim fails. Preserve the printed fresh `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_csim_*` folder. Inspect `result.txt`, `hls_effective_config.cfg`, `01_csim.log`. If CSim passes, proceed only then to `--rolling --synth` and review top-level BRAM, loop timings and arithmetic resources; after that pass `--rolling --cosim`. All calls are offline and create NEW evidence folders, never mutate old results or touch the KV260.

The rolling wheel is a *research comparison candidate*, not a replacement for the accepted earlier integrated real-tool result until genuine parity/synthesis is established.
