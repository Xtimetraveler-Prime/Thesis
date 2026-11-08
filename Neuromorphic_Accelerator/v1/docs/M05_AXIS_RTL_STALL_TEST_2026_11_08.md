# M05.6 — Direct RTL ready/valid and output trace stall test (operator gate)

**Status:** harness and local prep tests committed; **genuine direct Verilog XSim test has NOT yet been run on the operator's Vivado 2025.2 workstation**. This does NOT claim that the current HLS C/RTL co-simulation already tested intentional stalls. No KV260, JTAG, PS/DDR, Vivado block-design edits or device programming.

## First operator-run failure, diagnosed (2026-11-08)

The first invocation of `bash scripts/run_m05_rolling_rtl_stress.sh "$ROLL_IMPL"` checked out at `c6ac13e114037db513c21af82175595ef540244b` produced evidence `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_20261108T203112Z_209004` with `exit_status=1`. The generated AXI-Lite register map was parsed successfully from the **actual Vitis driver header**, and all HLS-generated Verilog files parsed. **The NEW testbench itself did not compile**:

```text
ERROR: [VRFC 10-4982] syntax error near '"trace=24; stalled_output_cycles=%0d; ingress_gap_cycles=%0d;' [tb_m05_rolling_axis_stress.sv:305]
```

Root cause: a `$display` call had **three adjacent string literals** on separate lines instead of one SystemVerilog format string. Repaired to one literal, and added a source-only native regression to prevent reintroduction. This event is **not a failure of the previously routed rolling engine**; the simulation did not reach `xelab` or `xsim`. **Please re-pull branch and rerun the exact offline stress command**, allowing the script to produce a fresh evidence folder. The repair is not a genuine RTL PASS until new `xvlog`, `xelab`, and `xsim` logs verify it. Leave failed evidence untouched.

## Why this gate is now appropriate

The evaluation engine has completed every preceding numerical / feasibility milestone on the target K26 `xck26-sfvc784-2LV-c`:

- Native 2026-11-08: full independent M02/M03/M04 oracle tests PASS for signed W16 and signed32 temporal wheel.
- Vitis HLS 2025.2 real `--rolling --cosim` at commit `07913bbf925e5cd1ffc0d84dd6f9d5b4c2ee519a`: genuine XSim Verilog PASS, **10/10 testbench transactions**, including 64-tick recurrent, exact ±4096 bound, alias, late failure and multiple runs.
- Vitis HLS actual `--rolling --synth` at commit `827f719778472da39ffa294b431ee848fe360529`: **39 BRAM18K**, 9956 LUT, 8346 FF, 2 DSP; estimated period 8.256ns (10ns target).
- **NEW Vivado OOC place+route PASS** from `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_impl_20261108T200432Z_186026` at commit `334ca0ee78c2651019d72101f23f253b62396aed`: **required 10.000ns, post-route period 6.503ns, WNS +3.497081ns, WHS +0.055000ns**, zero unrouted nets, **6257 LUT, 6887 FF, 35 BRAM, 2 DSP**. This is NOT a complete physical FPGA system.

The canonical [evaluation-engine optimization ledger](M05_EVALUATION_ENGINE_EVOLUTION.md) records every source variant, resource utilization, distinct stage and original folder. The i32 kernel `hls/m05_rolling/m05_rolling.cpp` is deliberately **unchanged** for this follow-on gate.

## New hardware-targeting test files

1. [`hls/m05_rolling/rtl_stress/tb_m05_rolling_axis_stress.sv`](../hls/m05_rolling/rtl_stress/tb_m05_rolling_axis_stress.sv): SystemVerilog testbench that instantiates the **actual generated `m05_rolling_replay` RTL top**, connects AXI-Lite control and 4 AXIS ports, drives a two-neuron, 12-tick network with one `pre0→post1`, weight +5, delay 8 synapse and one external tick0 +5 event.
2. [`scripts/m05_axis_regmap.py`](../scripts/m05_axis_regmap.py): derives AP_CTRL/AP_RETURN and all six parameter addresses from **the actual Vitis-generated `*_hw.h`** or (if `package.output.format=rtl` exported no software header) parses the generated `m05_rolling_replay_control_s_axi.v` localparams. Refuses collisions, bad width, missing addresses, and conflicting copies. **No hardcoded guessed addresses.**
3. [`scripts/run_m05_rolling_rtl_stress.sh`](../scripts/run_m05_rolling_rtl_stress.sh): offline `xvlog → xelab → xsim` workflow which consumes **only a previously successful** rolling `--impl` evidence directory. It checks source SHA256 against the currently checked-out RTL input kernel, target part/top, and status 0; creates a **new exclusive** `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_*` directory. It does not rerun HLS, rewrite source RTL, edit an existing Vivado project, or program the board.
4. [`tests/test_m05_axis_rtl_prep.py`](../tests/test_m05_axis_rtl_prep.py): **14 native Python tests** of the generated-register map parser, missing software-header fallback, safe source provenance and bench signal/runner contracts. These native tests **do not run actual Verilog, compile SV, or drive AXIS**; only workstation XSim can close the gate.

### Explicit stall/scoreboard contract

- **Input TVALID gaps:** neuron/synapse/external source drivers assert VALID only on scheduled clock patterns and do not withdraw a stalled beat before handshake. This is a real *clock-level* stimulus for the generated RTL.
- **Output TREADY stalls:** the sink permits only **one trace beat in every 11 clock cycles**, forcing backpressure. Every cycle after `TVALID=1,TREADY=0` must preserve `TVALID` and the exact 192-bit `TDATA` until a handshake; a violation is an immediate `$fatal`.
- **Accepted-row oracle:** for this tiny workload, neuron0 spikes at tick0 and neuron1 at tick8. The scoreboard validates **24 sequential trace beats**, tick/neuron ordering, W16 voltage, spike/evaluated flags and per-tick `delivered_count`. A duplicate/extra/missing record, timeout, wrong AXI-Lite return status, incorrect input counts, no real stalls, or wrong field alignment is an immediate `$fatal`.
- HLS generated RTL uses padded C-layout AXIS structs, not concatenated dense bitfields. The bench uses widths from the real top HLS report (**neuron 128, synapse 192, external 128, trace 192 bits**), checks semantic fields and ignores padding fields. **If the exported RTL uses a different layout, stop and examine the actual generated TDATA definitions; do NOT weaken the checking logic to force PASS.**
- AXI-Lite start/config is performed once per **run**, not per tick; the bench only polls `ap_done` **after concurrently draining the expected trace** and checks the final status via the generated register offset.
- Test currently covers **one successful 12-tick stream** under explicit stalls. It does **NOT** yet prove robustness under randomized seeds, invalid input at RTL, long multi-run resets, transaction ID tags, DMA/DDR, or physical link backpressure. The host `RollingTraceCommitGate` remains native-only.

## Operator commands (NO BOARD)

After pulling the latest existing M05 development branch:

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
cd Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m05*.py' -v

# With Vivado 2025.2 environment sourced, use exactly the known successful
# implementation folder, not "ls -dt | head -1" (which might choose another).
export ROLL_IMPL="$HOME/Thesis_Evidence/neuromorphic_v1_m05_rolling_impl_20261108T200432Z_186026"
bash scripts/run_m05_rolling_rtl_stress.sh "$ROLL_IMPL"
```

This is an **experimental new RTL test**, not an already established green Vitis stage. A simulator elaboration error may mean a generated Verilog dependency, AXI-Lite port naming, or control address map needs adaptation; it is **not automatically a logical engine failure**. An RTL trace mismatch or VALID/TDATA stability failure *after successful elaboration* is more informative and must be treated as a serious hardware verification issue.

The runner returns a new evidence directory. On success or failure capture:
```bash
export AXIS_EVIDENCE="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_* | head -n 1)"
cat "$AXIS_EVIDENCE/result.txt"
cat "$AXIS_EVIDENCE/commit.txt"
cat "$AXIS_EVIDENCE/source_impl_evidence.txt"
cat "$AXIS_EVIDENCE/m05_rolling_regmap.svh" 2>/dev/null || true
tail -n 100 "$AXIS_EVIDENCE/02_xvlog.log" 2>/dev/null || true
tail -n 100 "$AXIS_EVIDENCE/03_xelab.log" 2>/dev/null || true
tail -n 100 "$AXIS_EVIDENCE/04_xsim.log" 2>/dev/null || true
```

Leave all raw old/new evidence folders unchanged; do not delete untracked original v2 hardware logs and Vivado journals. **A native green GitHub CI run is not a direct RTL stress PASS.**

## Future gates and known integration limits

1. Expand actual RTL stall testing to multiple ordered/malformed workloads, several deterministic gap patterns and deliberate late failure; wire the sink to the host transactional commit/discard policy.
2. Develop an explicitly bounded concurrent ingress feeder / AXIS output drainer + completion monitor for the target PS/PL transport, using the exact HLS-padded struct ABIs and actual AXI-Lite map. Establish reset/retry protocol after timeout.
3. Add performance counters measured for controlled identical workloads, and extend beyond 64 ticks / 8 delayed recurrent slots without discarding pending events.
4. Only after explicit owner approval begin a physical-device integration on the FPGA. Out-of-context timing alone cannot establish DMA feasibility or whole-shell timing closure.

**Status: M05 OPEN; PR #79 DRAFT/UNMERGED; no physical board operation authorized or performed.**
