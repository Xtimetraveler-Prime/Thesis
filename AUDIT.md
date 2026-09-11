# Thesis Originality, Provenance, and Source-Use Audit

**Status:** Active / living audit  
**Audit started:** 2026-09-11  
**Repository:** `Xtimetraveler-Prime/Thesis`  
**Current phase:** Phase 1 — high-risk source-code and provenance review

## Purpose

This document records an ongoing audit of the thesis repository for potential plagiarism, unattributed source derivation, inappropriate code reuse, licensing/attribution problems, and related provenance concerns.

The purpose is not to generate a single "plagiarism percentage." Similarity by itself is not enough to determine whether work is improperly copied. Neuromorphic implementations will naturally share terminology, equations, parameter ranges, interfaces, and common engineering patterns. The audit therefore combines:

1. exact source/version identification;
2. side-by-side source inspection;
3. structural comparison of implementations;
4. Git-history chronology;
5. separation of behavioral/equation reuse from source-code reuse;
6. documentation/text review;
7. licensing/attribution review; and
8. explicit tracking of material that has not yet been audited.

This document is an engineering/research provenance record, not a legal opinion and not a substitute for the university's academic-integrity determination.

---

## Audit classification vocabulary

Each finding is assigned one of the following states.

| State | Meaning |
|---|---|
| **CLEAR — no concerning similarity identified** | The reviewed material has expected conceptual overlap but materially independent expression/implementation and no copying signal was found in the reviewed boundary. |
| **MONITOR — citation/provenance sensitive** | No copying finding is present, but the work follows an externally documented equation, API, format, or behavior closely enough that source attribution should be explicit and further provenance review is useful. |
| **INVESTIGATE** | Similarity, chronology, or attribution is sufficiently unusual that a deeper comparison is required before the material should be treated as clean. |
| **REMEDIATE** | The audit has identified material that should be rewritten, attributed, relicensed, or otherwise corrected before thesis submission. |
| **NOT YET AUDITED** | No conclusion has been reached. This is intentionally different from CLEAR. |

A finding can also carry a separate **license/attribution note** even when plagiarism risk is low.

---

# 1. External-source inventory frozen for this audit

The first phase concentrates on the two executable external implementations that most directly influenced or were used to validate the project, plus the published Loihi sources already frozen by M13.

## 1.1 Catalyst N1

**Repository:** `catalyst-neuromorphic/catalyst-n1`  
**Pinned tag:** `v2.3-paper` (equivalent `n1-final`)  
**Pinned commit:** `1806bb4b4114d7671e5648fa75b7b83b3a8d5543`  
**License:** Apache-2.0  
**Published reference recorded by M13:** *Catalyst N1: A 131K-Neuron Open Neuromorphic Processor with Programmable Synaptic Plasticity*, DOI `10.5281/zenodo.18727094`

Primary Catalyst source inspected in Phase 1:

- `README.md`
- `rtl/lif_neuron.v`
- `rtl/scalable_core_v2.v`
- the pinned repository tree and K26/Kria source inventory

Catalyst is the highest-priority external codebase for an originality review because M13 involved direct source inspection, RTL probing, and a Vivado reproduction of the pinned implementation.

## 1.2 Brian2Loihi

**Repository:** `sagacitysite/brian2_loihi`  
**Pinned version/tag:** `0.5.2` / `v0.5.2`  
**Pinned commit:** `d54676cb113e48dc886615a0b589bb0e4bccbca4`  
**License:** MIT

Primary Brian2Loihi source inspected in Phase 1:

- `loihi_neuron_group.py`
- `loihi_synapses.py`, including `calcActualWeights()`
- repository tree / public class boundary

Brian2Loihi is important because it was used much earlier than Catalyst as an executable behavioral reference during the creation and validation of the independent Python golden model.

## 1.3 Published Loihi references already frozen by M13

The existing M13 reference manifest records at least the following publications as primary Loihi evidence:

- Mike Davies et al., *Loihi: A Neuromorphic Manycore Processor with On-Chip Learning*, IEEE Micro 38(1), 2018, DOI `10.1109/MM.2018.112130359`.
- Eric Lin et al., *Programming Spiking Neural Networks on Intel's Loihi*, Computer 51(3), 2018, DOI `10.1109/MC.2018.157113521`.

**Phase-1 limitation:** these papers are inventoried here, but a complete equation-by-equation and prose-similarity audit against the publications has **not yet been completed**. That is a Phase-2/Phase-3 task. This matters most for the static-weight encoder, whose arithmetic intentionally implements a published Loihi-style contract.

## 1.4 Existing project independence rule

Before this originality audit was created, M13 had already frozen an explicit source-independence rule in `Neuromorphic Digital Twin/references/m13_1_reference_manifest.json`. Among other restrictions, it states that Catalyst RTL, simulator equations, state-machine code, constants, and implementation structures are not to be copied into the project's computational core. Catalyst may instead be used to formulate comparison questions, reproduce Catalyst itself, and classify architectural differences.

This audit does **not** treat that policy statement as proof that copying did not occur. The source comparisons below are intended to test whether the repository is consistent with that rule.

---

# 2. Git-history provenance check

Chronology is strong evidence in this repository because the computational baseline was built and physically validated before the detailed Catalyst audit began.

## 2.1 M11 implementation predates the formal Catalyst audit

The repository records M11 HLS work beginning on **2026-08-20**, including:

- `4b60639c16518976800022a27757e0d3b5f95881` — `Start M11.1 HLS neuron datapath`
- `2dc8ceecc1569279ec4ddd7b227f3ddb0ababfb1` — `Implement M11.1 HLS neuron transition`

The formal M13 external-reference pin was not added until **2026-09-08**:

- `e8499a996a509949a0d6fb7763c54097646ff6ec` — `Pin M13.1 external reference baseline`

An M12/M13 roadmap mentioning the planned Catalyst comparison appears on 2026-08-27 (`341570cc2a8658b0e351810ad3afecdbe04462cb`), after the initial HLS implementation was already underway and after the Python golden model had existed for substantially longer.

**Interpretation:** the repository chronology is inconsistent with a theory that the main M11 HLS implementation was created by copying code encountered during the September M13 Catalyst source audit. This is strong provenance evidence, although Git history alone cannot prove that an external repository was never seen informally before a recorded audit.

## 2.2 Frozen M12 computational baseline did not change during M13

M13 pins the completed M12 project baseline at:

`80a502ec6dfc4c8d61372089b08c9a584ad65f85`

A Git comparison from that M12 baseline to current `main` shows approximately 190 subsequent commits, overwhelmingly adding M13 documentation, reference manifests, comparison software, tests, Catalyst runners, and audit infrastructure.

Crucially, the comparison contains **no modifications to the production HLS core or `rtl/core_v1` computational RTL**. The existing `comparison/brian2loihi_backend.py` received only a small M13 comparison-boundary change (+8 lines); new M13 comparison modules were added separately.

**Finding P-001 — CLEAR / strong provenance evidence.** The frozen computational baseline was not rewritten after detailed Catalyst inspection. Therefore M13 source inspection did not introduce Catalyst implementation code into the already M12-validated production HLS/RTL path.

---

# 3. Phase-1 source-code comparisons

## 3.1 Python neuron transition vs. Brian2Loihi neuron implementation

### Project source reviewed

`Neuromorphic Digital Twin/src/neuromorphic_twin/neuron.py`

The project represents one neuron transition as a small explicit integer state transformation:

- immutable `NeuronStepResult`;
- explicit `NeuronState` and `NeuronConfig` inputs;
- explicit delivered-current-before-decay ordering;
- explicit refractory state update;
- explicit voltage decay and bias application;
- explicit strict `voltage > threshold` comparison;
- explicit reset and future blocked-tick count.

### External source reviewed

Brian2Loihi `loihi_neuron_group.py` at commit `d54676cb...`.

Brian2Loihi implements its neuron as a subclass of Brian2 `NeuronGroup`. Its behavior is primarily expressed through Brian2 differential-equation strings such as separate rounded current/voltage decay expressions, Brian2's `(unless refractory)` mechanism, a threshold expression string, and Brian2's reset/refractory scheduler.

### Similarities

Expected behavioral similarities include:

- current-based LIF behavior;
- 4096-scale decay representation;
- round-away-from-zero style decay in the compared subset;
- strict greater-than threshold semantics;
- reset/refractory behavior.

Those similarities are exactly the behaviors the project intentionally tested against Brian2Loihi and are not, by themselves, evidence of copied source code.

### Material implementation differences

- Project: explicit pure Python integer transition operating on project dataclasses.
- Brian2Loihi: Brian2 object model and differential-equation strings.
- Project: arithmetic policy (`ArithmeticConfig`) is separated from neuron behavior.
- Brian2Loihi: behavior is delegated into Brian2's simulation/scheduling framework.
- Project: FPGA-oriented explicit state flow and return object.
- Brian2Loihi: simulator-framework state variables and monitors.

No distinctive Brian2Loihi code structure, class hierarchy, documentation paragraph, or equation-string implementation was identified in the project neuron source reviewed here.

**Finding C-001 — CLEAR.** The Phase-1 side-by-side review supports the project's claim that the Python neuron transition is an independently structured implementation that was behaviorally validated against Brian2Loihi rather than copied from Brian2Loihi source.

**Citation note:** thesis prose describing Loihi/Brian2Loihi semantics still needs appropriate citations even when the implementation is independent.

---

## 3.2 Static weight encoder vs. Brian2Loihi weight calculation

### Project source reviewed

`Neuromorphic Digital Twin/src/neuromorphic_twin/weights.py`

The project source explicitly states that the encoder is intended to be independent of Brian2Loihi and to implement the published static-weight contract with integer-only operations.

The main path is:

1. validate a requested mantissa against sign mode;
2. truncate/quantize the mantissa toward zero at the configured precision;
3. apply exponent scaling and 64-value alignment;
4. clip to the signed 21-bit-aligned effective range;
5. preserve requested value, quantized value, pre-clip value, final value, and clipping status in an immutable result object.

### External source reviewed

Brian2Loihi `loihi_synapses.py`, including:

- `__getWeightPrecision()`;
- `__getWeightLimit()`;
- `__buildNoLearningRule()`; and
- `calcActualWeights()`.

Brian2Loihi also calculates precision from `num_weight_bits` and sign mode, quantizes a mantissa, applies `2**(6 + w_exp)` scaling, aligns to a multiple of `2**6`, and clips to a 21-bit range with six low zero bits.

### Why this area receives extra scrutiny

The arithmetic stages are necessarily similar because both implementations are attempting to represent the same Loihi-style static-weight initialization rule. This means a superficial line-of-thought comparison will look substantially closer than the neuron implementation.

### Differences identified in Phase 1

The project implementation is not a transliteration of `calcActualWeights()`:

- it uses explicit project types (`WeightFormat`, `WeightSignMode`, `StaticWeightEncoding`) rather than a Brian2 `Synapses` subclass;
- it is scalar, deterministic, and integer-only rather than NumPy array arithmetic embedded in a simulator object;
- sign-mode validation and trace metadata are explicit project interfaces;
- helper decomposition and control flow differ;
- the project retains pre-clip and quantized intermediate values for FPGA traceability;
- the implementation includes project-specific immutable format objects and a hardware-storage-oriented contract.

However, because the high-level sequence and constants naturally match, this finding should not be closed solely by comparing the two code files.

**Finding C-002 — MONITOR (citation/provenance sensitive), no copying finding at this stage.** Phase 1 found no evidence that `weights.py` is copied or mechanically translated from Brian2Loihi, but the arithmetic is close enough that Phase 2 should trace each formula/constants set directly to the published Loihi sources and make that derivation explicit in the audit. If the published sources do not support a particular detail, the audit should identify the actual origin of that detail rather than assuming it is public knowledge.

---

## 3.3 HLS neuron datapath vs. Catalyst LIF neuron RTL

### Project source reviewed

`Neuromorphic Digital Twin/hls/core_v1/src/neuron_step_v1.cpp`

The project HLS datapath contains:

- explicit signed 24-bit state saturation;
- signed 64-bit working arithmetic;
- `round_away_from_zero_div4096_v1()`;
- separately represented current and voltage state;
- configurable current and voltage decays;
- bias;
- configurable reset voltage;
- explicit project refractory semantics;
- Vitis HLS interface pragmas;
- project specification identifiers such as `CORE-NEURON-001`.

### External source reviewed

Catalyst `rtl/lif_neuron.v` at commit `1806bb4b...`.

The Catalyst module is a small synchronous Verilog LIF neuron with:

- 16-bit potential;
- one synaptic-input signal;
- `THRESHOLD`, `LEAK_RATE`, `RESTING_POT`, and `REFRAC_CYCLES` parameters;
- a simple potential/leak comparison;
- a 4-bit refractory counter.

### Comparison

The two files share only domain-level LIF concepts. Their arithmetic models, widths, state decomposition, refractory implementation, programming language, interface model, and update equations are materially different.

A particularly relevant difference is that Catalyst's simple LIF implementation clamps sufficiently negative sub-rest state to `RESTING_POT`, whereas the project/Brian2Loihi tested behavior preserves negative state in the relevant probe. M13 explicitly documented that difference rather than modifying the project to match Catalyst.

**Finding C-003 — CLEAR.** No source-code or structural copying signal was identified between the production HLS neuron transition and Catalyst `lif_neuron.v`.

---

## 3.4 Project integrated RTL vs. Catalyst `scalable_core_v2.v`

### Project source reviewed

- `Neuromorphic Digital Twin/rtl/core_v1/integrated_core_controller_v1.sv`
- `Neuromorphic Digital Twin/rtl/core_v1/phase_b_synapse_accumulator_v1.sv`

The project architecture is deliberately decomposed into independently testable blocks. The integrated controller sequences a Phase-B synapse accumulator and a separate neuron-array/HLS transition. The Phase-B walker consumes external then recurrent events, traverses the project's frozen M08 axon-row CSR storage image, reconstructs project weight formats, and produces signed-64 per-neuron accumulators. The implementation is intentionally serialized for traceability.

Representative project FSM states include:

- integration: `S_PHASE_B_START`, `S_PHASE_B_WAIT`, `S_COPY_READ`, `S_COPY_WAIT`, `S_COPY_WRITE`, `S_NEURON_TICK_START`;
- Phase B: `S_CLEAR`, `S_EVENT_LOAD`, `S_EVENT_VALIDATE`, `S_ROW_VALIDATE`, `S_SYN_READ`, `S_SYN_VALIDATE`, `S_ACCUM_READ`, `S_ACCUMULATE`, `S_EVENT_ADVANCE`.

### External source reviewed

Catalyst `rtl/scalable_core_v2.v` at the pinned M13 commit.

Catalyst is a substantially broader, largely monolithic RTL core. Its interface and FSM incorporate features absent from FPGA-v1, including learning, graded operation, dendritic behavior, three-factor learning, noise, delayed events, microcode programming, trace state, and other Catalyst-specific features. Its state machine contains a large set of `S_DELIVER_*`, `S_UPDATE_*`, `S_LEARN_*`, delay-drain, and related states. Its native synaptic memory/index arrangement and runtime control are not the project's M08 CSR + Phase-B/Phase-C composition.

### Comparison

There is unavoidable conceptual overlap: both are clocked neuromorphic processors, both must store neuron/synapse state, both traverse synaptic connectivity, and both use FSMs and SRAM/BRAM-like memories. Those are generic engineering necessities and are not evidence of plagiarism.

The distinctive implementation structures are materially different:

- project: modular Phase-B walker + neuron-array controller + packaged HLS transition;
- Catalyst: much broader Catalyst core state machine containing delivery, update, learning, delay, and other feature paths;
- project: project-specific M08 format/CSR contract and signed-64 accumulator boundary;
- Catalyst: Catalyst pool/index formats and its own per-neuron/state memories;
- project: verification-first serialized architecture and explicit trace windows;
- Catalyst: different feature/capacity/performance goals and internal organization.

Combined with the Git chronology and the frozen-M12-to-main comparison, this is strong evidence against production-core source copying from Catalyst.

**Finding C-004 — CLEAR.** No concerning structural/code similarity was identified between the reviewed project core RTL and pinned Catalyst `scalable_core_v2.v`.

---

## 3.5 M13 Catalyst audit testbench

### Project source reviewed

`Neuromorphic Digital Twin/rtl/m13_4/tb_m13_4_catalyst_cuba.sv`

This file intentionally instantiates the external `scalable_core_v2` module. It therefore repeats Catalyst public module/port/parameter names such as `NUM_NEURONS`, `ext_current`, `pool_we`, `prog_param_we`, and `probe_state_id` so that the external module can be elaborated and driven.

This is **intentional interface use**, not evidence that the project's computational core copied Catalyst. The file is isolated under `rtl/m13_4`, labels itself as an audit-only testbench, and is part of a comparison harness rather than the FPGA-v1 implementation.

The testbench supplies project-authored directed stimulus, captures Catalyst probe outputs, and emits machine-readable trace lines used by M13. Its existence should nevertheless remain explicitly attributed because readers should not mistake the Catalyst interface names for independently invented project interfaces.

**Finding C-005 — CLEAR with attribution note.** Repetition of Catalyst module/port names in this audit-only testbench is necessary to instantiate the pinned external RTL and is correctly contextualized as Catalyst-facing audit infrastructure. No Catalyst RTL implementation body was identified as vendored into the project.

**License note:** the pinned Catalyst source is Apache-2.0. The project currently fetches/uses the external source for comparison rather than tracking a copy of `scalable_core_v2.v` in the production tree. Phase 4 should still produce an explicit third-party-notices record for the repository.

---

## 3.6 Brian2Loihi comparison adapter

### Project source reviewed

`Neuromorphic Digital Twin/src/neuromorphic_twin/comparison/brian2loihi_backend.py`

The adapter necessarily uses Brian2Loihi's public API names (`LoihiNetwork`, `LoihiNeuronGroup`, `LoihiSpikeGeneratorGroup`, `LoihiSpikeMonitor`, `LoihiSynapses`, and `synapse_sign_mode`) and maps project scenarios into parameters accepted by those classes.

The adapter itself is project-specific orchestration:

- validates whether a project scenario is representable in Brian2Loihi;
- groups project synapses by immutable project `WeightFormat`;
- preserves project scenario ordering;
- records external package versions;
- normalizes monitored state into the project's backend-neutral `BackendTrace` schema;
- explicitly rejects unsupported recurrence and repeated-same-source event cases instead of silently changing semantics.

The reviewed implementation does not reproduce Brian2Loihi class bodies, equation strings, or internal learning-rule logic.

**Finding C-006 — CLEAR with dependency-attribution note.** The file is an interoperability adapter that calls the external library's public API; no copied Brian2Loihi implementation was identified in the reviewed adapter.

---

# 4. Documentation/prose spot check

A complete prose audit has not yet been performed. Phase 1 performed only a targeted screen of the highest-risk M13 material.

## Sources spot-checked

- Catalyst pinned `README.md`.
- Project `Neuromorphic Digital Twin/docs/M13_1_REFERENCE_BASELINE.md`.
- Project M13 final/audit documentation already reviewed during milestone reporting.
- Brian2Loihi source docstrings and selected README/source phrases.

## Preliminary result

The project M13 methodological prose is substantially different in structure and wording from Catalyst's README. Catalyst's README primarily contains product description, specifications, directory layout, simulator instructions, SDK examples, FPGA build instructions, and benchmark commands. The project's M13 documents instead describe evidence hierarchy, source pins, normalization policy, discrepancy classification, and project change control.

No verbatim paragraph reuse was identified in this spot check. Exact names, commit hashes, module names, capacities, licenses, command names, and technical parameter labels are factual/source-identifying material and will naturally match.

**Finding T-001 — MONITOR / incomplete.** The M13 documentation spot-check found no concerning copied prose, but this is **not** a repository-wide text-similarity clearance. All Markdown/README/comments remain scheduled for a systematic phrase/token scan against the external documentation and papers.

### Search-tool caution

GitHub code search was tested for several distinctive identifiers/phrases as a supplemental screen, but indexing can lag and returned at least one false-negative relative to known current files. Negative code-search results are therefore **not** used as substantive originality evidence in this audit.

---

# 5. Licensing and attribution observations

## 5.1 External licenses identified

- Catalyst N1: Apache-2.0.
- Brian2Loihi: MIT.

No tracked copy of the pinned Catalyst repository or Brian2Loihi package was identified in the thesis repository tree reviewed in Phase 1. The project uses fetch/install scripts and runtime dependencies for external comparisons.

## 5.2 Repository-level notice recommendation

Even if Phase 1 continues to support the conclusion that no external implementation code was copied into the production core, the repository would benefit from a dedicated `THIRD_PARTY_NOTICES.md` or attribution section that records:

- external repository name;
- exact version/commit used;
- license;
- how it was used (behavioral reference, comparison dependency, externally fetched RTL, etc.);
- whether any source is vendored or merely fetched/installed;
- relevant publication citation.

This is useful both for licensing hygiene and for thesis provenance. It does **not** imply that third-party code has been copied.

## 5.3 Project license

No root project `LICENSE` was observed in the initial repository root inventory. That is not a plagiarism finding. Before broad redistribution, the project should decide whether/how its own source is licensed and ensure that decision is compatible with any material eventually determined to be derived from third-party code.

**Finding L-001 — MONITOR.** No Phase-1 license violation was identified, but formal third-party notices and a project licensing decision remain open tasks.

---

# 6. AI-assistance provenance

This project has received substantial generative-AI assistance during design discussion, implementation, debugging, documentation, and audit work. That creates a **separate academic-integrity question** from source-code plagiarism.

The relevant issues are:

1. whether generated material inadvertently reproduced protected external source;
2. whether the institution/program requires disclosure of generative-AI assistance;
3. what level of human verification/authorship is required for thesis submission.

This originality audit addresses item 1 by comparing generated/project material against known external sources. Items 2 and 3 require a separate review of the applicable institutional/departmental thesis and academic-integrity policy.

**Finding A-001 — MONITOR.** AI assistance should be disclosed or described according to the applicable academic policy. No claim about the required form of disclosure is made here because that policy has not yet been audited.

---

# 7. Phase-1 overall assessment

## Current conclusion

**No evidence of production-core plagiarism has been identified in the Phase-1 material reviewed so far.**

That conclusion is deliberately narrower than "the repository is plagiarism-free." The strongest evidence currently is:

- the project Python neuron implementation and Brian2Loihi neuron source are structurally very different;
- the project HLS neuron datapath and Catalyst LIF RTL are materially different implementations;
- the project integrated RTL organization and Catalyst's core FSM/memory organization are materially different;
- detailed Catalyst inspection occurred after the core HLS/FPGA architecture was already developed;
- the M12 production computational baseline was frozen before M13 and the core HLS/RTL files were not changed during the Catalyst audit;
- Catalyst-facing and Brian2Loihi-facing code is isolated as explicit comparison/adaptation infrastructure;
- no Catalyst implementation body has been identified as vendored into the thesis repository;
- the weight encoder shows expected equation-level similarity but not obvious code-level copying and is explicitly retained as a deeper provenance target.

## Current risk table

| ID | Area | Compared against | Status | Current risk |
|---|---|---|---|---|
| P-001 | Git chronology / M12 freeze | M13 development history | CLEAR | Low |
| C-001 | `neuron.py` | Brian2Loihi `loihi_neuron_group.py` | CLEAR | Low |
| C-002 | `weights.py` | Brian2Loihi `loihi_synapses.py` | MONITOR | Medium provenance/citation sensitivity; no copying finding |
| C-003 | HLS `neuron_step_v1.cpp` | Catalyst `rtl/lif_neuron.v` | CLEAR | Low |
| C-004 | integrated/Phase-B RTL | Catalyst `rtl/scalable_core_v2.v` | CLEAR | Low |
| C-005 | M13 Catalyst testbench | Catalyst module interface | CLEAR + attribution | Low |
| C-006 | Brian2Loihi adapter | Brian2Loihi public API | CLEAR + dependency attribution | Low |
| T-001 | M13 prose spot check | Catalyst README / Brian source text | MONITOR / incomplete | No issue found; insufficient coverage |
| L-001 | licensing/third-party notices | Apache-2.0 / MIT dependencies | MONITOR | Hygiene task open |
| A-001 | AI assistance | institutional policy | MONITOR | Policy audit open |

---

# 8. Limitations of Phase 1

The following statements must **not** be inferred from the current audit:

- It does not prove that every repository file is original.
- It does not yet compare every Python, C++, HLS, RTL, Tcl, Bash, test, and Markdown file against every external source.
- It does not yet perform a complete source-token/n-gram similarity scan.
- It does not yet compare thesis/project prose against the full text of all cited papers.
- It does not yet audit every external repository or web source consulted earlier in the project.
- It does not make a legal determination about copyright or derivative works.
- It does not make the university's academic-integrity determination.

A local full-repository clone/token-analysis attempt was planned for this phase, but the current audit runtime lacked direct GitHub network/DNS access. Exact files were still retrieved through the authenticated GitHub connector, allowing the high-risk side-by-side review above. Repository-wide automated similarity scanning remains an explicit follow-up rather than being silently omitted.

---

# 9. Planned next phases

## Phase 2 — Complete source/provenance inventory

**Goal:** identify every external source that may have influenced the repository before running exhaustive similarity analysis.

Planned work:

- extract all external repositories, papers, DOIs, URLs, vendor examples, and documentation mentioned in `MILESTONES.md`, `EXPERIMENTS.md`, `docs/`, comments, scripts, and commit history;
- identify any AMD/Xilinx/Vivado/Vitis example code or Tcl patterns that may have been adapted;
- identify any Stack Overflow/forum/blog/source snippets used during board bring-up;
- record exact source versions where possible;
- classify each source as behavioral reference, equation/reference source, API/dependency, tooling example, or implementation inspiration.

## Phase 3 — Repository-wide similarity audit

**Goal:** perform systematic code/text comparisons after the source inventory is complete.

Planned code checks:

- exact line/block matches;
- comment-stripped and whitespace-normalized matches;
- token n-grams;
- identifier-normalized structural similarity where practical;
- unusual constants/state names/test vectors;
- function/module decomposition similarities;
- copied comments or error messages.

Languages/surfaces:

- Python;
- C++ / HLS;
- Verilog/SystemVerilog;
- Tcl;
- Bash;
- JSON/reference schemas;
- tests and testbenches.

Every high-scoring match should be manually adjudicated because generic language boilerplate and required API declarations can create false positives.

## Phase 4 — Documentation and publication audit

**Goal:** compare prose and derivations, not only code.

Planned work:

- compare all `docs/*.md`, `MILESTONES.md`, `EXPERIMENTS.md`, READMEs, and substantial comments against external READMEs/documentation;
- compare Loihi arithmetic/equation statements against the Davies/Lin and other actual sources used;
- classify verbatim quote, close paraphrase, standard technical fact, independently worded synthesis, and uncited source-derived claim;
- add citations where claims clearly depend on external publications;
- rewrite any close paraphrase that is unnecessarily source-shaped.

The static-weight derivation (Finding C-002) is a priority in this phase.

## Phase 5 — License and attribution closure

Planned work:

- determine whether any third-party source is actually incorporated rather than merely called/fetched;
- add `THIRD_PARTY_NOTICES.md` if appropriate;
- preserve required notices for any incorporated Apache/MIT material;
- decide the thesis repository's own license;
- record any required vendor-source attributions.

## Phase 6 — Thesis-submission provenance review

Before thesis submission:

- rerun the audit against the final repository state;
- audit the actual thesis manuscript separately from repository documentation;
- verify all external technical claims have appropriate citations;
- check institutional AI-use/disclosure requirements;
- resolve all `INVESTIGATE` / `REMEDIATE` findings;
- freeze a final audit summary with commit hash and date.

---

# 10. Audit log

## 2026-09-11 — Phase 1 opened

Completed:

- pinned the exact Catalyst N1 and Brian2Loihi comparison sources already used by M13;
- confirmed external licenses from the frozen project manifest/source repositories;
- reviewed repository chronology around M11/M12/M13;
- compared the M12 baseline against current `main` for post-Catalyst production-core changes;
- manually compared the project Python neuron transition with Brian2Loihi's neuron implementation;
- manually compared the project static-weight encoder with Brian2Loihi's weight calculation;
- manually compared the project HLS neuron implementation with Catalyst's standalone LIF RTL;
- manually compared the project integrated/Phase-B RTL architecture with Catalyst `scalable_core_v2.v`;
- reviewed the project Catalyst audit-only testbench and Brian2Loihi adapter for intentional external-interface reuse;
- performed a preliminary M13 documentation/source-language spot check;
- recorded audit limitations and next phases.

Current result: **no production-core plagiarism finding; one priority citation/provenance-sensitive implementation area (`weights.py`); documentation-wide and publication-wide audit still incomplete.**

---

## Maintenance rule

This file should be updated whenever:

- a new external source is identified;
- a new comparison phase is completed;
- a suspicious similarity is found or resolved;
- copied/adapted material is attributed or rewritten;
- licensing/notice status changes;
- the final thesis manuscript becomes available for audit.

A prior CLEAR result applies only to the file/version and comparison boundary recorded at the time. Material changes should trigger re-review.