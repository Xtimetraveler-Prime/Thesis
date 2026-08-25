# M11.5.5 — Integrated Observability and Vivado System Validation

**Status:** Complete  
**Started:** 2026-08-24  
**Completed:** 2026-08-25  
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

That profile could not proceed to physical implementation even though Vivado
synthesis completed. The result identified CLB LUT capacity—not arithmetic DSPs,
register capacity, or nominal BRAM capacity—as the actual blocker.

The RAM report exposed the structural cause worth correcting before any
higher-level redesign. Several large arrays annotated for block RAM did not map
to BRAM, including the Phase-B event/accumulator path, neuron state/accumulator
path, and recurrent event banks. One clear cause was an asynchronous read of
`accumulator_mem`; a `ram_style="block"` attribute cannot compensate for an
access pattern that is incompatible with dedicated block-RAM inference.

#### Resource remediation

The affected paths were rewritten as canonical synchronous single-clock RAM
ports without changing algorithmic behavior:

- Phase-B external and recurrent 4096 x 16 event buffers use registered read
  outputs and explicit write/read ports.
- Phase-B 256 x 64 signed accumulator uses an implementation-only
  `S_ACCUM_READ` cycle so read-modify-write accumulation consumes a synchronous
  registered RAM output rather than an asynchronous array read.
- The neuron controller's 256 x 64 state and signed-64 copied accumulator use
  synchronous RAM outputs plus an implementation-only `S_TICK_CAPTURE` state
  before the existing validation/HLS launch path.
- Both 4096 x 16 recurrent physical banks use explicit synchronous read/write
  processes; bank selector, counts, ordering, and Phase-F swap behavior are
  unchanged.

These added cycles are hardware scheduling details only. They do not change the
M10 six-phase algorithmic tick, weight arithmetic, neuron equations, routing
order, recurrence delay, or externally visible commit boundary.

The synthesis runner was also hardened to parse `utilization.rpt` and fail if
any of these device resource classes exceeds the K26 capacity:

```text
CLB LUTs
CLB Registers
Block RAM Tile
DSPs
URAM
```

This prevents a resource-overflowing design from producing a misleading M11.5.5
completion marker.

#### Final whole-core resource profile — accepted

After the synchronous-RAM remediation, the independently rerun synthesis gate
reported:

```text
M11.5.5 resource capacity check passed:
CLB_LUT=1757/117120
CLB_REG=944/234240
BRAM_TILE=27/144
DSP=2/1248
URAM=0/64
```

Equivalent utilization percentages are approximately:

```text
CLB LUTs       1.50%
CLB Registers  0.40%
Block RAM Tile 18.75%
DSPs           0.16%
URAM           0.00%
```

The increase from 16 to 27 BRAM tiles is intentional: large runtime arrays that
had previously exploded into LUT logic now map into dedicated block memory. The
corresponding LUT reduction from 172,225 to 1,757 is the decisive evidence that
the physical memory organization is now appropriate for the selected K26.

The verification-first separation between Phase-B and Phase-C accumulator
storage is therefore retained. It is now explicitly budgeted by real synthesis
rather than justified only by the M11.5.1 logical 14-BRAM36 lower bound.

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

#### Synthesis timing evidence and M11.6 handoff

The first complete-core synthesis profile reported:

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

That profile met the 100 MHz synthesis-stage setup target but had a 149 ps
pre-route hold estimate. No RTL timing exception or artificial delay was added.
The synthesis flow now records explicit setup and hold paths so physical
implementation can diagnose any remaining min-delay problem.

The final post-remediation synthesis completed successfully and passed the
resource-capacity gate. Its detailed timing summary was not separately
transcribed into the milestone evidence, so M11.5.5 does **not** claim routed or
post-remediation timing closure. M11.6 is the authoritative physical timing
stage and must require nonnegative routed setup/hold slack before accepting the
implemented design.

Material nonfunctional warnings observed during this work include the known
scalar overrides of packaged HLS `ap_ctrl` members, clock-interface metadata
without associated bus interfaces, skipped automatic incremental compilation
when no reference checkpoint is supplied, and hierarchy/floorplanning
advisories on the flattened synthesized netlist. None changes the frozen
arithmetic or recurrent behavior.

### M11.5.5.4 — Final trace-aware behavioral regression

The final trace gate is implemented by:

```text
examples/generate_m11_5_5_trace_vectors.py
rtl/core_v1/tb/tb_neuromorphic_twin_m11_5_5_trace.sv
rtl/core_v1/vivado/create_m11_5_5_trace_project.tcl
rtl/core_v1/run_m11_5_5_trace_sim.sh
```

After the resource remediation, the focused Python/source regressions, complete
Python regression suite, affected M11.5.2/M11.5.3/M11.5.4 hardware regression
gates, and the final trace-aware real-HLS gate were independently rerun and
reported passing.

The final trace gate verifies after every Phase-F commit:

- post-commit hardware tick converts exactly to zero-based trace tick;
- external event count/data match the actual Phase-B external buffer;
- the now-inactive recurrent bank matches the consumed recurrent sequence;
- the new current recurrent bank matches the routed output sequence;
- every neuron's trace-only pre-state equals the state seen before HLS Phase C;
- every signed-64 trace synaptic input equals the Python Phase-B accumulator;
- committed state and spike flags remain exact; and
- the transient neuron-controller accumulator is zero after writeback.

The independently observed final trace markers included:

```text
M11.5.5 trace real-HLS block design validated successfully.
M11.5.5 trace snapshot + real-HLS recurrent regression passed: ticks=4, neurons=3, tag=0x4d353554
M11.5.5 trace real-HLS Vivado simulation flow completed.
M11.5.5 trace snapshot + real packaged HLS IP simulation completed successfully.
```

The final synthesis then reported:

```text
M11.5.5 resource capacity check passed: CLB_LUT=1757/117120, CLB_REG=944/234240, BRAM_TILE=27/144, DSP=2/1248, URAM=0/64
M11.5.5 complete-core synthesis and reporting completed successfully.
```

## Completion evidence summary

M11.5.5 closed with all required evidence layers:

1. lossless software reconstruction of every normative M10/M12 tick-trace field;
2. passive hardware trace storage/readback that cannot feed or change the
   computational datapath;
3. exact real-packaged-HLS recurrent behavioral regression after trace and RAM
   instrumentation;
4. discovery and correction of an initially impossible 147.05% LUT synthesis
   profile;
5. a final synthesis profile that fits every checked K26 resource class with
   substantial headroom; and
6. a hardened source-controlled synthesis gate that rejects future resource
   overflow automatically.

## What completion means

M11.5.5—and therefore M11.5 as a whole—now establishes a complete simulated FPGA
computational core with finite memories, packed M08 synapse traversal, exact
signed-64 accumulation, real packaged HLS neuron execution, deterministic
next-tick recurrent routing, atomic tick commit, and post-tick trace readback.
The design is no longer only behaviorally correct: Vivado synthesis also shows
that the final memory organization fits the selected K26 device.

Physical placement, routing, routed timing closure, bitstream generation, board
programming, and hardware smoke tests remain M11.6. Full Python-versus-physical-
FPGA tick conformance remains M12.
