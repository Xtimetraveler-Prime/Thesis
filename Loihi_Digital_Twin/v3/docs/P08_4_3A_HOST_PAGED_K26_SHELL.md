# P08.4.3a — Host-Paged K26 Shell Implementation Gate

**Status:** implementation candidate; physical-shell route verification pending  
**Phase:** P08.4 physical K26 conformance  
**Target:** AMD Kria K26 / `xck26-sfvc784-2LV-c`  
**Tool contract:** Vivado/Vitis 2025.2

## Purpose

P08.4.2 proved the exact trained/converted five-logical-core deployment in the software architectural model, including five-over-three context paging. The next physical proof cannot reuse the accepted P05 bitstream unchanged: P05's controller assumes that all configured logical destinations are among its three resident contexts and owns packet routing plus the global barrier internally.

That behavior is correct for P05/P06/P07, but it is not the P08.2 host-paged execution protocol for five logical cores.

P08.4.3a therefore creates the first routed physical shell that directly implements the accepted P08 paging boundary.

## Preserved hardware

The shell intentionally reuses the already accepted hardware pieces wherever possible:

```text
P03-compatible HLS compute engine:  unchanged
P05 full-context memory fabric:     unchanged
resident full-context slots:        3
physical HLS engines:               1
K26 PL clock request:                100 MHz
reset conditioner:                   unchanged P04 source-controlled conditioner
host/debug memory transport:         unchanged P05 banked memory interface
```

The memory banks remain:

```text
0  compartment configuration
1  compartment state
2  axon descriptors
3  synapse entries
4  route descriptors
5  route entries
6  input event bank 0
7  trace words
8  output packet words
9  input event bank 1
```

## Changed controller boundary

The P05 `p05_virtualized_controller` is replaced with the already P08.2-verified:

```text
rtl/p08_paged_dispatch_controller.v
```

This controller performs exactly one loaded logical-context dispatch. The host supplies:

- resident slot;
- P05-compatible metadata carrying the stable logical core ID;
- algorithmic timestep;
- event-read bank;
- the page contents through the banked host interface.

The controller supplies the HLS engine with the selected resident context and records completion/status/cycle observations.

## Host ownership

Cross-page behavior remains where P08.2 defined it:

```text
page victim selection:        host
backing context storage:       host
cross-page packet routing:     host
next-event insertion:          host
algorithmic global barrier:    host
resident HLS dispatch:         FPGA controller
neuron/synapse arithmetic:     FPGA HLS engine
```

The old P05 controller-side packet/event integration path is hard-disabled in the P08 shell. Packet and event banks are instead accessed through the same host/debug Port-B interface after each dispatch while compute is idle.

This is deliberate. It ensures the physical implementation cannot silently use P05's three-resident-context routing semantics while claiming P08 paging.

## VIO physical interface

`vio_p08` exposes commands for:

- dispatch start;
- reset request;
- resident slot;
- logical-core metadata;
- timestep;
- event-read bank;
- direct host bank read/write operations.

It exposes observations for:

- dispatch completion/busy/blocking;
- active physical slot and logical core ID;
- packet/status latches;
- dispatch/cycle counters;
- HLS ready/idle/done, spike count, packet count, and status;
- host transaction completion/readback;
- reset-release heartbeat;
- HLS/integration address guards.

P08.4.3b will use this interface to load and replace exact logical-context snapshots generated from the frozen P08.4.2 corpus.

## Gate

Run:

```bash
bash vivado/run_p08_impl.sh
```

The gate must:

1. package the unchanged P03-compatible HLS engine;
2. rerun the P08 paged-dispatch RTL simulation;
3. construct and validate the new P08 block design;
4. route it on the K26;
5. require nonnegative setup and hold slack;
6. retain three resident context slots and one physical engine;
7. remain within K26 UltraRAM capacity;
8. report host ownership of cross-page routing and the global barrier;
9. report no logical-capacity change; and
10. produce a `.bit` and matching `.ltx` pair with SHA-256 identities.

Expected high-level output:

```text
PASS: P08.4.3a routed timing wns_ns=... whs_ns=...
PASS: P08.4.3a physical topology logical_backing=5 resident_contexts=3 physical_engines=1 host_paged=true logical_capacity_changed=false
PASS: P08.4.3a routing ownership cross_page=host global_barrier=host on_fabric_cross_page_router=false
PASS: P08.4.3a resources uram=...
PASS: P08.4.3a artifacts bitstream_sha256=... probes_sha256=...
P08.4.3a host-paged K26 implementation gate completed successfully.
```

## Acceptance boundary

A P08.4.3a pass means the physical implementation needed for real host paging exists and closes timing. It does not by itself prove trained-MNIST execution on the board.

P08.4.3b will generate exact dispatch snapshots from official-test index 0 and physically exercise at least one true context replacement on the routed shell, comparing the K26's state/packets/readout against the already accepted P08.4.2 software expectations.
