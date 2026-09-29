# P03 Integration Challenges and Resolution Log

## Purpose

P03 is the first phase that carries the source-backed v2 architecture through
Python, HLS, packaged RTL, Vivado IP Integrator, and routed K26 implementation.
This file records integration problems encountered at those boundaries, why they
occurred, and how they were resolved.  These are kept separate from the Loihi-1
architecture contract so tool-specific accommodations are not mistaken for
architectural requirements.

## Baseline that remains accepted

Before the issues below were encountered, the P03 one-core implementation had
already passed the Python/HLS C differential corpus and C/RTL co-simulation.  A
later K26 route also completed successfully at the requested 100 MHz with
post-route WNS `+1.468 ns` and WHS `+0.020 ns`.  The compute/control logic was
small (`2,144` LUTs, `3,017` registers, `2` DSPs), so none of the integration
problems to date requires changing the P02/P03 neuron, axon, synapse, routing,
or timestep semantics.

The successful route reported only `26` BRAM tiles, however.  That is not enough
to contain the complete transparent P03 external-memory image (about 3.38 Mbit
before the HLS-local accumulator).  The expected external memory banks were also
absent from the hierarchical utilization grep.  That result proved that the
compute engine is routable, but not that one complete programmable logical-core
memory image survived synthesis.

## Challenge / resolution history

| Challenge | Observation | Resolution / current status |
|---|---|---|
| Packaged HLS BRAM interface names | Vitis packaged array ports as `<argument>_PORTA`; the first Vivado helper queried the unsuffixed C argument name. | Fixed the packaged-interface lookup. |
| Input-event physical word width | Vivado 2025.2 Block Memory Generator rejected the first 16-bit native event-memory port in this K26 configuration. | Widened only the physical event word to 32 bits. The logical axon ID remains 12 bits in `[11:0]`; upper bits are reserved. |
| Grouped BRAM metadata mismatch | Directly connecting grouped HLS `bram` interfaces to manually configured BMG instances produced incompatible `MEM_SIZE` and `READ_LATENCY` interface metadata. | Replaced the grouped HLS `bram` protocol with discrete `ap_memory` ports. |
| Unsupported BMG controller-mode assumption | An attempted `Interface_Type=BRAM_Controller` configuration was rejected because the instantiated BMG exposed only the Native interface mode. | Abandoned controller-mode propagation and retained native BMG ports. |
| Full memories optimized from the routed baseline | The first successful `ap_memory`/native route used only one memory access path. Read-only configuration banks had no runtime writer and trace/packet banks had no runtime reader, allowing synthesis to remove storage that could not affect an observable result. | Current redesign: true-dual-port BMG banks. Port A remains the HLS compute port; Port B is connected to a retained unified host/debug bridge. |
| Thin routed hold margin | The successful single-port baseline closed hold with WHS `+0.020 ns`. | Not a redesign trigger; continue monitoring post-route hold and add bus-skew reporting to the automated gate. |

## Current memory-shell redesign

The next routed shell uses the following invariant:

```text
                         Port A
P03 HLS compute core  <---------->  true-dual-port memory
                                      ^
                                      |
                                      | Port B
                                      |
                              p03_memory_host_bridge
                                      ^
                                      |
                                  VIO / JTAG
```

All nine HLS-visible banks use this pattern:

1. compartment configuration;
2. compartment state;
3. input axon table;
4. shared synapse table;
5. output-route descriptors;
6. output-route table;
7. input-event list;
8. normalized trace records; and
9. normalized packet records.

The host/debug side presents one banked request interface rather than nine
independent host protocols.  Its command consists of bank ID, word address,
read/write direction, and a 256-bit superset data word.  Narrow memories use the
least-significant bits and read data is zero-extended back to 256 bits.

Host/debug accesses are rejected while the HLS core is running.  This prevents
same-address dual-port collisions from becoming an accidental architectural
behavior.  The bridge is deliberately transport-neutral: P03 drives it from
VIO/JTAG for physical bring-up, while a later PS/AXI front end can replace the
VIO controls without changing memory-bank semantics.

## Required evidence before this challenge is considered solved

The redesigned shell is accepted only when all of the following are true:

- all nine true-dual-port banks validate in IP Integrator;
- all nine banks remain present after synthesis/route;
- routed BRAM-equivalent use is consistent with the complete physical memory
  image rather than the previous 26-tile optimized-away result;
- setup, hold, and bus-skew reports pass at the requested 100 MHz clock;
- the host/debug bridge can write and read every bank while the core is idle;
- access while the compute core is busy is rejected deterministically; and
- the physical differential corpus can load state/configuration and read back
  normalized trace/packet results through this retained memory path.

When those checks pass, this file should be updated with the measured resource
cost and the exact resolution rather than deleting the failed approaches.  The
failed iterations are useful evidence of how the logical architecture was made
robust against HLS/Vivado interface conventions.