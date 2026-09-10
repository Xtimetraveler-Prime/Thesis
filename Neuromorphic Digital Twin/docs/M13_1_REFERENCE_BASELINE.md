# M13.1 External Reference Baseline and Comparison Methodology

## Status

**Complete — M13.1 pass boundary achieved on 2026-09-08 and independently validated locally on 2026-09-09.** Development and closure evidence are on branch `agent/m13-1-pin-catalyst-methodology` pending merge.

M13.1 begins only after M12 closes the software-to-physical validation ladder for this project's FPGA-v1 digital twin. The M12-closed project is therefore the implementation **under audit**, not an implementation waiting to be rewritten to match Catalyst N1. M13.1 freezes the external sources, terminology, evidence hierarchy, and discrepancy policy before M13.2 inspects architectural differences in detail.

The machine-readable authority for the pins below is:

```text
references/m13_1_reference_manifest.json
schema: neuromorphic-twin-m13-reference-manifest-v1
```

## Core methodological rule

M13 uses four separate evidence columns:

```text
published Loihi material
        |
        +-------- Brian2Loihi interpretation
        |
        +-------- this project's M12-closed Python/FPGA implementation
        |
        +-------- Catalyst N1 implementation/interpretation
```

These columns must not be collapsed into one presumed ground truth.

Published Loihi sources are the primary authority for claims about Loihi itself. Brian2Loihi and Catalyst N1 are independently developed implementations or interpretations that can increase confidence, expose ambiguity, or reveal useful architectural alternatives, but agreement between them cannot establish undocumented Intel microarchitecture. This project's Python/FPGA pair remains frozen at the M12 closure baseline unless a later M13 discrepancy meets the explicit class-A or class-B change-control threshold.

## Frozen project baseline

The implementation under audit is pinned to the M12 closure merge:

```text
repository: Xtimetraveler-Prime/Thesis
branch:     main
commit:     80a502ec6dfc4c8d61372089b08c9a584ad65f85
state:      M12 Complete
```

This pin matters because later M13 work may add comparison adapters, Catalyst-native runners, normalization code, and reports. Those additions must not make it ambiguous which computational behavior originally passed the physical M12 evidence.

The normative project behavior remains the frozen M10 FPGA-v1 contract as realized by the independent Python model and physically validated FPGA implementation through M12. M13 comparison code is non-normative unless a discrepancy is formally adjudicated and the required M12 revalidation is completed.

## Frozen Catalyst N1 source

### Selected pin

M13 uses:

```text
repository:     catalyst-neuromorphic/catalyst-n1
primary tag:    v2.3-paper
equivalent tag: n1-final
commit:         1806bb4b4114d7671e5648fa75b7b83b3a8d5543
commit date:    2026-03-15T09:01:18Z
commit message: Open source release under Apache 2.0
license:        Apache-2.0
```

Both `v2.3-paper` and `n1-final` are lightweight Git tags whose refs resolve directly to the same commit. No GitHub Release object exists for the repository, so the tag+commit pair is the stable software pin. M13.1 verifies both tag object types as `commit`, not annotated tag objects.

The `v2.3-paper` tag is preferred as the human-facing identifier because it explicitly ties the frozen code to the paper-era N1 baseline. The full commit SHA remains the normative identifier because branch names and tag labels are less precise than an immutable commit object.

### Why current `master` is not the comparison baseline

At the time M13.1 was frozen, Catalyst N1 `master` had advanced to a later commit. M13 intentionally does not compare against a moving branch. Later documentation or bug fixes on `master` may be consulted as clearly labeled supplemental evidence, but they do not silently replace `v2.3-paper` in M13 results.

If a later Catalyst commit fixes a defect that materially affects an M13 comparison, the thesis should preserve the original pinned result and explicitly document a second comparison against the newer commit rather than retroactively moving the pin.

## Catalyst N1 paper and documentation set

The frozen Catalyst publication reference is:

```text
Henry Arthur Shulayev Barnes
Catalyst N1: A 131K-Neuron Open Neuromorphic Processor with
Programmable Synaptic Plasticity
DOI: 10.5281/zenodo.18727094
record: https://zenodo.org/records/18727094
```

The source-controlled Catalyst documentation/implementation boundaries most relevant to later M13 work are pinned by both repository commit and Git blob identity in the manifest. They include:

| Path | M13 role |
| --- | --- |
| `README.md` | Top-level architecture, simulator, SDK, and FPGA usage claims |
| `LICENSE` | Apache-2.0 licensing boundary |
| `rtl/scalable_core_v2.v` | Primary per-core RTL implementation source for architecture inspection |
| `run_regression.sh` | Native RTL regression definition |
| `sdk/neurocore/simulator.py` | Catalyst CPU/reference simulator implementation |
| `sdk/tests/test_simulator.py` | Direct tests of that simulator boundary |
| `sdk/setup.py` | Python/runtime dependency declaration |
| `fpga/kria/build_kria.tcl` | K26 synthesis project source |
| `fpga/kria/run_impl.tcl` | K26 place/route/report path |
| `fpga/kria/kria_neuromorphic.v` | Reduced K26 hardware wrapper |
| `fpga/f2/run_build.sh` | Explicit repository evidence for Vivado 2025.2 use on the F2 path |

This list is not a claim that these are the only Catalyst files M13 may inspect. It defines the initial reproducibility boundary. M13.2 can cite additional files at the **same pinned commit** as needed for the architectural crosswalk.

## Catalyst native simulator/testbench boundary

### RTL regression

The pinned Catalyst README documents Icarus Verilog v12+ for simulation. The native `run_regression.sh` enumerates 25 RTL testbenches and compiles them using SystemVerilog-2012 (`iverilog -g2012 -DSIMULATION`).

The script contains one portability defect unrelated to the RTL itself: its first command hard-codes the original author's WSL checkout path:

```text
/mnt/c/Users/mrwab/neuromorphic-chip
```

M13 does **not** edit the Catalyst repository to fix this. `scripts/run_m13_1_catalyst_rtl_regression.sh` reads the RTL source list and 25-testbench list directly from the pinned native script and runs the same compile language/defines from the actual checkout directory. It fails on compile errors, nonzero/timeout execution, native failure markers, missing result markers, or a changed testbench count.

This relocation is test infrastructure normalization, not an architectural modification. The Catalyst checkout must remain clean and every source blob checked by the M13 manifest must retain its pinned identity.

### CPU simulator

The pinned SDK describes `sdk/neurocore/simulator.py` as a cycle-accurate software LIF simulator matching `scalable_core_v2.v`. Its source documents a synchronous per-timestep pipeline of `DELIVER -> UPDATE -> LEARN`, with a separate event-driven asynchronous mode. The companion `sdk/tests/test_simulator.py` directly exercises neuron timing, refractory behavior, subthreshold decay, propagation, inhibition, and additional supported features.

M13.1 treats this CPU simulator as **Catalyst's reference software implementation**, not as Loihi ground truth. Later M13 behavioral comparisons must preserve both Catalyst-native outputs and any normalized representation derived from them.

### SDK runtime boundary

The pinned `sdk/setup.py` declares:

```text
package:         neurocore 1.0.0
Python:          >=3.9
numpy:           >=1.21
matplotlib:      >=3.5
pyserial:        >=3.5
optional pandas: >=1.4
```

These are Catalyst's declared minimums, not a fully locked environment. M13.1 records them as the source requirement boundary. If M13.3/M13.4 requires a long-lived Python behavioral harness, that later milestone should freeze the exact comparison environment actually used rather than pretending these lower bounds are an immutable lockfile.

## Catalyst K26 hardware boundary

The pinned repository contains a Kria-targeted implementation, which is significant because this project also uses a K26/KV260-class platform.

The pinned Catalyst wrapper records:

```text
Catalyst wrapper:      fpga/kria/kria_neuromorphic.v
Catalyst version ID:   N1 v2.3
cores:                 2
neurons/core:          256
total configured:      512 neurons
pool depth/core:       4096
host boundary:         AXI-facing wrapper
neural clock setting:  100 MHz
```

The K26 build script targets:

```text
xczu5ev-sfvc784-2-i
```

while this project has used the K26 SOM part identity:

```text
xck26-sfvc784-2LV-c
```

These identify closely related K26/ZU5EV hardware boundaries but are not textually identical Vivado target parts. M13.5 must disclose this rather than treating the two build scripts as automatically identical device configurations.

The implementation script applies a 10.000 ns clock constraint to `s_axi_aclk`, performs `opt_design`, `place_design`, `phys_opt_design`, and `route_design`, then emits timing, utilization, power, clock, and design-analysis reports.

### Important K26-flow caveat frozen at M13.1

The README presents:

```text
vivado -mode batch -source fpga/kria/build_kria.tcl
```

as the K26 build command. At the pinned commit, however, `build_kria.tcl` only launches synthesis when its mode argument is exactly `synth_only`; the default `full` path creates the project and then closes it without launching synthesis or implementation. `run_impl.tcl` separately expects the synthesis checkpoint produced by the synthesis run.

Therefore M13.1 records the strongest source-supported two-stage interpretation as:

```text
vivado -mode batch -source fpga/kria/build_kria.tcl -tclargs synth_only
vivado -mode batch -source fpga/kria/run_impl.tcl
```

This is **not yet accepted as a reproduced Catalyst hardware flow**. M13.5 will test it and will classify any required build normalization as tooling/reproduction evidence rather than quietly altering Catalyst RTL.

### Vivado version boundary

The pinned K26 Tcl files do not declare a Vivado version. A separate build script in the same pinned N1 repository, `fpga/f2/run_build.sh`, explicitly sources:

```text
/opt/Xilinx/2025.2/Vivado/settings64.sh
```

This project already uses Vivado 2025.2. Accordingly, the planned M13 Catalyst K26 reproduction environment is Vivado 2025.2 unless later evidence shows the pinned K26 flow requires something different.

That choice must be worded carefully:

- **Direct Catalyst documentation:** K26 build exists and uses the pinned Tcl/RTL files.
- **Direct Catalyst repository evidence:** the pinned F2 path explicitly uses Vivado 2025.2.
- **Project reproduction choice:** use Vivado 2025.2 for the future Catalyst K26 attempt to align both projects.
- **Not claimed:** that Catalyst's K26 Tcl itself explicitly requires Vivado 2025.2.

## Frozen Brian2Loihi reference

The existing project dependency already fixes:

```text
brian2-loihi==0.5.2
```

M13.1 resolves that package to a stable source and artifact identity:

```text
repository:       sagacitysite/brian2_loihi
tag:              v0.5.2
commit:           d54676cb113e48dc886615a0b589bb0e4bccbca4
release date:     2021-07-20
license:          MIT
PyPI wheel:       brian2_loihi-0.5.2-py3-none-any.whl
wheel SHA-256:    fc0bf66ea9e212a0c7d5003332b244fe02a47bc874382092b0bff6d83ebbd4d3
Brian2 declared:  >=2.4.2
```

The pinned source commit is particularly appropriate because its commit message records the decay-zero correction included in release 0.5.2.

Brian2Loihi remains a **separate evidence column** in M13. Earlier M03-M08 comparisons already established direct observable agreement for the supported subset used at that stage. M13.2 should link those results rather than reinterpret Brian2Loihi as synonymous with published Loihi behavior.

## Frozen published Loihi references

M13.1 begins with the same two stable publications used by the Brian2Loihi documentation and earlier project reasoning:

1. **Davies et al. (2018), _Loihi: A Neuromorphic Manycore Processor with On-Chip Learning_**, IEEE Micro 38(1), 82-99. DOI `10.1109/MM.2018.112130359`.
2. **Lin et al. (2018), _Programming Spiking Neural Networks on Intel's Loihi_**, Computer 51(3), 52-61. DOI `10.1109/MC.2018.157113521`.

The DOI is the stable identity. M13.2 may add further published Loihi sources when a feature requires stronger or more specific evidence. Adding another publication does not move any software pin and must be recorded as an extension of the source set, not an undocumented replacement.

## Evidence vocabulary frozen before comparison

Every substantive M13 crosswalk statement or discrepancy should identify the type of evidence supporting it.

### `published_documentation`

A stable paper, DOI record, or source-controlled document states the behavior or architecture directly. The statement must be attributed to that source. Documentation from Catalyst or Brian2Loihi establishes what those projects claim; only published Loihi evidence should be used as the primary source for claims about Loihi itself.

### `direct_observation`

A result obtained by executing a pinned simulator, testbench, RTL design, or physical FPGA under recorded inputs and tools. Direct observation is stronger than guessing from source structure, but it is still evidence about the implementation that was executed.

### `implementation_inference`

A conclusion drawn from reading RTL/software structure where the behavior is not explicitly documented or has not yet been isolated experimentally. These statements must remain labeled as inference until a directed observation supports them.

### `project_interpretation`

A normalization, parameter mapping, terminology choice, or architectural interpretation introduced by this thesis project. These are necessary for a fair comparison, but they must never be presented as facts copied from an external source.

## Source-authority rules

The following rules are frozen before M13.2 begins:

1. Published Loihi material is the primary authority for claims about Loihi itself.
2. Brian2Loihi and Catalyst N1 are independent implementations/interpretations, not substitute ground truth for undocumented Loihi behavior.
3. This project's M12-closed Python/FPGA pair is the implementation under audit.
4. Agreement among independent implementations can increase confidence in a shared interpretation but cannot establish undocumented physical microarchitecture.
5. Catalyst source is authoritative for what the pinned Catalyst implementation does, not for what Intel Loihi necessarily does.
6. Brian2Loihi source/behavior is authoritative for Brian2Loihi's interpretation, not automatically for all Loihi configurations.
7. Native artifacts must be preserved when normalization is later introduced so a mapping error can be distinguished from an implementation difference.

## Implementation-independence rule

M13 is an audit, not a port of Catalyst into this project.

The project computational core must not copy Catalyst:

- RTL equations or FSMs;
- simulator state-transition code;
- constants merely because Catalyst chose them;
- memory organization;
- scheduling implementation;
- routing implementation;
- learning-engine implementation.

Catalyst source **may** be inspected to:

- understand Catalyst's own architecture;
- find questions that the four-way crosswalk should ask;
- identify native parameters and trace fields;
- reproduce Catalyst's native simulation/RTL/FPGA behavior;
- diagnose why Catalyst and this project differ;
- distinguish documentation from implementation inference.

If Catalyst exposes a plausible defect in this project, the project changes only after stronger evidence and the discrepancy process below justify that change.

## Discrepancy classes frozen before behavioral testing

Every meaningful disagreement must receive at least one explicit class:

| Class | Meaning |
| --- | --- |
| A | Project implementation defect |
| B | Project interpretation/specification incomplete or inconsistent with stronger Loihi evidence |
| C | Catalyst N1 makes a different architectural choice |
| D | Brian2Loihi makes or exposes a different modeling choice |
| E | Published Loihi evidence is ambiguous or insufficient |
| F | Comparison mapping/normalization issue |
| G | Feature is unsupported or outside the project's validated subset |
| H | Test/capture/tooling defect |

A raw output mismatch is **not** itself class A.

## Change-control rule

Only sufficiently supported discrepancies classified as **A** or **B** may modify the M10/M12 computational baseline.

An A/B change requires all five steps:

1. create a minimized directed regression reproducing the issue;
2. update the applicable normative project specification/source model;
3. regenerate or update dependent HLS/RTL if behavior changes;
4. rerun every affected M12 physical conformance gate;
5. record which previous thesis claims or evidence were superseded.

Classes C-G should normally be documented as architecture, ambiguity, normalization, or scope. Class H is fixed in the test/capture/tooling layer and does not become computational evidence until the corrected test is rerun.

This policy deliberately makes preserving a well-supported difference cheaper than forcing two unrelated implementations to agree.

## What M13.1 does not do

M13.1 intentionally does **not**:

- declare a common behavioral subset;
- translate project parameters into Catalyst parameters;
- decide whether Catalyst's neuron arithmetic is closer to Loihi;
- compare native traces;
- alter the frozen FPGA-v1 neuron or routing contract;
- add Catalyst-inspired features to this project's core;
- compare resource/performance numbers;
- build or program Catalyst on the KV260;
- interpret a Catalyst discrepancy as a project defect.

Those boundaries belong to M13.2-M13.6.

## Reproducibility commands

From the project root:

```bash
cd "/home/dna/Git/Thesis/Neuromorphic Digital Twin"

# Validate the source-controlled manifest only.
PYTHONPATH=src python3 examples/validate_m13_1_reference_manifest.py

# Fetch exactly the pinned Catalyst source into the ignored build tree and
# verify commit, tags, clean status, key Git blob identities, native test list,
# and frozen K26 configuration fields.
bash scripts/fetch_m13_1_catalyst.sh

# Run the pinned native RTL regression without modifying Catalyst source.
bash scripts/run_m13_1_catalyst_rtl_regression.sh
```

Generated external source and regression products live under `build/m13_1/`, which is ignored by the thesis repository. Catalyst source is not vendored into this project's computational tree.

## M13.1 validated execution environment

The source-declared minimum requirements above are deliberately distinct from the exact environment used for the successful M13.1 closure gate. The accepted direct-observation environment on 2026-09-08 was:

```text
Ubuntu:              24.04.4 LTS (GitHub-hosted ubuntu-24.04 runner)
Python:              3.11.16
Icarus Verilog:      12.0 (Ubuntu package 12.0-2build2)
pytest:              9.1.1
project numpy:       2.4.6
project Brian2:      2.9.0
project Brian2Loihi: 0.5.2
Catalyst neurocore:  1.0.0
Catalyst matplotlib: 3.11.1
Catalyst pyserial:   3.5
```

The complete thesis regression suite passed in this environment. The pinned Catalyst checkout then passed exact commit/tag/blob verification while clean, all **25/25** testbenches enumerated by its native `run_regression.sh`, and all **56/56** tests in `sdk/tests/test_simulator.py`. These results establish that the external reference boundaries selected by M13.1 are independently runnable; they do not establish that Catalyst behavior is Loihi ground truth.

Two development-only Class-H issues were found and corrected before closure: an older M12.5 documentation test expected the exact already-intended power-exclusion wording, and the first M13.1 RTL harness falsely interpreted Catalyst's `0 FAILED` summary text as a failure. Neither issue changed project computation or Catalyst source.

The DOI `10.5281/zenodo.18727094` remains the stable Catalyst N1 publication identity. Catalyst-controlled secondary sources observed during M13.1 use more than one title string for that DOI, so M13 records the DOI as normative and treats publication-title text as descriptive metadata.

## Independent local validation closure

The user independently reproduced the M13.1 external-reference boundary on the development branch on 2026-09-09. The pinned Catalyst CPU simulator suite completed **56/56** tests successfully, and the pinned Catalyst native RTL regression completed **25/25** testbenches successfully with exit code 0. No Catalyst source, RTL expectation, testbench list, compile flag, or project computational baseline was changed for this reproduction.

Two host-harness portability issues were exposed during local reproduction and were corrected as Class-H tooling issues before final acceptance:

1. With `set -euo pipefail`, piping `iverilog -V` into `head -n 1` could cause some local Icarus builds to receive SIGPIPE and terminate the wrapper before emitting diagnostics. The runner now captures the full version output first and extracts the first line in Bash without a pipe.
2. The original wrapper imposed a fixed 120-second `vvp` timeout. On the user's PC, `tb/tb_p13a.v` was still producing the expected cross-core spike sequence when GNU `timeout` terminated it with exit code 124. The wrapper now defaults to 300 seconds per native testbench and exposes `M13_1_TB_TIMEOUT_SECONDS` as an explicit host-performance override. The successful local acceptance used 600 seconds per testbench. A timeout is reported separately from a genuine simulator failure.

The longer local timeout does not weaken the behavioral gate: compile failures, nonzero simulator exits, explicit native failure markers, missing native result markers, changed testbench count, dirty/moved Catalyst source, and incorrect commit/tag/blob provenance remain fatal. The local 25/25 pass therefore confirms that the earlier 120-second stop was host-runtime variability rather than a Catalyst architectural discrepancy.

The independent local closure result is:

```text
Catalyst native RTL: 25/25 PASS
Catalyst CPU tests:   56/56 PASS
Catalyst source pin:  1806bb4b4114d7671e5648fa75b7b83b3a8d5543
Project M12 baseline: unchanged
Discrepancy outcome:  no architectural discrepancy identified in M13.1
```

## M13.1 pass boundary

**Achieved on 2026-09-08.** M13.1 closed only after the provenance-corrected final gate reproduced the clean external checkout and both independent Catalyst execution boundaries.

The closure criteria are:

- the manifest validates from source control;
- `v2.3-paper` and `n1-final` resolve to the frozen Catalyst commit;
- a clean local Catalyst checkout verifies against the recorded Git blob identities;
- the native 25-testbench Catalyst RTL regression is reproducible under Icarus v12+ after only working-directory normalization;
- the pinned Catalyst CPU simulator test boundary is independently runnable;
- the complete thesis regression suite remains passing;
- M13's evidence vocabulary, source authority, independence policy, discrepancy classes, and A/B change-control rule are recorded before M13.2 begins.

No physical-board validation is required for M13.1. K26 reproduction is explicitly deferred to M13.5.

## Handoff to M13.2

M13.2 should build the four-way feature crosswalk using the frozen references here. Every row should distinguish published documentation, direct observation, implementation inference, and project interpretation. Catalyst-specific claims should cite the pinned commit; Brian2Loihi-specific claims should use v0.5.2/M03-M08 evidence; Loihi claims should cite published sources; and this project's claims should link the M10/M12 normative evidence.

Most importantly, M13.2 starts with a stable question: **how do these four evidence columns relate?** It does not start with the assumption that one external implementation must be made to match another.
