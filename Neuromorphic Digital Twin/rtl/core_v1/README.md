# M11.5.2 Serialized Neuron-Array Controller

**Status:** Complete  
**Started:** 2026-08-24  
**Completed:** 2026-08-24  
**Repository evidence:** branch `agent/m11-5-core-integration`

M11.5.2 is the first RTL integration layer around the M11.3/M11.4-verified
`neuron_step_v1` HLS IP. It does not change neuron arithmetic. It adds finite
neuron memories plus a deterministic controller that presents one neuron at a
time to the verified HLS block.

## Frozen boundary

- Toolchain: AMD Vivado 2025.2.
- FPGA target: `xck26-sfvc784-2LV-c`.
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
neuron. M11.5.3 replaces testbench-preloaded accumulators with the real M08
axon-row/synapse/weight-format traversal.

For one tick, the controller performs:

```text
neuron 0 state/config/accumulator read
        -> validate config word
        -> assert HLS ap_start
        -> wait for the ap_ctrl_hs transaction
        -> capture all four ap_vld results
        -> write next state/spike and clear accumulator
neuron 1
        -> ...
...
last active neuron
        -> increment architectural tick
        -> pulse tick_done
```

`ap_start` remains high through the clock edge on which `ap_ready` is sampled.
Leaving the wait-ready FSM state deasserts it on the following cycle. The
controller also captures the non-pipelined case in which `ap_ready` and
`ap_done` coincide.

## Atomic-tick observability

M10 prohibits partially updated neuron state from becoming architecturally
visible inside the same tick. This implementation uses one state memory and
writes each neuron back as it completes, but debug/state/config/accumulator reads
are serviced only while `busy == 0`. No neuron transition consumes another
neuron's state; all Phase-B synaptic inputs are already complete before Phase C.
Therefore the serialized writeback preserves the M10 atomic tick boundary
without a second state-memory bank.

## Architectural reset

`ap_rst` resets controller/control-plane registers. The architectural reset is a
separate `core_reset_start` transaction so block RAM contents do not require a
mass asynchronous reset.

For every active neuron, core reset writes:

```text
current                = 0
voltage                = reset_voltage
refractory_remaining   = 0
synaptic accumulator   = 0
spike flag             = 0
```

After the final active neuron, `tick` is zero and `core_reset_done` pulses.

## Configuration validation

Before reset or tick execution the RTL rejects a configuration if:

- reserved bits `[127:114]` are nonzero;
- current decay exceeds 4096;
- voltage decay exceeds 4096; or
- threshold is not strictly greater than reset voltage.

Neuron counts of zero or greater than 256 are also rejected.

## Standalone controller gate

The source-controlled testbench is:

```text
rtl/core_v1/tb/tb_neuron_array_controller_v1.sv
```

It uses a small mock HLS responder only to test controller sequencing,
handshaking, state/config memory addressing, architectural reset, accumulator
clearing, spike storage, tick increment, and the coincident
`ap_ready`/`ap_done` case. It does not revalidate neuron arithmetic.

Run with:

```bash
cd "Neuromorphic Digital Twin/rtl/core_v1"
bash run_m11_5_2_sim.sh | tee m11_5_2_controller_sim.log
```

The independently reproduced pass markers are:

```text
M11.5.2 neuron-array controller tests passed: 3 neurons, reset + 1 tick
M11.5.2 standalone RTL controller simulation completed successfully.
```

## Python packed-memory reference

`src/neuromorphic_twin/neuron_array_reference.py` adapts
`step_neuron(..., arithmetic=FPGA_CORE_ARITHMETIC_V1)` to the frozen 64-bit state
and 128-bit configuration words. This is the golden packed-memory reference used
by the real-IP testbench.

## Real packaged-HLS integration

The second gate connects the controller to the actual M11.4 packaged HLS IP.

The IP-Integrator-facing top is:

```text
rtl/core_v1/neuron_array_controller_bd_v1.v
```

Vivado 2025.2 rejects a SystemVerilog file as a Module Reference top, so the
actual controller remains SystemVerilog while this thin wrapper is Verilog-2001.
The wrapper contains no neuron arithmetic or sequencing behavior; it only
instantiates `neuron_array_controller_v1` and provides the Module Reference
boundary.

The HLS transaction handshake is intentionally kept as four scalar pins at this
boundary:

```text
controller hls_ap_start -> neuron_step_v1_0/ap_start
controller hls_ap_done  <- neuron_step_v1_0/ap_done
controller hls_ap_idle  <- neuron_step_v1_0/ap_idle
controller hls_ap_ready <- neuron_step_v1_0/ap_ready
```

`vivado/create_m11_5_2_project.tcl` connects and verifies each of these nets
explicitly. This avoids the Vivado 2025.2 behavior observed during integration
where a mixed inferred `acc_handshake` connection could leave `ap_start` tied to
zero. The `BD 41-1306` interface-member override warnings are expected because
the packaged HLS IP still groups these pins under its `ap_ctrl` interface; the
checked-in Tcl is the normative reconstruction source rather than generated
`write_bd_tcl` output.

The Module Reference wrapper also declares 100 MHz clock/reset metadata so the
clock contract is explicit at the source boundary.

## Deterministic real-IP corpus

`examples/generate_m11_5_2_vectors.py` produces an ephemeral SystemVerilog
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

The XSIM test first proves architectural reset for all 64 neurons, then reloads
arbitrary pre-tick state/accumulator values, executes one serialized tick through
the real HLS RTL, and compares every complete state word and spike bit with the
Python-generated expectations. Configuration must remain unchanged, consumed
accumulators must be zero, and the architectural tick must increment exactly
once.

## Reproduction

The runner reuses the ignored M11.4 packaged IP repository:

```text
hls/core_v1/build/m11_4/ip_repo/neuron_step_v1/component.xml
```

Run:

```bash
cd "Neuromorphic Digital Twin/rtl/core_v1"
bash run_m11_5_2_real_ip.sh | tee m11_5_2_real_ip.log
```

The final independently reproduced Vivado/XSIM run on 2026-08-24 reached:

```text
M11.5.2 connected controller_0/hls_ap_start -> neuron_step_v1_0/ap_start
M11.5.2 connected controller_0/hls_ap_done  -> neuron_step_v1_0/ap_done
M11.5.2 connected controller_0/hls_ap_idle  -> neuron_step_v1_0/ap_idle
M11.5.2 connected controller_0/hls_ap_ready -> neuron_step_v1_0/ap_ready
M11.5.2 real-IP block design validated successfully.
M11.5.2 real packaged-IP integration passed: neurons=64, directed=24, random=40, seed=0x4d313132
M11.5.2 controller + real packaged HLS IP simulation completed successfully.
```

XSIM finished at 11,590 ns after exact comparison of the full 64-neuron corpus.
No timeout, controller fault, state mismatch, spike mismatch, or accumulator
mismatch was reported.

## Completion meaning

M11.5.2 now proves, with both a standalone RTL controller test and the actual
packaged HLS RTL in XSIM:

- frozen state/config/accumulator memory boundaries;
- architectural reset;
- deterministic ascending-neuron serialization;
- explicit `ap_ctrl_hs` transaction wiring;
- all four `ap_vld` result paths;
- exact state/spike writeback versus the Python golden model;
- accumulator consumption/clearing;
- configuration preservation; and
- exactly one architectural tick commit after all configured neurons finish.

M11.5.3 is the next active gate. It replaces preloaded accumulator values with
M08-compatible weight-format, synapse, and axon-row memories plus exact signed
64-bit Phase-B accumulation.
