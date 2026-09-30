# P08.2 Deterministic Logical-Context Paging

## Status

**Phase:** P08.2 FPGA-v2 adaptation  
**Implementation state:** software/RTL verification candidate  
**Accepted P08.1 topology:** `14 -> 20 -> 12 -> 10` all-convolutional reconstruction  
**ANN training:** still locked  
**Official MNIST test set:** still locked

P08.1 established that the accepted source-bounded MNIST reconstruction maps to
five P06 logical cores under the capacity-safe structural policy, while the
accepted K26 P05 shell retains only three full logical-context slots and one HLS
compute engine. P08.2 therefore extends virtualization with deterministic
logical-context paging instead of shrinking the network.

The central rule is:

```text
logical cores / architectural state      = 5 for the current P08 graph
host/backing logical-context images      = 5
simultaneously resident K26 context slots = 3
physical HLS compute engines             = 1
```

Those are intentionally different quantities.

---

## 1. Architectural boundary

P08 paging does not change P06 mapping, logical-core limits, packet fields,
neuron arithmetic, or algorithmic timestep semantics. It changes only where a
logical core's physical image is retained while that core is not being serviced.

The authoritative normalized architecture remains the Python `LogicalChip`:

- logical core ID is stable and independent of resident slot;
- each logical core owns independent compartment state;
- packets carry logical destination core and destination axon;
- current-timestep and next-timestep traffic remain separated;
- the global barrier advances only after every logical core has completed and all
  current-timestep egress has been delivered to next-timestep destinations.

The P08 backing store is an implementation layer below those semantics.

---

## 2. Why the P05 shell can be reused

The accepted P05 context memory fabric already provides three complete retained
logical-core slots. Its host/debug interface can access all retained banks while
compute is idle, including:

```text
bank 0  compartment configuration
bank 1  compartment state
bank 2  axon descriptors
bank 3  synapse entries
bank 4  route descriptors
bank 5  route entries
bank 6  input event bank 0
bank 7  trace words
bank 8  output packet words
bank 9  input event bank 1
```

This means P08 does not need five copies of the P05 UltraRAM context. A host
runtime can save a resident logical context into backing storage and load another
logical context into the same slot while the compute engine is idle.

P05 itself remains unchanged and valid for deployments with at most three
resident logical cores. P08 adds a new host-paged mode above it.

---

## 3. P08 backing image

`src/loihi_twin_v2/hardware_p08.py` introduces a hardware-image contract that
contains one complete P03-compatible packed image for every logical core.

Unlike the older P05/P06 FPGA exporters, it does **not** require all route
destinations to be on the currently resident page. Routes are validated against
the complete logical deployment.

For the accepted P08 structural graph the contract is:

```text
logical/backing cores = 5
resident slots        = 3
physical engines      = 1
paging required       = yes
logical capacity      = unchanged
```

Any three configured logical cores can be materialized into resident slot 0, 1,
or 2. Their packed route words keep logical destination IDs unchanged.

---

## 4. Deterministic page policy

`src/loihi_twin_v2/paging.py` defines the first P08 scheduling policy:

```text
deterministic-round-robin-context-paging-v1
```

Initial residency is the lowest logical IDs that fit. A request for an already
resident logical core is a page hit. A miss replaces the slot selected by a
round-robin victim pointer. The policy records:

- service index;
- logical core ID;
- physical context slot;
- page hit/miss;
- evicted logical core ID;
- residency before and after the algorithmic timestep.

Page policy is deliberately excluded from normalized neural traces. Different
legal page/service orders must produce the same normalized architectural result.

---

## 5. Host-paged physical execution protocol

The first P08 physical design uses host orchestration rather than embedding a
five-core backing store or a general page manager in programmable logic.

For each algorithmic timestep `T`:

1. Maintain a backing record for every logical core containing its static image,
   compartment state, and both event banks.
2. Choose a legal permutation of all configured logical core IDs.
3. For the next logical core, inspect the current resident-page mapping.
4. On a page miss, while compute is idle:
   - save the victim's updated state and required event-bank contents to its
     logical backing record;
   - capture trace/packet evidence before overwriting the slot when required;
   - load the requested logical core's config/state/axon/synapse/route/event
     banks into the selected physical slot;
   - load the P05-compatible metadata word with the requested logical ID and
     resource/event counts.
5. Dispatch that one resident slot through the unchanged P03-compatible HLS
   engine for timestep `T`.
6. After completion, read the HLS status and packet count. Read each packet word
   from the resident slot's packet bank.
7. Validate each output packet and route it by its **logical destination core
   ID**, even if that destination is not currently resident. Append the
   destination axon event to that logical core's backing **next-timestep** event
   image. Enforce the existing 4,096-event logical limit.
8. Save the serviced logical core's updated architectural state to backing
   storage before its slot is later reused.
9. Mark that logical core complete for timestep `T`.
10. Only after every logical core has completed and all generated packets have
    been committed to backing next-event images may the global barrier advance to
    timestep `T+1`. Event-bank ownership then flips coherently for every logical
    core.

The packet delivery policy is therefore:

```text
host-backing-by-logical-id-v1
```

Residency is never substituted for logical destination identity.

---

## 6. RTL dispatch primitive

`rtl/p08_paged_dispatch_controller.v` supplies the first hardware primitive for
this protocol. It deliberately performs **one loaded logical-core dispatch at a
time**.

It:

- accepts a resident slot and one P05-format metadata record;
- preserves the metadata logical core ID;
- latches the algorithmic timestep and selected event-read bank;
- starts the existing HLS core only when host memory access is idle;
- waits for HLS completion;
- latches packet count and core status for host inspection;
- exposes packet overflow, metadata, and HLS-status errors;
- records dispatch cycle count and completed-dispatch count.

It intentionally does **not**:

- assume the packet destination is resident;
- route packets into one of three local slots;
- flip the global event bank;
- decide the global barrier;
- choose page victims.

Those operations require knowledge of all five logical backing contexts and are
owned by the host-side P08 paging runtime. This avoids reintroducing the P05
three-resident-core assumption into P08 routing semantics.

---

## 7. Directed verification contract

### Python / architecture tests

The P08.2 tests require:

- legacy P05/P06 exporters to continue rejecting a five-resident-context image;
- the P08 exporter to accept the same five logical cores as five backing images
  plus three resident slots;
- the actual accepted MNIST structural deployment to retain the exact P06
  resource footprint established in P08.1;
- route words to keep logical destination identity across page changes;
- deterministic page hit/load/eviction accounting;
- architectural state to survive a real page eviction and later reload;
- normalized five-core execution to match the unpaged logical reference across
  different logical service orders, page schedules, and packet-drain orders.

For the accepted MNIST structural graph the frozen P06 usage remains:

| Core | Compartments | Input axons | Output routes | Synapse bytes | Shared params | Expanded conns |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 900 | 729 | 2,700 | 12,120 | 2,197 | 22,500 |
| 1 | 900 | 729 | 2,700 | 16,336 | 3,211 | 22,500 |
| 2 | 900 | 2,745 | 1,210 | 82,360 | 17,181 | 91,584 |
| 3 | 900 | 2,016 | 729 | 101,024 | 22,680 | 113,400 |
| 4 | 618 | 3,828 | 521 | 95,464 | 18,966 | 88,896 |

### RTL test

`rtl/tb/test_p08_paged_dispatch_controller.v` checks:

- logical core ID 4 executing through physical slot 2;
- metadata/timestep/event-bank preservation;
- packet/status/cycle accounting;
- host/compute mutual exclusion;
- invalid metadata rejection;
- packet overflow and nonzero HLS status reporting.

Run it with:

```bash
bash rtl/run_p08_paged_dispatch_controller_sim.sh
```

with Vivado 2025.2 tools on `PATH`.

---

## 8. P08.2 acceptance boundary

P08.2 can be accepted when:

1. `scripts/run_p08_2_preflight.sh` passes;
2. the P08 RTL dispatch simulation passes;
3. the five-core/three-resident/one-engine report is reproduced locally;
4. page/service-order invariance and explicit state-preservation tests pass;
5. no P05/P06/P07 regression used by the preflight fails.

This phase does not require final physical K26 MNIST inference. Physical
representative conformance belongs to P08.4 after a trained/converted deployment
exists. P08.2 only proves that the accepted graph can be represented and serviced
without shrinking it or changing logical semantics.

ANN training and the official MNIST test set remain locked until P08.2 is
accepted.
