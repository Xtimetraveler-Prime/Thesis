# M11.1 HLS Computational Core

This directory starts the hardware implementation of the frozen M10 FPGA-v1 computational-core specification.

## Standard M11 toolchain

M11 and later FPGA-development work standardize on:

```text
AMD Vitis  2025.2
AMD Vivado 2025.2
```

The command-line HLS flow uses the 2025.2 Unified IDE tools:

- `vitis-run --mode hls --csim` for C simulation;
- `v++ -c --mode hls` for HLS synthesis;
- `vitis-run --mode hls --cosim` for C/RTL co-simulation;
- `vitis-run --mode hls --package` for the later Vivado-IP packaging step.

The repository no longer uses the legacy `vitis_hls -f ...` project script as the primary M11 flow.

## Scope of M11.1

M11.1 deliberately implements the smallest useful synthesis boundary: one complete neuron state transition. The HLS top function is:

```text
neuron_step_v1(...)
```

It consumes:

- current before the tick;
- voltage before the tick;
- refractory counter before the tick;
- already-accumulated integer synaptic input;
- current and voltage decay;
- threshold, bias, and reset voltage;
- configured refractory duration.

It produces:

- current after the tick;
- voltage after the tick;
- refractory counter after the tick;
- spike/no-spike.

Synapse-memory traversal, per-neuron accumulation, recurrent event routing, tick scheduling, host interfaces, and trace buffering are intentionally outside the M11.1 top function. Those pieces are integrated in later M11 sub-milestones after the neuron arithmetic has an independently testable HLS implementation.

## Frozen M10 semantics implemented

The C++ datapath follows the FPGA-v1 contract rather than relying on native C/C++ overflow behavior:

```text
I_work = SAT24(I0 + S)
I_next = SAT24(DECAYED(I_work, current_decay))
```

For a non-refractory neuron:

```text
V_decay_base = DECAYED(V0, voltage_decay)
V_work       = SAT24(V_decay_base + I_work + bias)
spike        = (V_work > threshold)
```

A spike hard-resets voltage and loads `max(refractory_ticks - 1, 0)`. A blocked refractory tick still updates current, holds voltage at reset voltage, suppresses spiking, and decrements the refractory counter.

Decay removes:

```text
round_away_from_zero(value * decay / 4096)
```

Because `4096 == 2^12`, the HLS implementation computes the magnitude ceiling with an add-and-shift operation while preserving the exact M10 integer result.

## HLS widths

The frozen architectural state uses:

- `ap_int<24>` current and voltage;
- `ap_uint<16>` refractory state;
- `ap_uint<13>` decay configuration;
- `ap_uint<1>` spike output.

M11.1 uses a signed 64-bit HLS integer for the scalar synaptic-accumulator input and intermediate arithmetic. This is an implementation boundary, not a change to M10 neuron semantics. The finite event/accumulator capacity of the complete hardware core will be frozen when synapse traversal and core scheduling are integrated later in M11.

## Vitis 2025.2 C simulation

The HLS component definition is in `hls_config.cfg`. The exact FPGA part is deliberately supplied at run time because the project should not guess the physical target.

First source the Vitis/Vivado 2025.2 environment, then determine the exact part used by the target Vivado project. From an open Vivado project, the Tcl console command is:

```tcl
get_property PART [current_project]
```

Export that result in the shell:

```bash
export HLS_PART='<exact-part-name>'
```

Then, from this directory, run:

```bash
bash run_csim.sh
```

The wrapper verifies that `vitis`, `vitis-run`, `v++`, and `vivado` all resolve and report version `2025.2`, clears the generated C-simulation work directory, and runs:

```bash
vitis-run --mode hls --csim \
  --config hls_config.cfg \
  --work_dir build/csim \
  --part "$HLS_PART"
```

The self-checking testbench should finish with:

```text
M11.1 HLS neuron-step tests passed: 11 cases
```

The testbench returns a non-zero process status on a mismatch.

## Why synthesis is not part of M11.1 yet

C simulation validates the behavioral C++ boundary before device-specific scheduling decisions are introduced. The exact target part is already supplied to keep the 2025.2 component reproducible, but clock constraints, C synthesis, resource/latency inspection, and C/RTL co-simulation remain M11.3 work after M11.2 establishes a broader Python-to-HLS behavioral comparison.
