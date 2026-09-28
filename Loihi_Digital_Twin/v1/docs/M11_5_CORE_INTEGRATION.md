# M11.5 FPGA Core Integration Plan

**Status:** In progress  
**Started:** 2026-08-24  
**Target:** `xck26-sfvc784-2LV-c`  
**Toolchain:** AMD Vitis/Vivado 2025.2

M11.5 turns the M11.4 packaged `neuron_step_v1` IP into the first finite,
multi-neuron FPGA computational core. The Python FPGA-v1 model and M10 remain
the behavioral contract; this document freezes only the additional physical
capacity, storage, scheduling, and integration choices required to realize that
contract on the K26.

These capacities and memory layouts are project-specific implementation choices.
They are not claims about undocumented Intel Loihi physical memory sizes or SRAM
organization.

## 1. Integration strategy

The first integrated implementation is deliberately serialized and observable:
correctness and traceability take priority over throughput optimization.

```text
M08 memory image + neuron config/state + events + routes
                         |
                         v
                M11.5 RTL controller
                         |
             +-----------+-----------+
             |                       |
             v                       v
      storage / queues        neuron_step_v1 IP
             |                       |
             +-----------+-----------+
                         |
                         v
              committed state / spikes /
              next recurrent-event queue
```

The verified HLS neuron transition remains an isolated IP block. A handwritten
RTL controller will own memory addressing, tick phase sequencing, capacity
faults, recurrent queue banking, and debug/trace-facing control. This keeps the
algorithmic controller explicit and avoids forcing memory/control behavior into
the HLS arithmetic block that already passed M11.3 RTL co-simulation.

For memory arrays, the intended RTL implementation uses AMD XPM memory macros
where practical. XPM keeps memory depth/width and block-vs-distributed mapping in
source-controlled RTL and avoids making the architecture depend on manually
configured Block Memory Generator GUI instances. Actual synthesized mapping is
still measured later; the bit counts below are capacity-only estimates.

## 2. Frozen finite capacity profile v1

Architectural neuron/axon/route IDs remain 16 bits as required by M10. The
physical arrays instantiated by the first K26 core are intentionally smaller:

| Resource | Frozen capacity |
|---|---:|
| Neurons | 256 |
| Axon rows | 1,024 |
| Static synapses | 4,096 |
| Shared weight formats | 16 |
| Recurrent routes | 4,096 |
| External events per tick | 4,096 |
| Recurrent events per tick | 4,096 |

The machine-readable source is
`src/neuromorphic_twin/fpga_core_capacity.py`, schema:

```text
neuromorphic-twin-fpga-core-capacity-v1
```

A static image or runtime event sequence that exceeds this physical profile is
outside the first M11.5 implementation domain even if its individual IDs still
fit the wider M10 16-bit architectural fields.

## 3. Why the 64-bit synaptic accumulator is now sufficient

M10 requires the exact mathematical synaptic sum to be preserved until the
single current-state width operation. M11.1-M11.4 used a signed 64-bit HLS
`synaptic_input` boundary without yet proving a finite physical event capacity.
M11.5 now closes that gap.

The M08 effective static-weight magnitude is bounded by:

```text
WEIGHT_LIMIT = 2^21 - 64 = 2,097,088
```

The worst possible contribution count under the frozen physical profile is a
pathological case where every external and recurrent event references one axon
whose row contains all 4,096 stored synapses and every synapse targets the same
neuron:

```text
max events/tick       = 4096 + 4096 = 8192
max row length        = 4096
max weight magnitude  = 2,097,088

max absolute sum
  = 8192 * 4096 * 2,097,088
  = 70,366,596,694,016
  < 2^46
```

Therefore a signed 64-bit tick-local accumulator is not merely convenient; it
provably preserves every mathematical synaptic sum possible inside the frozen
M11.5 capacity profile with very large margin. No accumulator saturation or
wrapping is allowed.

## 4. Neuron storage words

### 4.1 Dynamic state — 64 bits per neuron

The state word is exactly packed with no reserved bits:

```text
63                    48 47                    24 23                     0
+-----------------------+------------------------+------------------------+
| refractory_remaining  | voltage                | current                |
+-----------------------+------------------------+------------------------+
        16 bits                 24 bits                  24 bits
```

- `[23:0]`: signed 24-bit current.
- `[47:24]`: signed 24-bit voltage.
- `[63:48]`: unsigned 16-bit refractory state.

Python `pack_neuron_state_word()` / `unpack_neuron_state_word()` are the
software/testbench reference for this layout.

### 4.2 Configuration — 128 bits per neuron

M10 configuration consumes 114 used bits and is rounded to a 128-bit physical
word:

| Bits | Field |
|---|---|
| `[12:0]` | current decay, unsigned 13-bit |
| `[25:13]` | voltage decay, unsigned 13-bit |
| `[49:26]` | threshold, signed 24-bit |
| `[73:50]` | bias, signed 24-bit |
| `[97:74]` | reset voltage, signed 24-bit |
| `[113:98]` | refractory ticks, unsigned 16-bit |
| `[127:114]` | reserved, must be zero |

Python `pack_neuron_config_word()` / `unpack_neuron_config_word()` freeze this
layout. Nonzero reserved bits are rejected.

## 5. Existing M08 weight storage remains normative

M11.5 does not redefine the M08.5 static-weight image:

```text
weight_formats.mem     16-bit format entries
weight_synapses.mem    32-bit requested-mantissa/format/target records
weight_axon_rows.mem   32-bit CSR row pointers
```

The first physical core limits those memories to:

```text
formats  <= 16
synapses <= 4096
axon rows <= 1024
```

The hardware synapse path must reconstruct the same effective integer weight as
`encode_static_weight()` from requested mantissa plus referenced format. It may
not silently replace the M08 source representation with a different weight
contract.

## 6. Recurrent route storage

Recurrent routes use a second CSR organization chosen to preserve the M09/M10
ordering contract efficiently:

```text
route_rows[source_neuron] : 32-bit start/terminal offsets
route_targets[]            : 16-bit target axon IDs
```

For source neuron `n`, declared routes occupy:

```text
route_targets[route_rows[n] : route_rows[n + 1]]
```

The table is grouped by ascending source neuron and preserves declaration order
inside each source row. Since Phase D/E processes spike sources in ascending
neuron ID, traversing this storage directly reproduces the required routing
order.

Physical depths:

```text
route_rows:    257 x 32 bits
route_targets: 4096 x 16 bits
```

## 7. Runtime event storage

### External events

One 4,096-entry x 16-bit external-event buffer is filled before a tick begins.
The controller consumes entries in ascending buffer index, preserving host/test
sequence order and multiplicity.

### Recurrent events

Recurrent events use two 4,096-entry x 16-bit banks:

- current bank: events emitted by tick `t-1`, consumed during tick `t`;
- next bank: events generated by spikes during tick `t`.

Phase F swaps bank roles atomically. This makes same-tick recurrence impossible
by construction and avoids read/write aliasing while Phase A consumes the old
queue and Phase E builds the new queue.

## 8. Tick-local storage

### Synaptic accumulators

A signed 64-bit accumulator exists for each physical neuron:

```text
256 x 64 bits
```

The first controller explicitly clears all configured-neuron accumulators at the
start of Phase B. This costs cycles but is simple, deterministic, and not
architecturally visible.

### Spike flags

One bit per neuron stores the result of Phase C until routing completes:

```text
256 bits
```

The first implementation scans these flags in ascending neuron ID during Phase
D/E rather than attempting to generate recurrent events before all neuron state
updates have completed.

## 9. Initial controller schedule

The controller must be behaviorally equivalent to the six M10 phases even
though each phase spans many 100 MHz hardware cycles.

### RESET / CONFIGURED-IDLE

Before accepting a tick:

- static configuration counts must fit the frozen profile;
- row-pointer tables must terminate within their physical table capacities;
- state reset iterates configured neurons and writes current=0,
  voltage=reset_voltage, refractory=0;
- tick becomes zero;
- recurrent queue counts become zero;
- capacity-fault state is cleared.

### Phase A — latch input boundaries

Latch the external-event count and the current recurrent-bank count. The
external buffer is logically consumed first, then the current recurrent bank.

### Phase B — exact synaptic accumulation

1. Clear configured-neuron accumulators.
2. Iterate external events in sequence.
3. Iterate recurrent events in sequence.
4. For each event, read `weight_axon_rows[event]` and `[event+1]`.
5. Traverse every synapse in that CSR interval in stored order.
6. Reconstruct the effective M08 integer weight.
7. Read-modify-write the signed 64-bit accumulator for the target neuron.

The first implementation is intentionally serialized around memory read latency;
it does not require one synapse per cycle. A later optimization may pipeline or
cache accumulator accesses only if exact sums and deterministic behavior remain
unchanged.

### Phase C — update neurons

Iterate configured neuron IDs in ascending order. For each neuron:

1. read the 64-bit pre-tick state word;
2. read the 128-bit configuration word;
3. read its signed 64-bit accumulator;
4. drive the M11.4 `neuron_step_v1` IP inputs;
5. assert the HLS `ap_start` transaction;
6. wait for `ap_done` / valid outputs;
7. write next state to the same neuron's state slot;
8. record the spike flag.

Sequential writeback is safe because one neuron's transition never consumes
another neuron's state; every transition depends only on its own pre-tick state,
configuration, and already-completed Phase-B accumulator.

### Phase D/E — collect spikes and route

Scan neuron IDs from 0 upward. If a spike flag is set, traverse that source's
route CSR row in stored declaration order and append each 16-bit target axon to
the next recurrent bank.

### Phase F — commit

After all routes finish:

- swap recurrent-bank roles;
- publish the new recurrent count;
- increment the 32-bit tick;
- assert tick-done/idle status;
- expose committed state to debug/host reads.

No recurrent event generated during this sequence is visible to Phase B until
the next tick transaction.

## 10. Capacity-fault behavior

The first physical core does not silently truncate workload that exceeds its
finite memories. The controller will expose a sticky fault and refuse to report
a successful tick commit for conditions such as:

- external event count > 4,096;
- next recurrent queue would exceed 4,096 events;
- configured counts exceed the frozen profile;
- CSR terminal pointers exceed their table capacities;
- a synapse target is outside the configured neuron count;
- a route target is outside the physical axon capacity;
- a runtime event axon is outside the physical axon capacity.

M12 exact-conformance scenarios for this first core must stay inside the valid
physical profile. Fault behavior is an implementation guardrail, not a new
neuron-model semantic.

## 11. Capacity-only storage estimate

At the frozen maxima:

| Storage | Logical bits |
|---|---:|
| 256 x 64 neuron state | 16,384 |
| 256 x 128 neuron config | 32,768 |
| 256 x 64 accumulators | 16,384 |
| 16 x 16 weight formats | 256 |
| 4096 x 32 synapses | 131,072 |
| 1025 x 32 axon row pointers | 32,800 |
| 4096 x 16 route targets | 65,536 |
| 257 x 32 route row pointers | 8,224 |
| 4096 x 16 external events | 65,536 |
| 2 x 4096 x 16 recurrent events | 131,072 |
| 256 spike flags | 256 |
| **Total** | **500,288** |

Using 36,864 logical bits per BRAM36 gives a capacity-only lower bound of:

```text
ceil(500288 / 36864) = 14 BRAM36
```

The K26 synthesis report from M11.3 listed 288 BRAM18 resources, equivalent to
144 BRAM36 capacity units. The 14-block figure is therefore intentionally
conservative in total capacity, but actual synthesis can consume more than 14
blocks due to legal widths/depths, banking, dual-port requirements, replication,
placement, and timing.

## 12. Vivado integration approach

The normative project flow remains scripted. M11.5 will add source-controlled
Verilog RTL modules to the Vivado project and instantiate them in IP Integrator
as Module References where appropriate. This avoids packaging every small
controller/memory wrapper as a separate catalog IP while keeping the verified
HLS neuron transition as its existing packaged IP.

The expected top-level BD direction is:

```text
                         +-------------------------+
 host/test/config ------>| M11.5 core controller   |
                         | + memories / queues      |
                         +-----------+-------------+
                                     |
                             ap_ctrl + scalar data
                                     |
                                     v
                         +-------------------------+
                         | neuron_step_v1_0        |
                         | packaged HLS IP         |
                         +-------------------------+
```

GUI edits are not required to define this architecture. Opening the generated
Vivado project and inspecting the block diagram is useful as a visual check, but
any connection needed for reproducibility should be added to the Tcl/RTL source
rather than made only in the GUI.

## 13. M11.5 implementation order

M11.5 will proceed in smaller implementation gates:

1. **M11.5.1 — capacity and neuron-memory contract**
   - freeze the finite profile;
   - freeze 64-bit state / 128-bit config words;
   - add machine-readable Python pack/unpack and capacity tests.
2. **M11.5.2 — neuron state/config memories + HLS transaction sequencer**
   - add controller RTL;
   - sequence multiple neurons through `neuron_step_v1`;
   - prove reset and state writeback in simulation.
3. **M11.5.3 — M08 synapse traversal and exact accumulation**
   - instantiate weight-format/synapse/axon-row memories;
   - implement effective-weight reconstruction;
   - accumulate exact signed 64-bit sums.
4. **M11.5.4 — recurrent route CSR and double-buffered queue**
   - preserve ascending-source/declaration-order routing;
   - prove next-tick-only recurrence and capacity faults.
5. **M11.5.5 — integrated observability and Vivado system validation**
   - expose tick/status/state/spike/route observations;
   - run integrated RTL simulation against Python-generated directed traces;
   - validate the scripted Vivado block design before M11.6 implementation.

The current repository work starts M11.5.1. It is not evidence that later
controller, synapse, recurrence, or board integration stages are complete.
