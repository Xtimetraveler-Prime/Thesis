# P03 One-Core FPGA-v2 Hardware Boundary

## Status

Initial source-level hardware contract for **P03 — One FPGA-v2 logical core**.

This document is subordinate to `docs/LOIHI1_TARGET_SPEC.md`. It freezes the
first K26 implementation boundary needed to translate the verified P02 Python
core into synthesizable logic. Nothing here changes the source-backed Loihi-1
logical capacities or the P02 normalized architecture semantics.

## 1. Design strategy

P03 uses one serialized, transparent hardware engine for one logical core. The
engine implements the same architectural stages already exercised by the P02
model:

```text
input axon events
       ↓
axon descriptor lookup
       ↓
shared synapse-template traversal
       ↓
64-bit per-compartment accumulation
       ↓
24-bit saturating compartment update
       ↓
spike decision
       ↓
output-route traversal
       ↓
normalized egress packet records
```

The design intentionally optimizes for determinism and observability before
throughput. P04 adds inter-core packet transport and global barrier behavior;
P03 only has to emit/observe the normalized packet boundary for one core.

## 2. Logical capacity versus physical storage

The logical limits remain the v2 target limits:

| Logical resource | Limit |
|---|---:|
| compartments | 1,024/core |
| input axon IDs | 4,096/core |
| output route slots | 4,096/core |
| modeled synaptic fan-in storage | 128 KiB/core |

P02 currently accounts synaptic storage with the project model
`v2-simple-32bit-entry`. Therefore the maximum unique template-entry table
address space for P03 is conservatively bounded at `128 KiB / 4 = 32,768`
logical entries.

The **physical FPGA word width is a separate quantity**. The first HLS table uses
transparent 64-bit synapse words so target, effective weight, reserved delay,
and tag fields can be inspected directly. That may consume more than 128 KiB of
physical BRAM for a maximally filled logical core. Physical BRAM/URAM use must be
reported from synthesis and must not be confused with the modeled Loihi logical
synapse budget.

## 3. Arithmetic profile

The first hardware core uses the already validated FPGA-v1 compatible arithmetic
profile:

```text
state current          signed 24-bit, saturating
state voltage          signed 24-bit, saturating
refractory state       unsigned 16-bit
decay                   unsigned 13-bit, scale 4096
synaptic accumulator   signed 64-bit, no intermediate saturation
threshold comparison   strict greater-than
```

The P02 hardware exporter requires:

```python
ArithmeticConfig(state_bits=24, overflow=OverflowMode.SATURATE)
```

This is an explicit project hardware profile; it is not claimed to be every
native Loihi-1 internal state width.

## 4. Memory word layouts

### 4.1 Compartment state — 64 bits

```text
[23:0]   current, signed 24-bit
[47:24]  voltage, signed 24-bit
[63:48]  refractory_remaining, unsigned 16-bit
```

This intentionally retains the proven FPGA-v1 state packing.

### 4.2 Compartment configuration — 128 bits

```text
[12:0]    current_decay
[25:13]   voltage_decay
[49:26]   threshold, signed 24-bit
[73:50]   bias, signed 24-bit
[97:74]   reset_voltage, signed 24-bit
[113:98]  refractory_ticks
[127:114] reserved = 0
```

### 4.3 Input-axon descriptor — 64 bits

```text
[14:0]   synapse_start       (0..32767)
[30:15]  synapse_count
[40:31]  target_offset       (0..1023)
[41]     valid
[63:42]  reserved = 0
```

Multiple axon IDs may point to the same `synapse_start/count` pair with
different `target_offset` values. This is the P03 physical expression of P02
shared synapse templates; shared templates are not duplicated merely because
multiple axons bind to them.

### 4.4 Synapse entry — 64 bits

```text
[9:0]    template-relative target compartment
[33:10]  effective signed 24-bit weight
[39:34]  delay (reserved; executable P03 requires zero)
[47:40]  tag / auxiliary field
[63:48]  reserved = 0
```

P03 consumes the effective integer weight used by the P02 compatibility profile.
This does not claim native Loihi SRAM bit packing. Native/mixed weight formats
remain a later fidelity/mapping concern.

### 4.5 Output-route descriptor — 32 bits

```text
[11:0]   route_start
[24:12]  route_count
[25]     valid
[31:26]  reserved = 0
```

### 4.6 Output-route record — 32 bits

```text
[6:0]    destination logical core
[18:7]   destination axon ID
[31:19]  reserved = 0
```

### 4.7 Egress packet record — 64 bits

```text
[6:0]    destination logical core
[18:7]   destination axon ID
[28:19]  source compartment
[60:29]  target algorithmic timestep
[61]     valid
[63:62]  reserved = 0
```

Source core is implicit for the one-core engine. When normalized back to P02,
`source_core` is the configured logical core ID and `source_timestep` is
`target_timestep - 1`.

### 4.8 Per-compartment trace record — 256 bits

```text
[63:0]     state_before word
[127:64]   signed 64-bit synaptic accumulator presented to neuron update
[191:128]  state_after word
[192]      spike bit
[255:193]  reserved = 0
```

This creates an explicit differential boundary for P03 without requiring final
classification behavior to diagnose a mismatch.

## 5. One-tick HLS boundary

The first top-level component is `loihi_core_v2_tick`. One invocation processes
one algorithmic timestep for one logical core. Configuration/state/table
memories are explicit top-level memory ports; state is updated in place.

Inputs include:

- active compartment count;
- input-event count and event-axon list;
- active unique synapse-entry count;
- active output-route count;
- current algorithmic timestep;
- configuration/state/axon/synapse/route memories.

Outputs include:

- updated compartment state;
- per-compartment normalized trace records;
- normalized output packet records;
- spike count;
- packet count; and
- status/error flags.

The eventual P03 Vivado wrapper may load these memories through BRAM/debug/host
logic. The HLS compute boundary does not force a final host transport protocol.

## 6. Runtime integrity/status checks

The HLS engine shall reject or flag at least:

- active counts exceeding fixed capacities;
- an event referencing an invalid/unconfigured axon;
- an axon row extending beyond active synapse storage;
- a nonzero delay in the initial executable profile;
- a synapse expanding beyond the active compartment range;
- a route row extending beyond active route storage; and
- packet-buffer overflow.

These checks defend against corrupt hardware images. The Python mapper/exporter
still remains responsible for rejecting logically invalid deployments before
hardware execution.

## 7. P03 verification sequence

The source-level hardware gate is:

```text
P02 one-core Python configuration
        ↓
hardware_p03.py packed image
        ↓
Python-generated differential corpus
        ↓
HLS C simulation
        ↓
HLS synthesis + C/RTL co-simulation
        ↓
Vivado wrapper / K26 bitstream
        ↓
physical normalized trace comparison
```

The generated differential corpus intentionally exercises shared-template axon
bindings, excitatory/inhibitory contributions, refractory behavior, state
persistence, output-route expansion, and multi-tick execution.

## 8. Deferred from this boundary

P03 does not yet implement:

- inter-core router queues;
- global quiescence/barrier coordination;
- virtualization across logical cores;
- programmable nonzero synaptic delays;
- native Loihi compression bit packing; or
- online learning.

Those omissions follow the roadmap phase boundaries and do not weaken the P03
one-core differential target.
