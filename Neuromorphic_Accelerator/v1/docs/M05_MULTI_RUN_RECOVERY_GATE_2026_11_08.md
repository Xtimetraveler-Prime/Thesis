# M05.9 — Two consecutive direct RTL executions, error recovery and state isolation

**State at development checkout (2026-11-08):** Source-only two-run XSim testbench
and native transactional replay are implemented; native CI runs the synthetic
tests but **genuine multi-run XSim result is PENDING**. The original signed32
HLS numerical kernel, its RTL implementation and both earlier passing RTL
stress benches remain byte-for-byte unchanged. M05 OPEN; PR #79 DRAFT / UNMERGED.

## Operator-confirmed M05.8 late-error gate: genuine PASS

At the Vivado 2025.2 K26 workstation, the real direct Verilog
`--late-error` stress test **PASSED** with `exit_status=0`.
Original evidence:
`~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_20261108T211756Z_234592`.
The previously routed signed32 implementation from
`~/Thesis_Evidence/neuromorphic_v1_m05_rolling_impl_20261108T200432Z_186026`
was **not regenerated**.

- Generated AXI-Lite addresses parsed from real Vitis driver; exact **11**
  tool-generated RAM `.dat` files staged, with SHA256 provenance.
- `xvlog` PASS, `xelab` PASS, **XSim PASS** against the real generated
  Verilog; source stimulated external ticks **0, 4, 3**.
- Actual RTL produced **eight provisional trace transfers** (ticks 0..3,
  two neurons each), including a real tick0/neuron0 spike.
- Actual AXI-Lite status **4: M05_ROLL_BAD_EXTERNAL**;
  **56 output stall cycles**, **436 input-valid gap cycles**.
- Actual `04_xsim.log` included
  `M05_RTL_FINAL status=4 provisional=8 committed=0`.
- Runner's **read-only host trace replay** printed
  `PASS: M05 RTL transactional replay: status=4, provisional=8, drained=8, committed=0, early_spike=1, all failure rows discarded`.
  This proves transcript-to-native receiver policy, **not** a live DMA
  consumer or a physical board interface.

Those results remain permanently in the
[canonical evaluation-engine optimization/evidence ledger](M05_EVALUATION_ENGINE_EVOLUTION.md).
M05.8 is now complete as a directed RTL failure case; it does not prove
all possible error statuses, host transport failures or physical restart.

## Why M05.9

A single successful kernel invocation does not verify **session boundaries**.
After an early/late hardware error, the next `ap_start` can theoretically
experience state leakage from the failed graph, pending temporal-wheel
slots, trace packets, stale completion status, or HLS register state.

The new test addresses that risk **without asserting `ap_rst_n` between
invocations**. It is a **fresh invocation on the same RTL module**, not a
continuous simulation longer than 64 ticks and not proof of a hardware
reset after a hard timeout.

### Run 0 — failed transaction with valid provisional prefix

- 2 neurons, 1 synapse `0→1` weight +5 delay **8**, ticks=12,
  3 out-of-order external events at ticks **0,4,3**.
- Tick0 neuron0 spikes and schedules future tick8 neuron1 input.
- Ticks0..3 produce exactly **8 provisional output beats** under deliberate
  `trace_TREADY` stalls.
- Tick4 detects out-of-order external input and returns hardware status **4**.
- Receiver discards all eight rows, despite their individually valid values.
- **Critical:** the future recurrent event scheduled for tick8 of run0 remains
  in the old wheel state *until the next kernel invocation initializes it*.

### Run 1 — successful independent fresh transaction

- Same *physical simulated* DUT instance, **no `ap_rst_n` pulse**;
  new `ap_start`, newly loaded two-neuron graph, **zero synapses**,
  1 external input at tick **1** targeting neuron **1**, weight +5.
- 10 ticks, exactly **20 trace beats**, all ordered by tick and neuron.
- Only tick1/neuron1 spikes, and only tick1 has one event delivery;
  output voltages are zero after firing and neurons otherwise skipped.
- In particular, tick8 is **silent**, demonstrating the previous failed run's
  scheduled tick8 recurrent event did **not** leak into this valid run.
- Actual AXI-Lite return must be **0**, row count exactly20, no extra
  trace transfers after completion.
- Only run1's 20 rows may be published; run0's eight rows are discarded.

This uses two separate sets of input producer counters in the **testbench**,
one receiver per hardware transaction, but the SAME RTL DUT and a continuously
asserted hardware reset-release level. The receiver must drain stream
concurrently, because waiting for `ap_done` before draining can deadlock.

### What is implemented

1. [`tb_m05_rolling_axis_multi_run.sv`](../hls/m05_rolling/rtl_stress/tb_m05_rolling_axis_multi_run.sv)
   instantiates the genuine HLS-generated Verilog once, performs both AXI-Lite
   `ap_start` transactions, continuously checks stable `TVALID/TDATA`
   through output TREADY stalls, validates every one of the **28 trace
   transfers** and their split **8 + 20**, checks each final return status
   through the real generated AXI-Lite address map, and emits
   `M05_RTL_MULTI_ROW run=...` / `M05_RTL_MULTI_FINAL...` markers.
2. [`scripts/m05_rtl_multi_run_replay.py`](../scripts/m05_rtl_multi_run_replay.py)
   **only after genuine XSim** parses this run's actual simulator log,
   rejects missing/duplicate/incorrect run boundaries and trace/status
   markers, sends each run's rows into a **fresh**
   `RollingTraceCommitGate`, and requires **0 rows committed from run0**
   and **20 accepted from run1**. Verifies spike at tick1 and silent tick8.
3. [`scripts/run_m05_rolling_rtl_stress.sh`](../scripts/run_m05_rolling_rtl_stress.sh)
   now accepts `--multi-run`. It validates the original immutable
   `--impl` kernel SHA, stages the same **11 exact generated memory files**
   into an exclusive new `Thesis_Evidence` directory, compiles/elaborates/
   runs direct XSim, and calls the strict native replay, saving
   `05_trace_commit.log`. Any `RTL_STRESS_FAIL`, missing-memory warnings,
   malformed transcript or nonzero shell status stops the gate.
4. [`tests/test_m05_rtl_multi_run_replay.py`](../tests/test_m05_rtl_multi_run_replay.py)
   contains **15 synthetic-trace/source-contract native regression methods**;
   they never run Vivado and do not prove the real RTL gate.

## Local verification (workstation Vivado 2025.2; NO BOARD)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD

cd Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m05*.py' -v

export ROLL_IMPL="$HOME/Thesis_Evidence/neuromorphic_v1_m05_rolling_impl_20261108T200432Z_186026"
bash scripts/run_m05_rolling_rtl_stress.sh "$ROLL_IMPL" --multi-run

export REUSE_EVIDENCE="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_* | head -n 1)"
echo "$REUSE_EVIDENCE"
cat "$REUSE_EVIDENCE/result.txt"
cat "$REUSE_EVIDENCE/commit.txt"
cat "$REUSE_EVIDENCE/stress_mode.txt"
cat "$REUSE_EVIDENCE/01_ram_init.log" 2>/dev/null || true
tail -n 80 "$REUSE_EVIDENCE/02_xvlog.log" 2>/dev/null || true
tail -n 80 "$REUSE_EVIDENCE/03_xelab.log" 2>/dev/null || true
tail -n 120 "$REUSE_EVIDENCE/04_xsim.log" 2>/dev/null || true
cat "$REUSE_EVIDENCE/05_trace_commit.log" 2>/dev/null || true
```

**Expected genuine XSim marker (NOT YET SEEN):**
```text
M05_RTL_MULTI_FINAL run=0 status=4 rows=8 committed=0
M05_RTL_MULTI_FINAL run=1 status=0 rows=20 committed=20
PASS: M05 REAL RTL AXIS MULTI-RUN fail-then-success rows=8+20 committed=0+20; output_stalls=...
PASS: M05 RTL multi-run transactional replay: failed_run_discarded=8, next_run_accepted=20, statuses=4,0, ...
```

### Failures and boundaries

- An `xvlog` or `xelab` error can be due to the **new testbench** rather than
  DUT arithmetic. Preserve all original logs; do not alter old HLS code
  merely to make the new test pass.
- A run1 failure to start or complete can be a **real ap_ctrl restart contract
  issue**, or a testbench handshake problem; inspect generated control
  `ap_start/ap_done/ap_ready` signals and use the real `*.v` code to
  distinguish them.
- A leak at tick8 is an important scheduler wheel state regression.
- Real host DMA/interrupt concurrency, physical board, power-on reset,
  timeout-triggered reset/retry and unbounded >64 tick state continuity
  remain **separate** work items.
- Keep all original `Thesis_Evidence` directories, Loihi digital-twin v2
  hardware logs, and Vivado journals. No JTAG or physical operations.
