# P03 Integration Challenges and Resolution Log

## Purpose

P03 is the first phase that carries the source-backed v2 architecture through
Python, HLS, packaged RTL, Vivado IP Integrator, and routed K26 implementation.
This file records integration problems encountered at those boundaries, why they
occurred, and how they were resolved. These are kept separate from the Loihi-1
architecture contract so tool-specific accommodations are not mistaken for
architectural requirements.

## Baseline that remains accepted

Before the issues below were encountered, the P03 one-core implementation had
already passed the Python/HLS C differential corpus and C/RTL co-simulation. A
K26 route of the first observable compute shell completed at the requested
100 MHz with post-route WNS `+1.468 ns` and WHS `+0.020 ns`. The compute/control
logic was small (`2,144` LUTs, `3,017` registers, `2` DSPs), so none of the
integration problems to date requires changing the P02/P03 neuron, axon,
synapse, routing, or timestep semantics.

The first successful route reported only `26` BRAM tiles, which was not enough
to contain the complete transparent P03 external-memory image (about 3.38 Mbit
before the HLS-local accumulator). A later true-dual-port BMG/host-bridge shell
improved retention to `48` RAMB36E2 tiles and still routed at 100 MHz with WNS
`+0.953 ns` and WHS `+0.013 ns`, but the build correctly failed the explicit
memory-retention assertion.

Diagnosis of that 48-tile build found the root cause: after block-design
validation **every one of the nine Block Memory Generator instances reported
`Write_Depth_A=2048`**, regardless of the requested logical depth. This included
banks intended to be 1,024, 4,096, and 32,768 words. The physical under-sizing
therefore occurred before synthesis/route; it was not primarily a synthesis
trimming problem.

The replacement fixed-depth XPM fabric then passed a synthesis-only retention
gate at **94.5 BRAM-tile equivalents**. The complete HLS + XPM K26 shell routed
successfully at 100 MHz using **96.5 BRAM tiles**, `3,545` LUTs, `5,607`
registers, `2` DSPs, and no URAM. Post-route timing closed with WNS `+1.148 ns`
and WHS `+0.010 ns`, and the bus-skew report passed. Primitive-level evidence
showed the 32,768 x 64 synapse bank alone occupying `57` RAMB36E2 primitives,
confirming that the dominant full-depth bank survived synthesis and route.

This closes the P03 physical-memory-retention challenge. The all-BRAM XPM shell
is retained as the transparent P03 reference implementation. Moving the large
synapse bank to UltraRAM remains a later scaling optimization for P04/P05, not a
repair required for one-core correctness.

## Challenge / resolution history

| Challenge | Observation | Resolution / current status |
|---|---|---|
| Packaged HLS BRAM interface names | Vitis packaged array ports as `<argument>_PORTA`; the first Vivado helper queried the unsuffixed C argument name. | Fixed the packaged-interface lookup. |
| Input-event physical word width | Vivado 2025.2 Block Memory Generator rejected the first 16-bit native event-memory port in this K26 configuration. | Widened only the physical event word to 32 bits. The logical axon ID remains 12 bits in `[11:0]`; upper bits are reserved. |
| Grouped BRAM metadata mismatch | Directly connecting grouped HLS `bram` interfaces to manually configured BMG instances produced incompatible `MEM_SIZE` and `READ_LATENCY` interface metadata. | Replaced the grouped HLS `bram` protocol with discrete `ap_memory` ports. |
| Unsupported BMG controller-mode assumption | An attempted `Interface_Type=BRAM_Controller` configuration was rejected because the instantiated BMG exposed only the Native interface mode. | Abandoned controller-mode propagation and retained native memory signaling. |
| Full memories optimized from the routed baseline | The first successful `ap_memory`/native route used only one memory access path. Read-only configuration banks had no runtime writer and trace/packet banks had no runtime reader, allowing synthesis to remove storage that could not influence an observable result. | Added a host/debug access path and hardware arbitration so every bank is programmable/readable while the compute core is idle. |
| BMG depth collapse in IP Integrator | The retained true-dual-port BMG shell routed with 48 RAMB36E2 tiles. Validation logs then showed all nine banks at depth 2048, including the intended 32,768x64 synapse bank. | **Resolved:** replaced BMG block-design instances with fixed-parameter `xpm_memory_tdpram` banks in RTL. The standalone fabric synthesized to 94.5 BRAM tiles and the complete routed shell used 96.5, with the synapse bank accounting for 57 RAMB36E2s. |
| Thin routed hold margin | The first successful shell closed hold with `+0.020 ns`; the retained 48-BRAM shell closed with `+0.013 ns`; the accepted full XPM shell closed with `+0.010 ns`. | Timing is passing with zero failing hold endpoints. Continue monitoring hold as the design grows, but this is not a P03 redesign trigger. |
| JTAG/VIO observability of one-cycle handshakes | The first host bridge emitted one-cycle `ack`/`rvalid` pulses, which are suitable for RTL simulation but not reliably pollable over JTAG at a 100 MHz PL clock. | P03 board-bring-up hardening makes host completion sticky until the next request and adds a completed-run counter so physical scripts can deterministically observe transaction and tick completion. |
| Hardware Manager VIO HEX formatting | The first physical harness programmed the K26 and discovered `vio_p03`, then failed on its first output write because Vivado HEX-radix VIO properties require exactly `ceil(width/4)` hexadecimal characters with no `0x` prefix. Passing decimal address/count strings directly would also have caused them to be reinterpreted as hexadecimal. | **Resolved in the harness:** all output values now pass through a width-aware formatter that distinguishes decimal Tcl integers from explicit `0x...` packed words, range-checks against the probe width, strips prefixes/underscores, and emits exactly the required number of hexadecimal characters. No bitstream change is required for this fix. |

## Accepted memory shell

The accepted P03 shell uses this invariant:

```text
                         Port A
P03 HLS compute core  <---------->  fixed-depth XPM true-dual-port RAM
                                      ^
                                      |
                                      | Port B
                                      |
                              p03_memory_host_bridge
                                      ^
                                      |
                                  VIO / JTAG
```

The XPM fabric defines all nine physical capacities directly in RTL:

1. configuration: `1024 x 128`;
2. state: `1024 x 64`;
3. axons: `4096 x 64`;
4. synapses: `32768 x 64`;
5. route descriptors: `1024 x 32`;
6. routes: `4096 x 32`;
7. input events: `4096 x 32`;
8. traces: `1024 x 256`; and
9. packets: `4096 x 64`.

Each bank uses `MEMORY_PRIMITIVE="block"` and
`MEMORY_OPTIMIZATION="false"` for the P03 reference baseline. The latter is not
a claim that future implementations must disable all storage optimization; it is
a bring-up choice so physical-capacity evidence cannot be confused with
unused-bit elimination.

The host/debug side remains one banked request interface rather than nine
independent host protocols. Host/debug accesses are rejected while the HLS core
is running, preventing same-address dual-port collisions from becoming an
accidental architectural behavior. The bridge remains transport-neutral: P03
uses VIO/JTAG for bring-up, while a later PS/AXI front end can reuse the same
bank semantics.

## Accepted routed evidence

The full fixed-depth one-core reference shell is accepted at the implementation
boundary with:

```text
PL clock target     100 MHz
WNS                 +1.148 ns
WHS                 +0.010 ns
CLB LUTs            3,545 / 117,120  (3.03%)
CLB registers       5,607 / 234,240  (2.39%)
Block RAM tiles     96.5 / 144       (67.01%)
URAM                0 / 64
DSPs                2 / 1,248        (0.16%)
external image      3,375,104 bits
memory shell        xpm_true_dual_port_v2
```

The standalone XPM fabric used 94.5 BRAM-tile equivalents. The extra two tiles
in the full shell correspond to the HLS core's local accumulator storage, so the
standalone and integrated resource counts reconcile cleanly.

## Remaining P03 evidence

The memory-shell challenge is solved, but P03 itself remains open until physical
directed conformance is demonstrated. The remaining gate is:

- generate a bitstream/debug-probe artifact from the accepted routed shell;
- program the physical K26;
- load the deterministic one-core corpus through the host/debug memory path;
- execute each directed timestep;
- read back state, normalized trace, packet records, status, and physical cycle
  counts;
- compare those values against the Python-generated expectations (T10); and
- preserve the resulting physical evidence before P03 is closed.

The failed BMG and VIO bring-up iterations remain in this log because they
document how the logical architecture was made robust against HLS/Vivado and
Hardware Manager interface conventions.
