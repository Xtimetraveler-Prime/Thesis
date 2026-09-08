from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "MILESTONES.md"
text = path.read_text(encoding="utf-8")

summary_old = "| M12 | Validate FPGA against Python golden model | In progress | 2026-08-27 | — |"
summary_new = "| M12 | Validate FPGA against Python golden model | Complete | 2026-08-27 | 2026-09-07 |"
if summary_old not in text:
    raise SystemExit("M12 summary row anchor not found")
text = text.replace(summary_old, summary_new, 1)

header_old = '''## M12 — Validate FPGA against Python golden model

**Status:** In progress  
**Started:** 2026-08-27  
**Repository evidence:** branch `agent/m12-validation-plan` for milestone planning; implementation branches to follow by sub-milestone
'''
header_new = '''## M12 — Validate FPGA against Python golden model

**Status:** Complete
**Started:** 2026-08-27
**Completed:** 2026-09-07
**Repository evidence:** M12.1 through M12.4 merged physical-validation work plus final closure branch `agent/m12-5-fpga-characterization`
'''
if header_old not in text:
    raise SystemExit("M12 header anchor not found")
text = text.replace(header_old, header_new, 1)

criteria_replacements = {
    "- [ ] Final timing, utilization, latency/throughput, supported-scope, and limitation evidence is recorded for thesis use.":
    "- [x] Final timing, utilization, latency/throughput, supported-scope, and limitation evidence is recorded for thesis use.",
    "- [ ] The complete software regression suite remains passing after the final M12 validation infrastructure changes.":
    "- [x] The complete software regression suite remains passing after the final M12 validation infrastructure changes.",
    "- [ ] Final M12 evidence is reproducible from source-controlled commands and artifacts.":
    "- [x] Final M12 evidence is reproducible from source-controlled commands and artifacts.",
}
for old, new in criteria_replacements.items():
    if old not in text:
        raise SystemExit(f"M12 completion criterion anchor not found: {old}")
    text = text.replace(old, new, 1)

criteria_tail = "- [x] Final M12 evidence is reproducible from source-controlled commands and artifacts.\n"
closure = '''

### Final M12 closure evidence

M12 closes the software-to-physical validation ladder for the first FPGA-v1 digital twin. The accepted evidence is layered rather than relying on one final pass/fail signal:

```text
independent Python FPGA-v1 golden model
        |
        +--> M12.1 physical trace boundary
        |      atomic, machine-readable, reproducible observation
        |
        +--> M12.2 directed single-tick physical equivalence
        |      16/16 cases exact
        |
        +--> M12.3 stateful/recurrent physical equivalence
        |      10 scenarios / 40 committed ticks exact
        |      plus independent reset/replay evidence
        |
        +--> M12.4 broad deterministic physical regression
        |      22 cases / 166 committed ticks exact
        |
        +--> M12.5 characterization image
               repeats the same 22 cases / 166 ticks
               zero mismatches after passive instrumentation
               plus routed resources, timing, physical cycles,
               throughput, scaling, supported scope, and limitations
```

Across the primary non-duplicate M12.2/M12.3/M12.4 validation corpora, the project exercised 48 physical workloads and 222 committed algorithmic ticks. M12.5 then independently reran the complete 22-case / 166-tick M12.4 corpus on the instrumented characterization image and again observed zero mismatches. The M12.3 reset/replay run provides additional duplicate-execution evidence and is not included in the 222-tick primary-corpus count.

The final M12.5 routed characterization image on `xck26-sfvc784-2LV-c` records:

```text
clock target:             100 MHz / 10.0 ns
routed WNS:               +0.493 ns
routed WHS:               +0.011 ns
CLB LUTs:                 4,424 / 117,120  (3.78%)
CLB registers:            4,280 / 234,240  (1.83%)
BRAM tiles, conservative: <=18 / 144       (<=12.50%)
RAMB36 / RAMB18:          15 / 5
DSPs:                     2 / 1,248        (0.16%)
URAM:                     0 / 64
physical cycle samples:   166
cycle min / mean / max:   26 / 379.10 / 8,218
latency min / mean / max: 0.260 / 3.791 / 82.180 us
```

The characterization corpus contains 2,035 neuron updates, 2,231 consumed input events, 4,084 actual CSR synapse visits, and 725 newly routed output events across 62,931 measured PL cycles. Considered back-to-back at 100 MHz with host/JTAG time excluded, this finite corpus corresponds to approximately 263,781 architectural ticks/s, 3.234 million neuron updates/s, 3.545 million consumed input events/s, 6.490 million CSR synapse visits/s, and 1.152 million routed output events/s. These values describe the accepted mixed corpus; they are not universal workload-independent throughput guarantees.

The selected stress cases make the serialized implementation cost interpretable rather than opaque. In the isolated no-route cases, quiescent physical ticks are exactly consistent with `16*N + 10` cycles for `N` configured neurons. External-event and dense-fanin cases then expose increments consistent with four cycles per consumed input event plus four cycles per actual CSR synapse visit. The recurrent fanout and long recurrent ring expose additional costs consistent with three cycles per consumed recurrent event and two cycles per newly routed output event. These are implementation-level observations for the current transparent FSM/HLS architecture, not Loihi timing claims or frozen behavioral semantics.

The final claim remains deliberately bounded. M12 demonstrates exact physical reproduction of the project's explicitly defined and externally validated Loihi-inspired FPGA-v1 subset. It does not claim Intel's undocumented physical microarchitecture, a complete Loihi feature set, production Linux deployment integration, maximum Fmax, or measured power/energy.

The complete M12 software regression gate remained passing after the final validation/characterization infrastructure changes. The final branch also regenerated the frozen broad corpus, linted the passive characterization hierarchy, reran the M12.2 synchronous recurrent-bank selector regression, and syntax-checked the source-controlled M12.5 runners.

Detailed M12.5 methodology, numerical results, stress-case interpretation, generated artifact paths, supported-feature matrix, exclusions, and reproducibility commands are recorded in `Neuromorphic Digital Twin/docs/M12_5_CHARACTERIZATION.md`.
'''
if criteria_tail not in text:
    raise SystemExit("M12 criteria tail not found")
text = text.replace(criteria_tail, criteria_tail + closure, 1)

start = text.find("### M12.5 — Characterize the validated FPGA and assemble thesis-level evidence")
end = text.find("\n---\n\n## M13 — Cross-validate and audit against Catalyst N1", start)
if start < 0 or end < 0:
    raise SystemExit("M12.5 section anchors not found")
new_m12_5 = '''### M12.5 — Characterize the validated FPGA and assemble thesis-level evidence

**Status:** Complete
**Started:** 2026-09-07
**Completed:** 2026-09-07
**Repository evidence:** branch `agent/m12-5-fpga-characterization`; accepted physical KV260 characterization with 22 cases / 166 ticks / zero mismatches

#### Core goal

Turn the exact-conformance result into a defensible final characterization of what the first FPGA digital twin implements, how it performs, where it differs from a complete Loihi processor, and what evidence supports the thesis claims.

#### Frozen characterization boundary

M12.5 leaves the validated M10/M11.5 computational-core RTL unchanged. It reuses the exact M12.4 22-case / 166-tick input corpus and adds a passive 32-bit PL-cycle counter, `observed_last_tick_cycles`, to the characterization shell. The counter never feeds computational state, routing, event delivery, or trace data.

Because even passive instrumentation changes the implemented image, M12.5 requires the complete M12.4 physical trace differential to pass again before accepting any timing or throughput measurement. The physical characterization image achieved 22/22 passing cases, 166/166 exact committed ticks, and zero Python-to-FPGA mismatches.

#### Routed implementation results

```text
target part:               xck26-sfvc784-2LV-c
target clock:              100 MHz / 10.0 ns
routed WNS:                +0.493 ns
routed WHS:                +0.011 ns
CLB LUTs:                  4,424 / 117,120
CLB registers:             4,280 / 234,240
BRAM tiles, conservative:  <=18 / 144 (RAMB36=15, RAMB18=5)
DSPs:                      2 / 1,248
URAM:                      0 / 64
```

Both setup and hold timing therefore close at the frozen 100 MHz target. M12.5 deliberately does not infer a maximum Fmax from positive WNS.

#### Physical latency results

All 166 committed ticks produced positive on-FPGA PL-cycle measurements:

```text
cycles min / mean / max:   26 / 379.10 / 8,218
latency min / mean / max:  0.260 / 3.791 / 82.180 us
```

JTAG/Hardware Manager wall-clock time is excluded. The measurement is architectural PL execution from accepted tick start through observed outer-core tick completion.

#### Throughput and scaling evidence

The analyzer derives per-tick ticks/s, neuron updates/s, consumed input events/s, and actual CSR synapse visits/s. Repeated events remain repeated and synaptic work is counted from exact packed CSR row lengths rather than assuming one event equals one synapse operation.

The 22-case workload-level scaling artifact records stable case metadata plus min/mean/max cycles, configured neuron/axon/synapse/route counts, total event activity, total CSR visits, and routed-event activity. Selected physical stress cases include:

```text
external multiplicity 1024:  26 / 4122 / 8218 cycles
dense fan-in 256 synapses:   522 / 1098 / 1674 cycles
recurrent fanout 256:         42 / 1154 / 2858 cycles
128-neuron population:      2058 / 2570 / 3082 cycles
32-tick recurrent ring:      276 / 278.906 / 279 cycles
mixed dense history:         834 / 1388 / 1798 cycles
```

The isolated cases expose a transparent implementation timing decomposition. For the exercised serialized paths, the measured cycle costs are exactly consistent with a quiescent `16*N + 10` cycle cost, four cycles per consumed input event, four cycles per CSR synapse visit, three additional cycles per consumed recurrent event, and two cycles per newly routed output event. This is documented as an implementation-level observation, not a Loihi timing claim or universal asymptotic law.

#### Supported scope and exclusions

The final M12.5 record consolidates the validated integer neuron arithmetic, saturating state width, decay/rounding, threshold/reset/refractory behavior, M08 Loihi-style project weight representation, signed-64 synaptic accumulation, deterministic event multiplicity/order, next-tick recurrence, double-buffered recurrent queues, atomic trace semantics, and finite physical capacities.

It also explicitly excludes unsupported Loihi features, Intel undocumented microarchitecture, online plasticity, multicore NoC behavior, production Linux/FPGA-manager deployment, maximum Fmax beyond the demonstrated target, and measured power/energy. Power remains outside the validated claim set because no trustworthy calibrated board-level measurement method was established.

#### Reproducibility

The accepted source-controlled command chain is:

```text
run_m12_5_bitstream.sh
run_m12_5_hardware_characterization.sh
run_m12_5_analysis.sh
```

The hardware command programs the image, captures the 22 physical traces and 166 cycle rows, reruns the complete exact M12.4 differential, rejects any mismatch, and assembles characterization outputs. The host-only analysis command can regenerate derived tables from preserved physical cycle/report artifacts without rerunning the board.

#### Pass boundary

**Achieved.** M12.5 has exact behavior-preservation evidence, routed implementation/resource evidence, physical PL-cycle measurements, latency/throughput/scaling artifacts, supported-scope documentation, explicit limitations, and reproducible source-controlled commands suitable for direct thesis use.

#### Detailed design record

See `Neuromorphic Digital Twin/docs/M12_5_CHARACTERIZATION.md` for the full physical results, cycle-accounting interpretation, stress-case analysis, resource percentages, throughput definitions, artifact paths, supported-feature matrix, exclusions, and thesis-level conclusion.
'''
text = text[:start] + new_m12_5 + text[end:]

path.write_text(text, encoding="utf-8")
