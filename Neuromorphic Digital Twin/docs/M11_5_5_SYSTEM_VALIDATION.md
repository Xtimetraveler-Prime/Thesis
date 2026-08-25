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
and final regression after resource-oriented review.

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
`trace_state_before_mem`. After the existing configuration-validity check and
immediately before the HLS launch, the controller copies `work_state` into that
trace memory. The memory never feeds HLS inputs or architectural writeback.
Idle neuron debug reads return the pre-state word alongside the already existing
configuration, committed state, legacy accumulator, and spike values.

`phase_b_synapse_accumulator_v1.sv` exposes two idle-only trace paths:

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
accumulator memories to keep the two verified blocks isolated. M11.5.5 allowed
either collapsing that storage or retaining it if whole-core synthesis showed
that the verification-first organization remained comfortably inside the K26
resource budget.

The independently reproduced synthesis result supports retaining the current
organization for M11.5. The inferred **block-memory** total was:

```text
RAMB36E2 = 15
RAMB18E2 = 2
URAM     = 0
```

Counting each RAMB18 as half a RAMB36, that is 16 RAMB36-equivalents. The K26
baseline from M11.3 exposes 144 RAMB36-equivalent capacity units, so the measured
block-RAM footprint is about 11.1% of available capacity. This is only two
RAMB36-equivalents above the M11.5.1 capacity-only lower bound of 14 despite the
verification-first composition and the new pre-state trace memory.

The RAM report shows the new 256 x 64 `trace_state_before_mem` mapping into one
RAMB36E2. It also shows expected width/depth fragmentation and replication in
other memories, including the 128-bit neuron configuration and 32-bit CSR row
storage. No M11.5 behavioral block is being rewritten solely to reduce this
block-RAM footprint.

The complete LUT/FF/DSP summary remains part of the final M11.5.5 evidence and
must be copied from `utilization.rpt`; the block-RAM excerpt alone is not treated
as the complete resource profile.

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

and now generates:

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

#### Independent synthesis evidence — 2026-08-25

All three scripted synthesis markers were independently observed. The submitted
timing summary reported:

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

Therefore the complete synthesized core meets the 100 MHz **setup** target with
1.337 ns estimated setup margin, but the synthesis-stage report as a whole does
not meet timing because min-delay/hold analysis contains a 149 ps worst
violation.

This is not being converted into an RTL timing exception or an artificial data
path delay during M11.5. Vivado synthesis uses estimated net delays; physical
placement/routing performs hold fixing and determines the real min-delay result.
M11.6 must require nonnegative routed hold slack before a bitstream timing result
is accepted. The M11.5.5 Tcl now records the 20 worst explicit setup and hold
paths on future runs so any persistent violation has reproducible endpoints.

The material warnings observed in the synthesis log were:

- the known scalar override of the packaged HLS `ap_ctrl` members used by the
  source-controlled integration flow;
- no bus interface associated with the clock interface;
- automatic incremental compile skipped because no reference checkpoint was
  supplied; and
- hierarchy/floorplanning advisories caused by the flattened synthesized
  wrapper/netlists.

None of those warnings changes the already verified arithmetic or recurrent
behavior. The scalar `ap_ctrl` connections are explicitly reconstructed and
connectivity-checked by Tcl; generated `write_bd_tcl` is not the normative
reconstruction artifact.

### M11.5.5.4 — Final trace-aware behavioral regression

The final gate is now implemented by:

```text
examples/generate_m11_5_5_trace_vectors.py
rtl/core_v1/tb/tb_neuromorphic_twin_m11_5_5_trace.sv
rtl/core_v1/vivado/create_m11_5_5_trace_project.tcl
rtl/core_v1/run_m11_5_5_trace_sim.sh
```

It reuses the same four-tick M11.5.4 Python oracle and actual M11.4 packaged HLS
IP. In addition to the established state/spike/recurrent checks, it verifies
after every Phase-F commit:

- post-commit hardware tick converts exactly to zero-based trace tick;
- external event count/data match the actual Phase-B external buffer;
- the now-inactive recurrent bank matches the consumed recurrent sequence;
- the new current recurrent bank matches the routed output sequence;
- every neuron's trace-only pre-state equals the state seen before HLS Phase C;
- every signed-64 trace synaptic input equals the Python Phase-B accumulator;
- committed state and spike flags remain exact; and
- the transient neuron-controller accumulator is zero after writeback.

The state-before expectations are mechanically derived from the original
M11.5.4 vector corpus: tick 0 uses the initial/reset image and every later tick
uses the preceding tick's committed Python state.

## Current implementation state

Implemented and independently synthesized:

- `FpgaTickTraceSnapshot` and focused reconstruction/validation tests;
- passive pre-Phase-C neuron-state capture;
- post-tick Phase-B signed-64 accumulator readback;
- post-tick external-event memory/count readback;
- propagation of trace ports through the recurrent controller and Vivado Module
  Reference boundary;
- the K26/100 MHz complete-core synthesis/reporting flow;
- measured 16-RAMB36-equivalent block-memory footprint;
- measured +1.337 ns synthesis setup WNS and -0.149 ns synthesis hold WHS;
- detailed setup/hold path report generation for future synthesis runs;
- the final trace-aware real-packaged-HLS recurrent XSIM gate and source guards.

Remaining evidence before M11.5.5 closure:

1. rerun the focused/full Python source regressions after the final trace-gate
   additions;
2. run `run_m11_5_5_trace_sim.sh` and independently observe its real-HLS trace
   pass markers; and
3. record the final LUT/FF/DSP utilization summary from `utilization.rpt`.

## Completion boundary

M11.5.5 is complete only when:

1. every normative M10 trace field can be reconstructed losslessly after a
   completed hardware tick;
2. the final complete-core memory/resource organization is measured from Vivado
   synthesis rather than inferred only from logical bit counts;
3. the 100 MHz synthesis setup result, pre-route hold result, and material
   warnings are recorded without misrepresenting synthesis timing as routed
   signoff; and
4. the final real packaged-HLS recurrent behavioral gate matches the Python
   golden expectations after instrumentation/resource review.
