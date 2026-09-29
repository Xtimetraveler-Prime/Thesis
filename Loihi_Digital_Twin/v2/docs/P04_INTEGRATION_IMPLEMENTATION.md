# P04 Two-Endpoint Integration Implementation

## Status

Source implementation prepared on `agent/p04-multicore-routing-v2`.  P04.1 and
P04.2 are verified.  The integrated P04.3/P04.4/P04.5 flow described here is
pending local Vivado/Vitis and physical-K26 verification.

This document is subordinate to `docs/LOIHI1_TARGET_SPEC.md` and complements
`docs/P04_MULTICORE_ARCHITECTURE.md`.

## 1. Why the P04 hardware fixture is resource-scaled

The accepted P03 reference shell uses `96.5 / 144` K26 BRAM tiles for one
full-capacity physical memory image.  Two literal copies would require about
`193` BRAM tiles before routing queues or barrier logic.  P04 therefore does
**not** duplicate the P03 full-capacity memory shell and does **not** reduce the
logical Loihi resource contract.

Instead, P04 instantiates two copies of the unchanged P03 HLS compute engine and
gives each one a guarded physical validation memory image sized for the directed
P04 corpus:

| Physical fixture resource | Per endpoint retained depth |
|---|---:|
| compartment config/state/route descriptors/trace | 16 |
| input axon descriptors | 64 |
| synapse entries | 256 |
| output routes | 64 |
| input events | 64 |
| output packet records | 64 |

These values are **physical validation depths only**.  Logical validation still
uses the full v2 architectural limits of 1,024 compartments, 4,096 input axon
IDs, 4,096 output route slots, and the modeled 128 KiB synaptic fan-in budget
per core.

`src/loihi_twin_v2/hardware_p04.py` intentionally performs a second,
physical-fixture fit check after normal logical validation.  Its errors state
that the directed physical allocation was exceeded rather than claiming a
logical capacity error.

The FPGA memory wrapper preserves the original HLS logical address widths.  A
high address outside the retained physical allocation is disabled and flagged;
it is never truncated/aliased into low memory.  The physical board harness also
checks this property by issuing an access exactly one word beyond the fixture's
compartment allocation and requiring rejection.

## 2. Reusing the accepted P03 compute engine

P04 does not fork the neuron/synapse datapath.  The same packaged
`loihi_core_v2_tick` HLS IP is instantiated twice.  Therefore P04 inherits the
accepted P03:

- compartment arithmetic;
- axon descriptor format;
- synapse traversal and accumulation;
- route descriptor/record formats;
- packet packing;
- per-compartment trace word; and
- runtime status checks.

The new logic is outside the compute core: packet retention/drain, routing,
next-event construction, completion/barrier control, and two-endpoint host/debug
selection.

## 3. Why packet output is retained before routing

The P03 HLS component writes packets into `packet_words` through an `ap_memory`
write port.  That write interface has no downstream `ready` signal.  Connecting
those writes directly to a backpressured packet router would create a loss risk:
the router could stall while HLS continues producing packet-memory writes.

P04 therefore uses a deterministic two-stage boundary:

```text
P03 HLS core
    |
    | writes complete packet_words image
    v
resource-scaled packet memory
    |
    | read after ap_done
    v
p04_packet_memory_streamer
    |
    | ready/valid with backpressure
    v
p04_packet_router_barrier
```

A core is not reported complete to the global barrier merely when its HLS
`ap_done` asserts.  The integration controller reports that endpoint complete
only after `ap_done` **and** after its packet-memory streamer has transferred all
retained packet records into the routing boundary.  This prevents the barrier
from advancing while architectural packets still exist only as unread memory
records.

## 4. Next-timestep event construction

The router produces destination-specific packet streams.  For every accepted
packet, the integration controller writes the packet's destination axon ID into
the destination endpoint's `input_events` Port-B image and increments that
endpoint's next-event count.

The destination event memory is written during timestep `t` only after the
corresponding core computation has completed.  It therefore becomes the event
list consumed when both endpoints start timestep `t+1`.  No additional
algorithmic timestep is inserted by the physical packet-memory drain.

The global advance condition remains:

```text
both endpoints have completed HLS execution and egress drain
AND both producer capture slots are empty
AND both destination queues are empty
AND no packet is being accepted on the current cycle
```

Only then does the controller:

- increment `current_timestep`;
- replace each current event count with its constructed next-event count; and
- report a completed physical tick.

## 5. Differential corpus

`examples/generate_p04_hls_vectors.py` derives all HLS expectations from the
Python `LogicalChip` model.  The C-simulation harness runs two scenarios:

### Feed-forward

Core 0 receives an external event at timestep 0, spikes, and routes a packet to
Core 1.  Core 1 consumes the routed axon and spikes at timestep 1.

### Recurrent multicast

Both cores receive an external event at timestep 0 and fire simultaneously.
Each firing core emits:

- one **local** packet back to itself; and
- one **remote** packet to the other core.

The local and remote axons each contribute weight 3 to the same destination
compartment.  The resulting fan-in sum recreates the threshold-crossing input,
so both cores fire again on the subsequent timestep.  This compact scenario
therefore exercises:

- simultaneous producers;
- local routing;
- remote routing;
- multicast/fanout;
- fan-in from independent packet sources;
- bidirectional recurrence; and
- multiple architectural timesteps.

The HLS differential harness invokes the unchanged core function twice per tick,
routes the **actual HLS output packet words** into the next tick's event lists,
and compares both state/trace/packet boundaries to Python.  It runs every
scenario under both forward and reversed legal source/packet service order.
Packet and input-event comparisons are multisets because same-timestep packet
sequence is not part of the normalized architecture contract.

## 6. RTL integration layers

The new P04 RTL is intentionally separated by responsibility:

- `p04_packet_router_barrier.v` — verified packet queues, arbitration,
  destination delivery, traffic counts, and quiescence barrier;
- `p04_packet_memory_streamer.v` — converts one completed HLS packet-memory image
  to a backpressured stream;
- `p04_two_core_controller.v` — starts both endpoints, coordinates egress drain,
  writes next-event memories, and advances algorithmic time;
- `p04_endpoint_memory_fabric.v` — guarded resource-scaled true-dual-port XPM
  banks with unchanged HLS logical address widths; and
- `p04_host_mux.v` — selects one endpoint for the shared VIO/JTAG host path and
  provides a free-running heartbeat.

## 7. Verification/build sequence

### Source-level P04 preflight

```bash
bash scripts/run_p04_preflight.sh
```

This runs:

1. the full Python test suite;
2. P04 vector-generation smoke checks;
3. the Python/HLS two-core C differential;
4. the standalone router/barrier XSim gate; and
5. the integrated controller XSim gate.

### Integrated synthesis gate

```bash
bash vivado/run_p04_integration_synth.sh
```

The synthesis gate packages the accepted P03 HLS engine, instantiates it twice,
connects both guarded endpoint fabrics and the P04 controller/router, and emits
post-synthesis timing/utilization/hierarchical reports plus a checkpoint.

### Routed K26 gate

```bash
bash vivado/run_p04_impl.sh
```

The routed flow emits timing, utilization, memory-primitive, DRC, methodology,
bus-skew, checkpoint, `.bit`, `.ltx`, and a compact metrics file.  The metrics
file explicitly records the physical fixture depths and
`logical_capacity_changed=0`.

### Physical conformance

```bash
bash hardware/run_p04_physical.sh
```

The physical harness:

- verifies clock/reset with a heartbeat;
- verifies all nine physical banks on both endpoints;
- proves one-past-allocation addresses are rejected rather than aliased;
- reloads each scenario from Python-generated packed images;
- runs each scenario under both router service priorities;
- compares both cores' state, trace, spike count, packet count, and packet words;
- compares routed next-event memories as unordered axon multisets;
- compares local/remote packet counts and timestep/event-count advancement; and
- requires every controller/router/HLS/memory error flag to remain clear.

## 8. Phase boundary with P05

P04 demonstrates two concurrently instantiated compute endpoints and the
correct multicore architectural transport/barrier semantics.  The resource-
scaled test memories are an explicit validation-fixture limitation.

P05 remains responsible for making the physical storage/engine count transparent
with respect to independently retained **full logical core contexts**.  P05 must
demonstrate virtualization invariance rather than simply increasing the P04
fixture depths.
