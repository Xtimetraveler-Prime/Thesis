# M04 — Tests explained (source audit + host C++ proof; NO BOARD)

**Status:** M04 in progress, not accepted. This document describes **the exact test methods implemented** in [`test_m04_eval.py`](../tests/test_m04_eval.py) and observed audit/smoke activities, not a synthesized FPGA test. There are **13 M04 Python unittest methods**, including **16 seeded cross-tick randomized network subcases**. The M01 (20), M02 (21), M03 (28) test suites are retained, not reimplemented. **CI execution verified:** GitHub Actions [M04 host run #42452694640](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42452694640) at source commit `703ac9943ffbca06ab4aac507b99ec7f7e30fdc4`: **13 M04 tests PASS**, 16 randomized network subcases within one method; accepted regressions **28 M03 + 21 M02 + 20 M01 PASS** (82 total methods). Verified by reading job logs, not inferred from steps alone. Independently run user-native evidence is **still pending**.

## M04.1 and M04.2 review procedures (not test methods)

Read-only source inspection: v3 `src/loihi_core_v2.cpp`, `include/loihi_core_v2.hpp`, P03/P04 C++ differential testbenches, HLS config, README, run scripts, P03 XPM memory fabric, P05 three-context controller, P08 paged dispatch controller, P02/P03 hardware boundary/acceptance/implementation docs, then M02 revision-1 neural contract and both independently implemented Python evaluators. Compare every state field, rounding step, threshold condition, packed memory field, input/output port, and scheduling/DDR assumption in [M04_HLS_ENGINE_AUDIT.md](M04_HLS_ENGINE_AUDIT.md). **Actual review conclusion:** v3's old saturated current state, rounded-away 1/4096 decay, strict threshold and refractory change the mathematical behavior; its HLS ap_memory ports are not AXI master/stream interfaces. Reading the P03 testbench and historical 100-MHz implementation notes does **not** execute either testbench or reproduce a resource/timing estimate.

## Native harness and independent references

The M04 suite uses Python standard library to invoke an installed C++17 compiler (`g++` or `c++`) on `hls/m04_lif_eval/m04_eval.cpp` and the host-only `m04_host_cli.cpp` with `-std=c++17 -O2 -Wall -Wextra -Werror -pedantic`. Compilation failure **fails** the test setup; no silent skip. A fresh OS temporary build directory is disposed after the suite. Each input line is exactly:

```text
neuron_id neuron_count tick old_voltage aggregate_current bias threshold reset_voltage state_bits decay_num decay_den
```

Each output is `neuron_id tick status next_voltage spike`. The test asserts response count and ID/tick echo for every case. Status 0 means valid; 1 invalid neuron ID/empty count, 2 invalid W, 4 invalid numerical/state parameters; error response has zero voltage and spike. Invalid inputs must not mutate a persistent state (the function has none). The request consumes the **already summed** signed current; this CLI does not implement routing or a real event FIFO. The host CLI explicitly exits code 2 on malformed or unrepresentable decimal input, instead of silently wrapping or truncating outside its documented u32/i64 fields.

The two real prior independent oracles are [`m02_dense_reference.py`](../src/neuromorphic_accelerator_v1/m02_dense_reference.py) and [`m02_event_reference.py`](../src/neuromorphic_accelerator_v1/m02_event_reference.py), sharing only validated `m02_types`. The network tests first assert the two oracles agree and then generate one C++ request per neuron/tick from the oracle's *preceding* voltage/spike row, external events and independently enumerated delayed synaptic deliveries. C++ replies are checked against the **entire expected voltage and spike row**, not merely the final number of spikes. These assertions avoid relying solely on a compiler's agreement with itself.

| Exact unittest method | Setup and mechanism | Independent expected result / failure path |
| --- | --- | --- |
| `test_negative_decay_truncates_toward_zero` | 16-bit signed prior voltages -3,-7,+7, rational decay 1/2 and 2/3 | -1,-4,+4; catches Python-floor or v3-style round-away leak |
| `test_inclusive_threshold_and_reset` | One current-free neuron at/below threshold=5, reset=-2 | 5 fires and stores -2; 4 remains 4 and does not fire; catches v3 strict `>` |
| `test_signed_saturation_and_extreme_aggregate` | W=4, signed currents ±30 and ±(2^63 bounds) | Upper clamps to 7 then fires/resets, lower clamps to -8 without fire, no C++ signed overflow |
| `test_aggregate_before_single_clamp` | Mathematically grouped +7,+7,-7 -> +7 at W4; also negative bias-only | Fires on equality; no intermediate per-event saturation; bias -4 yields -4 |
| `test_bias_only_autonomous_spike` | Quiet neuron bias +3, threshold 5, reset=0, ticks 0,1,2 | Voltages 3,0,3; spike only tick 1; tests required idle-neuron evaluation |
| `test_valid_width_32_and_large_decay_ratio` | W=32, ±extremal stored voltage, `num=den=UINT32_MAX` | Preserve minimum or fire/reset at exact maximum; signed product stays in int64 |
| `test_invalid_id_and_empty_network_fail_closed` | ID>=count, and count 0 | Status 1, zero state/spike |
| `test_invalid_width_and_decay_fail_closed` | Width 3 or 33; denominator 0; num>den; also valid zero decay | Four invalid statuses 2/2/4/4 and one valid silent zero |
| `test_invalid_state_threshold_and_reset_fail_closed` | Out-of-range old voltage/bias/reset, nonpositive/too-large threshold, reset>=threshold | Each status 4, zero state/spike |
| `test_identical_old_state_is_tick_independent` | Same mathematical request at ticks 0,1,9999999 | Identical result each time; tick is metadata and no persistent hidden core state |
| `test_delayed_self_loop_and_parallel_signed_edges` | One-neuron recurrent self-edges delay 1 inhibitory, delay 2 excitatory, external ticks 0 and 2 | Both M02 oracles and all 6 ticks of C++ output agree; tick 0 fires, tick 1 voltage -1, no same-tick feedback |
| `test_host_protocol_rejects_unrepresentable_or_malformed_fields` | Host-only CLI parses one row with out-of-range u32 decay/ID, i64 current, missing fields or trailing tokens | Process exits nonzero (2) and emits no silent result; confirms explicit bounded transport rejection, **not** that future hardware/scheduler checks it |
| `test_randomized_networks_match_two_m02_oracles_all_ticks` | 4 widths × 4 deterministic seeds, each 5 neurons, 14 parallel/recurrent/signed edges, 35 possibly duplicate/unsorted currents over 8 ticks, decay ratio 0..10/10 | 16 entire `8x5` full-voltage/spike comparisons and independent dense/event exact parity |

## What has been run vs what remains

- **Observed here before remote CI:** native `g++` C++17 compilation of the isolated candidate and CLI with strict warning flags **PASS**, plus several manually hand-calculated host CLI queries (negative division, equality threshold, positive/negative huge currents and invalid flags) **PASS**. These are local *developer smoke checks*, **not** operator-source/commit-pinned verification and do not establish the 12-method Python suite PASS.
- **M04 full suite:** **CI PASS** (13 methods, 16 seeded randomized subcases); the [M04 host run](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42452694640) job log shows all 13 method names individually `ok`, `Ran 13 tests`, `OK`. **User-local original native evidence remains pending**. Reproduce via [M04_PC_ONLY_VERIFICATION.md](M04_PC_ONLY_VERIFICATION.md).
- **Regressions:** the *same* [M04 CI job](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42452694640) logged `Ran 28 tests` / `OK`, `Ran 21 tests` / `OK`, and `Ran 20 tests` / `OK`. Independent [M03](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42452694625), [M02](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42452694621), and [M01](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42452694552) no-board workflows also concluded `success` at the same code commit; this is **CI**, not user-PC reproduction.
- **M04.4:** no Vitis HLS/Vivado tools in this agent environment; HLS C simulation, synthesis, C/RTL cosimulation, routed timing, PL DDR transfers, A53/PS control, JTAG, power and physical correctness **NOT RUN**.

## Explicit coverage limits

The C++ update uses signed 64-bit current and 32-bit decay numerator/denominator, whereas Python M02 allows unbounded exact integer aggregates and denominators. The current candidate **does not** cover every legal M02 input. In particular the scheduler must fail closed if a sum cannot fit i64 or the ratio cannot fit u32; native tests here do **not** prove its future hardware aggregator enforces that. The CLI also cannot prove that the same logical neuron is processed only once per tick, that queues preserve positive delays, that AXI/DDR routing works, or that a streaming pipeline achieves II=1. Host C++ compilers do not establish HLS synthesis, Fmax, resource costs, numerical correctness of future RTL, or physical performance.

**Review gate:** M04 cannot be accepted or merged until source/CI tests actually pass, the user independently reproduces native tests, and gives explicit approval. No physical FPGA authorization is included.
