# M13.5.3 — Normalize routed hardware evidence and close M13.5

## Status

**In progress — M13.5.2 independent Vivado 2025.2 reproduction passed; tracked evidence promotion is the remaining closure step.**

The independently executed M13.5.2 runner completed successfully on the pinned Catalyst N1 K26-class flow with:

```text
Catalyst commit: 1806bb4b4114d7671e5648fa75b7b83b3a8d5543
Vivado:          2025.2
Target part:     xczu5ev-sfvc784-2-i
Clock target:    100 MHz / 10 ns
Routed WNS:      +0.001 ns
Routed WHS:      +0.013 ns
Timing closed:   yes
```

The same runner also reported the fairness guards intact: latency/throughput comparison withheld, power comparison withheld, and Catalyst physical execution false.

M13.5.3 does not rerun Vivado. Its purpose is to validate and promote the already-preserved routed evidence into a compact tracked thesis artifact without committing bulky vendor products or machine-specific paths.

---

## Why an evidence-promotion step is needed

The Vivado runner preserves its complete output under:

```text
build/m13_5/catalyst-k26-vivado/
```

The repository intentionally ignores `build/`, because that tree contains logs, native reports, and an implemented DCP that should not become normal source-controlled project files.

The routed result itself is nevertheless thesis evidence. M13.5.3 therefore validates the complete local evidence tree and emits a compact tracked authority at:

```text
references/m13_5_closure.json
```

The closure artifact records the normalized routed timing/resource result, the project/Catalyst comparison boundary, the deliberately withheld comparisons, and cryptographic digests tying the compact record back to the preserved vendor evidence.

---

## Source-controlled closure command

From `Neuromorphic Digital Twin/` run:

```bash
bash scripts/run_m13_5_closure.sh
```

The script defaults to the evidence produced by the successful M13.5.2 run and performs three stages:

1. validate and promote the preserved Vivado evidence;
2. run the focused M13.5 audit/comparison/closure tests;
3. run the complete project regression and verify that no frozen computational-core/HLS/FPGA-v1 baseline path changed.

The generated human-readable summary remains in ignored build output:

```text
build/m13_5/m13_5_closure_summary.md
```

The compact JSON is intentionally placed under `references/` so it can be inspected and committed after independent reproduction:

```text
references/m13_5_closure.json
```

---

## Evidence-tree validation

`m13_hardware_closure.py` fails closed unless all of the following hold:

- every artifact required by the source-controlled Vivado runner is present;
- the exact Catalyst commit, Vivado version, target part, and frozen 100 MHz boundary agree with the pre-vendor M13.5 manifest;
- routed WNS and WHS are non-negative;
- the saved JSON hardware comparison is exactly reproducible from the normalized Catalyst result;
- the saved Markdown comparison is exactly reproducible from the JSON comparison;
- latency/throughput remains marked `withheld`;
- power/energy remains marked `withheld`;
- routed Catalyst evidence remains explicitly non-physical;
- the preserved synthesis/implementation commands match the frozen source-supported commands;
- every preserved evidence file except the hash manifest itself is covered by the recorded SHA-256 map;
- every recorded SHA-256 digest matches the current local evidence file.

An extra un-hashed file, missing native report, changed normalized result, comparison drift, or tampered preserved artifact causes closure to fail.

---

## Tracked closure schema

A successful promotion writes:

```text
schema = neuromorphic-twin-m13-hardware-closure-v1
status = validated_complete
milestone = M13.5
```

The tracked artifact deliberately excludes absolute paths from the M13.5.2 machine. It retains:

- Catalyst and project source pins;
- Vivado/clock/part identities;
- configured-scope context;
- project and Catalyst routed timing margins at 10 ns;
- project and Catalyst resource context with local capacities;
- physical-versus-routed evidence-strength distinction;
- latency/throughput and power comparison exclusions;
- SHA-256 identity of the complete evidence manifest;
- hashes of normalized comparison artifacts and all native vendor reports.

This makes the committed record small enough for the thesis repository while preserving a cryptographic link to the exact local Vivado evidence used for closure.

---

## Interpretation of the observed timing result

Catalyst closed the frozen 100 MHz target with only `+0.001 ns` routed setup margin and `+0.013 ns` hold margin. The thesis M12.5 image previously closed the same nominal 10 ns target with `+0.493 ns` WNS and `+0.011 ns` WHS.

These values may be reported side-by-side as implementation context, but M13.5 does **not** interpret the larger project setup margin as proof of superior architecture or efficiency. The target part strings, configured capacities, feature scope, serialization/parallelism, and validation/debug overhead are materially different. Neither result is converted into a maximum-Fmax claim.

---

## M13.5 closure boundary

If evidence promotion and the full regression pass, no additional Catalyst board-programming step is required for M13.5. The pinned `fpga/kria/` release lacks a complete source-supported KV260 board integration and bitstream flow, so successful routed implementation is the strongest directly reproducible hardware boundary attributable to the pinned Catalyst release.

A future thesis-created Catalyst board integration could be an additional experiment, but it is not required to close M13.5 and must not be retroactively described as part of the pinned upstream release.

After `references/m13_5_closure.json` is independently generated and reviewed, the remaining repository work is to record its observed resource numbers and evidence hash in the main M13.5 narrative and `MILESTONES.md`, run final source-level consistency checks, and merge the branch.

## Closure-tooling CI checkpoint

Before local evidence promotion, the M13.5.3 host-side tooling passed **19/19 focused M13.5 tests** and the complete **350/350 project regression suite** in a clean Ubuntu 24.04 environment. The same run revalidated the frozen M13.5 hardware manifest, exact Catalyst checkout, K26 wrapper elaboration, shell syntax, and branch-diff guard. This validates the promotion machinery itself; the independent local evidence tree is still required to generate `references/m13_5_closure.json`.
