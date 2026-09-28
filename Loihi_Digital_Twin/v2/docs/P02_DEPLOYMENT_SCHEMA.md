# P02 Deployment Document

## Purpose

P02 introduces a deterministic, versioned deployment document that is consumed
by the Python golden model and is intended to become the configuration boundary
used by later FPGA and mapper/compiler work.

The deployment format is **not** a claim that Loihi-1 stores configuration in
this JSON representation. It is a project-defined interchange format for the
source-backed logical architecture specified in `LOIHI1_TARGET_SPEC.md`.

## Version

The initial schema identifier is:

```text
v2.0-p02
```

Readers must reject an unknown schema version instead of silently interpreting
it as a compatible deployment.

## Determinism and fingerprint

A deployment fingerprint is the SHA-256 hash of the canonical logical payload:

```text
{
  "version": <schema version>,
  "cores": <core configuration list>
}
```

Core configurations are sorted by logical core ID before hashing. JSON keys are
sorted and compact separators are used for the hash input. Therefore equivalent
core ordering produces the same deployment fingerprint.

When a serialized document includes a `fingerprint`, the loader recomputes the
fingerprint and rejects the document if it does not match. This detects accidental
or manual edits that are not accompanied by a new deployment identity.

## Top-level fields

```text
version
fingerprint
cores[]
```

- `version` — deployment schema identifier.
- `fingerprint` — SHA-256 identity of the canonical logical payload.
- `cores` — non-empty list of logical core configurations.

## Per-core configuration

Each core document records:

```text
core_id
compartments[]
input_axons[]
synapse_templates[]
output_routes[]
arithmetic
capacity
synapse_cost_model
```

### `core_id`

Logical core identity. The P02 model enforces the one-chip logical ID space from
the target specification.

### `compartments[]`

Each compartment contains the v2.0 single-compartment execution profile:

```text
current_decay
voltage_decay
threshold
bias
reset_voltage
refractory_ticks
parent_compartment
root_compartment
```

Parent/root fields are reserved for later multi-compartment fidelity work.

### `input_axons[]`

Each destination-side axon binding contains:

```text
axon_id
template_id
target_offset
```

`template_id` selects a reusable synapse template. `target_offset` permits one
stored template to be reused at different destination-compartment offsets.

### `synapse_templates[]`

Each template contains:

```text
template_id
encoding_profile
entries[]
```

Each entry contains:

```text
target_compartment
weight
delay
tag
```

P02 executes delay zero only. Delay/tag fields are reserved so later fidelity
extensions do not require a new routing abstraction.

### `output_routes[]`

Each source-side route entry contains:

```text
source_compartment
routes[]
```

Each route contains:

```text
destination_core
destination_axon
```

This is the normalized logical fanout boundary used by the Python model and
intended for later FPGA normalization.

### `arithmetic`

The arithmetic profile records:

```text
state_bits
overflow
```

The initial compatibility profile normally uses unbounded Python integers with
`overflow = "none"`, matching the validated v1 subset unless a bounded arithmetic
profile is explicitly selected.

### `capacity`

The logical core capacity document contains:

```text
compartments
input_axons
output_routes
synapse_bytes
```

These values make capacity assumptions explicit and allow directed tests to use
smaller synthetic capacities while production mappings retain the source-backed
Loihi-like limits.

### `synapse_cost_model`

The P02 accounting policy records:

```text
name
bytes_per_template_header
bytes_per_template_entry
bytes_per_axon_binding
```

The initial `v2-simple-32bit-entry` policy is a PROJECT CHOICE and is not native
Loihi SRAM packing.

## Round-trip requirement

For a valid deployment `D`:

```text
D == load(serialize(D))
```

at the logical configuration boundary, including:

- identical deployment fingerprint;
- identical resource usage;
- identical normalized execution traces for the same external event schedule.

P02 tests enforce this requirement.

## Future P06 relationship

P06 may add graph partitioning, placement optimization, sharing/compression
selection, traffic estimates, and richer metadata. It should emit this same
logical core configuration boundary or a strictly versioned successor rather
than inventing a second incompatible Python/FPGA configuration format.
