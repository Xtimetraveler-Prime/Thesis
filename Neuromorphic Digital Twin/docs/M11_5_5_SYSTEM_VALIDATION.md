# M11.5.5 — Integrated Observability and Vivado System Validation

**Status:** In progress  
**Started:** 2026-08-24  
**Repository evidence:** branch `agent/m11-5-5-system-validation`

## Goal

Turn the behaviorally complete M11.5.4 recurrent core into the final M11.5
system boundary that is observable enough for M12 and measured honestly enough
to proceed to physical implementation in M11.6.

M11.5.5 does not change the frozen M10 neuron, synapse, or routing semantics.
Its work is instrumentation, physical-memory accounting, integrated synthesis,
and final regression after any resource-oriented cleanup.

## Closure sequence

### M11.5.5.1 — Freeze and expose the post-tick trace snapshot

For every completed hardware tick, the M10/M12 comparison path requires:

```text
tick
external_input_axons
recurrent_input_axons
input_axons
synaptic_input
current_before
voltage_before
current_after
voltage_after
refractory_after
spikes
routed_output_axons
```

The project-specific software reconstruction schema is:

```text
neuromorphic-twin-fpga-trace-snapshot-v1
```

implemented by `FpgaTickTraceSnapshot` in
`src/neuromorphic_twin/fpga_trace_snapshot.py`.

### Post-Phase-F readback mapping

The intended read window is **after top-level `tick_done` and before the next
`tick_start` or architectural reset**. During that window all fields represent
one atomically committed algorithmic tick.

| M10 trace field | M11.5.5 source after commit |
|---|---|
| `tick` | outer recurrent-core committed tick counter, translated from post-commit count to zero-based `TickTrace.tick` |
| `external_input_axons` | Phase-B external event buffer and accepted count for the completed tick |
| `recurrent_input_axons` | old recurrent bank, now inactive after Phase-F swap, using `last_consumed_recurrent_count` |
| `input_axons` | lossless reconstruction `external_input_axons || recurrent_input_axons` |
| `synaptic_input` | Phase-B signed-64 accumulator image retained after Phase B until the next accumulation clear |
| `current_before`, `voltage_before` | new per-neuron pre-Phase-C state snapshot memory |
| `current_after`, `voltage_after`, `refractory_after` | committed neuron state memory |
| `spikes` | committed spike flags |
| `routed_output_axons` | new recurrent current bank after Phase-F swap using `last_routed_count` |

The hardware may retain additional fields such as pre-tick refractory state;
that is allowed, but conversion into `TickTrace` must preserve at least the
normative fields above exactly.

### Why `state_before` needs explicit storage

M11.5.4 updates the neuron state memory in place during serialized Phase C. That
is behaviorally safe because Phase B completes before any neuron is stepped and
architectural reads are blocked while the core is busy, but after the tick the
original current/voltage values no longer exist. M11.5.5 therefore captures the
64-bit neuron state word before each HLS transaction into a trace-only memory.
This does not feed the datapath and cannot affect neuron behavior.

### M11.5.5.2 — Resolve resource-accounting ambiguities

M11.5.3 deliberately preserved separate Phase-B and neuron-controller signed-64
accumulator memories to keep the two verified blocks isolated. M11.5.5 must do
one of two things before accepting the final resource baseline:

1. collapse the duplicate storage into a shared physical organization without
   changing the verified Phase-B/Phase-C behavior; or
2. retain the duplication and explicitly include it in the synthesized resource
   profile if the K26 budget and timing remain acceptable.

The same review applies to any trace memory or debug-port-driven BRAM
replication introduced by M11.5.5.1.

### M11.5.5.3 — Synthesize and measure the complete integrated core

Reconstruct the complete recurrent design in Vivado 2025.2 for:

```text
xck26-sfvc784-2LV-c
100 MHz baseline / 10 ns clock
```

Record at minimum:

- BRAM_18K/BRAM36-equivalent utilization;
- DSP utilization;
- LUT utilization;
- FF utilization;
- URAM utilization;
- inferred memory mapping and replication warnings;
- synthesized timing estimate / worst path against the 10 ns baseline;
- any design-rule or interface warnings that affect physical implementation.

The M11.5.1 value of 14 BRAM36 units remains only a logical capacity lower
bound. M11.5.5.3 is the first accepted whole-core synthesis mapping.

### M11.5.5.4 — Final behavioral regression after cleanup

Any observability or resource change must retain the established M11.5.4
behavior. The final gate must rerun the packed-M08 + real-HLS recurrent
multi-tick XSIM path and verify the trace snapshot against Python-derived
expectations before M11.5 is marked complete.

## Current implementation state

Implemented so far:

- `FpgaTickTraceSnapshot`, including physical-capacity validation and lossless
  conversion into the existing `TickTrace` schema;
- focused tests for zero-based trace tick reconstruction, event order and
  multiplicity, state-word decoding, signed-64 accumulator bounds, spike
  reconstruction, and invalid physical inputs;
- the post-Phase-F mapping above, which identifies `state_before` as the only
  required neuron-state field that M11.5.4 did not already retain.

Next implementation step: add the trace-only pre-state memory and expose the
Phase-B accumulator/pre-state readback through the recurrent integrated core,
then prove those additions leave the M11.5.4 real-HLS behavior unchanged.

## Completion boundary

M11.5.5 is complete only when:

1. every normative M10 trace field can be reconstructed losslessly after a
   completed hardware tick;
2. the final complete-core memory/resource organization is measured from Vivado
   synthesis rather than inferred only from logical bit counts;
3. the 100 MHz baseline synthesis/timing result and material warnings are
   recorded; and
4. the final real packaged-HLS recurrent behavioral gate still matches the
   Python golden expectations after instrumentation/resource cleanup.
