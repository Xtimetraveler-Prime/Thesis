# M05 — Tests explained (native stream candidate + PC event scheduling)

**Status:** M05 IN PROGRESS, not user-accepted. Actual source [test_m05_stream.py](../tests/test_m05_stream.py) contains **17 named unittest methods**, with 12 seeded recurrent-network subcases inside one method. Accepted regressions: M04 **22**, M03 **28**, M02 **21**, M01 **20**, for **108 named tests total**.

## Test setup and methodology

`setUpClass` compiles the **real new C++ source** [m05_stream.cpp](../hls/m05_stream_eval/m05_stream.cpp) + [m04_eval.cpp](../hls/m04_lif_eval/m04_eval.cpp) + native-only CLI with g++/c++17 (`-O2 -Wall -Wextra -Werror -pedantic -Wno-unknown-pragmas`); missing compiler or compilation failure fails the suite (no silent skip). Host-stream fallback is a `std::queue`, **not real RTL ready/valid**. Each native batch accepts count 0..1024 and one text line per full 11-field M04 request; returns status, count and ID/tick/status/new state/spike per request. Malformed batch exits nonzero.

[Host sparse runtime](../src/neuromorphic_accelerator_v1/m05_host_runtime.py) runs the actual compiled kernel once per nonempty tick, performs its **own** event-bucket traversal, signed aggregation, exact-zero-safe worklist, positive-delay synaptic fanout, status checks and state snapshots. It does **not** call M02 to produce its result. Tests independently compare **all tick voltage/spike rows** with both M02 dense and M02 event evaluators, and compare worklists/delivery counts with M03 sparse evaluator.

| Exact test method | Mechanism and asserted outcome |
| --- | --- |
| `test_stream_batch_exact_negative_division_and_threshold_equality` | -3×1/2 → -1, inclusive threshold 5 fires/resets -2; W16 maximum old state at threshold also fires. |
| `test_stream_batch_preserves_order_and_per_request_status` | Non-sorted IDs 2,1,0 and tick41; invalid width3 returns status2/zero; legal minimum current -32768 preserved. |
| `test_stream_zero_requests_returns_empty` | Valid empty batch returns success and no fabricated output. |
| `test_stream_input_protocol_rejects_malformed_and_overlarge_batches` | 1025 or negative count, invalid/missing/extra tokens, extra rows and out-of-u32 rational → exit 2, no false output. |
| `test_bias_only_neurons_always_evaluated` | Bias+3 threshold5, zero event; voltages 3,0,3,0; spikes at t1,t3; neuron evaluated all 4 ticks. |
| `test_only_exact_zero_state_idle_is_skipped` | 4-neuron N, only neuron1 has +4 t0; decay1/2 yields 4,2,1,0,0; last tick safely omitted. |
| `test_duplicate_signed_cancellation_before_one_saturation` | Simultaneous +32767,-32768,+6 sums to +5, equality fires/reset -3; no intermediate clamp. |
| `test_parallel_recurrent_self_edges_with_strictly_positive_delays` | Two neurons with self-feedback, signed parallel synapses, delays 1/2/3 and bias; M02/M03 full trace parity. |
| `test_seeded_recurrent_networks_all_tick_state_and_spike_parity` | **12 deterministic seeds**, 6 neurons, 16 signed recurrent/parallel edges, 36 events over 10 ticks; exact M02 dense/event/M03 voltage, spike and worklist parity; bounded evaluation count. |
| `test_4096_admitted_events_exact_without_intermediate_clipping` | 2048 copies (+32767,-32768) → -2048; counts 4096 individual deliveries, one update. |
| `test_4097_external_events_fail_closed` | 4097 zero-current external events cause explicit M04AdmissionError, not silent drop. |
| `test_4097_scheduled_recurrent_events_fail_closed` | One neuron fires and creates 4097 delayed parallel self deliveries; future-tick limit rejected before any successful trace is returned. |
| `test_provisional_resident_capacity_bound` | 1024 empty neurons admitted, all safely skipped; 1025 and zero budget rejected. This **models** a capacity, not SRAM. |
| `test_m02_legal_other_width_or_ratio_rejected_by_first_profile` | W4/W8/W32 or denominator=2^32 valid in Python M02 but outside first W16/u32 hardware admission profile. |
| `test_invalid_zero_delay_is_rejected_before_any_engine_call` | Zero-delay recurrent edge fails M02 validation; no same-tick recursion. |
| `test_missing_host_binary_rejected_without_fake_pass` | Missing native binary fails rather than silently executing Python-only arithmetic. |
| `test_tick_exceeding_u64_rejected_before_any_large_replay` | Horizon outside 64-bit tick metadata rejected before costly/unbounded work. |

**Observed CI:** initial M05 compile **failed** on `-Werror=unused-label` in the HLS top; removed label without changing behavior. Tightened an invalid u32-denominator fixture. [Run 42454758437](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42454758437) at `cd483fe5` logged **17 M05 PASS, 22 M04 PASS, 28 M03 PASS, 21 M02 PASS, 20 M01 PASS**. Documentation/source additions require final HEAD CI recheck.

**What these tests do NOT establish:** HLS synthesis, C/RTL co-sim, actual AXIS backpressure, real bounded event FIFO or future queue, on-chip state memory ownership/RAW hazards, DDR/AXI traffic, microarchitectural II/latency, routed clock, physical FPGA performance, energy or Loihi/YANA equivalence. [HLS Csim vectors](../hls/m05_stream_eval/m05_hls_csim_tb.cpp) are **unexecuted** Vitis inputs; include no fake HLS PASS. M05 operator native testing and user approval remain pending. See [M05 verification](M05_PC_ONLY_VERIFICATION.md) and [v3 comparison](M05_ENGINE_V3_COMPARISON.md).


## Additional independent native Csim-testbench smoke gate (not a unittest method)

The M05 workflow now also compiles [`m05_hls_csim_tb.cpp`](../hls/m05_stream_eval/m05_hls_csim_tb.cpp) against the *same* C++ M05 kernel/M04 step via native `g++`, runs it, and requires the testbench's fixed scalar fixtures to return PASS. This confirms the staged Vitis testbench **itself** is internally consistent under the host-only stream shim. It does **not** add an 18th unittest method, call Vitis, prove AXIS ready/valid, achieve II=1, or demonstrate C/RTL parity. **Genuine Vitis HLS Csim/synthesis/C-RTL remain NOT RUN.**
