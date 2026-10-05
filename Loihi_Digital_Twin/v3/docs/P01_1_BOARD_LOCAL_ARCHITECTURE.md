# P01.1 — Board-Local Ownership and Interface Architecture

**Status:** Verification candidate  
**Phase:** P01 — Board-local architecture, ownership, and v3 contract  
**Date drafted:** 2026-10-05

## 1. Purpose

P01.1 freezes the first v3 implementation partition before DDR paging or PS
runtime code is written.

The goal is to remove the external PC from the algorithmic execution loop while
preserving the accepted v2 logical architecture exactly.

This document does **not** change Loihi-like neuron, routing, packet, capacity,
or timestep semantics. It defines where the existing semantics are physically
implemented on the KV260/K26.

## 2. Inherited architectural invariants

The following v2 rules remain normative:

- logical core ID is architectural identity;
- resident context slot is a physical storage location;
- physical engine ID is independent of both;
- current-timestep and next-timestep input events remain double buffered;
- a packet generated while evaluating timestep `t` affects the destination at
  the subsequent architectural update;
- all logical cores must complete and current-timestep traffic must be committed
  before the global barrier advances;
- service order, page order, and physical-engine count must not change the
  normalized logical result;
- algorithmic timestep and physical clock cycles are separate quantities.

The existing `docs/LOIHI1_TARGET_SPEC.md` remains the logical architecture
contract. P01 introduces implementation ownership rules below that boundary.

## 3. Hardware facts used by this design

### 3.1 K26 DDR capacity

AMD DS987 revision 1.6 describes the K26 SOM as having 4 GB of 64-bit-wide DDR4
memory.

Reference:

```text
AMD Kria K26 SOM Data Sheet (DS987), rev. 1.6, 2026-03-25
https://docs.amd.com/r/en-US/ds987-k26-som/Functional-Overview-and-Block-Diagram
```

The accepted v2 full retained context is 3,506,176 bits = 438,272 bytes =
428 KiB. Therefore even a simple 512 KiB-aligned backing allocation for every
one of the 128 reserved logical core IDs would consume 64 MiB, far below the
available 4 GB DDR capacity.

This is a project sizing observation, not a claim about native Loihi storage.

### 3.2 PS/PL memory interfaces

AMD PG201/UG1085 document the Zynq UltraScale+ MPSoC interfaces relevant to v3:

- `M_AXI_HPM{0,1}_FPD`: PS masters into PL;
- `S_AXI_HP{0:3}_FPD`: PL masters into the PS/DDR path without CPU-cache
  coherency;
- `S_AXI_HPC{0,1}_FPD`: PL masters through the cache-coherent interconnect;
- ACP/ACE interfaces for stronger coherency use cases.

References:

```text
AMD PG201 — Zynq UltraScale+ MPSoC Processing System Product Guide
https://docs.amd.com/r/en-US/pg201-zynq-ultrascale-plus-processing-system/Slave-Interface

AMD UG1085 — Zynq UltraScale+ Device Technical Reference Manual
https://docs.amd.com/api/khub/documents/xzMsp_c5sG9J6A3u7NkJYQ/content
```

P01.1 chooses a non-coherent HP path for the initial DDR page data plane.
Coherent HPC/ACP/ACE access is not required for the first v3 implementation.

## 4. v3 execution partition

The accepted first implementation target is:

```text
External PC
    |
    | provisioning / debug / result retrieval only
    v
+-------------------------------------------------------------+
| KV260 / K26                                                 |
|                                                             |
|  PS / Cortex-A53 control plane                              |
|   - deployment/run control                                  |
|   - logical-core schedule                                   |
|   - page-victim policy                                      |
|   - cross-page packet routing bookkeeping                   |
|   - global barrier/timestep ownership                       |
|   - final result collection                                 |
|          |                         ^                         |
|          | AXI control/status      | completion/telemetry    |
|          v                         |                         |
|  PL -----------------------------------------------------   |
|   control/status wrapper                                   |
|        |                                                    |
|        +--> page mover <==== AXI bursts ====> PS DDR        |
|        |                                                    |
|        +--> 3 resident full URAM context slots              |
|        |          |                                         |
|        |          v                                         |
|        +--> 1 existing P03-compatible HLS core engine       |
|                   |                                         |
|                   +--> packet/trace/state images            |
|                                                             |
|  PS DDR                                                     |
|   - compiled deployment metadata                            |
|   - logical-core backing images                             |
|   - input/result buffers                                    |
|   - optional regression vectors/evidence                    |
+-------------------------------------------------------------+
```

## 5. Ownership table

| Resource / operation | External PC | PS/A53 | PL | DDR |
|---|---|---|---|---|
| build bitstream/software | owner | no | no | no |
| initial provisioning / launch | owner | target | target | target |
| deployment validation | optional reference | owner | status support | stores artifact |
| logical-core scheduling | no | **owner** | executes command | no |
| page-victim selection | no | **owner** | no | no |
| bulk page transfer | no | commands | **owner** | source/destination |
| resident context state | inspect only when stopped | control | **owner while resident** | backing copy |
| non-resident context state | no during run | metadata owner | transfer agent | **owner/storage** |
| logical packet destination interpretation | no | **owner initially** | exposes packet image | event backing |
| cross-page packet routing | no | **owner initially** | optional local assist | destination event image |
| HLS neuron/synapse arithmetic | no | no | **owner** | no |
| global barrier | no | **owner** | completion/status | no |
| global event-bank flip | no | **owner command** | applies selector | backing metadata |
| algorithmic timestep | no | **owner** | receives current value | optional run record |
| PL cycle counters | no | reads | **owner** | optional log |
| full-sample timing | no | **owner** | sub-counters | optional log |
| result retrieval | reads after run | produces | produces evidence | stores result |

"Owner" means implementation responsibility in v3; it is not a statement about
Loihi's proprietary physical implementation.

## 6. Why the PS owns the first v3 control plane

The first v3 design intentionally keeps scheduling, cross-page routing, and the
global barrier in PS software rather than moving all of them immediately into
RTL.

Reasons:

1. It is the closest board-local translation of the already accepted P08 host
   algorithm, reducing semantic migration risk.
2. It removes the PC from the timestep loop without requiring a new general
   on-fabric scheduler/router before DDR paging is proven.
3. It keeps the logical scheduling/barrier code inspectable and easy to compare
   against the Python paging reference.
4. It allows the PL to remain focused on deterministic high-throughput
   operations: HLS dispatch, resident memories, packet images, counters, and
   page movement.
5. It creates a clean later optimization boundary: selected routing/scheduling
   functions may move into PL after correctness and performance are measured.

The initial PS runtime target should be a Vitis-built Cortex-A53 application with
direct device access. A standalone/bare-metal build is preferred for first
bring-up because it gives deterministic ownership of caches, timers, and AXI
control. A Linux-hosted runtime may be added later without changing the
architectural contract.

## 7. PS-to-PL control plane

The PS must control the v3 PL shell through a memory-mapped register interface,
not JTAG transactions from the PC.

Initial intended path:

```text
Cortex-A53
  -> PS M_AXI_HPM0_FPD
  -> AXI interconnect / AXI-Lite peripheral
  -> v3 control/status block
```

Required control/status classes:

- shell reset / initialization;
- deployment/run identity;
- logical core ID;
- resident context slot;
- timestep;
- event-read bank;
- metadata/resource counts;
- dispatch start;
- page-in/page-out command;
- DDR source/destination address;
- transfer byte count / section mask;
- command busy/done/error;
- dispatch busy/done/error;
- packet count;
- core status;
- dispatch PL cycles;
- page-transfer PL cycles;
- sticky fault/status registers.

Exact register addresses belong to P01.2.

## 8. DDR page data plane

### 8.1 Selected first path

The first implementation should use a PL master issuing burst accesses to DDR
through one `S_AXI_HP*_FPD` port.

Conceptually:

```text
DDR backing image
   ^
   | AXI4 bursts
   v
PL context page mover
   ^
   | internal URAM bank read/write
   v
resident context slot
```

The PS commands transfers but does not copy every context word itself.

This makes page transfer bandwidth/latency independently measurable and keeps
the data path available if the later PS runtime changes.

### 8.2 Why non-coherent first

The backing region is treated as explicitly owned memory.

Initial ownership rule:

1. PS creates/loads the backing image.
2. PS performs the required cache clean/flush before handing the region to PL.
3. During autonomous inference, PL/DDR backing-store state is not concurrently
   cached and modified by the PS.
4. When the PS needs to inspect memory modified by PL, it performs the required
   invalidate/ownership handoff first.

This avoids hidden cache-coherency behavior in the acceptance boundary.

P01.2 must freeze the exact cache-maintenance API and DDR reservation method for
the selected PS software environment.

## 9. Context sizing consequence

The inherited full v2 context contains:

| Bank | Bytes |
|---|---:|
| configuration | 16,384 |
| compartment state | 8,192 |
| input axons | 32,768 |
| synapses | 262,144 |
| route descriptors | 4,096 |
| output routes | 16,384 |
| input events A | 16,384 |
| input events B | 16,384 |
| traces | 32,768 |
| packets | 32,768 |
| **Total** | **438,272 bytes (428 KiB)** |

For P01.2, the preferred starting ABI is a fixed **512 KiB DDR stride per
logical core ID**. That yields simple address arithmetic and leaves 84 KiB per
slot for metadata/versioning/alignment/future growth.

With 128 architectural logical IDs:

```text
128 * 512 KiB = 64 MiB
```

This is only a proposed ABI until P01.2 is reviewed and accepted.

## 10. Packet routing boundary

P01.1 keeps cross-page packet interpretation in PS software for the first board-
local runtime.

After each logical-core dispatch:

1. PL reports packet count and retains packet words.
2. PS drains/reads the packet image.
3. PS validates packet fields.
4. PS resolves the logical destination core.
5. If the destination is resident, the event may be appended through a PL
   command path.
6. If the destination is non-resident, the PS appends it to that logical core's
   DDR-backed **NEXT** event image.
7. The source logical core is marked complete only after all of its packet
   traffic is committed.

A later optimization may implement a PL packet router that writes directly to
DDR/resident next-event buffers. Such an optimization must preserve normalized
results and is not required for initial P03 closure.

## 11. Global barrier and timestep ownership

The PS owns the v3 global logical barrier.

For timestep `t`, it must not advance until:

- every configured logical core has been dispatched exactly as required;
- each dispatch packet image has been fully drained/committed;
- no pending routing work remains;
- all next-event counts/backing images are finalized.

Only then may the PS:

- increment the algorithmic timestep;
- swap CURRENT/NEXT ownership globally;
- clear/reinitialize next-event counts as required;
- begin servicing timestep `t+1`.

The PL may expose counters/flags to make these conditions observable, but an idle
HLS engine alone is never sufficient evidence of barrier completion.

## 12. Runtime state machine

The first v3 board-local runtime is defined at this level:

```text
RESET
  -> LOAD_DEPLOYMENT
  -> INITIALIZE_BACKING
  -> INITIALIZE_RESIDENT_SET
  -> LOAD_INPUT
  -> TIMESTEP_BEGIN
       -> SELECT_LOGICAL_CORE
       -> ENSURE_RESIDENT
            -> page hit: continue
            -> page miss:
                 SAVE_VICTIM
                 LOAD_REQUESTED
       -> DISPATCH_CORE
       -> DRAIN_AND_ROUTE_PACKETS
       -> SAVE_DIRTY_STATE_IF_REQUIRED
       -> MARK_LOGICAL_CORE_COMPLETE
       -> next logical core
  -> BARRIER_CHECK
       -> not quiescent: service remaining work
       -> quiescent:
            SWAP_EVENT_BANKS
            ADVANCE_TIMESTEP
  -> next timestep or FINALIZE
  -> WRITE_RESULT
  -> DONE
```

P01.3 will freeze exact state/error transitions and recovery behavior.

## 13. Timing/measurement boundary

The design must expose enough counters/timestamps to later separate:

- page-in latency;
- page-out latency;
- HLS dispatch cycles;
- packet-drain/routing time;
- barrier overhead;
- complete timestep latency;
- complete inference latency.

PL operations should expose cycle counts at the PL clock. The PS runtime should
use a PS hardware timer for board-local wall-clock boundaries. The external PC
must not define the inference start/stop timing boundary used for final v3
latency claims.

## 14. Failure model

At minimum, the board-local shell/runtime must fail closed on:

- invalid logical core ID;
- invalid resident slot;
- context ABI/version mismatch;
- out-of-range DDR backing address;
- page-transfer length/alignment error;
- resource-count overflow;
- HLS status error;
- packet format error;
- packet/event capacity overflow;
- page command while compute owns a slot;
- dispatch command while page transfer owns a slot;
- barrier attempted with incomplete logical work.

Errors must be sticky and observable until explicitly cleared/reset.

## 15. Effect on the Loihi target specification

**P01.1 decision:** no existing logical Loihi-1 semantic rule needs to change.

The inherited `LOIHI1_TARGET_SPEC.md` remains normative for logical behavior.
However, v3 does need a small implementation addendum so later documents do not
confuse:

- source-backed Loihi behavior;
- inherited project architectural choices;
- new v3 board-local implementation choices.

That addendum should be created in P01.3 after the DDR ABI and runtime state
machine are frozen.

## 16. P01.1 acceptance criteria

P01.1 may be accepted when independent review agrees that:

1. the PC is absent from all algorithmic timestep operations;
2. PS, PL, DDR, and external-host ownership is unambiguous;
3. the selected interface directions are physically supported by the K26 MPSoC;
4. the first DDR data path does not require coherent CPU-cache behavior;
5. current/next event separation and global barrier semantics are preserved;
6. the design does not change accepted v2 logical Loihi claims;
7. later P01 work has clear boundaries for the DDR ABI/cache contract and exact
   runtime state machine.

No RTL or PS runtime implementation is claimed by P01.1.
