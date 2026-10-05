# P06 Deterministic Mapper / Compiler

## Purpose

P06 converts a machine-readable network graph into the same logical-core
configuration boundary already consumed by the Python golden model and the FPGA
hardware-image tooling. The compiler does **not** introduce a second hardware-
specific mapping format.

The core rule is:

```text
network.json
    -> deterministic P06 compiler
    -> compiled_deployment.json
       -> Python LogicalChip
       -> P05/P06 full-context FPGA image
```

The compiled deployment therefore becomes the shared configuration artifact for
later mapped-network validation.

## P06.1 source graph contract

The source network schema is `p06-network-v1`.

A network contains:

- neuron populations;
- optional external input populations;
- neuron-to-neuron projections; and
- external-input-to-neuron projections.

Each neuron population has:

```text
name
size
compartment
```

The initial compiler uses one `CompartmentConfig` per population. Individual
neurons inside a population therefore share the same compartment parameters.
This is a project compiler restriction, not a Loihi hardware claim.

Each projection contains explicit weighted sparse connections:

```text
source_index
destination_index
weight
delay
```

P06 currently accepts delay zero only because the v2 execution model currently
executes delay zero only. Unsupported delays are rejected rather than silently
changed.

Population names and projection names must be unique. Source/destination indices
are checked against population bounds, and duplicate logical edges are rejected
explicitly.

## Deterministic source fingerprint

`NetworkSpec.fingerprint` is a SHA-256 hash of the canonical source graph.
Canonicalization sorts:

- neuron populations by name;
- external input populations by name;
- projections by name; and
- connections by `(source_index, destination_index, weight, delay)`.

Equivalent tuple ordering therefore does not change the source fingerprint or
the resulting placement.

## P06.2 placement policy

The first P06 placement algorithm is intentionally simple and inspectable:

1. sort populations by name;
2. walk neurons in ascending index order;
3. fill logical core 0 up to the configured packing target;
4. continue to logical core 1, core 2, and so on; and
5. split populations across logical cores when required.

The default packing target is the architectural maximum of 1,024 compartments
per logical core. `MappingOptions.compartments_per_core` may be lowered for
validation or deliberate partitioning, but lowering the packing target does not
change `CoreCapacity` and therefore does not redefine the logical Loihi limit.

The current policy is deterministic first-fit placement, not an optimization
claim. More sophisticated placement heuristics can later replace it behind the
same deployment boundary if they remain deterministic and resource-valid.

## Placement records

Every mapped neuron receives one explicit `PlacementRecord`:

```text
population
neuron_index
core_id
compartment_id
```

Physical FPGA engine or P05 context-slot identity does not appear in placement.
That separation preserves the P05 virtualization boundary.

## Axon and synapse allocation

For each source neuron and each destination logical core, all of that source's
connections into the destination core are grouped into one destination axon.

Example:

```text
source neuron A -> destination core 2 compartments 10, 11, 12
```

becomes one input axon on logical core 2 whose synapse template expands to three
entries.

The same rule is used for one external input index targeting one destination
logical core.

This means one source spike needs at most one packet per destination core for a
given source group, while destination-side axon expansion represents the fanout
inside that core.

## Deterministic connection sharing

P06 implements one explicit project-defined sharing rule.

For a source-to-destination-core group, let the destination compartment IDs be:

```text
b + d0, b + d1, ..., b + dn
```

The compiler stores:

- `target_offset = b` in the input-axon binding; and
- one normalized synapse template containing `(d_i, weight_i)` entries.

Two source groups reuse the same template when their sorted relative target
pattern and weights are identical, even if their absolute target offsets differ.

Example:

```text
source 0 -> compartments 20, 21 with weights 3, 4
source 1 -> compartments 40, 41 with weights 3, 4
```

stores one two-entry template and two input-axon bindings with target offsets 20
and 40.

This is a **project-defined mapping optimization** expressed through the v2
`SynapseTemplate` abstraction. It is not a claim that Loihi-1 uses this exact
compiler or physical SRAM encoding.

## Output-route allocation

For neuron-generated traffic, every allocated destination axon creates an
`OutputRoute` from the source neuron's mapped logical core/compartment to the
destination logical core/axon.

Routes are sorted by destination core and destination axon before deployment
serialization. Multiple routes from one source compartment are stored in one
`OutputRouteEntry`.

Local logical-core routes remain explicit routes. They are not converted into a
special same-core shortcut because the architectural packet semantics still
apply and the event targets the next algorithmic timestep.

## External ingress mapping

External input populations do not consume logical compartments. Instead the
compiler emits explicit `IngressRoute` records:

```text
input_population
input_index
destination_core
destination_axon
```

`CompiledDeployment.external_packets(...)` converts active external indices into
normalized `SpikePacket` objects using those records. External packets therefore
use the exact destination axons allocated by the compiler rather than a separate
manually maintained input map.

## Hard resource enforcement

The compiler eventually constructs ordinary `LogicalCoreConfig` objects. This
means the same architectural capacity checks used everywhere else remain the
final authority for:

- compartments;
- input axons;
- output routes; and
- project-modeled synapse bytes.

A mapper overflow is reported as `MappingError(code="core_resource_capacity")`
with:

```text
core_id
resource
used
limit
```

The mapper also rejects a graph that would require more logical cores than the
configured logical-chip policy.

Physical FPGA memory availability is not used to relax any logical resource
limit.

## Compiled deployment schema

The P06 compiled deployment schema is:

```text
v2.1-p06
```

It contains:

```text
schema
compiler_version
source_fingerprint
fingerprint
logical_deployment
placement[]
ingress_routes[]
report
```

`logical_deployment` is the already validated P02 `Deployment` document and its
logical core configurations. P06 therefore extends rather than replaces the
existing configuration boundary.

The P06 fingerprint covers the compiler version, source fingerprint, complete
logical deployment, placement records, and ingress routes. The derived report is
not part of the fingerprint because it can be recomputed exactly from the
canonical mapping.

Readers reject unknown schema/compiler versions and fingerprint mismatches.

## Mapping report

`CompiledDeployment.report()` separates logical mapping information from FPGA
implementation information. It includes:

- logical core count;
- neuron placement count;
- external ingress route count;
- per-core logical usage;
- per-core logical headroom;
- local/remote static output-route counts;
- total expanded connections;
- total stored shared synapse parameters; and
- expanded-connections-per-stored-parameter sharing ratio.

`static_route_estimate` is a topology count, not measured runtime packet traffic.
Actual traffic still depends on network activity.

## Shared Python / FPGA artifact

The Python path consumes a compiled artifact with:

```python
compiled = CompiledDeployment.read_json(path)
chip = compiled.build_chip()
```

The current FPGA path consumes that same object with:

```python
fpga = export_compiled_fpga_image(compiled)
```

The FPGA export then uses the accepted P05 full-context hardware packer. No
logical core is regenerated from an independent hardware-only placement.

For the currently accepted K26 shell, FPGA export supports at most three
simultaneously retained compiled logical cores because P05 physically retains
three full contexts. A larger valid logical deployment is rejected by the
current FPGA exporter rather than truncated or remapped silently.

`examples/generate_p06_fpga_load_vectors.py` converts the serialized compiled
artifact into deterministic Tcl host-load records. Those records carry the same
source and compiled-deployment fingerprints.

## Command-line flow

A source graph can be compiled with:

```text
python scripts/compile_p06.py network.json \
    --output deployment.json \
    --report report.json \
    --fpga-report fpga_report.json
```

The packing target can be changed without changing logical capacity:

```text
--compartments-per-core N
```

The resulting deployment can be converted to FPGA host-load vectors with:

```text
python examples/generate_p06_fpga_load_vectors.py \
    deployment.json \
    --output fpga_load_vectors.tcl
```

## Validation strategy

P06 source-level regressions cover:

- source graph JSON/fingerprint round trip;
- compiled deployment JSON/fingerprint round trip;
- deterministic output under equivalent source ordering changes;
- population splitting across logical cores;
- relative-fanout template sharing;
- external ingress allocation;
- execution of mapped connectivity in the Python golden model;
- explicit resource-capacity failure diagnostics;
- export of the same deployment artifact into the P05 full-context FPGA image;
- rejection of compiled deployments larger than the current resident FPGA
  context count; and
- end-to-end CLI generation of source, deployment, report, FPGA report, and Tcl
  load vectors with one preserved deployment fingerprint.

## Scope boundary

P06 does not yet claim an optimal placer, native Loihi compiler equivalence, or
native Loihi synapse compression. Its purpose is to make mapping deterministic,
resource-valid, inspectable, versioned, and shared by both execution paths.

That is the required foundation for P07, where a deeper network must be mapped
through this compiler rather than manually configured.
