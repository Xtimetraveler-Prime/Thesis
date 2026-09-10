# M13.5 — Catalyst N1 K26-Class Hardware/RTL Reproduction

## Status

**Status: Complete**

M13.5.1, M13.5.2, and M13.5.3 are complete. The final tracked result authority is `references/m13_5_closure.json`; bulky native Vivado products remain in the ignored local evidence tree.

M13.5 extends the Catalyst audit beyond documentation and software simulation. Its goal is to reproduce the pinned Catalyst N1 release at the strongest hardware boundary actually supplied by that release, preserve vendor evidence, and compare it with the accepted M12.5 FPGA characterization without turning unlike implementations into an unfair performance contest.

The machine-readable authority for the comparison boundary is:

```text
references/m13_5_hardware_manifest.json
schema = neuromorphic-twin-m13-hardware-comparison-v1
status = preflight_frozen_pending_vivado_reproduction
```

M13.5 starts from the independently validated M13.4 merge:

```text
54c7840dff765d585e7ff236845b085007405c05
```

No M10/M12 computational behavior, HLS datapath, FPGA-v1 RTL, or physical-conformance expectation is modified by this work.

---

## Frozen Catalyst source boundary

Catalyst remains pinned to:

```text
repository: catalyst-neuromorphic/catalyst-n1
tag:        v2.3-paper
commit:     1806bb4b4114d7671e5648fa75b7b83b3a8d5543
```

The M13.1 checkout validator remains authoritative for exact commit/tag/blob verification. M13.5 adds K26-specific checks rather than replacing that provenance gate.

At the pin, `fpga/kria/` contains exactly four files:

```text
build_kria.tcl
kria_neuromorphic.v
kria_neuromorphic_8core_backup.v
run_impl.tcl
```

The three files used by the 2-core reproduction are pinned by Git blob identity:

```text
build_kria.tcl       6aff405e689cdd2dce402b78002516039777a340
run_impl.tcl         672705d32baf5ca473f9ad538a3272ec3c483a11
kria_neuromorphic.v  fee15b738087c155d271f7d7c1eddc5bc9544072
```

The wrapper configures:

```text
2 cores
256 neurons/core
512 configured neurons total
4096 synapse-pool entries/core
100 MHz neural/AXI clock
AXI-facing host boundary
```

This is substantially broader in architectural feature scope than the thesis FPGA-v1 core. Raw resource totals therefore cannot be interpreted as a simple efficiency ranking.

---

## The upstream K26 command has a reproducibility caveat

The pinned README shows:

```bash
vivado -mode batch -source fpga/kria/build_kria.tcl
```

However, the pinned Tcl initializes:

```tcl
set mode "full"
```

and only launches `synth_1` inside:

```tcl
if {$mode eq "synth_only"} {
    ...
    launch_runs synth_1 -jobs 4
    ...
}
```

The default `full` path creates the project and then closes it without synthesis. `run_impl.tcl`, meanwhile, expects the synthesis checkpoint:

```text
fpga/kria/build/catalyst_kria_n1.runs/synth_1/kria_neuromorphic.dcp
```

M13.5 therefore freezes the strongest source-supported two-stage invocation as:

```bash
vivado -mode batch -source fpga/kria/build_kria.tcl -tclargs synth_only
vivado -mode batch -source fpga/kria/run_impl.tcl
```

This is a **tooling normalization only**. Catalyst source is not patched, copied into the thesis core, or behaviorally altered. The first command selects a mode already implemented and documented in the pinned Tcl header; the second is the pinned implementation script unchanged.

---

## Vivado version

The pinned K26 Tcl does not specify a Vivado release. The same pinned Catalyst repository explicitly selects Vivado 2025.2 in its AWS F2 build flow, and the thesis M11/M12 flow already standardizes on AMD Vivado/Vitis 2025.2.

M13.5 therefore uses:

```text
Vivado 2025.2
```

as the **thesis reproduction environment**. This must not be restated as an upstream Catalyst K26 requirement.

The runner fails closed if a different Vivado version is active so a later result cannot silently mix toolchains.

---

## Target-part distinction

The two hardware results are K26-class but do not use the same Vivado part string.

| Boundary | Vivado part |
| --- | --- |
| Thesis accepted M12.5 image | `xck26-sfvc784-2LV-c` |
| Pinned Catalyst K26 Tcl | `xczu5ev-sfvc784-2-i` |

M13.5 does **not** rewrite the Catalyst Tcl to make these strings look identical. The upstream part selection is part of the reproduction evidence and must remain visible in every resource/timing comparison.

Vivado's `Available` resource counts from the Catalyst report are preserved next to its `Used` counts. Percentages may be shown only with the target-part distinction disclosed.

---

## Physical-programming boundary discovered before vendor execution

The pinned Catalyst `fpga/kria/` release does **not** currently provide a complete directly programmable KV260 image flow.

Specifically, that directory provides:

- the AXI-facing Verilog wrapper;
- a synthesis Tcl;
- a routed-implementation Tcl;
- an 8-core backup wrapper.

It does not provide:

- a K26/KV260 XDC in that directory;
- a Vivado block design integrating the Zynq processing system;
- a PS/PL clock/reset platform design;
- package-pin constraints for a standalone top;
- a `write_bitstream` step.

`run_impl.tcl` opens the synthesized checkpoint, constrains `s_axi_aclk` to 10 ns, performs `opt_design`, `place_design`, `phys_opt_design`, and `route_design`, writes an implemented DCP, and emits implementation reports. That is a real FPGA implementation boundary, but it is not by itself proof that the design was programmed and executed on a physical KV260.

Therefore the currently source-supported M13.5 boundary is:

```text
pinned Catalyst RTL
        |
        v
Kria AXI wrapper elaboration
        |
        v
Vivado synthesis
        |
        v
place / phys_opt / route
        |
        v
implemented DCP + timing/resource reports
```

If that flow reproduces successfully, routed implementation is a defensible M13.5 fallback/closure boundary even if physical programming remains unavailable from the pinned source. A separate board integration could be built later, but it would be thesis-created integration work and must be labeled as such rather than attributed to the pinned Catalyst release.

---

## Automated preflight implemented in this branch

### 1. Frozen manifest validation

Run:

```bash
PYTHONPATH=src python3 examples/validate_m13_5_hardware_manifest.py
```

With a fetched Catalyst checkout:

```bash
PYTHONPATH=src python3 examples/validate_m13_5_hardware_manifest.py \
  --catalyst-checkout build/m13_1/catalyst-n1
```

The checkout gate reuses the M13.1 exact provenance validator and additionally verifies:

- exact `fpga/kria` file inventory;
- target part and 10 ns clock fragments;
- 2-core / 256-neuron / 4096-pool wrapper parameters;
- existing `synth_only` control flow;
- routed implementation/report commands;
- absence of an upstream K26 XDC in the pinned directory;
- absence of `write_bitstream` from the pinned K26 build/implementation Tcl.

### 2. Kria wrapper RTL elaboration

Run:

```bash
bash scripts/run_m13_5_catalyst_kria_elaboration.sh
```

This compiles the exact 15-file RTL list used by the pinned K26 synthesis Tcl with Icarus Verilog 12+ and top module `kria_neuromorphic`. It is an RTL integration/elaboration gate, not a timing/resource result.

The existing M13.1 native regression should also remain 25/25:

```bash
bash scripts/run_m13_1_catalyst_rtl_regression.sh
```

Together these checks ensure the exact pinned RTL still runs its native regression and that the K26-specific wrapper elaborates before scarce Vivado time is used.

---

## Vendor reproduction runner

The source-controlled vendor command is:

```bash
bash scripts/run_m13_5_catalyst_k26_vivado.sh
```

By default it uses:

```text
Catalyst checkout: build/m13_1/catalyst-n1
Evidence output:   build/m13_5/catalyst-k26-vivado
```

The runner performs the following in order:

1. validates the exact Catalyst pin and frozen M13.5 hardware manifest;
2. requires Vivado 2025.2;
3. removes any previous generated `fpga/kria/build` directory;
4. runs the pinned `build_kria.tcl -tclargs synth_only` flow;
5. verifies the expected synthesized DCP exists;
6. runs the pinned `run_impl.tcl` flow through `route_design`;
7. requires all expected synthesis/implementation reports and the implemented DCP;
8. copies those native artifacts into the thesis evidence tree;
9. parses routed utilization and timing into machine-readable JSON;
10. hashes all preserved evidence files;
11. fails if routed WNS or WHS is negative;
12. verifies tracked Catalyst source remains unchanged;
13. removes only the generated upstream build directory after evidence is preserved.

No Catalyst source file is modified by the runner.

### Preserved evidence

A successful vendor run produces:

```text
build/m13_5/catalyst-k26-vivado/
  catalyst-head.txt
  commands.txt
  vivado-version.txt
  synthesis.log
  implementation.log
  catalyst-hardware-result.json
  hardware-comparison.json
  hardware-comparison.md
  evidence-manifest.json
  native_reports/
    synth_utilization.rpt
    synth_utilization_hier.rpt
    synth_timing.rpt
    kria_n1_impl.dcp
    timing_summary.rpt
    timing_paths.rpt
    utilization.rpt
    utilization_hier.rpt
    power.rpt
    clock_utilization.rpt
    design_analysis.rpt
```

`power.rpt` is preserved because it is a native upstream output. It is **not** used for a project-versus-Catalyst power comparison.

---

## Report normalization

`src/neuromorphic_twin/m13_hardware_audit.py` parses only quantities that the Vivado reports actually expose:

```text
routed WNS
routed WHS
CLB LUTs: used / available / percent
CLB registers: used / available / percent
Block RAM tiles: used / available / percent
DSPs: used / available / percent
URAM when present
```

The parser fails if a major utilization row or timing summary cannot be identified. It deliberately does not infer an Fmax from WNS.

A parsed result uses:

```text
schema = neuromorphic-twin-m13-hardware-result-v1
status = routed_implementation_observed
```

and explicitly carries:

```text
physical_programming_source_supported = false
```

so a routed implementation result cannot later be misquoted as physical Catalyst execution.

---

## Frozen project comparison baseline

The project side remains the accepted M12.5 physical characterization image:

```text
target:  xck26-sfvc784-2LV-c
clock:   100 MHz
WNS:    +0.493 ns
WHS:    +0.011 ns
LUTs:    4,424 / 117,120
regs:    4,280 / 234,240
BRAM:   <=18 / 144 tiles
DSPs:    2 / 1,248
URAM:    0 / 64
behavior: 22/22 workloads, 166/166 physical ticks exact, 0 mismatches
```

That image contains the thesis core **plus** its workload image, VIO/debug shell, physical trace path, and passive timing counter. It is not a stripped-down core-only resource number.

The M12 latency corpus remains:

```text
min:    26 cycles
mean:   379.10 cycles
max:    8,218 cycles
```

These values are retained in the M13.5 manifest for provenance but are **not yet comparable to Catalyst latency** because the pinned K26 implementation flow does not establish an equivalent per-architectural-timestep cycle measurement.

---

## Fairness rules applied to the final comparison

The following rules are frozen before Catalyst Vivado results are observed:

1. **No raw winner/loser claim.** Catalyst implements a broader architecture and a larger configured capacity; this project's M12 image contains different debug/validation overhead.
2. **Keep part strings visible.** `xczu5ev-sfvc784-2-i` and `xck26-sfvc784-2LV-c` are not silently collapsed into one label.
3. **Use report-local capacities.** Catalyst utilization percentages use the `Available` values from its own routed Vivado report.
4. **No throughput claim from routing reports.** Resource/timing closure does not provide cycles per neural timestep, events/s, or synapse-visits/s.
5. **No power comparison.** The project intentionally excluded power/energy from M12's validated claim set; Catalyst's `report_power` estimate is not a matching measurement method.
6. **Disclose feature scope.** Catalyst's wrapper carries 2 cores, NoC/host infrastructure and broader architectural machinery; the thesis implementation is a narrower Loihi-inspired subset optimized for transparency and exact state-transition validation.
7. **Physical means physical.** A routed DCP is not called a board execution. Physical Catalyst claims require an actual programmable integration and runtime evidence.

---

## Final M13.5 hardware boundary

The independent AMD-toolchain step and tracked evidence promotion are complete. The pinned Catalyst K26-class RTL reproduced successfully through Vivado 2025.2 synthesis, placement, physical optimization, and routing at 100 MHz. M13.5 closes at **source-supported routed implementation** because the pinned `fpga/kria/` release does not supply the board constraints, processing-system integration, or bitstream-generation path needed to attribute a physical KV260 run to upstream Catalyst.

The accepted result is deliberately asymmetric in evidence strength: the thesis project retains physical M12.5 execution evidence, while Catalyst contributes routed implementation evidence. This is recorded as a platform/integration boundary rather than a behavioral discrepancy.

## Independent M13.5.2 Vivado reproduction

The source-controlled `run_m13_5_catalyst_k26_vivado.sh` runner was independently executed on 2026-09-10 with the local Vivado 2025.2 installation and completed successfully. It reproduced the pinned Catalyst commit `1806bb4b4114d7671e5648fa75b7b83b3a8d5543` on upstream target `xczu5ev-sfvc784-2-i` at the frozen 100 MHz constraint. The routed timing result was WNS `+0.001 ns` and WHS `+0.013 ns`, so setup and hold both closed.

The generated normalized comparison retained the frozen evidence rules: project part `xck26-sfvc784-2LV-c` remains distinct from the Catalyst part, latency/throughput is withheld, power/energy is withheld, and Catalyst physical execution remains false. The runner reached its final PASS only after required synthesis/implementation reports and the implemented DCP were preserved, the evidence tree was hashed, and tracked Catalyst source was confirmed unchanged.

M13.5.2 is therefore complete. M13.5.3 subsequently validated the preserved evidence through `scripts/run_m13_5_closure.sh`, independently re-parsed the native routed timing/utilization reports, reproduced the normalized comparison, verified the complete SHA-256 evidence manifest, and promoted `references/m13_5_closure.json` as the tracked authority. Independent local closure passed **23/23 focused M13.5 tests** and the complete **354/354 project regression suite**; the final tracked-result source gate extends those counts to **23/23 focused** and **358/358 complete** tests.

---

## Automated M13.5.1 preflight evidence

A clean Ubuntu 24.04 current-head reconstruction completed the non-Vivado M13.5 boundary successfully. The run verified the exact pinned Catalyst checkout and `fpga/kria` inventory, elaborated the K26 wrapper from the same 15 RTL files named by `build_kria.tcl` with Icarus Verilog 12+, passed **13/13 focused M13.5 tests**, and passed the complete **344/344 thesis regression suite**. Both M13.5 shell runners passed syntax validation and the branch-diff guard confirmed no frozen computational-core, HLS, routing, weight, or FPGA-v1 behavior file changed.

M13.1 already established the unchanged Catalyst pin at **25/25 native RTL regression testbenches**; the M13.5 branch consumes that exact source and adds the K26-wrapper-specific elaboration gate rather than redefining Catalyst's regression suite.

That pre-vendor checkpoint is retained as provenance for the frozen comparison contract; the independently observed vendor result and final closure are recorded below.

---

## Final M13.5.3 observed result and closure

Independent evidence promotion completed on 2026-09-10 from the preserved M13.5.2 Vivado tree. The closure command re-parsed the native `timing_summary.rpt` and `utilization.rpt`, required exact regeneration of the normalized result/comparison, verified every preserved evidence hash, reran the focused M13.5 tests and full project regression, and emitted the tracked machine-independent closure record.

### Routed implementation result

| Metric | Thesis M12.5 | Catalyst N1 |
| --- | ---: | ---: |
| Target part | `xck26-sfvc784-2LV-c` | `xczu5ev-sfvc784-2-i` |
| Clock target | 100 MHz | 100 MHz |
| Routed WNS | +0.493 ns | +0.001 ns |
| Routed WHS | +0.011 ns | +0.013 ns |
| CLB LUTs | 4,424 / 117,120 | 19,891 / 117,120 (16.98%) |
| CLB registers | 4,280 / 234,240 | 30,850 / 234,240 (13.17%) |
| Block RAM tiles | <=18 / 144 | 52.5 / 144 (36.46%) |
| DSPs | 2 / 1,248 | 14 / 1,248 (1.12%) |
| URAM | 0 / 64 | 0 / 64 (0.00%) |

Both implementations close the same nominal 10 ns constraint. The different WNS margins are **not** converted into an Fmax or architectural-efficiency claim. The designs differ in target-part string, configured capacity, feature scope, serialization/parallelism, host infrastructure, and validation/debug overhead. Resource totals are therefore contextual rather than a winner/loser metric.

Latency/throughput remains withheld because the Catalyst routed flow does not establish an equivalent on-fabric architectural-timestep cycle boundary. Power/energy remains withheld because the project has no matching validated physical power methodology. Catalyst physical execution remains false; the implemented DCP is not relabeled as a programmed-board result.

### Evidence identity

The compact tracked closure is `references/m13_5_closure.json` with schema `neuromorphic-twin-m13-hardware-closure-v1` and status `validated_complete`. Its preserved evidence-manifest SHA-256 is:

```text
80a03e53f8775c6358654fa34e35176442f79b94b43de8e58ecf10920665b2bc
```

The closure record also stores hashes for the normalized result/comparison and all 11 native Vivado reports/DCP products while intentionally omitting machine-local absolute paths.

### M13.5 conclusion

**M13.5 is complete.** The exact pinned Catalyst N1 K26-class RTL was reproducibly implemented through route at 100 MHz under Vivado 2025.2, with positive setup and hold slack and source provenance intact. Because the pinned Catalyst release does not provide a complete directly programmable KV260 integration, routed implementation is the strongest source-supported Catalyst hardware boundary used by this thesis. No project computational baseline changed, and no M12 physical rerun is required by M13.5.

