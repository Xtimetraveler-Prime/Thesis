# M11.5.5 — Integrated Observability and Vivado System Validation

**Status:** In progress  
**Started:** 2026-08-24  
**Repository evidence:** branch `agent/m11-5-5-system-validation`

## Goal

Turn the behaviorally complete M11.5.4 recurrent core into the final M11.5
system boundary that is observable enough for M12 and measured honestly enough
to proceed to physical implementation in M11.6.

M11.5.5 does not change the frozen M10 neuron, synapse, or routing semantics.
Its work is instrumentation, physical-memory accounting, resource-fit cleanup,
integrated synthesis, and final regression after that cleanup.

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

#### Post-Phase-F readback mapping

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

#### Implemented trace hardware

`neuron_array_controller_v1.sv` contains a passive 256 x 64-bit
`trace_state_before_mem`. After configuration validation and immediately before
the HLS launch, the controller copies the HLS input state into that trace memory.
The memory never feeds HLS inputs or architectural state writeback.

`phase_b_synapse_accumulator_v1.sv` exposes idle-only readback of:

- the exact per-neuron signed-64 accumulator image produced by Phase B; and
- the external-event memory actually consumed by the engine.

`integrated_core_controller_v1.sv` multiplexes its internal Phase-B accumulator
copy with post-tick host trace reads and retains the completed tick's external
event count. `recurrent_integrated_core_controller_v1.sv` propagates the fields
through the complete recurrent boundary while suppressing public read-valid
signals while the outer core is busy. The existing route-bank debug path supplies
both the consumed old bank and routed new bank after Phase F.

The Verilog-2001 Module Reference wrapper exposes the same trace ports in the
Vivado system design.

### M11.5.5.2 — Whole-core resource accounting and BRAM-friendly cleanup

M11.5.3 deliberately preserved separate Phase-B and neuron-controller signed-64
accumulator memories to keep the two verified blocks isolated. M11.5.5 accepts
that verification-first organization only if the final synthesized core fits the
selected K26 device.

#### First whole-core synthesis profile — not physically acceptable

The first independently reproduced synthesis run completed and all original
scripted report-generation markers appeared, but the utilization report exposed
a hard physical-capacity failure:

```text
CLB LUTs       172225 / 117120 = 147.05%
  LUT as Logic 165205 / 117120 = 141.06%
  LUT as Memory  7020 /  57600 =  12.19%
CLB Registers   34274 / 234240 =  14.63%
Block RAM Tile     16 /    144 =  11.11%
  RAMB36E2         15
  RAMB18E2          2
URAM                 0 /     64 =   0.00%
DSPs                  2 /   1248 =   0.16%
```

The design therefore **cannot** proceed to M11.6 from this profile even though
Vivado synthesis itself completed. BRAM, registers, DSPs, and URAM are
comfortable; CLB LUT capacity is the blocker.

The RAM report also revealed the structural cause worth addressing before any
higher-level redesign. Several large arrays annotated for block RAM did not
appear in the inferred BRAM list, including the Phase-B event/accumulator path,
neuron state/accumulator path, and recurrent event banks. One particularly clear
cause was an asynchronous read of `accumulator_mem`; dedicated block RAM requires
synchronous read behavior. Large arrays with non-BRAM-friendly read patterns can
create deep LUT read muxes even when a `ram_style="block"` attribute is present.

#### Resource remediation implemented

The affected paths are now written as canonical synchronous single-clock RAM
ports without changing algorithmic behavior:

- Phase-B external and recurrent 4096 x 16 event buffers use registered read
  outputs and explicit write/read ports.
- Phase-B 256 x 64 signed accumulator uses a new implementation-only
  `S_ACCUM_READ` cycle so read-modify-write accumulation consumes a synchronous
  registered RAM output rather than an asynchronous array read.
- The neuron controller's 256 x 64 state and signed-64 copied accumulator use
  synchronous RAM outputs plus an implementation-only `S_TICK_CAPTURE` state
  before the existing validation/HLS launch path.
- Both 4096 x 16 recurrent physical banks use explicit synchronous read/write
  processes; bank selector, counts, ordering, and Phase-F swap behavior are
  unchanged.

These extra cycles are hardware scheduling details only. They do not alter the
M10 six-phase algorithmic tick, weight arithmetic, neuron equations, routing
order, recurrence delay, or externally visible commit boundary.

The synthesis runner now parses `utilization.rpt` after Vivado completes and
fails if any of the following exceeds the selected device capacity:

```text
CLB LUTs
CLB Registers
Block RAM Tile
DSPs
URAM
```

This prevents a >100% design from producing a misleading M11.5.5 completion
marker again.

### M11.5.5.3 — Synthesize and measure the complete integrated core

The source-controlled synthesis flow is implemented by:

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
setup_paths_synth.rpt
hold_paths_synth.rpt
methodology_synth.rpt
clocks.rpt
neuromorphic_twin_m11_5_5_synth.dcp
```

#### First synthesis timing evidence — 2026-08-25

The first profile reported:

```text
Clock:      ap_clk = 10.000 ns / 100 MHz
WNS:        +1.337 ns
TNS:         0.000 ns
Setup failing endpoints: 0 / 73353
WHS:        -0.149 ns
THS:       -22.122 ns
Hold failing endpoints: 213 / 73353
WPWS:       +4.238 ns
```

Thus the first synthesized profile met the 100 MHz **setup** target but not the
synthesis-stage min-delay/hold check. The 149 ps pre-route hold estimate is not
being converted into an RTL timing exception or artificial data-path delay.
Physical placement/routing is responsible for final min-delay behavior; M11.6
must require nonnegative routed hold slack before the timing result is accepted.
The Tcl records explicit worst setup and hold paths so any persistent routed issue
can be traced to endpoints.

Material nonfunctional warnings in the first synthesis log were the known scalar
overrides of the packaged HLS `ap_ctrl` members, clock-interface metadata without
associated bus interfaces, skipped automatic incremental compilation because no
reference checkpoint was supplied, and hierarchy/floorplanning advisories on the
flattened synthesized netlist. None changes the frozen arithmetic or recurrent
behavior.

A new synthesis run after the BRAM-friendly cleanup must replace the first
resource/timing profile before M11.5.5 can close.

### M11.5.5.4 — Final trace-aware behavioral regression

The final trace gate is implemented by:

```text
examples/generate_m11_5_5_trace_vectors.py
rtl/core_v1/tb/tb_neuromorphic_twin_m11_5_5_trace.sv
rtl/core_v1/vivado/create_m11_5_5_trace_project.tcl
rtl/core_v1/run_m11_5_5_trace_sim.sh
```

Before the resource-remediation RTL changes, the focused/full Python gates and
all four real-HLS trace markers were independently reported passing. The trace
test verifies after every Phase-F commit:

- post-commit hardware tick converts exactly to zero-based trace tick;
- external event count/data match the actual Phase-B external buffer;
- the now-inactive recurrent bank matches the consumed recurrent sequence;
- the new current recurrent bank matches the routed output sequence;
- every neuron's trace-only pre-state equals the state seen before HLS Phase C;
- every signed-64 trace synaptic input equals the Python Phase-B accumulator;
- committed state and spike flags remain exact; and
- the transient neuron-controller accumulator is zero after writeback.

Because Phase-B, neuron-memory, and recurrent-bank RTL access patterns changed
after that pass, the strong hardware regressions must be rerun on the remediated
branch before their earlier evidence can be used for final closure.

## Current implementation state

Implemented:

- lossless `FpgaTickTraceSnapshot` reconstruction contract;
- complete trace readback through the recurrent Module Reference boundary;
- K26/100 MHz whole-core synthesis/reporting flow;
- initial whole-core synthesis evidence including the discovered 147.05% LUT
  overutilization;
- BRAM-friendly synchronous refactoring of the major large runtime memories;
- resource-capacity enforcement in the synthesis runner;
- final trace-aware real-packaged-HLS XSIM gate and source guards.

Still required before M11.5.5 closure:

1. rerun focused/full Python source regressions after the RAM refactor;
2. rerun the strongest RTL/HLS regression gates that touch the changed blocks;
3. rerun complete-core synthesis and confirm **every physical resource class is
   at or below 100%**, especially CLB LUTs;
4. replace the first resource/timing baseline with the remediated result; and
5. rerun the final trace-aware real-HLS recurrent regression on that same source
   state.

## Completion boundary

M11.5.5 is complete only when:

1. every normative M10 trace field can be reconstructed losslessly after a
   completed hardware tick;
2. the complete core fits the selected `xck26-sfvc784-2LV-c` resource capacities
   at synthesis, with no resource class above 100%;
3. the final complete-core memory/resource organization is measured from Vivado
   synthesis rather than inferred only from logical bit counts;
4. the 100 MHz synthesis setup result, pre-route hold result, and material
   warnings are recorded without misrepresenting synthesis timing as routed
   signoff; and
5. the final real packaged-HLS recurrent behavioral gate matches the Python
   golden expectations after the resource/observability cleanup.
