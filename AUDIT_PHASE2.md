# Thesis Originality, Provenance, and Source-Use Audit — Phase 2

**Status:** Complete for the boundaries listed below; broader audit remains active  
**Audit date:** 2026-09-13  
**Repository:** `Xtimetraveler-Prime/Thesis`  
**Parent audit:** `AUDIT.md`  
**Phase:** Phase 2 — source provenance, equation provenance, tool/vendor material, and pre-history limits

## Executive result

### PLAGIARISM — REMEDIATE IMMEDIATELY

**NONE FOUND IN THE PHASE-2 BOUNDARIES AUDITED.**

This statement is intentionally narrow. It means Phase 2 did not identify a project file that appears to contain substantial verbatim or mechanically translated source code, distinctive comments/prose, or implementation structure copied from Brian2Loihi, Catalyst N1, or the sampled Vivado/tooling material without attribution. It does **not** mean every file in the repository or the eventual thesis manuscript has been exhaustively cleared.

Two issues do require remediation or documentation before thesis submission:

1. **A-001 — REMEDIATE ATTRIBUTION:** the exact static-weight transformation implemented in `weights.py` is directly described in the Brian2Loihi publication by Michaelis et al. (2022). The implementation appears independent, but the published source should be cited wherever the thesis presents this arithmetic as an externally derived Loihi/Brian2Loihi behavior.
2. **P-002 — PROVENANCE GAP / MONITOR:** the initial Python implementation first enters this repository in one bulk `file copy` commit. The code inspected is structurally independent of Brian2Loihi, but Git history cannot prove how the pre-import files were authored before that commit. This is a provenance limitation, not evidence of plagiarism.

A third documentation issue is lower severity but should be cleaned up:

3. **A-002 — REMEDIATE ATTRIBUTION BEFORE MANUSCRIPT:** internal project specifications state several externally derived Loihi facts (for example the 24-bit current/voltage state and 12-bit decay-scale context) without inline scholarly citations. Those statements should be cited when reused in thesis prose, and adding citations to the engineering docs would improve the provenance record.

---

# 1. Sources compared in Phase 2

## 1.1 Project source

The following project files or history records were directly reviewed:

- `Neuromorphic Digital Twin/src/neuromorphic_twin/weights.py`
- `Neuromorphic Digital Twin/src/neuromorphic_twin/arithmetic.py`
- `Neuromorphic Digital Twin/src/neuromorphic_twin/core.py`
- `Neuromorphic Digital Twin/src/neuromorphic_twin/fpga_weight_storage.py`
- `Neuromorphic Digital Twin/src/neuromorphic_twin/comparison/weight_conformance.py`
- `Neuromorphic Digital Twin/rtl/core_v1/m08_weight_decoder_v1.sv`
- `Neuromorphic Digital Twin/rtl/core_v1/integrated_core_controller_bd_v1.v`
- `Neuromorphic Digital Twin/hls/core_v1/vivado/create_m11_4_project.tcl`
- `Neuromorphic Digital Twin/docs/FPGA_WEIGHT_STORAGE.md`
- `Neuromorphic Digital Twin/docs/CORE_SPECIFICATION.md`
- `MILESTONES.md`
- commit `6f01889b99f6f651a0bae044aaabf108deb6b717` (`file copy`)
- its parent, `d1b93502ce8d458112205fad78997eb14e3e86e1`
- commit `b00467b89160a9e085f5e5d80622b1940682b463` (`Implement M08 static weight encoder and exhaustive validation`)

## 1.2 Brian2Loihi executable source

Frozen comparison source remains:

- repository: `sagacitysite/brian2_loihi`
- commit: `d54676cb113e48dc886615a0b589bb0e4bccbca4`
- license: MIT

Phase 2 directly compared against:

- `loihi_synapses.py`, especially weight precision, weight limit, no-learning weight equations, and `calcActualWeights()`;
- `loihi_neuron_group.py` from the Phase-1 review;
- `loihi_network.py`, including its Brian2 `Network` subclassing, registered state updaters, one-millisecond clock, and reordered Brian scheduler.

The frozen commit predates this thesis repository work and is therefore a meaningful external source for provenance analysis.

## 1.3 Published Brian2Loihi source

A publication that should be added explicitly to the project/thesis provenance record is:

Carlo Michaelis, Andrew B. Lehr, Winfried Oed, and Christian Tetzlaff, **“Brian2Loihi: An emulator for the neuromorphic chip Loihi using the spiking neural network simulator Brian”**, *Frontiers in Neuroinformatics*, vol. 16, 2022, article 1015624. DOI: `10.3389/fninf.2022.1015624`.

This paper is particularly important because its static-weight section directly documents the operations that initially appeared potentially close to Brian2Loihi source code: sign mode, configured precision, truncation toward zero, exponent scaling, 21-bit clipping, and final six-bit alignment.

## 1.4 Catalyst N1 and vendor/tool material

Phase 2 retained the Phase-1 Catalyst pin:

- repository: `catalyst-neuromorphic/catalyst-n1`
- commit: `1806bb4b4114d7671e5648fa75b7b83b3a8d5543`
- license: Apache-2.0

Phase 2 also reviewed representative project Vivado Tcl and a project block-design wrapper for signs that generated/vendor example code had been copied into authored RTL or scripts.

---

# 2. Weight arithmetic provenance resolved

## 2.1 Why `weights.py` was the highest-risk Phase-2 item

Phase 1 marked `weights.py` as `MONITOR` because its high-level arithmetic necessarily resembles Brian2Loihi `calcActualWeights()`:

- determine weight precision from `num_weight_bits` and sign mode;
- truncate a requested mantissa to that precision;
- scale using a configured exponent;
- align the effective value to a multiple of 64;
- clip to the effective signed range.

If that operation sequence were only discoverable by reading Brian2Loihi source, a source-code derivation concern would remain. Phase 2 therefore traced the algorithm to the publication rather than comparing code alone.

## 2.2 Published support

Michaelis et al. explicitly describe the relevant static-weight behavior in the paper’s weight section. The publication states the weight-exponent range, the three sign modes, the dependence of precision on configured weight bits/sign mode, mantissa rounding toward zero for initialization, exponent scaling, the 21-bit effective limit, and the final alignment behavior.

That substantially changes the provenance assessment: the shared algorithmic sequence is a published behavioral specification, not a distinctive implementation sequence that can only have come from `loihi_synapses.py`.

## 2.3 Project implementation vs. Brian2Loihi implementation

Project `weights.py` expresses the rule through:

- `WeightSignMode` enum;
- immutable `WeightFormat`;
- immutable `StaticWeightEncoding` retaining requested, quantized, pre-clip, final, and clipping state;
- scalar integer-only helpers;
- explicit toward-zero quantization;
- explicit FPGA-oriented traceability.

Brian2Loihi `loihi_synapses.py` expresses the same behavioral rule inside a Brian2 `Synapses` subclass using NumPy arrays, simulator state variables, private precision/limit helpers, and Brian2 equation strings.

The implementations therefore share required mathematics but not distinctive program structure.

### Finding C-002A — CLEAR AT SOURCE-CODE LEVEL

No evidence was found that `weights.py` is copied or mechanically translated from Brian2Loihi source. The similarity is explained by both implementations realizing the same published behavior.

### Finding A-001 — REMEDIATE ATTRIBUTION

The current project documentation says the encoder implements a “published static-weight contract,” but the most directly relevant publication should be named explicitly in the thesis and preferably in the engineering provenance documentation.

**Required remediation before thesis submission:** cite Michaelis et al. (2022), DOI `10.3389/fninf.2022.1015624`, when presenting or deriving the static-weight precision/quantization/exponent/clipping/alignment rules. If the thesis distinguishes Intel-published behavior from emulator interpretation, label the paper as a Brian2Loihi interpretation/description rather than silently elevating it to undocumented Intel microarchitecture.

This is an attribution issue, **not a finding of plagiarism**.

---

# 3. Weight HDL and storage architecture

## 3.1 `m08_weight_decoder_v1.sv`

The RTL decoder reconstructs the project’s frozen M08 format from a project-specific 16-bit format word and 32-bit synapse word. It performs sign-mode validation, project fault reporting, toward-zero mantissa quantization, exponent shifting, six-bit alignment, and clipping.

The HDL is not a transliteration of Brian2Loihi Python source. Its inputs, packed fields, fault interface, intermediate signals, and output contract are specific to this project’s M08/M11 hardware path.

### Finding C-004 — CLEAR

The behavioral mathematics is externally derived, but the HDL implementation is an independent hardware realization of the project’s already frozen encoder/storage contract.

## 3.2 `fpga_weight_storage.py` and `FPGA_WEIGHT_STORAGE.md`

The project defines its own storage schema:

- 16-bit shared weight-format entries;
- 32-bit synapse records;
- a 4-bit project format index;
- 16-bit target-neuron field;
- 9-bit requested mantissa;
- reserved-bit rules;
- CSR-style axon row pointers;
- explicit schema identifier `neuromorphic-twin-fpga-weight-storage-v1`.

The documentation explicitly says this is a **project-specific Loihi-inspired storage profile** and not a claim about Intel Loihi’s undocumented physical SRAM layout.

### Finding C-005 — CLEAR

No source-copying concern was identified. This is a project architecture built to transport the validated weight semantics into FPGA memories; it should continue to be described as project-specific.

---

# 4. Arithmetic helper provenance

Project `arithmetic.py` implements `round_away_from_zero()` with integer arithmetic:

- reject a non-positive denominator;
- compute a ceil-like magnitude using `(abs(numerator) + denominator - 1) // denominator`;
- restore the sign;
- separately define project overflow modes (`NONE`, `SATURATE`, `WRAP`).

Brian2Loihi represents its decay rounding through simulator expressions based on sign and `ceil(abs(...))` inside Brian2 equations. The resulting behavior overlaps, but the code expression, abstraction boundary, and implementation role are different.

### Finding C-006 — CLEAR

The project arithmetic helper is an independent integer implementation of a mathematical rounding rule. No distinctive Brian2Loihi source expression or surrounding simulator structure is reproduced.

**Attribution note:** when the thesis claims that this rounding rule models a particular Loihi/Brian2Loihi behavior, that claim needs a citation even though the helper code itself is independent.

---

# 5. Whole-core Python architecture vs. Brian2Loihi

Project `core.py` implements a project-owned `NeuromorphicCore` with:

- ordinary Python collections;
- explicit structure-of-arrays current/voltage/refractory state;
- explicit axon-to-synapse mapping;
- explicit pending recurrent events;
- a deterministic project tick function;
- explicit trace construction;
- calls to the project `step_neuron()` function.

Pinned Brian2Loihi `loihi_network.py` instead subclasses Brian2 `Network`, registers Brian2 `ExplicitStateUpdater` methods, changes `defaultclock.dt`, reorders the Brian2 scheduler, and delegates network execution to Brian2.

These are fundamentally different software architectures.

### Finding C-007 — CLEAR

No copying or mechanical translation was identified between the project core orchestration and Brian2Loihi’s network layer.

---

# 6. Conformance code is comparison infrastructure, not copied implementation

`comparison/weight_conformance.py` deliberately names Brian2Loihi and calls the project’s generic Brian2Loihi backend because its purpose is differential testing. It constructs project `Synapse.encoded(...)` scenarios, runs the project candidate and external reference, and compares effective weights/traces.

External names in this file are therefore expected interface references. The file does not embed Brian2Loihi’s weight implementation; the external package performs the reference computation at runtime.

### Finding C-008 — CLEAR / EXPLICIT EXTERNAL INTERFACE USE

This is an example of proper separation: external behavior is invoked for validation rather than copied into the candidate implementation.

---

# 7. Vivado and AMD/Xilinx-facing material

## 7.1 `create_m11_4_project.tcl`

The reviewed Tcl script is a concise project-recreation flow around the packaged `neuron_step_v1` IP. It uses ordinary Vivado commands such as `create_project`, `set_property`, `update_ip_catalog`, `create_bd_design`, `create_bd_cell`, `make_bd_*_external`, `validate_bd_design`, `generate_target`, and `make_wrapper`.

The script’s comments and control flow are project-specific: they describe the M11.4 isolation boundary, why the HLS control interface is externalized, and why secondary generated Tcl snapshots are intentionally not checked in.

## 7.2 `integrated_core_controller_bd_v1.v`

The reviewed Verilog wrapper is a thin module-reference boundary around `integrated_core_controller_v1`. It contains Xilinx `X_INTERFACE_INFO` / `X_INTERFACE_PARAMETER` attributes so Vivado recognizes the clock/reset interface. Those strings are vendor-defined metadata/interface syntax, not copied neuromorphic logic.

### Finding C-009 — CLEAR

No vendor example or generated algorithmic implementation was identified in these representative files. Standard Vivado command names, VLNV/interface strings, and interface attributes are not originality concerns by themselves.

**Future audit note:** Phase 3 should still sample the remaining Vivado scripts/wrappers and flag any file that contains a vendor copyright banner or unmistakable generated-example body. Such a file may be perfectly lawful to include, but it should be classified as generated/third-party rather than authored thesis logic.

---

# 8. Documentation attribution review

`CORE_SPECIFICATION.md` is predominantly a project-defined normative specification. It clearly distinguishes project-specific choices, including the FPGA-v1 saturation rule, from claims about undocumented Intel behavior.

However, its opening profile rationale states externally derived technical facts about published Loihi precision/decay representation without inline references in that engineering document.

### Finding A-002 — REMEDIATE ATTRIBUTION BEFORE MANUSCRIPT

This is **not** a plagiarism finding. The wording inspected is project-specific and the document is an internal engineering contract. But external technical facts must be cited when they appear in the thesis manuscript, and adding citations to the project spec would make the research provenance more defensible.

**Recommended remediation:** for each externally derived numerical/behavioral assertion in the thesis—state width, decay scaling, threshold scaling, weight ranges/precision/sign modes, etc.—attach the appropriate primary Intel publication or clearly labeled emulator/paper source. Do not cite Brian2Loihi as proof of undocumented Intel details.

---

# 9. Git-history provenance limitation

## 9.1 Initial import

The first substantial implementation commit in this repository is:

`6f01889b99f6f651a0bae044aaabf108deb6b717` — commit message: `file copy`.

It adds approximately 2,270 lines in one bulk import. Its parent `d1b93502ce8d458112205fad78997eb14e3e86e1` is essentially an initial repository shell rather than a line-by-line development history of the Python model.

This means Git history inside this repository cannot establish how the initial Python files were authored before they were copied into the repository.

### Finding P-002 — MONITOR / PROVENANCE GAP

The bulk import is **not evidence of plagiarism**. Direct source comparison in Phases 1 and 2 finds the project neuron/core architecture materially different from Brian2Loihi. The issue is evidentiary: this repository cannot provide a pre-import commit trail for those initial files.

**Recommended remediation/evidence preservation:**

- retain the project conversation/development notes that predate the import;
- retain any earlier local repository, archive, patch, notebook, or timestamped copy if one exists;
- in the thesis/research record, describe Brian2Loihi as a behavioral reference and the project Python model as an independently structured candidate;
- do not claim that Git proves independent authorship before `6f01889...`, because it does not.

No source rewrite is indicated by this finding.

## 9.2 M08 weight implementation history

The weight encoder has a much stronger repository provenance record. Commit:

`b00467b89160a9e085f5e5d80622b1940682b463` — `Implement M08 static weight encoder and exhaustive validation`

records an integer-only implementation plus exhaustive validation. The milestone text explicitly states the design intention to implement the published static-weight behavior independently rather than copy Brian2Loihi source. The source comparison is consistent with that stated intention.

The history statement is supporting evidence, not proof by itself; the stronger evidence is the combination of the published equation source and materially different code structure.

---

# 10. Search-tool limitation discovered during Phase 2

An attempted repository-wide source-signature scan using GitHub code search produced no hits even for terms known to exist in the repository, including `Brian2Loihi`. Therefore negative GitHub code-search results are **not accepted as audit evidence** in this phase.

This corrects an initially tempting but invalid inference: “search returned zero” cannot be used to claim that a token or phrase does not exist in the repository when the index demonstrably misses known material.

Phase-2 `CLEAR` findings instead rely on direct file reads, direct source-to-source comparison, repository-tree inspection, and commit history.

### Finding M-001 — AUDIT METHOD CORRECTION

Repository-wide automated token/n-gram similarity remains **NOT YET COMPLETED**. It should be run from complete local checkouts of the thesis repository and each pinned external source when a runtime with normal Git/network access is available. The resulting script/tool versions and thresholds should be committed alongside the report so the scan is reproducible.

---

# 11. License/attribution observations

## 11.1 Brian2Loihi

The pinned Brian2Loihi repository uses the MIT license and requires preservation of its copyright and permission notice in copies or substantial portions of its software.

Phase 2 did not identify a substantial portion of Brian2Loihi source copied into the thesis repository. Therefore no file-level MIT notice remediation is indicated by the reviewed project code. If later audit phases discover copied source, license compliance and academic attribution must both be handled; satisfying the MIT license alone would not make unattributed academic copying acceptable.

## 11.2 Catalyst N1

The pinned Catalyst N1 source is Apache-2.0 and carries Catalyst/Henry Arthur Shulayev Barnes copyright notices. Apache redistribution requirements matter if Catalyst source or a derivative is distributed.

The reviewed thesis M13 tooling **invokes** the pinned Catalyst checkout and uses audit-only interfaces/testbenches; the project production core remains separate. Phase 1/2 did not identify copied Catalyst production RTL embedded in the project’s production implementation.

If any Catalyst source is later vendored into this repository, its license/NOTICE handling must be audited separately.

---

# 12. Phase-2 finding register

| ID | Classification | Subject | Result / action |
|---|---|---|---|
| C-002A | **CLEAR** | `weights.py` vs Brian2Loihi source | Same published behavior, materially independent implementation. |
| A-001 | **REMEDIATE ATTRIBUTION** | Static-weight behavior | Cite Michaelis et al. 2022, DOI `10.3389/fninf.2022.1015624`, wherever the behavior is derived/presented. |
| C-004 | **CLEAR** | `m08_weight_decoder_v1.sv` | Independent HDL realization of frozen project contract. |
| C-005 | **CLEAR** | FPGA weight storage | Project-specific schema; explicitly not claimed as Intel SRAM layout. |
| C-006 | **CLEAR** | `arithmetic.py` | Independent integer implementation of shared mathematical rule. |
| C-007 | **CLEAR** | `core.py` vs `loihi_network.py` | Fundamentally different architecture/framework. |
| C-008 | **CLEAR** | weight conformance code | External backend is invoked, not reimplemented by copying. |
| C-009 | **CLEAR** | sampled Vivado Tcl/wrapper | Project-specific orchestration plus standard vendor commands/metadata. |
| A-002 | **REMEDIATE ATTRIBUTION BEFORE MANUSCRIPT** | External Loihi facts in project specs/thesis prose | Add explicit scholarly citations. Not a copying finding. |
| P-002 | **MONITOR / PROVENANCE GAP** | initial `file copy` import | Pre-import authorship history is not present in this Git repo; preserve other evidence. |
| M-001 | **METHOD LIMITATION** | repository-wide token scan | GitHub code-search negatives are unreliable; automated local scan remains pending. |

### Clear plagiarism finding count in Phase 2: **0**

### Attribution/provenance remediation items in Phase 2: **2 primary + 1 provenance gap**

The distinction is important. A missing citation for an externally derived technical rule should be fixed, but it should not be mislabeled as copied source code when direct comparison does not support that accusation.

---

# 13. Escalation rule for future phases

If a future comparison finds a likely copied artifact, the audit entry will begin with exactly:

## `PLAGIARISM — REMEDIATE IMMEDIATELY`

and will record all of the following before remediation:

1. thesis/project file and exact region;
2. external source, immutable commit/version, and exact region;
3. the distinctive overlap (code structure, identifiers, comments, prose, or ordering);
4. whether the overlap is verbatim, lightly edited, or mechanically translated;
5. applicable source license;
6. whether attribution already exists;
7. Git chronology showing when the material entered the project;
8. recommended remediation;
9. remediation commit; and
10. validation/tests rerun after the change.

For production code, the preferred remediation will normally be a clean reimplementation from a cited public specification or independently written behavioral contract rather than cosmetic renaming. Merely changing identifiers is not sufficient remediation for copied implementation structure.

---

# 14. Phase-3 priority list

The next audit phase should concentrate on areas not yet exhaustively cleared:

1. **Full prose/manuscript review.** Compare eventual thesis prose, captions, architecture descriptions, and equations against Davies et al., Lin et al., Michaelis et al., Catalyst publications/docs, AMD documentation, and any other cited source. This is the most important remaining academic-integrity boundary.
2. **Repository-wide local similarity scan.** Clone exact pins and run reproducible token/n-gram or clone-detection analysis across Python, C/C++, Verilog/SystemVerilog, Tcl, shell, and Markdown; manually adjudicate hits.
3. **Remaining vendor/tool scripts.** Sample all checked-in Vivado/Vitis Tcl, wrappers, constraints, and generated-looking files for vendor copyright headers or recognizable generated templates; classify generated/third-party files separately from authored code.
4. **Tests and examples.** Compare unusual directed test vectors, comments, and helper structure against Brian2Loihi/Catalyst tests to make sure external test code was not copied while building conformance cases.
5. **References and claims matrix.** Build a thesis-facing table that maps every externally derived numerical constant/equation/behavior to the source that supports it, while marking project-specific design choices separately.
6. **Initial-import evidence.** Locate any earlier working directory/repository/archive or project conversation evidence that predates `6f01889...` and preserve it as provenance evidence if available.

Until those tasks are complete, the correct repository-level statement is:

> The audited production-core boundaries show independent implementation and no identified plagiarism, with specific citation/provenance issues documented for remediation; the complete repository and final manuscript have not yet been exhaustively cleared.
