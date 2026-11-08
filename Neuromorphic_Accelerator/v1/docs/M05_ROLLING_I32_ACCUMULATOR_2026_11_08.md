# M05 rolling temporal wheel — provably exact signed-32 current storage

**Status:** new candidate source and native tests PASS; **GENUINE VITIS 2025.2 CSim, synthesis, and RTL co-simulation for this i32 change are NOT YET RUN**. The previously synthesized and operator-co-simulated i64 version is preserved in Git history at commit `03c3fbc5f8866c44510ff67d2cce8151988fa4d7`. Both are within draft/unmerged PR #79 and the same existing M05 research branch. No board/JTAG/DDR changes.

## Verified i64 baseline — user-provided report

The K26 2025.2 i64 `m05_rolling_replay` engine passed CSim, HLS synthesis and Verilog XSim C/RTL co-simulation at source commit `03c3fbc5f8866c44510ff67d2cce8151988fa4d7`:
- **Synthesis:** return 0; requested 10ns, **estimated 8.244ns**, **53 BRAM18K, 10,083 LUT, 8,459 FF, 2 DSP**. `current_U` `[8][1024]` × 64 bits occupied **30 BRAM18K** alone; no routed timing or physical board execution.
- **C/RTL:** XSim Verilog PASS, **8/8 testbench transactions**, C post-check PASS, `[COSIM 212-1000]`, `exit_status=0`. Clock-cycle latency **minimum 265, average 3616, maximum 16492**. Transaction intervals **minimum 285, average 3919, maximum 16512**. Total RTL simulation **29077 cycles**. At simulated 10ns, average transaction latency = **36.16µs**, but the eight test cases vary substantially. **These results do NOT quantify physical K26 throughput, neuron-updates/second or comparable per-tick performance.**
- Original user cosim report time **2026-11-08 12:30:45 MST**, matching verified HLS commit SHA above. Generated evidence stored locally by the operator under `~/Thesis_Evidence/`; raw reports intentionally NOT tracked in Git.

## Why signed 32-bit temporal accumulation is exact for our admission profile

The device still accepts **at most 4096 individual delivery events PER TICK, ACROSS ALL NEURONS**, counting independent external + recurrent contributions, zero-value events, and canceling events. Every legal contribution is a signed **W16** number in `[-32768, +32767]`.

For *any* single logical tick `t`, neuron `i`, and *any* legal event ordering, at most 4096 terms can have accumulated in its current cell before the cell is cleared. Hence every intermediate sum is within:

```text
minimum = 4096 * (-32768) = -134217728 = -2^27
maximum = 4096 * ( 32767) = +134213632 < 2^27
```

The result fits signed **28 bits**, so signed **32 bits** has margin and cannot overflow for an admitted tick. The same bound applies to recurrent fanout, including 4096 parallel synapses arriving at delay 8. The delivery counter increments and cap is checked **before** writing each term. This invariant would NOT hold if max arrivals per tick or contribution bitwidth were later increased without revisiting the proof.

The only physical memory change is `current[8][1024]` from `std::int64_t` to `std::int32_t`. **The external `M04Request::aggregated_current` remains signed 64-bit**; the exact W32 value is sign-extended when passed to the untouched accepted M04 LIF evaluator. Voltage, weight, touch, trace, and count semantics are unchanged. We still saturate once, AFTER sum + leak + bias, **never clip individual current contributions**.

This optimization reduces the current store's raw bits from **524,288 to 262,144**, regardless of user-selected run length (up to 64 ticks). HLS previously mapped that memory to 30 BRAM18K; a substantial BRAM reduction is plausible, but **new actual BRAM count and clock estimates must be measured using Vitis synthesis, not asserted as achieved**. Graph delays remain limited to 1–8, and output is still speculative until final successful return.

## Source and independent tests

- `hls/m05_rolling/m05_rolling.cpp`: i32 wheel, compile-time static bounds checks using `std::numeric_limits<std::int32_t>`, and explicit i32→i64 sign extension on the accepted M04 interface. No edits to `m05_integrated_replay` or `m04_eval_one`.
- `hls/m05_rolling/m05_rolling_csim_tb.cpp`: existing 64-tick independent dense oracle, wheel wrap, 2→1→2 epoch reset, late error and 4097th event invalidation, PLUS:
  - **8192 external events** across 2 separate ticks (each **exactly 4096**) with W16 all-positive and all-negative extreme values, checking spike/voltage/eligibility/count.
  - **4096 negative recurrent parallel synapses** to one target at `t+8` across a physical wheel slot alias, checking exact negative-endpoint arithmetic.
- `tests/test_m05_rolling.py`: two new M02 dense/event and M03 sparse parity tests with the same W16 extremes; earlier seeded recurrence, 4096 mixed-sign count, zero cancellation, max neuron ID 1023 tests retained. **76 M05 + 91 M01–M04 = 167 named native tests PASS** and the rolling bench compiled/executed natively in the project's GitHub CI. Native CI **does not** establish actual Vitis behavior for new i32 source.

## Next operator verification gate (offline only)

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
cd Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m05*.py' -v
export HLS_PART=xck26-sfvc784-2LV-c
bash hls/m05_stream_eval/run_m05_offline_hls.sh --rolling --synth
```

The runner automatically repeats **genuine** HLS CSim before synthesis, creates a **new, exclusive** evidence directory, saves source hashes/logs/reports, and does not touch physical hardware. Stop on CSim or HLS-synthesis failure; preserve the original logs. Inspect `result.txt`, `commit.txt`, `working_tree_status.txt`, and `work/hls/syn/report/m05_rolling_replay_csynth.rpt`. Compare old **53 total / 30 current** BRAM18K to the newly observed total and `current_U` count. Also check LUT/FF/DSP, HLS-estimated period, II warning and no functional changes. Only after reviewing new synthesis, run `--rolling --cosim`; for failure the 8192-element input benchmark can expose HLS stream depth/RTL simulation issues.

**M05 remains open** until complete live backpressure/transactional output, full continuous scheduler, place-and-route/physical feasibility, and user acceptance are addressed. Do not merge without user approval.
