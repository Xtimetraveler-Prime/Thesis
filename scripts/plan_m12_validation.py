from pathlib import Path

path = Path('MILESTONES.md')
text = path.read_text(encoding='utf-8')

old_summary = '| M12 | Validate FPGA against Python golden model | Planned | — | — |'
new_summary = '| M12 | Validate FPGA against Python golden model | In progress | 2026-08-27 | — |'
if text.count(old_summary) != 1:
    raise RuntimeError(f'expected one M12 summary row, found {text.count(old_summary)}')
text = text.replace(old_summary, new_summary, 1)

old = '''## M12 — Validate FPGA against Python golden model

**Status:** Planned

### Goal

Use the same scenarios and trace format to establish that RTL simulation and physical FPGA execution match the Python model.

### Planned deliverables

- RTL-simulation traces.
- Physical-FPGA trace capture.
- Automated Python-versus-RTL and Python-versus-FPGA comparison.
- Resource, timing, and throughput results.
- Final validation summary for the thesis results chapter.
'''

new = '''## M12 — Validate FPGA against Python golden model

**Status:** In progress  
**Started:** 2026-08-27  
**Repository evidence:** branch `agent/m12-validation-plan` for milestone planning; implementation branches to follow by sub-milestone

### Goal

Establish exact, reproducible evidence that the physical FPGA implementation realizes the frozen Python FPGA-v1 computational contract across directed, recurrent, and broader deterministic workloads. M12 moves beyond the autonomous M11.6 smoke by extracting machine-readable architectural traces from real hardware, comparing those traces against independently generated Python-golden expectations, expanding coverage across stateful networks and boundary cases, and finally characterizing the validated implementation for the thesis results.

### Validation philosophy

M11.6 proved that one known four-tick workload can execute and self-check successfully on the physical K26. M12 must make that evidence general and externally inspectable rather than relying only on an on-FPGA pass bit. The Python golden model remains the behavioral authority for FPGA-v1, and the physical FPGA must be treated as an independently observed implementation under test.

The intended evidence chain is:

```text
Python scenario / configuration
            ↓
Python golden trace + FPGA load image
            ↓
physical FPGA execution
            ↓
machine-readable FPGA trace
            ↓
exact field-by-field differential report
```

The work is split into five ordered sub-milestones. M12.1 creates the physical observation path; M12.2 proves exact one-tick whole-core behavior; M12.3 proves stateful and recurrent evolution; M12.4 broadens deterministic physical coverage; and M12.5 turns the validated implementation into final thesis-level characterization and evidence.

### Overall completion criteria

- [ ] A stable machine-readable physical-FPGA trace path exists for the required M10/M11 architectural observables.
- [ ] Directed single-tick physical cases match the Python golden model exactly.
- [ ] Directed multi-tick and recurrent physical scenarios match Python exactly at every compared tick.
- [ ] A broader deterministic physical corpus completes with zero unexplained mismatches and reproducible failure artifacts.
- [ ] Final timing, utilization, latency/throughput, supported-scope, and limitation evidence is recorded for thesis use.
- [ ] The complete software regression suite remains passing after the final M12 validation infrastructure changes.
- [ ] Final M12 evidence is reproducible from source-controlled commands and artifacts.

---

### M12.1 — Build the physical FPGA trace-capture boundary

**Status:** Planned

#### Core goal

Make the physical FPGA sufficiently observable that host-side tooling can reconstruct the architectural state needed for exact Python-versus-FPGA comparison without manually reading individual VIO values or relying only on the autonomous M11.6 `pass/fail` result.

#### Planned work

- Define a versioned physical trace schema aligned with the already frozen M10 trace requirements and existing Python/backend trace concepts.
- Expose, at minimum, architectural tick, neuron current/voltage/refractory state, spikes, core fault state, recurrent queue bank/count information, and the event/routing observations required to distinguish external input, consumed recurrence, and newly routed recurrence.
- Preserve atomic tick observability: a captured record must correspond to one committed algorithmic tick rather than a partially updated serialized implementation state.
- Add a source-controlled host capture path that converts hardware observations into a stable JSON or equivalent machine-readable artifact.
- Reuse JTAG/debug infrastructure where practical for the first validation path rather than introducing a large Linux/AXI software stack before behavioral equivalence is established.
- Keep the M11.5 computational semantics unchanged; changes in this sub-milestone should be observability/control infrastructure unless a genuine implementation defect is discovered.

#### Pass boundary

A small deterministic physical workload can be configured and executed, and the host can capture a complete machine-readable trace containing every required architectural observation for each requested committed tick. The trace can be parsed and replayed by automated tests without manual transcription.

---

### M12.2 — Exact single-tick Python-versus-FPGA differential validation

**Status:** Planned

#### Core goal

Prove that one complete physical FPGA algorithmic tick is exactly equivalent to the Python FPGA-v1 golden transition across a deliberately chosen directed corpus.

#### Planned coverage

- Positive and negative synaptic input.
- Mixed excitation and inhibition.
- Current- and voltage-decay boundary values.
- Positive and negative state saturation boundaries.
- Threshold equality and just-over-threshold behavior.
- Refractory entry, hold, countdown, and release behavior.
- Multiple neurons and multiple axons.
- Repeated event multiplicity and empty CSR rows.
- Representative M08 encoded-weight sign modes, exponents, and precisions.
- Legal finite-profile count and identifier boundaries where practical on the physical test path.

#### Comparison contract

For every case, Python independently generates the initial state/configuration, FPGA load image, and expected committed trace. The physical FPGA executes exactly one architectural tick. Host-side comparison then checks every required field exactly; the FPGA is not allowed to define its own expected result.

#### Pass boundary

The agreed directed single-tick corpus completes on the physical K26 with zero exact mismatches across all compared architectural fields. Any discovered defect must be reduced to a reproducible directed regression before M12.2 can close.

---

### M12.3 — Multi-tick and recurrent-network physical conformance

**Status:** Planned

#### Core goal

Prove that Python/FPGA equivalence survives state history, recurrent queue swaps, event ordering, fan-in/fan-out, and repeated algorithmic ticks rather than matching only isolated transitions.

#### Planned scenario classes

- Feed-forward spike chains.
- Self-recurrent neurons.
- Multi-neuron recurrent chains and loops.
- Fan-out from one source neuron.
- Fan-in from multiple sources.
- Same-target recurrent multiplicity.
- Mixed external and recurrent events on the same tick.
- Simultaneous spikes with deterministic routing order.
- Quiescent periods followed by renewed external input.
- Reset/replay cases proving deterministic restoration of architectural state and recurrent queues.

#### Per-tick comparison

The comparison should validate each committed tick rather than only the final state, including neuron state, spikes, architectural tick, consumed recurrent events, routed recurrent events, active queue bank/count, and core fault state. This preserves the M09/M10 timing and routing contract in physical evidence.

#### Pass boundary

Every directed multi-tick/recurrent scenario matches the Python golden trace exactly at every compared tick with zero unexplained mismatches. This sub-milestone is the primary evidence that the FPGA behaves as a stateful neuromorphic processor model rather than merely reproducing isolated neuron equations.

---

### M12.4 — Broad deterministic physical regression and boundary stress

**Status:** Planned

#### Core goal

Increase confidence beyond hand-authored demonstrations by running a reproducible deterministic corpus across a broad portion of the supported FPGA-v1 configuration and workload space.

#### Planned corpus strategy

Combine three layers rather than relying on undirected random testing alone:

1. **Directed architectural boundaries** retained from M12.2/M12.3.
2. **Seeded deterministic generated networks** varying neuron/axon/synapse/route counts, topology, weights, decays, thresholds, refractory settings, external events, recurrent multiplicity, and run length.
3. **Finite-capacity stress cases** approaching selected M11.5 physical limits where those cases are practical and informative on the board.

Every generated case should carry a stable case ID, generator version, seed, configuration hash, Python expectation artifact, FPGA trace artifact, and exact comparison report so any mismatch can be reproduced independently.

#### Failure policy

A corpus mismatch does not become an accepted exception merely because most other cases pass. Each mismatch must be classified as a golden-model problem, hardware implementation problem, capture/transport problem, unsupported configuration, or test-infrastructure defect. Valid implementation defects require a minimized directed regression before closure.

#### Pass boundary

The agreed deterministic physical corpus completes with zero unexplained mismatches, and the repository contains enough metadata to reproduce individual passing or failing cases without regenerating an opaque random workload.

---

### M12.5 — Characterize the validated FPGA and assemble thesis-level evidence

**Status:** Planned

#### Core goal

Turn the exact-conformance result into a defensible final characterization of what the first FPGA digital twin implements, how it performs, where it differs from a complete Loihi processor, and what evidence supports the thesis claims.

#### Planned characterization

- Final implemented resource utilization and routed timing evidence for the validation-capable image.
- Clock frequency/timing margin and measured or derived cycles per architectural tick.
- Tick latency across representative neuron/synapse/event loads.
- Neuron-update and event/synapse-processing throughput metrics appropriate to the serialized first implementation.
- Scaling observations as neuron, synapse, route, and event counts increase.
- Power/energy measurements only if a trustworthy board-level measurement method is available; otherwise explicitly leave power outside the validated claim set.
- Consolidated supported-feature matrix covering arithmetic, M08 static weights, synaptic accumulation, threshold/reset/refractory behavior, recurrent routing, trace semantics, and finite-capacity limits.
- Explicit limitations, including unsupported Loihi features and any remaining board/software integration constraints.

#### Thesis evidence chain

M12.5 should summarize the complete project verification ladder without overstating the implementation:

```text
Brian2Loihi reference
        ↓ supported-subset behavioral validation
independent Python golden model
        ↓ frozen M10 FPGA-v1 contract
HLS / RTL differential verification
        ↓ routed physical implementation
physical FPGA trace differential validation
        ↓
validated FPGA digital twin of the defined Loihi-inspired subset
```

The defensible claim is not that the project reproduces Intel Loihi's undocumented physical microarchitecture. The intended claim is that a transparent FPGA implementation reproduces the explicitly defined and externally validated Loihi-inspired computational subset, with exact state-transition evidence from software reference through physical hardware.

#### Pass boundary

M12 closes when exact physical conformance evidence, broad deterministic coverage, final implementation/performance characterization, supported-scope boundaries, and limitations are all recorded in a reproducible form suitable for direct use in the thesis results and conclusions.
'''

if text.count(old) != 1:
    raise RuntimeError(f'expected one original M12 block, found {text.count(old)}')
text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
print('Expanded M12 into five planned physical-validation sub-milestones.')
