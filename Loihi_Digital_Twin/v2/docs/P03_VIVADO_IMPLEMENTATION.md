# P03 Vivado Implementation Shell

## Purpose

This stage places the already C/RTL-co-simulation-verified `loihi_core_v2_tick`
HLS IP into a K26/KV260 Vivado design with explicit physical memories. It is a
physical implementation/measurement shell; it does **not** change the P02/P03
architectural contract.

## First implementation objective

The immediate gate is post-route evidence, not physical inference yet. The
Vivado design therefore provides:

- the K26/KV260 PS preset as a carrier-independent 100 MHz PL clock source;
- the packaged `loihi_core_v2_tick` HLS IP;
- one explicit memory IP for every HLS BRAM interface;
- a VIO/JTAG control/status surface for `ap_start`, logical counts, timestep,
  HLS completion/status, and physical cycle count; and
- `p03_run_monitor.v`, which measures PL cycles from start to `ap_done`.

The physical memories deliberately use the transparent P03 word widths and full
logical depths:

| Memory | Depth | Width | Raw bits |
|---|---:|---:|---:|
| compartment config | 1,024 | 128 | 131,072 |
| compartment state | 1,024 | 64 | 65,536 |
| input axon table | 4,096 | 64 | 262,144 |
| synapse table | 32,768 | 64 | 2,097,152 |
| route descriptors | 1,024 | 32 | 32,768 |
| route table | 4,096 | 32 | 131,072 |
| input events | 4,096 | 16 | 65,536 |
| normalized trace | 1,024 | 256 | 262,144 |
| output packets | 4,096 | 64 | 262,144 |

The HLS core also contains its 1,024 x 64-bit tick-local accumulator RAM.
Logical Loihi/P02 capacity accounting remains separate from this physical memory
cost.

## Memory-placement policy at this gate

The first routed build intentionally uses Vivado Block Memory Generator with its
normal block-memory implementation for every HLS-visible bank. This establishes
a conservative reproducible physical baseline and tests whether the complete
transparent memory boundary fits before introducing placement optimizations.

The 32,768 x 64 synapse bank is the obvious candidate for a later UltraRAM/XPM
implementation. That optimization is deferred until the baseline post-route
utilization and timing reports exist; moving it must not change memory contents
or logical resource accounting.

## HLS findings motivating this gate

The first P03 HLS synthesis/co-simulation gate passed exact Python/HLS/RTL
behavior over the five-timestep corpus and passed runtime integrity guards. Its
100 MHz estimate was 8.785 ns against the uncertainty-adjusted 8.8 ns budget,
which is functionally acceptable but too close to treat as timing closure.
The reported 272,664,582-cycle pathological maximum was dominated by the fully
serialized event x synapse-row traversal and is a capacity-bound worst case, not
a representative workload latency. Post-route timing and workload-scaled cycle
measurements are therefore required before optimizing that traversal.

## Next evidence

`vivado/run_p03_impl.sh` packages the HLS IP, creates the K26 project, routes the
complete memory shell, and emits timing/utilization reports under
`vivado/build/p03_impl/reports/`.

This gate passes only if:

1. Vivado validates the HLS-to-memory interfaces;
2. synthesis and implementation complete on `xck26-sfvc784-2LV-c`;
3. post-route timing is reported at the propagated ~100 MHz PL clock; and
4. resource reports make all BRAM/URAM/LUT/FF/DSP use explicit.

A bitstream/physical inference test follows this gate; it is not implied by a
successful routed implementation.
