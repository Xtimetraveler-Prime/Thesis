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

The intended read window begins **after top-level `tick_done` / Phase-F commit**.
The snapshot must be captured before the next `tick_start`, architectural reset,
or any host write that changes a backing trace source such as neuron state or the
external-event buffer. During that window all fields represent one atomically
committed algorithmic tick.

| M10 trace field | M11.5.5 source after commit |
|---|---|
| `tick` | outer recurrent-core committed tick counter, translated from post-commit count to zero-based `TickTrace.tick` |
| `external_input_axons` | Phase-B external event buffer plus `trace_external_event_count` for the completed tick |
| `recurrent_input_axons` | old recurrent bank, now inactive after Phase-F swap, using `last_consumed_recurrent_count` |
| `input_axons` | lossless reconstruction `external_input_axons || recurrent_input_axons` |
| `synaptic_input` | Phase-B signed-64 accumulator image retained after Phase B until the next accumulation clear |
| `current_before`, `voltage_before` | per-neuron pre-Phase-C state snapshot memory |
| `current_after`, `voltage_after`, `refractory_after` | committed neuron state memory |
| `spikes` | committed spike flags |
| `routed_output_axons` | new recurrent current bank after Phase-F swap using `last_routed_count` |

The hardware retains the full packed pre-state word, including pre-tick
refractory state, even though the current M10 minimum trace schema only requires
pre-tick current and voltage. Conversion into `TickTrace` remains lossless for
all normative fields.

### Implemented trace hardware

`neuron_array_controller_v1.sv` now contains a passive 256 x 64-bit
`trace_state_before_mem`. After the existing configuration-validity check and
immediately before the HLS launch, the controller copies `work_state` into that
trace memory. The memory never feeds HLS inputs or architectural writeback.
Idle neuron debug reads return the pre-state word alongside the already existing
configuration, committed state, legacy accumulator, and spike values.

`phase_b_synapse_accumulator_v1.sv` now exposes two idle-only trace paths:

- the exact per-neuron signed-64 accumulator image produced by Phase B; and
- the external-event memory actually consumed by the engine.

`integrated_core_controller_v1.sv` multiplexes its existing internal accumulator
copy read with host trace reads. Internal Phase-B-to-neuron copy has priority
while the core is busy, while post-tick reads are accepted only when the
composition is idle. It also retains the completed tick's external event count.

`recurrent_integrated_core_controller_v1.sv` propagates those fields to the full
recurrent boundary and keeps their public valid signals suppressed throughout
the outer busy interval, including the Phase-D/E spike scan. The existing
recurrent debug path supplies both physical banks; after Phase F the current
bank is the routed-output sequence and the opposite bank prefix of
`last_consumed_recurrent_count` is the consumed recurrent-input sequence.

The Verilog-2001 Module Reference wrapper exposes the same trace ports for the
Vivado system design.

### M11.5.5.2 — Resolve resource-accounting ambiguities

M11.5.3 deliberately preserved separate Phase-B and neuron-controller signed-64
accumulator memories to keep the two verified blocks isolated. M11.5.5 must do
one of two things before accepting the final resource baseline:

1. collapse the duplicate storage into a shared physical organization without
   changing the verified Phase-B/Phase-C behavior; or
2. retain the duplication and explicitly include it in the synthesized resource
   profile if the K26 budget and timing remain acceptable.

The same review applies to the new pre-state trace memory and to any memory
replication caused by debug ports, widths, or access patterns. Resource cleanup
will be driven by the actual M11.5.5 synthesis result rather than by changing a
verified organization speculatively.

### M11.5.5.3 — Synthesize and measure the complete integrated core

The source-controlled synthesis flow is now implemented by:

```text
rtl/core_v1/vivado/m11_5_5_timing.xdc
rtl/core_v1/vivado/create_m11_5_5_project.tcl
rtl/core_v1/run_m11_5_5_synth.sh
```

It reconstructs the complete recurrent design in Vivado 2025.2 for:

```text
xck26-sfvc784-2LV-c
100 MHz baseline / 10 ns clock
```

and generates:

```text
utilization.rpt
utilization_hierarchical.rpt
ram_utilization.rpt
ram_utilization.csv
timing_summary_synth.rpt
methodology_synth.rpt
clocks.rpt
neuromorphic_twin_m11_5_5_synth.dcp
```

The reports record at minimum:

- BRAM/LUTRAM/URAM mapping;
- DSP utilization;
- LUT utilization;
- FF utilization;
- inferred memory organization and replication;
- synthesized timing estimate against the 10 ns baseline;
- methodology warnings relevant to later physical implementation.

The M11.5.1 value of 14 BRAM36 units remains only a logical capacity lower
bound. M11.5.5.3 is the first accepted whole-core synthesis mapping. Synthesized
timing is an early estimate; routed timing signoff remains M11.6.

### M11.5.5.4 — Final behavioral regression after cleanup

Any observability or resource change must retain the established M11.5.4
behavior. The final gate must rerun the packed-M08 + real-HLS recurrent
multi-tick XSIM path and verify the new trace readback against Python-derived
expectations before M11.5 is marked complete.

## Current implementation state

Implemented, but not yet independently executed on this branch:

- `FpgaTickTraceSnapshot` and focused reconstruction/validation tests;
- passive pre-Phase-C neuron-state capture;
- post-tick Phase-B signed-64 accumulator readback;
- post-tick external-event memory/count readback;
- propagation of trace ports through the recurrent controller and Vivado Module
  Reference boundary;
- the K26/100 MHz complete-core synthesis/reporting flow;
- static source guards ensuring trace memories do not replace HLS datapath
  inputs and required synthesis/RAM/timing reports remain part of the flow.

The next evidence gate is to run the new Python/source tests and the complete
Vivado synthesis flow. Those results will decide whether duplicate accumulator
storage can be retained and explicitly budgeted or needs physical cleanup before
the final behavioral regression.

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
