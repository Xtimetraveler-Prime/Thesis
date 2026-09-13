# Thesis Originality, Provenance, and Source-Use Audit — Phase 3

**Status:** Complete for the sampled test/tool/prose boundaries below; broader audit remains active  
**Audit date:** 2026-09-13  
**Repository:** `Xtimetraveler-Prime/Thesis`  
**Parent records:** `AUDIT.md`, `AUDIT_PHASE2.md`  
**Phase:** Phase 3 — test code, Vivado integration shells, external-interface testbenches, and README prose

## Executive result

### PLAGIARISM — REMEDIATE IMMEDIATELY

**NONE FOUND IN THE PHASE-3 BOUNDARIES AUDITED.**

The material reviewed in this phase contains expected vendor API names, Catalyst port/interface names in an explicitly Catalyst-facing audit testbench, and generic HDL/testbench idioms. None of the sampled files show a distinctive third-party implementation or explanatory passage copied into project-authored material without attribution.

This phase does not close the final thesis-manuscript audit or the still-pending repository-wide automated similarity scan.

---

# 1. Sources compared

## Project material

- `Neuromorphic Digital Twin/README.md`
- `Neuromorphic Digital Twin/tests/` directory inventory
- `Neuromorphic Digital Twin/tests/test_m11_5_3_integrated.py`
- `Neuromorphic Digital Twin/rtl/core_v1/tb/tb_neuromorphic_twin_m11_5_3.sv`
- `Neuromorphic Digital Twin/rtl/core_v1/vivado/create_m11_5_3_project.tcl`
- `Neuromorphic Digital Twin/rtl/core_v1/integrated_core_controller_bd_v1.v`
- `Neuromorphic Digital Twin/rtl/core_v1/m11_6_smoke_controller_bd_v1.v`
- `Neuromorphic Digital Twin/rtl/core_v1/m12_1_capture_controller_bd_v1.v`
- `Neuromorphic Digital Twin/rtl/m13_4/tb_m13_4_catalyst_cuba.sv`

## Brian2Loihi material

Pinned source remains `sagacitysite/brian2_loihi` at commit `d54676cb113e48dc886615a0b589bb0e4bccbca4`.

Direct comparison material:

- `README.md`
- complete pinned repository tree from the previous phases

The pinned Brian2Loihi tree contains its package implementation files but no corresponding Python pytest suite from which the project’s `tests/` tree could have been copied.

## Catalyst material

Pinned source remains `catalyst-neuromorphic/catalyst-n1` at commit `1806bb4b4114d7671e5648fa75b7b83b3a8d5543`.

Direct comparison material:

- Catalyst `tb/` inventory
- `tb/tb_isolate.v` as a representative native Catalyst testbench
- previously audited `rtl/scalable_core_v2.v` interface

---

# 2. Project README vs. Brian2Loihi README

The project README is organized around a project-specific verification architecture:

- one `ComparisonScenario`;
- independent Python and Brian2Loihi backends;
- an exact trace comparator;
- backend-neutral trace/report artifacts;
- an explicit future path to RTL simulation and physical FPGA traces.

Brian2Loihi’s README is instead package documentation. It describes extending Brian2 classes, installation, parameter lists for `LoihiNetwork`, `LoihiNeuronGroup`, `LoihiSynapses`, monitors/generators, and a usage example.

There is natural vocabulary overlap (`Loihi`, `Brian2`, neuron, synapse, decay, refractory, weight exponent), but the structure, prose, purpose, and examples are different.

### Finding P3-C001 — CLEAR

No copied README prose or distinctive documentation structure was identified between the project README and the pinned Brian2Loihi README.

The project README’s description of Brian2Loihi as an optional reference backend is also consistent with the architecture actually present in the code.

---

# 3. Project Python tests vs. Brian2Loihi

The project `tests/` tree is dominated by project-specific pytest verification:

- arithmetic policy tests;
- Python core behavior;
- project core specification requirements;
- encoded synapse integration;
- FPGA weight storage;
- HLS/RTL integration contracts;
- later M12/M13 evidence and comparison logic.

At the pinned Brian2Loihi commit, the external repository tree consists of the package implementation modules and README/license material; it does not expose a comparable pytest tree.

### Finding P3-C002 — CLEAR

No evidence was identified that the project pytest suite was copied from a Brian2Loihi test suite. The external pinned repository does not contain the corresponding source category, and the inspected project tests assert project-specific milestone contracts, filenames, generated-vector names, and FPGA/HLS integration behavior.

This does not eliminate the need to cite externally sourced numerical expectations in thesis prose, but it strongly separates test implementation provenance from external emulator code.

---

# 4. M11.5.3 integrated RTL testbench vs. Catalyst testbench structure

## Project testbench

`tb_neuromorphic_twin_m11_5_3.sv` is built around the project’s own integrated architecture. Its distinctive elements include:

- generated `M11_5_3I_*` vector arrays;
- project 128-bit neuron configuration words and 64-bit state words;
- separate packed format, synapse, row, external-event, and recurrent-event loaders;
- explicit project debug reads;
- project fault/phase observability;
- assertions over reset state, packed M08 accumulators, state transition, tick increment, and spike outputs.

The associated Python test (`test_m11_5_3_integrated.py`) checks that those vectors are generated reproducibly from the Python model and that the Vivado flow connects the real packaged HLS interface.

## Sampled Catalyst testbench

Catalyst `tb/tb_isolate.v` carries the Catalyst copyright/Apache header, instantiates `scalable_core_v2`, ties off its Catalyst-specific learning/graded/dendritic/noise/parameter ports, toggles reset, and checks a simple idle condition.

The two testbenches share only generic HDL idioms such as a 10 ns clock and DUT instantiation. Their DUTs, data preload strategy, tasks, assertions, output format, and verification purpose are materially different.

### Finding P3-C003 — CLEAR

No copied Catalyst testbench implementation was identified in the project’s M11.5.3 integration testbench.

---

# 5. Project Vivado Tcl vs. vendor/generated scripts

`create_m11_5_3_project.tcl` is a project-specific reproducibility script. It:

- accepts explicit project source/IP paths as arguments;
- validates required files;
- defines project helper procedures (`expose_scalar_pin`, `connect_verified_pair`);
- creates the project’s module-reference controller and packaged HLS cell;
- explicitly verifies handshake/scalar connectivity;
- builds project external ports;
- adds the project testbench and generated vectors;
- runs the project behavioral simulation.

The script uses standard Vivado Tcl commands. Those command names and property names are vendor APIs, not authored implementation content owned by this project or a plagiarism signal.

The script does not carry a Xilinx/AMD copyright banner and does not read like a generated `write_project_tcl` dump. Its error messages, helper names, and comments are milestone/project specific.

### Finding P3-C004 — CLEAR

No evidence of a copied AMD/Xilinx example or generated vendor script was identified in the sampled Tcl flow.

Future files that do carry vendor copyright or generated-template banners should be classified as generated/third-party rather than claimed as original authored logic, even if their inclusion is licensed and appropriate.

---

# 6. Vivado Module Reference wrappers

The sampled wrappers:

- `integrated_core_controller_bd_v1.v`
- `m11_6_smoke_controller_bd_v1.v`
- `m12_1_capture_controller_bd_v1.v`

are thin project shells that expose the project SystemVerilog modules to Vivado Module Reference. They contain Xilinx-recognized interface attributes such as `X_INTERFACE_INFO` and `X_INTERFACE_PARAMETER` and then wire project-specific signals to the corresponding project module.

The later wrappers also contain project-specific physical-debug witnesses (for example heartbeat and sticky start-detection registers), which are part of the M11/M12 hardware validation strategy.

### Finding P3-C005 — CLEAR

Vendor-defined attribute strings and interface metadata are necessary interoperability syntax, not copied algorithmic code. The surrounding wrappers are project-specific and show no third-party copyright/provenance marker indicating that they were vendor-generated source.

---

# 7. M13 Catalyst audit-only testbench

`rtl/m13_4/tb_m13_4_catalyst_cuba.sv` deserves a separate classification because it deliberately instantiates the external Catalyst `scalable_core_v2` module.

The file explicitly labels itself an **audit-only testbench for pinned Catalyst `scalable_core_v2`**. It therefore reproduces Catalyst’s public module and port names as required to instantiate the external DUT. It also programs Catalyst parameter IDs and reads Catalyst probe state IDs because its sole purpose is to measure the pinned Catalyst implementation.

Its test logic is project audit logic:

- two-neuron positive/negative probes;
- `init_inputs`, `reset_core`, `set_param`, `run_tick`, `read_probe`, and `emit_tick` helpers;
- normalized `M13_4_CUBA|...` output lines consumed by project comparison tooling;
- probe values selected for the project M13 discrepancy questions.

A sampled native Catalyst testbench (`tb_isolate.v`) has a different purpose and implementation, and includes Catalyst’s copyright/license header. The project M13 audit testbench does not reproduce that body or header.

### Finding P3-C006 — CLEAR / EXPLICIT EXTERNAL INTERFACE USE

Use of Catalyst module/port names is an attributed interoperability requirement, not plagiarism. No sampled Catalyst testbench body was found copied into the project audit testbench.

**Boundary rule:** this file should continue to remain isolated under the M13 comparison/audit path and should not be presented as evidence that the project independently invented the Catalyst interface. It is intentionally an adapter/test harness for external code.

---

# 8. Third-party copyright-header check in sampled material

The sampled project-authored Python, RTL wrappers, testbench, and Tcl files do not carry a Brian2Loihi, Catalyst, Intel, AMD, or Xilinx copyright header.

The sampled external Catalyst source does carry an Apache-2.0/Catalyst copyright header. This difference makes it easier to distinguish native Catalyst code from the project’s audit harness in the reviewed boundary.

### Finding P3-L001 — NO LICENSE REMEDIATION TRIGGERED BY SAMPLED FILES

No sampled project file appears to contain a substantial third-party code body that would obviously require preservation of a third-party source-file copyright header.

This is not a repository-wide license clearance; it is a result for the files directly inspected.

---

# 9. What remains the highest plagiarism risk

After Phases 1–3, the remaining highest-risk area is **not the production computational code**. It is the eventual academic prose/equation presentation.

The project has accumulated many internal engineering documents that intentionally summarize external architectures and published behavior. Even when those summaries are independently worded, the final thesis needs disciplined citation so that:

- published Loihi facts are attributed to the appropriate Intel/published source;
- Brian2Loihi-specific interpretations are attributed to Michaelis et al. / Brian2Loihi rather than described as undocumented Intel fact;
- Catalyst-specific implementation observations are attributed to the pinned Catalyst paper/repository;
- project-specific FPGA design decisions are clearly labeled as this project’s choices;
- any figures/tables derived from external material are labeled and cited.

No final thesis manuscript has been cleared by this audit phase. A manuscript-level review should happen once that text exists in a stable form.

---

# 10. Phase-3 finding register

| ID | Classification | Boundary | Result |
|---|---|---|---|
| P3-C001 | **CLEAR** | project README vs Brian2Loihi README | No distinctive copied prose/structure identified. |
| P3-C002 | **CLEAR** | project pytest suite vs Brian2Loihi | Project-specific tests; pinned external repo has no comparable pytest tree. |
| P3-C003 | **CLEAR** | M11.5.3 RTL testbench vs sampled Catalyst testbench | Different DUT boundary, stimulus architecture, tasks, and assertions. |
| P3-C004 | **CLEAR** | sampled Vivado Tcl | Project-specific orchestration using standard vendor API commands. |
| P3-C005 | **CLEAR** | sampled Module Reference wrappers | Project-specific shells; vendor interface attributes are interoperability syntax. |
| P3-C006 | **CLEAR / EXTERNAL INTERFACE USE** | M13 Catalyst audit testbench | Explicitly attributed Catalyst interface use; no sampled Catalyst testbench body copied. |
| P3-L001 | **NO REMEDIATION TRIGGER** | sampled copyright/license headers | No third-party source body identified in sampled project files. |

### Clear plagiarism finding count in Phase 3: **0**

### New plagiarism remediation items in Phase 3: **0**

The citation/provenance remediation items from Phase 2 remain open.

---

# 11. Next audit actions

The most valuable next steps are:

1. perform a final-manuscript prose/equation/source audit once the thesis text is present;
2. run repository-wide clone/token similarity tools from full local checkouts when network/runtime access permits;
3. finish a machine-readable source/claim matrix for numerical constants and externally derived behavior;
4. inspect the remaining Vivado/Vitis scripts for explicit generated/vendor banners, treating such material as third-party/generated if found;
5. preserve any pre-`6f01889...` local development artifacts that can strengthen the initial Python model’s provenance record.

Until then, the defensible conclusion remains:

> The directly audited production code, test infrastructure, representative Vivado integration material, and README prose show independent project structure with no identified plagiarism. Specific citation/provenance issues remain documented for remediation, and the final manuscript plus an automated whole-repository clone scan are still pending.
