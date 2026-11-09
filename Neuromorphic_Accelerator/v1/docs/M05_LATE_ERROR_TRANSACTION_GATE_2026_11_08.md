> **LATEST M05.9 — 2026-11-08:** Operator's **real Vivado 2025.2 direct generated-RTL M05.8 late-error test PASSED** (original `~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_20261108T211756Z_234592`, exit0): 11 genuine generated RAM images staged, 8 ordered provisional rows from ticks0..3 including t0/n0 spike, real `BAD_EXTERNAL=4` at tick4, **56 output stalled cycles**, offline host `RollingTraceCommitGate` replay **drained 8 / committed 0**. Prior genuine directed 312 neuron-input and 7573 trace-output stalled cycles and routed 6.503ns OOC evidence unchanged. **New M05.9**: distinct SystemVerilog [two-run recovery test](M05_MULTI_RUN_RECOVERY_GATE_2026_11_08.md) runs the **same RTL instance without pulsing reset**: first run emits 8 provisional rows then status4, second run reloads an entirely new synapse-free network (2 neurons/10 ticks), emits exactly **20 valid rows** including a fresh t1/n1 spike and **zero stale t8 recurrence**, returns status0. New strict read-only XSim transcript replay feeds two independent host commit gates (0+20 committed). **15 new native synthetic/source tests = 157 M05 +91 accepted earlier =248 named native tests**. **Genuine M05.9 direct XSim NOT YET RUN**; do not claim physical PS/PL or DMA integration. [Canonical evaluation-engine optimization ledger](M05_EVALUATION_ENGINE_EVOLUTION.md). Owner next: run `bash scripts/run_m05_rolling_rtl_stress.sh "$ROLL_IMPL" --multi-run` using existing immutable --impl proof. M05 OPEN; PR #79 draft/unmerged, no board/JTAG.
>
# M05.8 — Late-error transactional AXI/RTL rollback test

**Current status (2026-11-08):** Direct RTL bench and offline Python host
transcript postcheck implemented on draft M05 PR #79. **Native-only tests pass
CI where checked; actual XSim RTL outcome for this new test is PENDING.**
The FPGA evaluation arithmetic/kernel remains **byte-for-byte unchanged**,
as do the two genuine passed direct RTL output- and input-stall benches.

## Last achieved operator gate (M05.7)

On Nov 8, 2026 the operator ran `--ingress` at the known routed K26
signed32 engine snapshot with the new 64-neuron bench. Original immutable
evidence folder:
`~/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_20261108T210506Z_227783`,
`exit_status=0`, `stress_mode.txt=ingress`, Vivado 2025.2
`xvlog` + `xelab` + direct generated Verilog `xsim` PASS.

- 11 authentic generated HLS RAM `.dat` images staged from original
  `--impl` evidence with source/checksum manifest, no new missing-image
  warnings.
- `N=64, E=1, S=1, T=12`; **768/768 fully validated trace records**;
  **7,573 output `TVALID && !TREADY` stall cycles** and **312 neuron input
  `TVALID && !TREADY` stall cycles**; 16,762 input gap cycles; final
  AXI-Lite hardware status 0.
- Pre-start 300-cycle stimulus confirmed only **2** neuron beats had entered
  before start, with **283** neuron stall cycles and
  `neurons_TVALID=1, neurons_TREADY=0`. The synapse and external inputs
  were 1 packet each and saw 0 input stall cycles. This proves *directed*
  neuron-input and trace-output backpressure in this tested workload, not
  arbitrary multi-stream saturation or physical DMA throughput.
- The preceding separate real 2-neuron output test also stays PASS
  (24 rows/188 output-stall cycles).

## New issue / reason for M05.8

The HLS rolling kernel emits a tick's complete trace **after that tick's
recurrent fanout checks**. A later tick may nevertheless fail due to sorted
external ingress or delivery limits. An AXIS sink cannot simply treat every
output row as committed: **the entire transaction is provisional until final
hardware `ap_done` plus 32-bit AXI-Lite return status 0**.

The native `RollingTraceCommitGate` already enforces this at host-model
level. The missing proof is that **the actual generated RTL** emits a
provisional prefix before a late nonzero final return under trace TREADY
stalls, and that a real-transcript-to-host gate refuses partial publication.

## Concrete intentionally invalid hardware test

[`tb_m05_rolling_axis_late_error.sv`](../hls/m05_rolling/rtl_stress/tb_m05_rolling_axis_late_error.sv)
is a separate testbench against **the exact prior routed and verified
signed32 `m05_rolling_replay` Verilog**. Config: 2 neurons,
1 delay-8 recurrent edge, 12 ticks, **3** external events.

Input is **intentionally NOT sorted** by tick:

| External packet | Tick | Neuron | Current | Meaning |
|---|---:|---:|---:|---|
| 0 | 0 | 0 | +5 | Causes valid t0 neuron0 spike. |
| 1 | 4 | 0 | +5 | Read as ordered future-event lookahead at t0. |
| 2 | 3 | 0 | +5 | Read when tick4 is serviced; now late, **invalid**. |

Tick 0 is valid and creates a neuron0 spike. Ticks 0,1,2,3 yield
**4 ticks ×2 neurons = 8 provisional rows**. At tick 4 the third packet
has `pending.tick < t`, so the kernel must return
`M05_ROLL_BAD_EXTERNAL=4` **without emitting tick4 rows**. The testbench
drains the trace *concurrently*, forces output `TREADY` low 10/11 cycles,
checks exact t0 spike and in-order trace prefix, checks no extra rows,
polls AXI-Lite `ap_done`, reads actual return status **4**, and prints
machine-readable `M05_RTL_PROVISIONAL ...` plus
`M05_RTL_FINAL status=4 provisional=8 committed=0` markers.

**Expected actual RTL result (NOT YET CLAIMED):**
```text
PASS: M05 REAL RTL AXIS LATE-ERROR status=4 provisional=8 committed=0
```
It is a **PASS of rejecting an intentionally INVALID simulation**, not an
unexpected accelerator failure.

## Host-side rollback using actual XSim transcript

[`m05_rtl_transaction_replay.py`](../scripts/m05_rtl_transaction_replay.py)
parses the exact provisional rows and terminal status from the **new run's
own XSim transcript**, rejects missing/duplicate/contradictory markers,
then stages the rows in the existing
[`RollingTraceCommitGate`](../src/neuromorphic_accelerator_v1/m05_trace_commit.py).

The host gate receives **8 streamed provisional rows, including an actual
t0 spike**, but must return `accepted=False` and **0 accepted rows**
because hardware returned status 4. The runner saves a separate
`05_trace_commit.log` and refuses success unless both the real RTL bench
and host replay report PASS. This is not a PS-connected DMA receiver: the
replay is an **offline log-based integration test**, and it cannot prove
concurrent real host/DMA drains.

New [native tests](../tests/test_m05_rtl_transaction_replay.py) use
**synthetic logs** to exercise valid rollback, missing/duplicate footer,
status 0, count mismatch, out-of-order records, invalid fields, missing
initial spike, XSim `$fatal` despite shell exit0, CLI read-only contract,
and new SV/runner source coverage. Do NOT describe these native tests as
having run generated RTL.

## User-operated offline next gate (NO BOARD)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip

cd Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m05*.py' -v

# Ensure Vivado 2025.2 is sourced in the terminal. Use exact old immutable
# routed HLS IP proof; DO NOT re-run 10-minute HLS synth/impl or touch board.
export ROLL_IMPL="$HOME/Thesis_Evidence/neuromorphic_v1_m05_rolling_impl_20261108T200432Z_186026"
bash scripts/run_m05_rolling_rtl_stress.sh "$ROLL_IMPL" --late-error

export RTL_EVIDENCE="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_rolling_axis_rtl_* | head -n 1)"
echo "$RTL_EVIDENCE"
cat "$RTL_EVIDENCE/result.txt"
cat "$RTL_EVIDENCE/stress_mode.txt"
cat "$RTL_EVIDENCE/01_ram_init.log" 2>/dev/null || true
tail -n 80 "$RTL_EVIDENCE/02_xvlog.log" 2>/dev/null || true
tail -n 80 "$RTL_EVIDENCE/03_xelab.log" 2>/dev/null || true
tail -n 110 "$RTL_EVIDENCE/04_xsim.log" 2>/dev/null || true
cat "$RTL_EVIDENCE/05_trace_commit.log" 2>/dev/null || true
```

If XSim unexpectedly fails, preserve logs as-original. A compile error
may be new testbench syntax; a prefix mismatch may be testbench struct
packing; unexpected status/row count could reveal a true kernel/RTL
contract discrepancy. Do not silently change the verified HLS source
or soften requirements to obtain PASS.

## Remaining explicit gates

After genuine direct XSim succeeds, verify a second genuinely late
hardware error (e.g. recurrent fanout `>4096` at a later tick) and a
second consecutive run with full reset/trace framing. Then develop real
concurrent PS/PL DMA drain, proper `ap_done`/status observation,
timeout/device reset/retry, and a realistic throughput benchmark. These
are **not** proven by this bench. No physical FPGA operations until new
specific owner authorization.

**M05 remains OPEN, PR #79 DRAFT/UNMERGED.** No original Vivado journals,
Vitis evidence or earlier Loihi digital-twin hardware logs were modified.
