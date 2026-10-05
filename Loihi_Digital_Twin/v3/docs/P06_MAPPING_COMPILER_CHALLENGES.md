# P06 Mapping/Compiler Challenges and Closure Notes

## Purpose

This document records the main implementation decisions, risks, and validation
lessons encountered while converting the manually configured v2 architecture
into a deterministic mapper/compiler. It complements
`P06_MAPPING_COMPILER.md`, which describes the compiler contract itself.

P06 did not introduce a new FPGA datapath. Its central requirement was that a
single compiled deployment artifact drive both the Python architecture and the
already accepted P05 virtualized FPGA shell without hand-authored hardware
configuration.

## 1. Avoiding a second configuration format

The project already had a validated logical `Deployment` representation from
P02 and a full-context hardware packing boundary from P05. The main P06 design
risk was creating a mapper-specific or FPGA-specific configuration format that
would duplicate those existing contracts.

P06 therefore adds a higher-level network/compiler layer around the existing
logical deployment instead of replacing it. The compiler emits a versioned
`CompiledDeployment` containing:

- the validated logical-core `Deployment`;
- deterministic population-to-core/compartment placement records;
- external ingress routes;
- compiler/source fingerprints;
- mapping/resource reports; and
- metadata needed to reproduce the mapping.

Python execution uses the contained logical deployment directly. FPGA export
uses the same compiled object and passes its logical cores through the accepted
P05 full-context hardware image packer. There is no separately maintained FPGA
mapping.

## 2. Deterministic placement

P06 must generate the same mapping for the same network and mapping options,
regardless of incidental Python container ordering or input document ordering.
The compiler therefore canonicalizes populations, projections, and connection
records before allocating resources.

Population compartments are assigned deterministically to logical cores subject
to the configured per-core placement target and the architectural core limits.
The resulting placement is explicitly serialized so the mapping is inspectable
rather than implicit in compiler execution order.

The network source document and compiled deployment both carry SHA-256
fingerprints. Round-trip loading recomputes the fingerprints and rejects
inconsistent/tampered documents.

## 3. Destination-axon allocation and connection sharing

The v2 architecture uses destination-side input axons that select reusable
synapse templates. P06 had to translate general source-to-destination
connections into that representation without expanding every connection into an
independent parameter record.

For each source neuron/destination-core fanout, the compiler constructs the
weighted destination pattern. It normalizes the destination compartment indices
relative to the lowest destination index. Fanouts with the same relative
weighted pattern reuse one `SynapseTemplate`; each source receives an
`InputAxonBinding` with its own `target_offset`.

For example, fanouts to compartments `(20, 21)` with weights `(3, 4)` and to
`(40, 41)` with weights `(3, 4)` share the same relative template `(0:+3,
1:+4)` while using offsets 20 and 40. This is the project's explicit supported
sharing mechanism. It is intentionally not described as native Loihi SRAM
compression.

## 4. Resource-limit failures must occur during mapping

Virtualization and physical memory capacity must not allow invalid logical
mappings. P06 therefore enforces the existing per-core logical limits while
allocating compartments, input axons, output routes, and synaptic storage.

Mapping failures are surfaced with explicit resource diagnostics rather than
being deferred to FPGA packing or execution. The regression suite includes
capacity-failure cases so a physical implementation with available memory cannot
silently bypass the modeled Loihi-like logical limits.

## 5. External inputs require explicit compiled ingress routes

An external input population is not a physical compute core and must not appear
as one in the deployment. P06 represents external sources separately and emits
explicit ingress records that map an external source/neuron to the destination
logical core and axon allocated by the compiler.

This keeps external stimulus generation outside the mapped chip while still
making the complete ingress contract deterministic and inspectable.

## 6. Shared artifact pipeline

A major P06 closure criterion was proving that the serialized deployment itself,
not a hand-edited Python object, is the common boundary. The implemented flow is:

```text
network.json
    -> P06 compiler
    -> deployment.json + mapping report
    -> Python LogicalChip
    -> P05-compatible FPGA context image/load vectors
```

The source fingerprint is embedded into the compiled deployment, while the
compiled deployment fingerprint is embedded into FPGA vector/report artifacts.
The physical harness records that same deployment fingerprint in its result and
rejects the run if the result does not match the deployment that was compiled.

## 7. Reusing the accepted P05 FPGA shell

P06 changes mapping/configuration generation, not the compute architecture.
Re-synthesizing a functionally identical FPGA image would add implementation
variation without strengthening the compiler claim. The physical P06 gate
therefore reuses the accepted P05 one-engine/three-full-context bitstream and
debug probes.

This cleanly isolates the new variable: the deployment is now compiler-produced
rather than manually assembled. P05 remains the hardware architecture evidence;
P06 validates the software-to-hardware deployment boundary on top of that
accepted shell.

## 8. Physical mapped-deployment conformance

The accepted P06 physical run compiled a three-layer demonstration network into
three logical contexts serviced by the single P05 physical engine. The same
serialized compiled deployment generated both Python expectations and FPGA load
vectors.

Three external input scenarios were exercised:

- `pixel0`;
- `pixel1`; and
- `both_pixels`.

Each scenario ran for four algorithmic timesteps under both forward and reverse
logical-context service order, for 24 directed physical ticks total. All ticks
passed. The physical result reported:

```text
schema=p06-physical-mapped-deployment-v1
source_fingerprint=8e5fb969a806aac8bdc82d1129fc8ee50b53aef8e053ee10b6e11bd9748a1383
deployment_fingerprint=32937f2fd8f861ac28f516509a054b03e6098c2c8a051512ad289fc3be49ea4b
logical_contexts=3
physical_engines=1
logical_capacity_changed=0
scenarios=3
result=PASS
```

The accepted evidence directory produced by the harness is:

```text
hardware/evidence/p06_physical_20260930T014904Z/
```

The directory is generated locally by the physical runner and should be committed
unchanged so the result, compiler inputs/outputs, reports, hashes, and P05
hardware provenance remain tied together.

## 9. Accepted directed observations

| Scenario | Reverse service | Timestep | PL cycles | Local packets | Remote packets |
|---|---:|---:|---:|---:|---:|
| pixel0 | 0 | 0 | 74 | 0 | 1 |
| pixel0 | 0 | 1 | 76 | 0 | 1 |
| pixel0 | 0 | 2 | 68 | 0 | 0 |
| pixel0 | 0 | 3 | 61 | 0 | 0 |
| pixel0 | 1 | 0 | 74 | 0 | 1 |
| pixel0 | 1 | 1 | 76 | 0 | 1 |
| pixel0 | 1 | 2 | 68 | 0 | 0 |
| pixel0 | 1 | 3 | 61 | 0 | 0 |
| pixel1 | 0 | 0 | 74 | 0 | 1 |
| pixel1 | 0 | 1 | 76 | 0 | 1 |
| pixel1 | 0 | 2 | 68 | 0 | 0 |
| pixel1 | 0 | 3 | 61 | 0 | 0 |
| pixel1 | 1 | 0 | 74 | 0 | 1 |
| pixel1 | 1 | 1 | 76 | 0 | 1 |
| pixel1 | 1 | 2 | 68 | 0 | 0 |
| pixel1 | 1 | 3 | 61 | 0 | 0 |
| both_pixels | 0 | 0 | 87 | 0 | 2 |
| both_pixels | 0 | 1 | 91 | 0 | 2 |
| both_pixels | 0 | 2 | 75 | 0 | 0 |
| both_pixels | 0 | 3 | 61 | 0 | 0 |
| both_pixels | 1 | 0 | 87 | 0 | 2 |
| both_pixels | 1 | 1 | 91 | 0 | 2 |
| both_pixels | 1 | 2 | 75 | 0 | 0 |
| both_pixels | 1 | 3 | 61 | 0 | 0 |

The heartbeat moved from `2,346,802` to `6,746,579` before deployment loading.
The physical cycle counts are synchronous FPGA implementation observations for
this mapped corpus; they are not native-Loihi timing claims.

## 10. P06 boundary carried into P07

P06 establishes the deterministic deployment mechanism; it does not by itself
claim that the demonstration network is a sufficiently deep application
workload. P07 should therefore consume the P06 compiler unchanged and increase
network depth/mapping pressure rather than returning to hand-authored logical
core configurations.

P07 should preserve the following P06 invariants:

1. one versioned source network document;
2. one deterministic compiled deployment;
3. identical deployment fingerprint for Python and FPGA consumers;
4. explicit per-core occupancy/headroom and mapping failures;
5. compiler-managed connection sharing; and
6. no manual FPGA-specific remapping after compilation.
