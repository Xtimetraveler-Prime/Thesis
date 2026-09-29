# FPGA-v2 P03 One-Core HLS Engine

This directory contains the first synthesizable one-core implementation for P03.
The architecture contract is `../../docs/LOIHI1_TARGET_SPEC.md`; the packed
hardware boundary is documented in `../../docs/P03_ONE_CORE_HARDWARE_BOUNDARY.md`.

## What this block does

`loihi_core_v2_tick` executes one algorithmic timestep for one logical core:

1. clear the tick-local 64-bit accumulators;
2. resolve each input event through the destination-side axon table;
3. traverse the referenced shared synapse-template row;
4. accumulate effective signed weights into destination compartments;
5. apply the v1-compatible 24-bit saturating compartment update;
6. emit spikes and walk explicit output-route rows;
7. write normalized packet records; and
8. write one normalized trace record per active compartment.

The top level has explicit memory ports for configuration/state/axon/synapse/
route/event/trace/packet storage. The final host/debug transport is intentionally
not frozen by this component.

## Toolchain

P03 is pinned to:

```text
AMD Vitis/Vivado 2025.2
xck26-sfvc784-2LV-c
100 MHz target clock (10 ns)
12% clock uncertainty
```

Before running HLS:

```bash
source /path/to/Vitis/2025.2/settings64.sh
export HLS_PART='xck26-sfvc784-2LV-c'
```

## C simulation

From `Loihi_Digital_Twin/v2` with the v2 Python package installed:

```bash
bash hls/core_v2/run_csim.sh
```

The runner generates `tb/generated_p03_vectors.inc` in a temporary staging
area directly from the P02 Python golden model. A successful run ends with:

```text
P03 Python/HLS one-core differential passed: 5 ticks, 3 compartments
P03 runtime integrity guards passed
P03 one-core HLS C-simulation suite passed
```

## Synthesis and C/RTL co-simulation

```bash
bash hls/core_v2/run_synth_cosim.sh
```

Reports are copied under:

```text
hls/core_v2/build/p03/
```

That directory is generated evidence and is not intended for source control.
The first synthesis result is a P03 decision/verification gate: timing, inferred
memories, interface generation, and resource use must be inspected before a
Vivado/K26 wrapper is frozen.

## Claim boundary

The HLS core preserves the P02 logical semantics. It does **not** claim that its
64-bit physical synapse words or BRAM layout reproduce native Loihi SRAM bit
packing. Logical resource accounting remains governed by the v2 specification
and Python deployment model; physical K26 memory use is reported separately.
