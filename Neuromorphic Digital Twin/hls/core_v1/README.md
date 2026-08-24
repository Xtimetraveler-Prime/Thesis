# M11 HLS Computational Core

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

## Scope of the current HLS top

M11.1 established the smallest useful synthesis boundary: one complete neuron state transition. The HLS top function is:

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

Synapse-memory traversal, per-neuron accumulation, recurrent event routing, tick scheduling, host interfaces, and trace buffering remain outside this top function. Those pieces are integrated in later M11 sub-milestones after neuron arithmetic has an independently verified HLS implementation.

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

The current HLS boundary uses a signed 64-bit integer for the already-accumulated synaptic-input scalar and intermediate arithmetic. M11.2 deliberately limits randomized synaptic-input vectors to signed 32-bit values: that range is large enough to stress both SAT24 boundaries while avoiding a false claim that the final physical accumulator/event capacity has already been frozen. That capacity remains M11.5 work.

## M11.1 C-simulation gate

The original self-checking C++ testbench contains 11 hand-written directed cases. The successful M11.1 vendor run under Vitis 2025.2 finishes with:

```text
M11.1 HLS neuron-step tests passed: 11 cases
```

This established that the HLS C++ source compiles under the selected vendor toolchain and reproduces the directed M10 equations.

## M11.2 Python-to-HLS differential gate

M11.2 extends C simulation so expected values come directly from the frozen Python FPGA-v1 profile instead of being hand-copied into C++.

The Python source of truth is:

```text
NeuronState + NeuronConfig
          ↓
step_neuron(..., arithmetic=FPGA_CORE_ARITHMETIC_V1)
          ↓
expected current / voltage / refractory / spike
```

`src/neuromorphic_twin/hls_conformance.py` generates the comparison corpus and `examples/generate_m11_hls_vectors.py` provides its CLI. The standard corpus is deterministic:

```text
directed boundary cases: 24
seeded random cases:   2048
---------------------------
total:                 2072
seed:             0x4D313132
```

The boundary set explicitly covers strict threshold equality, positive and negative SAT24 boundaries, decay values including `0`, `1`, `2048`, `4095`, and `4096`, positive/negative round-away-from-zero cases, refractory state/count boundaries including `65535`, bias saturation, reset boundaries, and large positive/negative accumulated synaptic inputs.

The pseudo-random set spans the legal FPGA-v1 state/configuration domains. About half of the randomized states are deliberately non-refractory so threshold and spike behavior remain heavily exercised rather than being hidden by random nonzero refractory counters.

The generator writes an ephemeral C++ initializer named:

```text
generated_m11_2_vectors.inc
```

The file is generated inside the HLS staging directory before Vitis compiles the testbench. It is not committed; the repository instead stores the Python generator, frozen seed, and tests that guarantee deterministic reproduction.

A successful M11.2 C simulation must additionally finish with:

```text
M11.2 Python/HLS differential tests passed: 2072 cases (directed=24, random=2048, seed=0x4d313132)
```

Any mismatch prints the vector name plus expected and actual current, voltage, refractory state, and spike before returning a nonzero process status.

## Running the combined M11.1 + M11.2 C simulation

The HLS component definition is in `hls_config.cfg`. The exact FPGA part is supplied at run time.

First source the Vitis/Vivado 2025.2 environment and export the target part:

```bash
export HLS_PART='xck26-sfvc784-2LV-c'
```

Then, from this directory, run:

```bash
bash run_csim.sh
```

The repository path contains the directory name `Neuromorphic Digital Twin`. Vitis HLS 2025.2 rejects HLS project/solution paths containing spaces, so `run_csim.sh` automatically copies the HLS source, headers, testbench, and config into:

```text
/tmp/neuromorphic_twin_hls_<uid>/m11_core_csim
```

The source checkout is not modified by staging, and the staging directory is recreated for every run. Before invoking Vitis, the wrapper runs the Python golden-vector generator with `PYTHONPATH` pointed at the repository `src` tree. It then verifies `vitis`, `vitis-run`, `v++`, and `vivado` all report version `2025.2` and runs:

```bash
vitis-run --mode hls --csim \
  --config hls_config.cfg \
  --work_dir /tmp/neuromorphic_twin_hls_<uid>/m11_core_csim/work \
  --part "$HLS_PART"
```

## Python-side regression tests

The M11.2 generator has dedicated pytest coverage:

```bash
pytest -q tests/test_m11_hls_conformance.py
```

Those tests check deterministic generation, required boundary coverage, exact replay of generated expectations through the Python golden model, and byte-for-byte reproducible C++ initializer output.

## Why synthesis is still deferred

M11.2 is a stronger behavioral gate, not RTL generation. C synthesis, clock constraints, latency/resource inspection, and C/RTL co-simulation are M11.3. Packaging generated RTL as a Vivado IP and creating the Vivado system project are M11.4.
