> **NEW VERIFIED HARDWARE BASELINE, 2026-11-08:** The **signed32 rolling HLS kernel itself** now has real Vitis 2025.2 CSim, HLS synthesis and Verilog XSim C/RTL co-sim **PASS**, 10/10 transactions at source commit `07913bbf925e5cd1ffc0d84dd6f9d5b4c2ee519a`. That verification tests the mathematical/event scheduler (not live AXIS READY stalls). The host-only transactional receiver is still CPU-only with no real AXI-Lite completion/interrupt or DMA link. [Evaluation-engine optimization ledger](M05_EVALUATION_ENGINE_EVOLUTION.md). Next offline OOC Vivado implementation, then an independent RTL TREADY/TVALID stress test.
>
# M05.5 — Host-side transactional trace receiver (NO BOARD)

**Status (2026-11-08):** Native-only proof-of-contract added to the M05 development branch; no actual DMA, AXIS ready/valid testing, AXI-Lite driver, hardware interrupts, real transaction-aware output FIFO, or KV260 operations. PR #79 remains **DRAFT / UNMERGED**; M05 remains OPEN.

## Why this is needed

The existing fifth `m05_rolling_replay` HLS top streams a full `neuron_count` rows after each tick's fanout checks, rather than buffering all 64 ticks. On tick 17, for example, a 4,097th arrival or an invalid out-of-order external record can cause a **nonzero final AXI-Lite return status after ticks 0–16 were already emitted**. The receiving system must never accept those rows as a partial successful inference.

**Critical deadlock avoidance:** the host/PS-side transport must drain `trace_TDATA/TVALID/TREADY` concurrently while the accelerator runs. Waiting for `ap_done` before reading from a backpressured output stream can prevent `ap_done` from ever occurring. Drain/retain first, then await completion and read the actual status; only then commit the entire trace. A timeout/transport error must ABORT/discard the staged rows, with hardware reset/recovery specified separately before reusing the device. The current HLS top's `ap_ctrl_hs` result alone has no end-of-transaction trace tag or per-row commit bit.

## New executable host-side prototype

[`m05_trace_commit.py`](../src/neuromorphic_accelerator_v1/m05_trace_commit.py) provides:

- `RollingTraceCommitGate(neuron_count, ticks)` with explicit shape bounds **1–1024 neurons, 1–64 ticks, maximum 65,536 rows**. Host staging is bounded by the admitted shape, **but these are Python objects in host memory, NOT FPGA BRAM or measured DDR/DMA traffic**.
- `offer_row(RollingTraceRow(...))` accepts each drained beat as a *provisional* record. It validates row-major order, one row per neuron/tick, W16 voltage, binary spike/evaluated, spike⇒evaluated, delivered_count in 0–4096 and agreement of counts across all neurons of the same tick.
- A malformed/duplicate/out-of-order/extra record **poisons** the run. The receiver keeps consuming subsequent frames so the caller can continue draining without blocking the accelerator; it clears staged results and never returns partial accepted output.
- `complete(final_status)` returns a frozen `TraceRunResult` containing accepted rows **only if final status==0, exactly all expected rows have arrived, and no framing error occurred**. A late hardware error status 1–6 discards the entire run, including previously staged ticks; an unexpected status also fails closed.
- `abort(reason)` invalidates all partial data if the completion status is unavailable. This is **host-local state only** and does not reset a stuck accelerator.

These checks are a *necessary consumer contract*, **not a substitute for hardware DMA/backpressure validation**. In particular, a real host must concurrently run an ingress feeder, trace receiver and AXI-Lite completion monitor. The bounded HLS scheduler still expects all declared incoming neuron/synapse/external-event packets to arrive; if the sender supplies fewer, it can stall indefinitely.

## Tests and evidence boundary

[`test_m05_trace_commit.py`](../tests/test_m05_trace_commit.py) adds **16 named native-only** tests:
- success withheld until final status;
- late overflow and malformed-event rollback;
- incomplete/extra/duplicate/out-of-order/invalid-W16/invalid-bit/delivery-count framing;
- unknown status and timeout abort;
- max 65,536-row staged run;
- **deterministic toy one-beat FIFO producer/consumer stall model** demonstrating no loss or prefix acceptance under delayed receiver readiness;
- integration with the **native C++ rolling top** via its existing CLI adapter, not a PS/DMA driver.

After adding these, there are **92 M05 + 91 M01–M04 = 183 named native tests**, plus five earlier independent native CSim benches. Host GitHub CI verifies the new tests, but the one-beat FIFO model does **not** drive actual `TREADY` or timing on an RTL port.

## Real Vitis synthesis results now obtained for optimized i32 rolling engine

Operator supplied Vitis HLS 2025.2 K26 **genuine CSim + synthesis PASS** at source commit `827f719778472da39ffa294b431ee848fe360529`:
- Original evidence directory: `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_synth_20261108T193909Z_169727`.
- Expected 10ns; HLS-estimated period **8.256ns** (12% uncertainty).
- **39 total BRAM18K** (old i64 rolling **53**), of which `current_U` `8192×32` is **16 BRAM18K** (old i64 **30**). The entire improvement is **14 BRAM18K fewer**, a **26.4%** top-level BRAM decrease, with **9,956 LUT, 8,346 FF, 2 DSP**.
- Old HLS warning `HLS 200-448` for lower-bound II=2 from competing bias RAM loads remains, and AXI synchronous active-low reset note `RTGEN 206-101` remains. Top-level HLS latency/interval still `?`. These are **not** routed physical timing, system throughput, or real on-device consumption.
- **Genuine XSim C/RTL co-simulation for the new i32 rolling version is still PENDING**. Old i64 rolling version at commit `03c3fbc5...` passed real XSim; that evidence cannot be applied to i32 RTL.

The trace-receiver module/tests/docs changes do **not** modify `hls/m05_rolling/m05_rolling.cpp`, the i32 hardware kernel synthesized above. Its GitHub content SHA is `e5443aa87dcc8819ee8aa680b6ca105facc1aced`.

## Next operator gate (offline Vitis 2025.2, NO BOARD)

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
cd Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m05*.py' -v
export HLS_PART=xck26-sfvc784-2LV-c
bash hls/m05_stream_eval/run_m05_offline_hls.sh --rolling --cosim
```

The runner creates a **fresh, exclusive** `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_cosim_*` folder and reruns real CSim, synthesis and XSim, with trace bench exercising 8,192 signed extreme events, 4,096 synapse fanout, full 64-tick dense trace and abort cases. **STOP on any failure/hang** and preserve all original stage logs. Return `result.txt`, `commit.txt`, `work/hls/sim/report/m05_rolling_replay_cosim.rpt`, and last 80 lines of `03_cosim.log`, plus warnings on failure. Only after successful i32 RTL gate should a separate HDL-level ready/valid stall and host/DMA integration stage be planned.

M05 acceptance still requires actual hardware-validated concurrent drain & commit semantics, comprehensive backpressure testing, >64 tick/long-delay scheduling, and physical placement/board evidence as separately authorized.
