# MNIST-07 Single-Image FPGA Conformance

**Status:** Implementation complete; local software generation/pytest and physical K26 run pending

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

The M12.3 controller already supports the MNIST-v1 physical limits: 10 neurons, up to 784 input axons, up to 4,086 stored synapses, two weight formats, zero routes, 16 ticks, and an external event schedule within the frozen 4,096-event/tick capacity.

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

## Expected workflow

First validate the application code and generate the two cases without Vivado:

```bash
pytest applications/mnist/tests -q
python applications/mnist/scripts/generate_fpga_conformance.py
```

Then, in a shell with Vivado 2025.2 available and the packaged HLS IP already present:

```bash
bash applications/mnist/fpga/run_mnist_07_bitstream.sh
```

The bitstream script stages the existing M12.3 capture shell but replaces its directed-test include with the generated MNIST-07 input-only include. The resulting application artifacts are copied to:

```text
applications/mnist/build/mnist-07/artifacts/
  neuromorphic_twin_mnist_07.bit
  neuromorphic_twin_mnist_07.ltx
  neuromorphic_twin_mnist_07.xsa
  neuromorphic_twin_mnist_07_routed.dcp
```

With the K26/KV260 connected and `pl_clk0` running:

```bash
bash applications/mnist/fpga/run_mnist_07_hardware.sh
```

The hardware script programs the board once, captures both 16-tick cases through the established JTAG/VIO path, and runs the MNIST-specific exact differential validator.

## Completion criteria

MNIST-07 closes when all of the following are demonstrated on the physical K26:

1. the generated case bundle is derived from the committed `mnist-v1` freeze;
2. the Vivado 2025.2 K26 implementation completes and passes the existing resource/timing gates;
3. cropped-dense produces 16 committed physical ticks with zero architectural mismatches;
4. native-sparse produces 16 committed physical ticks with zero architectural mismatches;
5. physical final spike counts and predictions equal the independent Python golden results for both profiles; and
6. physical traces and machine-readable differential reports are preserved for the accepted run.
