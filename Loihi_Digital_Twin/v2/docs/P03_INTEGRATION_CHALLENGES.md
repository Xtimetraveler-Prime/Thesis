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

The replacement fixed-depth XPM fabric has now passed its synthesis-only
retention gate. Vivado reported **94.5 Block RAM Tile equivalents** for the nine
external banks (`93` RAMB36E2 plus `3` RAMB18E2), exceeding the conservative
90-tile acceptance floor. The `32768 x 64` synapse bank alone accounted for
`57` RAMB36E2 primitives. This result is consistent with the intended
3,375,104-bit external image and confirms that the XPM fabric resolves the BMG
depth-collapse problem before full HLS + shell place/route.

## Challenge / resolution history

| Challenge | Observation | Resolution / current status |
|---|---|---|
| Packaged HLS BRAM interface names | Vitis packaged array ports as `<argument>_PORTA`; the first Vivado helper queried the unsuffixed C argument name. | Fixed the packaged-interface lookup. |
| Input-event physical word width | Vivado 2025.2 Block Memory Generator rejected the first 16-bit native event-memory port in this K26 configuration. | Widened only the physical event word to 32 bits. The logical axon ID remains 12 bits in `[11:0]`; upper bits are reserved. |
| Grouped BRAM metadata mismatch | Directly connecting grouped HLS `bram` interfaces to manually configured BMG instances produced incompatible `MEM_SIZE` and `READ_LATENCY` interface metadata. | Replaced the grouped HLS `bram` protocol with discrete `ap_memory` ports. |
| Unsupported BMG controller-mode assumption | An attempted `Interface_Type=BRAM_Controller` configuration was rejected because the instantiated BMG exposed only the Native interface mode. | Abandoned controller-mode propagation and retained native memory signaling. |
| Full memories optimized from the routed baseline | The first successful `ap_memory`/native route used only one memory access path. Read-only configuration banks had no runtime writer and trace/packet banks had no runtime reader, allowing synthesis to remove storage that could not affect an observable result. | Added a host/debug access path and hardware arbitration so every bank is programmable/readable while the compute core is idle. |
| BMG depth collapse in IP Integrator | The retained true-dual-port BMG shell routed with 48 RAMB36E2 tiles. Validation logs then showed all nine banks at depth 2048, including the intended 32,768x64 synapse bank. | **Resolved at the memory-fabric level:** replaced BMG block-design instances with fixed-parameter `xpm_memory_tdpram` banks in RTL. The synthesis-only retention gate now reports 94.5 BRAM tiles for the complete external image. Full HLS + XPM routing remains to be verified. |
| Thin routed hold margin | The first successful shell closed hold with `+0.020 ns`; the retained 48-BRAM shell closed with `+0.013 ns`. | Not a redesign trigger; continue monitoring post-route hold and bus-skew reports. |

## Current memory-shell implementation

The current shell uses this invariant:

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
`MEMORY_OPTIMIZATION="false"` for this validation baseline. The latter is not a
claim that future implementations must disable all storage optimization; it is
a P03 bring-up choice so physical-capacity evidence cannot be confused with
unused-bit elimination.

The synthesis-only gate measured `94.5 / 144` K26 Block RAM Tile equivalents,
or about `65.6%` of available BRAM, for the external fabric alone. This is high
enough that the large synapse bank remains a strong future UltraRAM candidate,
but P03 intentionally keeps the all-BRAM shell as the first full-capacity
reference implementation. UltraRAM migration will be driven by full routed
timing/resource evidence rather than introduced before that baseline exists.

The host/debug side remains one banked request interface rather than nine
independent host protocols. Host/debug accesses are rejected while the HLS core
is running, preventing same-address dual-port collisions from becoming an
accidental architectural behavior. The bridge remains transport-neutral: P03
uses VIO/JTAG for bring-up, while a later PS/AXI front end can reuse the same
bank semantics.

## Remaining evidence before this challenge is considered fully solved

The memory-shell challenge is accepted at the synthesis level and now requires
full-system evidence:

- [x] a fast synthesis-only XPM fabric gate reports BRAM use consistent with the
  complete 3,375,104-bit external image rather than the 26/48-tile baselines;
- [x] the dominant synapse bank remains identifiable in synthesized hierarchy
  and consumes the expected majority of the external storage (`57` RAMB36E2);
- [ ] the complete HLS + XPM shell synthesizes, places, and routes on the K26;
- [ ] setup, hold, and bus-skew reports pass at the requested 100 MHz clock;
- [ ] the host/debug bridge can write and read every bank on physical hardware
  while the core is idle;
- [ ] access while the compute core is busy is rejected deterministically on
  physical hardware; and
- [ ] the physical differential corpus can load state/configuration and read
  back normalized trace/packet results through this retained memory path.

When the remaining checks pass, this file should be updated with the measured
full-shell resource cost and exact routed resolution rather than deleting the
failed approaches. The failed iterations are useful evidence of how the logical
architecture was made robust against HLS/Vivado interface conventions.
