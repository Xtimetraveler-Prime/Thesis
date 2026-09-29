# P03 Vivado Implementation Shell

## Purpose

This stage places the already C/RTL-co-simulation-verified `loihi_core_v2_tick`
HLS IP into a K26/KV260 Vivado design with explicit physical memories. It is a
physical implementation/measurement shell; it does **not** change the P02/P03
architectural contract.

Integration problems and their resolutions are tracked in
`docs/P03_INTEGRATION_CHALLENGES.md`. Those notes intentionally distinguish
Vivado/HLS interface accommodations from source-backed Loihi architectural
requirements.

## First implementation objective

The immediate gate is a **retained, programmable post-route one-core shell**.
The Vivado design provides:

- the K26/KV260 PS preset as a carrier-independent 100 MHz PL clock source;
- the packaged `loihi_core_v2_tick` HLS IP;
- one true-dual-port Block Memory Generator bank for every HLS `ap_memory`
  interface;
- a unified banked host/debug bridge on memory Port B;
- VIO/JTAG controls for both HLS execution and host/debug memory requests;
- an interlock preventing host-memory access from overlapping a compute run;
- `p03_run_monitor.v`, which measures PL cycles from accepted start to
  `ap_done`; and
- explicit post-route timing, bus-skew, utilization, and retention checks.

## Physical memory image

The physical memories use transparent P03 word widths and full logical depths:

| Memory | Depth | Width | Raw bits | Host bank |
|---|---:|---:|---:|---:|
| compartment config | 1,024 | 128 | 131,072 | 0 |
| compartment state | 1,024 | 64 | 65,536 | 1 |
| input axon table | 4,096 | 64 | 262,144 | 2 |
| synapse table | 32,768 | 64 | 2,097,152 | 3 |
| route descriptors | 1,024 | 32 | 32,768 | 4 |
| route table | 4,096 | 32 | 131,072 | 5 |
| input events | 4,096 | 32 | 131,072 | 6 |
| normalized trace | 1,024 | 256 | 262,144 | 7 |
| output packets | 4,096 | 64 | 262,144 | 8 |

The external image therefore contains **3,375,104 raw bits** before the HLS
core's 1,024 x 64-bit tick-local accumulator RAM.

The logical event payload remains a 12-bit axon ID. The first draft used a
16-bit physical event word, but Vivado 2025.2 Block Memory Generator on this K26
configuration rejected that native-port width and reported a supported minimum
of 32 bits. P03 therefore uses a 32-bit physical event word with the axon ID in
bits `[11:0]` and upper bits reserved. This is a physical-interface choice, not
an architectural capacity change.

Logical Loihi/P02 capacity accounting remains separate from physical K26 memory
cost.

## HLS/Vivado memory-interface policy

The first implementation used HLS `bram` interfaces, which package each memory
as a grouped IP-Integrator BRAM bus. That path exposed all nine memories, but
Vivado validation reported incompatible `MEM_SIZE` and `READ_LATENCY` metadata
between the packaged HLS interface and manually configured Block Memory
Generator. An attempted controller-mode propagation path also failed because
this Vivado 2025.2 BMG instance exposed only the native interface type.

P03 therefore uses HLS `ap_memory` interfaces with `storage_type=ram_1p` for the
external memory arguments. `ap_memory` keeps the same RAM transaction semantics
while exposing discrete, word-addressed address/CE/WE/data pins. The compute side
connects those pins directly to native BMG Port A signals. This removes grouped
IP-Integrator memory metadata from the compute-memory boundary without changing
the algorithm, table contents, logical capacities, or synchronous RAM behavior.

## Retained dual-port memory policy

The first successful `ap_memory` route still used single-port banks connected
only to the HLS engine. It closed timing at 100 MHz, but the resulting `26` BRAM
tiles were far too small for the intended 3.38-Mbit external image and the named
external banks were absent from the hierarchical utilization grep. Because
several configuration banks had no runtime writer and trace/packet banks had no
runtime reader, synthesis was free to eliminate storage that could not influence
an observable result.

The redesigned shell therefore uses **True Dual Port RAM** for every external
bank:

```text
                       Port A
loihi_core_v2_tick  <---------->  retained memory bank
                                      ^
                                      |
                                      | Port B
                                      |
                           p03_memory_host_bridge
                                      ^
                                      |
                                  VIO / JTAG
```

Port A remains the HLS compute path. Port B is always connected to
`p03_memory_host_bridge`, so every bank is programmable and observable even when
the HLS datapath itself only reads or only writes that bank.

The bridge exposes one transport-neutral command:

```text
req
write
bank[3:0]
word_address[14:0]
write_data[255:0]
    ->
host_busy
ack
read_valid
error
read_data[255:0]
```

Narrow banks use the least-significant bits of the 256-bit data word and reads
are zero-extended. P03 drives this command surface through VIO/JTAG for bring-up.
A later PS/AXI front end can replace VIO without changing bank IDs, addresses,
or memory contents.

### Access arbitration

Host/debug requests are legal only while the HLS core is idle. A pending host
request makes `host_busy` true immediately; the run monitor will not issue an
HLS `ap_start` pulse while `host_busy` is true. Conversely, a host request that
arrives while the compute monitor is busy returns `ack + error` without touching
memory. This makes dual-port collision behavior an implementation guard rather
than part of the architectural model.

## Accepted single-port routing baseline

Before the retained-shell redesign, the `ap_memory`/native single-port design
completed K26 route at 100 MHz with:

```text
WNS       +1.468 ns
WHS       +0.020 ns
LUTs      2,144
registers 3,017
DSPs      2
BRAM      26 tiles
URAM      0
```

The positive setup/hold slack and small compute logic support the current P03
architecture; the anomalously small BRAM result is why the physical memory shell
is being redesigned rather than the neuron/synapse/routing semantics.

## Memory-retention assertion

The routed build script now treats memory retention as a correctness condition.
Because the nine external banks total 3,375,104 bits and are explicitly
BRAM-backed, the post-route flow requires at least **80 Block RAM Tile
equivalents**. This is intentionally below the theoretical raw-bit minimum and
is not an exact packing claim; it is a conservative guard that prevents a
26-tile optimized-away shell from being reported as a successful full-core
implementation.

The implementation flow also emits a dedicated bus-skew report in addition to
setup/hold, DRC, methodology, clock, hierarchy, and utilization reports.

## Large synapse-bank placement

The 32,768 x 64 synapse bank remains the obvious candidate for a later UltraRAM
implementation. The retained-shell gate intentionally keeps all banks BRAM
backed first so its physical cost is measured without silently changing the
memory architecture. Moving the synapse bank to URAM is an optimization decision
that can be made from measured routing/resource evidence and must not change its
contents or logical resource accounting.

## Next evidence

`vivado/run_p03_impl.sh` packages the HLS IP, creates the retained K26 shell,
routes it, and emits reports under `vivado/build/p03_impl/reports/`.

This gate passes only if:

1. Vivado validates all nine HLS-to-Port-A and host-to-Port-B memory paths;
2. synthesis and implementation complete on `xck26-sfvc784-2LV-c`;
3. post-route setup, hold, and bus-skew evidence is generated at the propagated
   ~100 MHz PL clock;
4. resource reports show a retained full memory image rather than the former
   optimized-away baseline; and
5. the build-time BRAM-retention assertion passes.

A physical read/write test through the host/debug bridge and the full
Python-vs-FPGA normalized trace corpus follow this routed gate. A successful
route alone does not imply physical differential conformance.
