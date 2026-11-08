> **LATEST native verification and RTL gate (2026-11-08):** **103 M05 named native methods** (existing 92 plus **11 synthetic source-only audit-parser tests**) + **91 accepted M01–M04** = **194 named native tests**. Five HLS benches additionally compiled/run natively; hardware-optimized signed32 rolling has passed operator-run real Vitis CSim + synth + XSim cosim (10/10 transactions), **not** routed or on-board. New [canonical optimization ledger](M05_EVALUATION_ENGINE_EVOLUTION.md) and [evidence audit parser](../scripts/m05_hls_evidence_audit.py) ensure next area/timing measurements are recorded with exact source+testbench identities, and no false performance comparisons. Next offline `--rolling --impl`.
>
> **LATEST M05.5 STATUS (2026-11-08):** Operator's optimized **signed32** rolling HLS top genuine Vitis 2025.2 K26 **CSim + synthesis PASS**, commit `827f719778472da39ffa294b431ee848fe360529`, original `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_synth_20261108T193909Z_169727`. HLS estimated period **8.256ns** vs requested 10ns; **39 BRAM18K** (down 14 from prior i64 rolling 53), including `current_U` **16 BRAM18K** vs old 30; 9,956 LUT, 8,346 FF, 2 DSP. The single-port bias II lower-bound-2 warning remains; full-run latency unknown. **i32 rolling XSim C/RTL cosim NOT YET RUN** (the old i64 rolling version was verified). `m05_rolling.cpp` source **unchanged** since this synthesis, sha `e5443aa87dcc8819ee8aa680b6ca105facc1aced`. After it, developed a strictly HOST-ONLY [transactional output accept/abort gate](M05_TRACE_COMMIT_GATE_2026_11_08.md): validates row-major framing and per-tick counts, drains provisional records, commits only on final status 0 plus expected row count, discards the whole run on late status, malformed framing or timeout. Added 16 native receiver/model/CLI tests including a toy 1-beat FIFO stall model; **92 M05 +91 accepted prior=183 named native tests PASS**. This is NOT an AXIS RTL/TREADY test, DMA/PS driver, real hardware recovery or physical timing. **NEXT OPERATOR GATE:** after pulling current branch run `--rolling --cosim` (cumulative real CSim, synth then XSim), preserve original reports. M05 remains OPEN, PR #79 DRAFT/UNMERGED; no board operations. [Full boundary and commands](M05_TRACE_COMMIT_GATE_2026_11_08.md).
>
> **LATEST 2026-11-08 VERIFIED RTL AND NEW SOURCE OPTIMIZATION:** The operator's **unchanged i64 rolling engine** at commit `03c3fbc5f8866c44510ff67d2cce8151988fa4d7` has now passed **actual Vitis HLS 2025.2 CSim, synthesis AND XSim C/RTL cosim**. Report: Verilog PASS, all **8/8 transactions**, latency **265 / 3616 / 16492 cycles** min/avg/max, intervals **285 / 3919 / 16512 cycles**, **29077 cycles total**, simulated 10ns clock. Old synthesis **53 BRAM18K (30 for 64-bit current_U), 10,083 LUT, 8459 FF, 2 DSP**, estimated 8.244ns vs 10ns requested. **NEW development since that PASS:** changed only fifth rolling top's internal current wheel `[8][1024]` from signed i64 to **signed i32**, mathematically exact under max 4096 individual signed W16 deliveries per tick (bounds **-134217728 .. +134213632**, signed28 sufficient), and preserve i64 M04 API via explicit sign extension. Added HLS CSim/RTL vectors for both extremal 4096-arrival polarities and 4096 negative delayed recurrent synapses at t+8, plus two M02/M03 full reference tests. **76 M05 + 91 older = 167 named native tests PASS**; current code's genuine Vitis CSim/synthesis/cosim **NOT YET RUN**. NEXT: pull branch and run cumulative `bash hls/m05_stream_eval/run_m05_offline_hls.sh --rolling --synth` (new genuine CSim first; then synth), compare previous current_U 30/total 53 BRAM18K before any new cosim. No physical action, M05 OPEN/PR #79 UNMERGED. [Signed32 proof + gates](M05_ROLLING_I32_ACCUMULATOR_2026_11_08.md).
>
> **LATEST verification count (2026-11-08):** **74 M05 native methods PASS** (14 rolling including new max-horizon 64-tick M02/M03 complete-trace parity and 1024 logical-neuron-boundary test) + **91 accepted M01–M04 = 165 native methods**; 5 HLS testbenches additionally compiled natively. The real rolling HLS synthesis passed on source commit `984f5baf45ce771e94e1e8b2947e1ef27ccc6d58`, new stronger rolling bench is not yet tested under actual Vitis; next gate `--rolling --cosim` cumulative. See [rolling design](M05_ROLLING_WHEEL_DESIGN_2026_11_08.md). Older counts below are historical.

> **LATEST 2026-11-08:** **72 M05 +91 M01–M04 = 163 named native regression tests**, five native-compiled HLS-Csim vector benches. New [12 rolling-wheel native tests](../tests/test_m05_rolling.py) exercise 24–40 tick full-trace M02 dense/event and M03 sparse parity, 8-slot wrap, signed coalescing and count, 4097 late-event invalidation, sorted external ingress and 8-tick delay bounds. Four earlier tops (including integrated) now have **operator-run genuine Vitis CSim + synthesis + XSim cosim PASS**. New *fifth* rolling top has **native-only** PASS; real Vitis is next. Older count/verification paragraphs below are preserved as historical snapshots. [Rolling design and exact commands](M05_ROLLING_WHEEL_DESIGN_2026_11_08.md).

# M05 — Tests explained (native stream candidate + PC event scheduling)

**CURRENT 2026-11-08 STATUS:** Three standalone IPs have real operator-run Vitis CSim, HLS synthesis and XSim cosim PASS. The fourth integrated finite-horizon candidate has **12 new native network tests** and a **native CSim bench PASS**, but has **NOT** been evaluated with genuine Vitis or RTL. **60 new M05 methods + 91 accepted earlier methods = 151 native test methods PASS**; M05 remains OPEN. The original failures/old host-only verification counts in historical sections below are provenance notes, not current gate results.

**Status:** M05 IN PROGRESS, not user-accepted. M05 has **60 named PC-native unittest methods** across [17 streaming/scheduler](../tests/test_m05_stream.py), [12 persistent state memory](../tests/test_m05_stateful.py), [11 signed tick accumulator](../tests/test_m05_accumulator.py) [5 HLS setup/runner safety](../tests/test_m05_hls_setup.py) [3 Vitis-workdir path regressions](../tests/test_m05_hls_path_regression.py) and [12 integrated finite-horizon network tests](../tests/test_m05_integrated.py); additional seeded cross-tick subcases are counted within methods. Accepted regressions: M04 **22**, M03 **28**, M02 **21**, M01 **20**, for **151 named methods total**. Four separate checked-in HLS Csim vector benches are also compiled and executed NATIVELY by CI, not in Vitis.

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


## NEW M05 integrated finite-horizon scheduler — 11 native whole-network methods

[Design details and safety boundary](M05_INTEGRATED_FINITE_HORIZON_DESIGN.md). Actual C++ [integrated top](../hls/m05_integrated/m05_integrated.cpp) owns 1,024 neuron states, a resident 4,096-edge adjacency graph, eight future-tick signed i64 aggregate+touch+delivery-count buckets and all neural steps in a **single** call. No Python logical-tick service. The CSim vectors in [m05_integrated_csim_tb.cpp](../hls/m05_integrated/m05_integrated_csim_tb.cpp) exercise self recurrence, over-capacity no-output, and a subsequent clean run; compiled natively by CI. **Neither these new tests nor the prior genuine real Vitis results for the three different tops establish integrated HLS or RTL PASS.**

| Exact new method | What is independently checked |
| --- | --- |
| `test_native_csim_vectors` | Compile and execute the separate integrated HLS CSim vector source natively |
| `test_exact_zero_bias_wakeup_with_no_external_events` | Bias wakeups and exact zero/biasless idle skips across all ticks |
| `test_unsorted_zero_and_canceling_deliveries_remain_touched` | Input order independence; zero and signed canceling terms count as touched |
| `test_recurrent_self_parallel_edges_and_future_delays` | Self, parallel, negative edge weights, positive delays, delayed graph fanout |
| `test_negative_decay_rounding_and_threshold_equality` | Truncate-toward-zero leak and inclusive threshold/reset |
| `test_all_4096_signed_deliveries_are_exact_and_admitted` | Full signed W16 admission count with exact i64 pre-clamp aggregate |
| `test_4097_external_deliveries_fail_before_any_trace` | External over-capacity status with no output |
| `test_4097_recurrent_deliveries_fail_before_any_trace` | Future-bucket recurrent overflow causes entire trace to be suppressed |
| `test_horizon_and_shape_validation_no_publication` | Reject 0/9 ticks, zero neurons, invalid unsigned decay ratio |
| `test_invalid_neuron_synapse_and_external_fail_closed` | Invalid threshold/delay/tick/W16 reject without output |
| `test_native_wrapper_rejects_extra_unframed_fields` | Reject trailing malformed data in the test-only native command adapter without publishing a misleading result | 
| `test_seeded_networks_full_trace_and_sparse_schedule` | 16 seeded recurrent networks, 8 ticks each; every voltage, spike, touched worklist and arrival count compared against independent M02 dense, event, and M03 sparse |

**Count now:** 60 M05 named PC-only methods + 91 M01–M04 = **151 native methods**, plus four native-compiled CSim vector benches. **NEXT REAL TOOL GATE:** new fourth `--integrated --csim`, then `--synth`, then `--cosim`, preserving full original Vitis evidence outside Git.
