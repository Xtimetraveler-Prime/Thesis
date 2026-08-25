# M11.5.2 Serialized Neuron-Array Controller

M11.5.2 is the first RTL integration layer around the M11.3/M11.4-verified
`neuron_step_v1` HLS IP. It does not change neuron arithmetic. It adds finite
neuron memories plus a deterministic controller that presents one neuron at a
time to the verified HLS block.

## Frozen boundary

- Toolchain: AMD Vivado 2025.2.
- Physical neuron capacity: 256.
- State word: 64 bits from M11.5.1.
- Configuration word: 128 bits from M11.5.1.
- Tick-local synaptic accumulator: signed 64 bits per neuron.
- Spike storage: one bit per physical neuron.
- HLS transaction protocol: `ap_ctrl_hs`.
- HLS result protocol: four `ap_vld` result signals.

The controller source is:

```text
rtl/core_v1/neuron_array_controller_v1.sv
```

## Serialized Phase-C operation

M11.5.2 assumes Phase B has already produced one signed-64 synaptic sum for each
neuron. M11.5.3 will later fill these accumulators by traversing the frozen M08
axon/synapse image.

For one tick, the controller performs:

```text
neuron 0 state/config/accumulator read
        -> validate config word
        -> assert HLS ap_start until ap_ready
        -> capture ap_done + all four ap_vld outputs
        -> write next state/spike and clear accumulator
neuron 1
        -> ...
...
last active neuron
        -> increment architectural tick
        -> pulse tick_done
```

`ap_start` remains high through the clock edge on which `ap_ready` is sampled.
Leaving the wait-ready FSM state then deasserts `ap_start` on the next cycle, so
the completed request does not auto-restart. The controller also handles the
non-pipelined case in which `ap_ready` and `ap_done` coincide by latching the
result before entering the writeback state.

## Atomic-tick observability

M10 prohibits partially updated neuron state from being architecturally visible
within the same tick. This first implementation uses one state memory and writes
each neuron back as it completes, but external state/config/accumulator debug
reads are serviced only while `busy == 0`. No other neuron consumes another
neuron's state during Phase C; all synaptic inputs must already be accumulated
before `tick_start`. The serialized writeback is therefore behaviorally
consistent with the M10 atomic tick boundary without doubling the state memory.

## Core reset

`ap_rst` resets only the controller/control-plane registers. The architectural
M10 reset is an explicit `core_reset_start` transaction so block RAM contents do
not require a mass asynchronous reset.

For each active neuron, core reset reads its validated configuration and writes:

```text
current                = 0
voltage                = reset_voltage
refractory_remaining   = 0
synaptic accumulator   = 0
spike flag             = 0
```

After the last active neuron, `tick` is set to zero and `core_reset_done` pulses.

## Configuration validation

Before reset or tick execution the RTL rejects a configuration word if:

- reserved bits `[127:114]` are nonzero;
- current decay exceeds 4096;
- voltage decay exceeds 4096; or
- threshold is not strictly greater than reset voltage.

The controller also rejects neuron counts of zero or greater than the physical
256-neuron profile.

## Standalone sequencer simulation

The source-controlled testbench is:

```text
rtl/core_v1/tb/tb_neuron_array_controller_v1.sv
```

It uses a small mock of the already-verified HLS block only to test controller
sequencing, handshaking, state/config memory addressing, architectural reset,
accumulator clearing, spike storage, tick increment, and the coincident
`ap_ready`/`ap_done` case. It intentionally does **not** claim to revalidate
neuron arithmetic.

Run under the standardized vendor toolchain with:

```bash
cd "Neuromorphic Digital Twin/rtl/core_v1"
bash run_m11_5_2_sim.sh | tee m11_5_2_controller_sim.log
```

A successful simulation ends with:

```text
M11.5.2 neuron-array controller tests passed: 3 neurons, reset + 1 tick
M11.5.2 standalone RTL controller simulation completed successfully.
```

## Python packed-memory reference

`src/neuromorphic_twin/neuron_array_reference.py` adapts the frozen Python
`step_neuron(..., arithmetic=FPGA_CORE_ARITHMETIC_V1)` transition to the exact
64-bit state and 128-bit configuration words. This gives integration tests one
golden function for comparing complete memory images across multiple neurons.

## Real packaged-HLS integration gate

The second M11.5.2 gate connects the controller to the **actual M11.4 packaged
HLS IP** rather than the mock.

The IP-Integrator-facing wrapper is:

```text
rtl/core_v1/neuron_array_controller_bd_v1.sv
```

It contains no sequencing arithmetic. It only instantiates
`neuron_array_controller_v1` and annotates its HLS control pins as a Vivado
`xilinx.com:interface:acc_handshake:1.0` master named `hls_ctrl`.

`vivado/create_m11_5_2_project.tcl` then creates a K26-targeted project and block
design containing:

```text
neuron_array_controller_bd_v1  (RTL Module Reference)
              |
              | hls_ctrl / scalar neuron data
              v
neuron_step_v1_0                (M11.4 packaged HLS IP)
```

The complete accelerator handshake is connected with `connect_bd_intf_net`;
individual `ap_start/ap_done/ap_idle/ap_ready` member pins are not overridden.
Clock/reset and every HLS scalar input/output-valid signal are connected
explicitly and block-design validation is mandatory.

### Deterministic integration corpus

`examples/generate_m11_5_2_vectors.py` produces one ephemeral SystemVerilog
include from the Python golden path. One integrated tick contains 64 neurons:

```text
24 M11.2 directed boundary neurons
40 deterministic SplitMix64 neurons
seed = 0x4D313132
```

For every neuron the include contains:

- packed 128-bit configuration;
- packed pre-tick 64-bit dynamic state;
- reset-state expectation;
- signed 64-bit synaptic accumulator;
- packed expected post-tick state; and
- expected spike flag.

The real-IP XSIM testbench first loads configurations and executes architectural
reset, checking the reset image for all 64 neurons. It then loads the arbitrary
pre-tick state/accumulator image, executes one serialized tick through the real
HLS IP, and requires exact agreement on every packed state word and spike flag.
It also requires configuration to remain unchanged, each consumed accumulator
to be cleared to zero, and the architectural tick counter to increment once.

### Prerequisite

The runner reuses the ignored M11.4 packaged IP repository:

```text
hls/core_v1/build/m11_4/ip_repo/neuron_step_v1/component.xml
```

If that build artifact was removed, regenerate it once with `run_m11_4.sh`.
The packaged IP itself is not committed; the M11.4 source/configuration remains
the reproducible source of truth.

### Run the real-IP gate

From this directory:

```bash
bash run_m11_5_2_real_ip.sh | tee m11_5_2_real_ip.log
```

A successful XSIM run must contain:

```text
M11.5.2 real packaged-IP integration passed: neurons=64, directed=24, random=40, seed=0x4d313132
M11.5.2 controller + real packaged HLS IP simulation completed successfully.
```

Generated Vivado projects, vector includes, journals, and logs live under ignored
`rtl/core_v1/build/` output.

## M11.5.2 completion boundary

M11.5.2 is complete only after both vendor gates have been independently run on
the current branch:

1. standalone controller RTL simulation with the mock HLS responder; and
2. controller + actual packaged HLS IP XSIM comparison against the 64-neuron
   Python-generated packed corpus.

Passing those gates proves the state/config/accumulator memory boundary,
serialized multi-neuron scheduling, `ap_ctrl_hs`/`ap_vld` integration, reset,
writeback, spike storage, and tick advancement before synapse-memory traversal is
introduced.

M11.5.3 then replaces testbench-preloaded accumulator values with the real M08
weight-format/axon-row/synapse traversal and exact tick-local accumulation path.
