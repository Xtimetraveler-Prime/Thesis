#!/usr/bin/env python3
"""Stage the M13.6 milestone and experiment handoff text for candidate freeze."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def patch_milestones() -> None:
    path = ROOT / "MILESTONES.md"
    text = path.read_text(encoding="utf-8")
    old = """### M13.6 — Adjudicate discrepancies and freeze M13 findings

**Status:** Planned

#### Core goal"""
    new = """### M13.6 — Adjudicate discrepancies and freeze M13 findings

**Status:** In progress
**Started:** 2026-09-10
**Repository evidence:** branch `agent/m13-6-adjudicate-freeze-findings`; candidate authority `Neuromorphic Digital Twin/references/m13_6_findings.json`

M13.6 is being executed in two ordered sub-boundaries:

- **M13.6.1 — Freeze evidence-driven A–H adjudication and change control.** Regenerate the final candidate findings from the tracked M13.2 crosswalk, M13.4 directed findings, and M13.5 hardware closure; fail closed on source-pin, classification, comparison-limit, or baseline drift.
- **M13.6.2 — Freeze thesis claim boundaries and experiment handoff.** Cross-reference the accepted differences into `EXPERIMENTS.md`, preserve the zero-A/B change-control decision, and complete independent local validation before M13.6/M13 closure.

#### Core goal"""
    if old not in text:
        raise SystemExit("M13.6 planned-status marker not found")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_experiments() -> None:
    path = ROOT / "EXPERIMENTS.md"
    text = path.read_text(encoding="utf-8")
    marker = "\n## Required experiment record\n"
    if marker not in text:
        raise SystemExit("EXPERIMENTS required-record marker not found")
    if "## M13.6 audit handoff" in text:
        return
    handoff = """
## M13.6 audit handoff

The candidate M13.6 adjudication preserves the validated FPGA-v1 baseline because the accepted M13 audit contains **zero Class-A/B findings**. The audit therefore changes experiment interpretation rather than silently changing the instrument:

- **E01 — update ordering:** retain the physically validated FPGA-v1 update schedule as the baseline. M13 agreement on current/voltage, transformed threshold, and refractory release does not make alternative schedules equivalent; ordering changes remain explicit counterfactuals.
- **E02 — weight representation:** M13 P07 found exact agreement for all 13 effective-weight cases inside Catalyst's signed-int16 common envelope, while native encoding fields are not field-for-field equivalent and two project/Brian2Loihi cases fall outside that envelope. Experiments should separate delivered effective-weight effects from encoding-layout effects.
- **E03 — recurrent timing:** M13 P10 found a one-tick source-to-target lag in FPGA-v1 and Catalyst synchronous execution, while the pinned Brian2Loihi native recurrent probe produced no target effect. The Brian2Loihi null result is retained as an emulator/modeling finding, not treated as Loihi ground truth.
- **E04 — finite precision:** M13 P03/P06/P11 make negative `/4096` rounding, sub-rest membrane clamping, and overflow/saturation policy especially useful controlled variants. Published Loihi evidence remains insufficient to promote one shared overflow policy to ground truth.
- **E05 — multi-feature ablation:** keep this deferred at the design level until the relevant single-factor variants from E01-E04 are independently frozen and validated, so an ablation cannot confound several M13 differences at once.
- **E06 — FPGA fidelity cost:** M13.5 routed Catalyst timing/resources are implementation context only. Fair cost experiments should compare controlled project variants under the same target part, tool version, constraints, workload boundary, and measurement method rather than rank the raw Catalyst and FPGA-v1 totals.

No experiment status is promoted by M13.6 alone. The machine-readable handoff is part of `Neuromorphic Digital Twin/references/m13_6_findings.json`; experiments move to Designed/Ready only when their own hypotheses, variants, workloads, and validation gates are frozen.
"""
    path.write_text(text.replace(marker, "\n" + handoff + marker, 1), encoding="utf-8")


def main() -> int:
    patch_milestones()
    patch_experiments()
    print("M13.6 candidate documentation staging PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
