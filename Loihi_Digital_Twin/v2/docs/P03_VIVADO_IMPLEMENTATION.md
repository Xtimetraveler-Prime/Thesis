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
- one explicit Block Memory Generator instance for every HLS memory argument;
- a VIO/JTAG control/status surface for `ap_start`, logical counts, timestep,
  HLS completion/status, and physical cycle count; and
- `p03_run_monitor.v`, which measures PL cycles from start to `ap_done`.

The physical memories deliberately use transparent P03 word widths and full
logical depths:

| Memory | Depth | Width | Raw bits |
|---|---:|---:|---:|
| compartment config | 1,024 | 128 | 131,072 |
| compartment state | 1,024 | 64 | 65,536 |
| input axon table | 4,096 | 64 | 262,144 |
| synapse table | 32,768 | 64 | 2,097,152 |
| route descriptors | 1,024 | 32 | 32,768 |
| route table | 4,096 | 32 | 131,072 |
| input events | 4,096 | 32 | 131,072 |
| normalized trace | 1,024 | 256 | 262,144 |
| output packets | 4,096 | 64 | 262,144 |

The logical event payload remains a 12-bit axon ID. The first draft used a
16-bit physical event word, but Vivado 2025.2 Block Memory Generator on this K26
configuration rejected that native-port width and reported a supported minimum
of 32 bits. P03 therefore uses a 32-bit physical event word with the axon ID in
bits `[11:0]` and the upper bits reserved. This is a physical-interface choice,
not an architectural capacity change.

The HLS core also contains its 1,024 x 64-bit tick-local accumulator RAM.
Logical Loihi/P02 capacity accounting remains separate from this physical memory
cost.

## HLS/Vivado memory-interface policy

The first implementation used HLS `bram` interfaces, which package each memory
as a grouped IP-Integrator BRAM bus. That path successfully exposed all nine
memories, but Vivado validation reported incompatible `MEM_SIZE` and
`READ_LATENCY` metadata between the packaged HLS interface and native Block
Memory Generator. A subsequent attempt to use a `BRAM_Controller` BMG interface
also failed because Vivado 2025.2 reported only `Native` as valid for this
`blk_mem_gen:8.4` instance.

P03 therefore uses HLS `ap_memory` interfaces with `storage_type=ram_1p` for the
external memory arguments. `ap_memory` keeps the same RAM transaction semantics
while exposing discrete, word-addressed address/CE/WE/data pins. The Vivado shell
connects those pins directly to explicitly sized native single-port BMG pins.
This intentionally removes IP-Integrator bus-metadata negotiation from the
compute-memory boundary without changing the algorithm, table contents, logical
capacities, or one-cycle synchronous RAM expectation.

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

Because the HLS memory protocol changed from grouped `bram` to discrete
`ap_memory`, the C/RTL co-simulation gate must be rerun once before treating the
Vivado implementation result as evidence.

This gate passes only if:

1. HLS C/RTL co-simulation still matches the Python-generated differential corpus;
2. Vivado validates every discrete HLS-to-native-memory connection;
3. synthesis and implementation complete on `xck26-sfvc784-2LV-c`;
4. post-route timing is reported at the propagated ~100 MHz PL clock; and
5. resource reports make all BRAM/URAM/LUT/FF/DSP use explicit.

A bitstream/physical inference test follows this gate; it is not implied by a
successful routed implementation.
