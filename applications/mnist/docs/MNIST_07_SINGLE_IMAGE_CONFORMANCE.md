# MNIST-07 Single-Image FPGA Conformance

**Status:** Complete

## Goal

MNIST-07 is the first application-specific physical-FPGA correctness gate. It does not measure classification accuracy over a corpus; it asks whether the already validated FPGA core executes one frozen MNIST workload exactly like the Python golden model for every presentation tick.

Two cases are run:

- case 0: `cropped-dense`;
- case 1: `native-sparse`.

Both use the same original MNIST test image: the first `both-correct` entry in the frozen MNIST-06 corpus. In the accepted `mnist-v1` freeze this is MNIST test index **3**, true label **0**. Using one shared source image isolates profile/deployment differences while keeping the physical conformance gate simple. The broader easy/divergent/hard 30-image corpus is reserved for MNIST-08.

## Correctness boundary

MNIST-07 reuses the M12.3 physical multi-tick conformance boundary rather than defining a second FPGA validation method.

The FPGA-visible generated include contains only:

- neuron configuration words;
- zero initial neuron state;
- frozen weight-format words;
- frozen synapse words;
- frozen axon-row pointers;
- empty route tables;
- per-tick external axon-event schedules; and
- case/count metadata needed by the capture shell.

It contains **no** expected neuron states, expected synaptic accumulators, expected spikes, expected predictions, or host-generated recurrent-event schedule.

The host independently runs the frozen deployment through `NeuromorphicCore` and preserves a golden 16-tick trace. After each physical FPGA tick, the existing M12 trace bridge/VIO capture path reads the committed state and event windows. Host-side validation compares:

- committed tick;
- external and recurrent input events;
- exact signed-64 synaptic accumulator per neuron;
- packed neuron state before the update;
- packed neuron state after the update;
- per-neuron spike flags;
- routed output events;
- core fault status;
- external event count; and
- final output spike counts and decoded prediction.

The profiles contain no recurrent routes, so recurrent queue bank-selection internals are not acceptance fields; recurrent consumed/routed event counts must remain zero.

## Reused platform hardware

No new neuron or synapse semantics are introduced. The bitstream flow reuses:

- `m08_weight_decoder_v1.sv`;
- `phase_b_synapse_accumulator_v1.sv`;
- `neuron_array_controller_v1.sv`;
- `recurrent_integrated_core_controller_v1.sv`;
- `m12_trace_read_bridge_v1.sv`;
- `m12_3_multitick_capture_controller_v1.sv`;
- `create_m12_3_project.tcl`;
- `capture_m12_3_multitick.tcl`; and
- the packaged `neuron_step_v1` HLS IP.

The M12.3 controller supports the MNIST-v1 physical limits: 10 neurons, up to 784 input axons, up to 4,086 stored synapses, two weight formats, zero routes, 16 ticks, and an external event schedule within the frozen 4,096-event/tick capacity.

## New application tooling

`mnist_app/fpga_conformance.py`:

- selects the frozen both-correct anchor;
- reloads the exact source MNIST image;
- regenerates both deterministic encoder schedules;
- reads the source-controlled frozen deployment images;
- packs FPGA configuration/state words;
- independently computes 16 golden ticks through `NeuromorphicCore`;
- emits an M12.3-compatible input-only SystemVerilog include; and
- performs exact host-side physical/golden comparison.

CLI entry points:

```text
scripts/generate_fpga_conformance.py
scripts/validate_fpga_conformance.py
scripts/validate_fpga_conformance_suite.py
```

Physical flows:

```text
fpga/run_mnist_07_bitstream.sh
fpga/run_mnist_07_hardware.sh
```

## Accepted physical result

The complete MNIST-07 flow was executed in the user K26/KV260 environment after the application pytest suite, software/golden generator, and Vivado bitstream flow passed.

Both frozen profiles completed their full 16-tick physical presentation with **zero architectural mismatches** against the independently generated Python golden traces:

| Case | Profile | Source MNIST index | Label | Ticks | Physical/golden result |
|---|---|---:|---:|---:|---|
| 0 | cropped-dense | 3 | 0 | 16 | PASS, 0 mismatches |
| 1 | native-sparse | 3 | 0 | 16 | PASS, 0 mismatches |

For both cases, the physical trace agreed exactly on the compared per-tick architectural fields, and final physical output spike counts/predictions matched the Python golden result. The accepted hardware run therefore closes both MNIST-07A and MNIST-07B.

This result is application-level physical conformance, not merely classification agreement: an equal final digit prediction would not have been sufficient if any intermediate state, synaptic accumulator, spike flag, event sequence, or packed state word had differed.

## Completion criteria

MNIST-07 required all of the following on the physical K26, and all were satisfied:

1. the generated case bundle was derived from the committed `mnist-v1` freeze;
2. the Vivado 2025.2 K26 implementation completed and passed the existing resource/timing gates;
3. cropped-dense produced 16 committed physical ticks with zero architectural mismatches;
4. native-sparse produced 16 committed physical ticks with zero architectural mismatches;
5. physical final spike counts and predictions equaled the independent Python golden results for both profiles; and
6. the physical flow produced machine-readable capture/differential artifacts for the accepted run.

MNIST-08 expands this same correctness boundary to the frozen 30-image common application corpus rather than introducing a new physical validation definition.
