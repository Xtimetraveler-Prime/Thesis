# M05 — Tests explained (native stream candidate + PC event scheduling)

**Status:** M05 IN PROGRESS, not user-accepted. M05 has **48 named PC-native unittest methods** across [17 streaming/scheduler](../tests/test_m05_stream.py), [12 persistent state memory](../tests/test_m05_stateful.py), [11 signed tick accumulator](../tests/test_m05_accumulator.py) [5 HLS setup/runner safety](../tests/test_m05_hls_setup.py) and [3 Vitis-workdir path regressions](../tests/test_m05_hls_path_regression.py); additional seeded cross-tick subcases are counted within methods. Accepted regressions: M04 **22**, M03 **28**, M02 **21**, M01 **20**, for **139 named methods total**. Three separate checked-in HLS Csim vector benches are also compiled and executed NATIVELY by CI, not in Vitis.

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

**Observed CI:** initial M05 compile **failed** on `-Werror=unused-label` in the HLS top; removed label without changing behavior. Tightened an invalid u32-denominator fixture. [Run 42454758437](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42454758437) at `cd483fe5` logged **17 M05 PASS, 22 M04 PASS, 28 M03 PASS, 21 M02 PASS, 20 M01 PASS**. HLS source/documentation additions require final HEAD CI recheck.

**What these tests do NOT establish:** HLS synthesis, C/RTL co-sim, actual AXIS backpressure, real bounded event FIFO or future queue, on-chip state memory ownership/RAW hazards, DDR/AXI traffic, microarchitectural II/latency, routed clock, physical FPGA performance, energy or Loihi/YANA equivalence. [HLS Csim vectors](../hls/m05_stream_eval/m05_hls_csim_tb.cpp) are **unexecuted** Vitis inputs; include no fake HLS PASS. M05 operator native testing and user approval remain pending. See [M05 verification](M05_PC_ONLY_VERIFICATION.md) and [v3 comparison](M05_ENGINE_V3_COMPARISON.md).


## Additional independent native Csim-testbench smoke gate (not a unittest method)

The M05 workflow now also compiles [`m05_hls_csim_tb.cpp`](../hls/m05_stream_eval/m05_hls_csim_tb.cpp) against the *same* C++ M05 kernel/M04 step via native `g++`, runs it, and requires the testbench's fixed scalar fixtures to return PASS. This confirms the staged Vitis testbench **itself** is internally consistent under the host-only stream shim. It does **not** add an 18th unittest method, call Vitis, prove AXIS ready/valid, achieve II=1, or demonstrate C/RTL parity. **Genuine Vitis HLS Csim/synthesis/C-RTL remain NOT RUN.**


## M05.3 — 12 additional named tests for the persistent 1,024-row state memory candidate

**Source:** [`test_m05_stateful.py`](../tests/test_m05_stateful.py), actual [C++ stateful HLS top](../hls/m05_stateful/m05_stateful.cpp), [text CLI](../hls/m05_stateful/m05_stateful_host_cli.cpp), and [separate HLS Csim vectors](../hls/m05_stateful/m05_stateful_csim_tb.cpp). C++ `static` voltage/bias/threshold/reset arrays and last-tick tags persist across successive function invocations in one process. Memory `BIND_STORAGE` requests BRAM; **native g++ does not establish physical BRAM inference**. The top rejects invalid/duplicate/backward ticks without changing stored state; it does not enforce global tick barrier or external event queue safety.

| Exact new method | Mechanism and required output |
| --- | --- |
| `test_init_read_and_clear_invalidate_without_leaking_old_data` | CLEAR → READ rejects uninitialized; INIT voltage=-11, READ exact; CLEAR then READ rejected, never stale state. |
| `test_negative_decay_inclusive_spike_and_reset` | INIT -3, update with 1/2 gives -1, next input +6 crosses inclusive threshold and resets -2. |
| `test_duplicate_tick_rejected_no_state_write` | First tick4 update accepted; second tick4 returns duplicate status6/zero; READ confirms prior committed voltage. |
| `test_stale_tick_rejected_and_gap_is_allowed_if_scheduler_proves_skip` | Tick9 accepted, tick3 rejects as stale status7, tick11 later accepted; skip legality is still external scheduler responsibility. |
| `test_invalid_init_and_invalid_step_no_state_update` | Out-of-W16 init, invalid threshold/reset and invalid denominators return error4; later READ verifies no write. |
| `test_duplicate_initialization_rejected_unless_cleared` | INIT twice gives status5; CLEAR permits a fresh INIT epoch. |
| `test_invalid_opcode_and_id_fail_closed` | Unknown command, zero/oversized network, or out-of-range neuron ID rejected with zero state/spike. |
| `test_two_neurons_can_advance_in_different_dispatch_order` | Two independent neuron rows processed in non-ID order; spike/reset and negative voltage preserved, demonstrating no old core scan. |
| `test_1024_neuron_physical_capacity_and_independent_state` | INIT all 1,024 row IDs with distinct voltages, READ nonadjacent IDs for independence; this is C++ storage, not BRAM proof. |
| `test_saturation_must_follow_exact_64bit_aggregate` | i64 max/min input triggers one W16 clamp and inclusive spike/reset; no early event-wise clipping. |
| `test_m02_dense_and_event_traces_match_stateful_ram_across_ticks` | **8 deterministic networks**, five neurons each, 13 signed/delayed recurrent edges and 25 currents; all 8×5 update outputs and spikes match BOTH accepted M02 oracles. |
| `test_malformed_or_unrepresentable_cli_inputs_rejected` | Missing, extra, negative-count, non-integer or unrepresentable fields exit 2 without misleading partial output. |

## M05.2 — 11 additional named tests for the tick-sealed signed-aggregate PL candidate

**Source:** [`test_m05_accumulator.py`](../tests/test_m05_accumulator.py), actual [C++ accumulator](../hls/m05_accumulator/m05_accumulator.cpp), [text CLI](../hls/m05_accumulator/m05_accum_host_cli.cpp), and [HLS Csim vectors](../hls/m05_accumulator/m05_accum_csim_tb.cpp). The one-tick store has 1,024 logical ID slots, signed i64 exact sums, a **SEAL barrier**, 4,096 individual W16 contributions/tick, and **sticky-invalid no-readout on error**. There is **no physical future-delay FIFO or router** yet.

| Exact new method | Mechanism and required output |
| --- | --- |
| `test_signed_cancellation_sealed_aggregate_matches_exact_sum` | +32767,-32768,+6 → exact +5, delivered flag1 for ID1; no current for ID0; read only after SEAL. |
| `test_4096_signed_contributions_success_including_zero` | 4,096 W16 signed values, including cancellations, accepted; exact -2048 and count 4096 on final read. |
| `test_4097th_signed_contribution_fails_closed_without_readout` | 4,097th W16 event rejects status5 and latches invalid; SEAL/READ reject status10 until explicit CLEAR. |
| `test_invalid_w16_current_sticky_failure_and_rearm` | Current +32768 outside W16 rejects and locks readout; CLEAR plus new tick allows -32768 exactly. |
| `test_duplicate_begin_or_unknown_opcode_invalidates_current_tick` | Second BEGIN or illegal opcode sets sticky failure; all later work rejected until CLEAR. |
| `test_read_before_seal_is_failure_not_partial_current` | Reading accumulated current while tick is open produces status7, then sticky status10; never exposes partial sum. |
| `test_sealed_tick_rejects_late_add_and_refuses_earlier_sum` | Valid READ succeeds after SEAL; subsequent ADD causes phase error9, then READ refuses previously valid data. |
| `test_wrong_tick_or_neuron_id_or_network_size_fail_closed` | Old tick, ID>=count, or mismatched count rejects, prevents corrupted cross-neuron/current routing. |
| `test_multiple_ticks_reset_touch_without_modifying_old_sum` | New tick clears touched flags; zero-attendance neuron reports zero even if previous tick held a nonzero signed aggregate. |
| `test_m02_recurrent_delivery_aggregate_across_seeded_networks` | **6 seeded recurrent networks**, six ticks each; external and delayed synapses enumerated using accepted M02 spike rows, then every sealed (tick,ID) sum/touched/count checked against independent enumeration. This validates aggregation, **not** future event routing in PL. |
| `test_malformed_transport_rejected_without_partial_results` | Host CLI missing/extra/invalid values cause parse error without partial output. |

## Five HLS config/offline runner tests (source and shell static checks ONLY)

**Source:** [`test_m05_hls_setup.py`](../tests/test_m05_hls_setup.py). Methods:
- `test_three_isolated_k26_configs_have_documented_2025_2_keys`: compare **all three** configs to documented `part=xck26-sfvc784-2LV-c`, `clock=10ns`, 12% uncertainty, `flow_target=vivado` and **`syn.output.format=rtl`**; reject old invalid `package.output.format`.
- `test_configs_reference_real_sources_and_independent_benches`: ensure every `syn.file`/`tb.file` in all 3 configs exists in current checkout and `csim.clean=true`.
- `test_offline_runner_bash_syntax_help_and_bad_flags`: `bash -n`, offline script `--help`, and invalid/duplicate option rejection before running Vitis.
- `test_offline_runner_never_invokes_board_or_old_v3_scripts`: static blocklist of JTAG/HW manager commands and no destructive `rm -rf`; original evidence folder/new run and failure trap required.
- `test_three_tops_are_distinct_and_syn_top_always_matches`: verify top signatures, persistent-state BRAM hints, accumulator overflow control, and script top selection.

**Observed source-only CI:** [M05 run 42456476435](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42456476435), source commit `7cb863b6`: **45 M05 tests PASS**, previous **91 tests PASS**, and **three separate HLS vector testbenches compiled/run with native g++ PASS**. Initial new accumulator test failed because a Python expected-row index was off by one; fixed and reverified, with no accumulator arithmetic change.

**Not validated:** actual 2025.2 HLS Csim/synthesis, RTL equivalence, inferred BRAM/URAM, achieved II/latency/Fmax, AXIS framing/backpressure, on-chip temporal FIFO/synaptic fanout, integrated global tick barrier, PS/AXI/DDR interface, physical K26 or overall speedup. Do not accept M05 as complete based only on native results. **Exact operator HLS stages and required original logs:** [M05_HLS_OPERATOR_RUNBOOK.md](M05_HLS_OPERATOR_RUNBOOK.md). M05 remains OPEN and unmerged pending user verification.


## 2026-11-08 genuine Vitis HLS CSim failure and three new workdir-path regressions

**Real operator evidence (not a CSim PASS):** all three Vitis 2025.2 CSim runs from initial commit `6f5ca78a` **FAILED** before source compilation, with warnings `HLS 200-2001` about missing `syn.file`/`tb.file`, followed by `HLS 200-627` no testbench; Vitis had changed into the evidence folder where old `relative_roots=cwd` no longer referred to the project. It additionally warned `syn.output.format` was deprecated, superseded by `package.output.format`. [Line-level error and remediation](M05_HLS_CSIM_FAILURE_2026_11_08.md).

**Correction:** [`prepare_hls_config.py`](../hls/m05_stream_eval/prepare_hls_config.py) creates a new evidence-local, validated `hls_effective_config.cfg` with absolute design/testbench/include paths and canonical package output format; the [runner](../hls/m05_stream_eval/run_m05_offline_hls.sh) passes it to **each** Vitis command and preserves config/report hashes. The original failed operator evidence is untouched.

**New methods (three named tests):**
- `test_all_three_effective_configs_resolve_from_unrelated_directory`: generate per-run configs for **each** top, prove all referenced C++ files exist via absolute paths even after changing outside the project, verify checked-in templates remained unchanged.
- `test_absolute_config_is_exclusive_and_fails_on_missing_input`: fail explicitly if a C testbench is absent (instead of leaving the error for Vitis) or if an output INI is being overwritten.
- `test_offline_runner_three_kernels_survive_vitis_chdir_with_stub`: run the **actual no-board runner** three times against an **explicitly fake Vitis executable** that changes CWD into each external evidence directory, validates the effective config, and checks that original logs/config hashes/result files are produced. **Stubbed tool output is NOT genuine Vitis CSim.**

The existing five HLS setup tests now assert the corrected `package.output.format=rtl` and `relative_roots=file/../..` (template), plus runner use of the generated effective config, instead of enforcing the deprecated key. Prior 45 M05 tests unchanged; new count **48 M05**, accepted regressions **91**, total **139** named host tests. Real successful Vitis Csim/synthesis/C-RTL evidence is still **NOT RECEIVED**; rerun the three actual CSim steps per [updated operator instructions](M05_HLS_OPERATOR_RUNBOOK.md) and review the original outputs before proceeding.
