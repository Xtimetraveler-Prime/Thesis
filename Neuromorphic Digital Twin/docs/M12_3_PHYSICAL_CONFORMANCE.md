# M12.3 Physical Multi-Tick and Recurrent Conformance

## Status

Complete on the physical KV260 on 2026-09-07.

M12.3 extends the exact one-tick physical equivalence established in M12.2 into stateful execution across repeated algorithmic ticks. The goal is to prove that recurrent queues, state history, event ordering, and reset/replay behavior remain exactly aligned with the independent Python FPGA-v1 golden model.

## Evidence boundary

The physical FPGA is not given expected outputs. The source-controlled Python generator produces two distinct classes of artifact:

1. host-side Python-golden committed-tick traces used only for differential comparison; and
2. FPGA-visible input images containing static configuration plus the per-tick external-event schedule.

No recurrent-event schedule and no expected state/spike/queue arrays are present in FPGA-visible generated source. Recurrent events consumed on tick `t+1` must therefore have been produced by the FPGA's own spike-routing and double-buffered queue logic on tick `t`.

The physical evidence chain is:

```text
Python scenario + input image
          ↓
physical FPGA host-stepped execution
          ↓
immutable post-commit trace window every tick
          ↓
JTAG/VIO machine-readable JSON capture
          ↓
exact Python field-by-field differential
```

## Directed corpus

The frozen M12.3 corpus contains 10 scenarios totaling 40 committed ticks:

1. `feedforward-recurrent-chain`
2. `self-recurrent-oscillator`
3. `two-neuron-recurrent-loop`
4. `recurrent-fanout`
5. `recurrent-fanin`
6. `same-target-recurrent-multiplicity`
7. `external-plus-recurrent-same-tick`
8. `simultaneous-routing-order`
9. `quiescence-then-renewed-input`
10. `decay-refractory-history`

Together they cover next-tick recurrence, repeated queue-bank swaps, loops, fan-in/fan-out, same-target multiplicity, simultaneous routing order, mixed external/recurrent input, quiescence/restart, and multi-tick state history.

## Physical execution and observability

The M12.3 capture shell reuses the validated M11.5 computational core, the M12.1 physical trace boundary, and the M12.2 synchronous recurrent-bank readback correction. One selected scenario is loaded and reset, then each host `capture_step` executes exactly one algorithmic tick. The shell pauses after commit so the host can capture the complete immutable observation before the next tick's external events are loaded.

For every committed tick the host records and compares:

- architectural tick;
- external input events;
- consumed recurrent input events;
- signed-64 per-neuron synaptic accumulation;
- packed neuron state before and after the tick;
- spike flags;
- newly routed recurrent output events;
- active recurrent queue bank and counts for both banks;
- core fault state and code.

## Main physical result

The complete directed physical suite succeeded on the KV260:

```text
M12.3 physical directed multi-tick suite capture completed successfully: cases=10 ticks=40
M12.3 exact physical multi-tick differential passed: cases=10 ticks=40 mismatches=0
```

This means all 40 committed physical ticks matched the independent Python FPGA-v1 expectation exactly across every compared field.

## Reset/replay closure

Case 02, `two-neuron-recurrent-loop`, is the reset/replay anchor. After the main suite, the Hardware Manager flow starts a separate programming/reset session and captures the six-tick loop again. Both the original and replay captures must independently pass the Python differential before they are compared to each other.

The physical replay succeeded:

```text
M12.3 targeted case PASS: 02 two-neuron-recurrent-loop ticks=6 mismatches=0
M12.3 reset/replay passed: case=02 name=two-neuron-recurrent-loop ticks=6 semantic_exact=1 first_sha256=1d261d6d4a52e37a95a3dfdd3b6f0e76fdfb21e87b1404bc81cbc41f646c78a3 replay_sha256=1d261d6d4a52e37a95a3dfdd3b6f0e76fdfb21e87b1404bc81cbc41f646c78a3
M12.3 physical multi-tick/recurrent suite completed successfully.
```

The two six-tick serialized physical artifacts are byte-identical, not merely semantically equivalent.

During the loop, after the initial external stimulus, every subsequent tick consumed one recurrent event and routed one new recurrent event. The active recurrent bank alternated on each tick, directly exercising the double-buffered next-tick queue contract over repeated stateful execution.

## Interpretation

M12.3 provides stronger evidence than a final-state comparison. A same-tick recurrence error, incorrect queue-bank swap, lost/duplicated routed event, routing-order change, state-history divergence, or reset/replay defect would appear at the first affected committed tick and fail the exact differential.

The completion claim is therefore limited but strong: for the frozen 10-scenario directed M12.3 corpus, the physical K26 implementation reproduces the explicitly defined Python FPGA-v1 state transition and recurrent-routing contract exactly across 40 committed ticks, and the selected six-tick recurrent loop reproduces byte-identically after an independent programming/reset session.

M12.3 does not claim exhaustive physical validation of the entire supported configuration space. Broader deterministic stress belongs to M12.4, while final implementation characterization belongs to M12.5.

## Reproduction

After a successful M12.3 bitstream build and with the KV260 available to Vivado Hardware Manager:

```bash
cd "Neuromorphic Digital Twin/rtl/core_v1"
bash run_m12_3_hardware_suite.sh
```

The command preserves physical traces, per-case differential reports, the suite report, the independent reset/replay trace, and both Hardware Manager logs under `build/m12_3/`.
