"""Build a fairness-preserving M13.5 project/Catalyst hardware comparison."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .m13_hardware_audit import M13_5_RESULT_SCHEMA, load_hardware_manifest

M13_5_COMPARISON_SCHEMA = "neuromorphic-twin-m13-hardware-comparison-result-v1"


def build_hardware_comparison(
    catalyst_result: dict[str, Any],
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    frozen = manifest or load_hardware_manifest()
    _validate_catalyst_result(catalyst_result, frozen)
    project = frozen["project_m12_physical"]
    catalyst_cfg = frozen["catalyst_k26"]

    project_resources = project["resources"]
    resource_rows = []
    mapping = [
        ("clb_luts", "CLB LUTs", "clb_luts"),
        ("clb_registers", "CLB registers", "clb_registers"),
        ("bram_tiles", "Block RAM tiles", "bram_tiles_upper_bound"),
        ("dsps", "DSPs", "dsps"),
        ("uram", "URAM", "uram"),
    ]
    for catalyst_key, label, project_key in mapping:
        c = catalyst_result["resources"].get(catalyst_key)
        p = project_resources.get(project_key)
        resource_rows.append(
            {
                "resource": label,
                "comparison_status": "contextual_only",
                "project": p,
                "catalyst": c,
                "reason": (
                    "Raw implementation counts are shown with local device capacities, but the target part strings, "
                    "configured capacities, architectural feature sets, and validation/debug overhead differ."
                ),
            }
        )

    return {
        "schema": M13_5_COMPARISON_SCHEMA,
        "status": "routed_hardware_comparison_available",
        "strongest_catalyst_boundary": "source-supported routed implementation",
        "source_pins": frozen["baseline"],
        "clock": {
            "comparison_status": "same_nominal_target",
            "project_hz": project["clock_hz"],
            "catalyst_hz": catalyst_cfg["clock_hz"],
            "period_ns": frozen["reproduction_environment"]["clock_period_ns"],
        },
        "targets": {
            "comparison_status": "related_k26_class_not_identical_part_string",
            "project": project["target_part"],
            "catalyst": catalyst_result["target_part"],
        },
        "configured_scope": {
            "project": project["scope"],
            "catalyst": {
                "cores": catalyst_cfg["configured_cores"],
                "neurons_per_core": catalyst_cfg["neurons_per_core"],
                "total_neurons": catalyst_cfg["total_configured_neurons"],
                "pool_depth_per_core": catalyst_cfg["pool_depth_per_core"],
                "host_boundary": catalyst_cfg["host_boundary"],
            },
        },
        "routed_timing": {
            "comparison_status": "contextual_same_10ns_constraint",
            "project": project["timing"],
            "catalyst": catalyst_result["timing"],
            "project_timing_closed": project["timing"]["wns_ns"] >= 0 and project["timing"]["whs_ns"] >= 0,
            "catalyst_timing_closed": catalyst_result["timing_closed"],
            "rule": "Do not infer maximum Fmax from WNS; both values only describe closure/margin at the 10 ns target.",
        },
        "resources": resource_rows,
        "behavioral_execution": {
            "project": project["behavioral_validation"],
            "catalyst": None,
            "comparison_status": "not_comparable_at_routed_boundary",
            "reason": "The supplied Catalyst K26 flow produces an implemented DCP/reports but no board runtime trace for the M13.4 common corpus.",
        },
        "latency_throughput": {
            "project_latency_cycles": project["latency_cycles"],
            "project_aggregate": project["aggregate"],
            "catalyst": None,
            "comparison_status": "withheld",
            "reason": "No equivalent Catalyst architectural-timestep on-fabric cycle measurement is established by the K26 routed implementation flow.",
        },
        "power_energy": {
            "comparison_status": "withheld",
            "project": None,
            "catalyst": None,
            "reason": "M12 excluded power/energy from the validated project claim set and Catalyst report_power is not a matching physical methodology.",
        },
        "physical_execution": {
            "project": True,
            "catalyst": False,
            "comparison_status": "different_evidence_strength",
            "reason": catalyst_cfg["physical_programming_boundary"]["reason"],
        },
        "fairness_rules": frozen["fairness_rules"],
    }


def render_hardware_comparison_markdown(comparison: dict[str, Any]) -> str:
    if comparison.get("schema") != M13_5_COMPARISON_SCHEMA:
        raise ValueError("unexpected M13.5 comparison schema")
    timing = comparison["routed_timing"]
    targets = comparison["targets"]
    lines = [
        "# M13.5 Routed Hardware Comparison",
        "",
        "This table is contextual evidence, not an efficiency ranking. The two implementations differ in configured capacity, architectural scope, target-part string, and validation/debug infrastructure.",
        "",
        "## Hardware boundary",
        "",
        f"- Project: physical M12.5 KV260 execution on `{targets['project']}`.",
        f"- Catalyst: source-supported routed implementation on `{targets['catalyst']}`; no physical KV260 execution claimed.",
        "- Both routed comparisons use a nominal 10 ns / 100 MHz target.",
        "",
        "## Routed timing",
        "",
        "| Metric | Project M12.5 | Catalyst N1 |",
        "| --- | ---: | ---: |",
        f"| WNS | {timing['project']['wns_ns']:+.3f} ns | {timing['catalyst']['wns_ns']:+.3f} ns |",
        f"| WHS | {timing['project']['whs_ns']:+.3f} ns | {timing['catalyst']['whs_ns']:+.3f} ns |",
        "",
        "These are margins at the 10 ns constraint; they are not converted into maximum-Fmax claims.",
        "",
        "## Resource context",
        "",
        "| Resource | Project | Catalyst | Comparison status |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in comparison["resources"]:
        lines.append(
            f"| {row['resource']} | {_format_resource(row['project'])} | {_format_resource(row['catalyst'])} | contextual only |"
        )
    lines.extend(
        [
            "",
            "Resource counts are not normalized into a winner/loser metric because the implementations do not provide the same feature/capacity/debug boundary.",
            "",
            "## Comparisons intentionally withheld",
            "",
            "- **Latency/throughput:** withheld until Catalyst has an equivalent on-fabric architectural-timestep cycle measurement.",
            "- **Power/energy:** withheld because the M12 project claim set has no matching validated power methodology.",
            "- **Physical behavioral execution:** the project has physical 22-case/166-tick exact evidence; the pinned Catalyst K26 source flow currently provides routed implementation rather than a directly programmable board image.",
            "",
            "## Interpretation boundary",
            "",
            "A successful Catalyst route establishes that the pinned K26-class RTL can be synthesized, placed, and routed under the recorded tool/part/clock conditions. It does not by itself establish physical Catalyst board execution, Loihi equivalence, or comparative architectural efficiency.",
            "",
        ]
    )
    return "\n".join(lines)


def load_catalyst_result(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _validate_catalyst_result(result: dict[str, Any], manifest: dict[str, Any]) -> None:
    if result.get("schema") != M13_5_RESULT_SCHEMA:
        raise ValueError("unexpected Catalyst hardware-result schema")
    if result.get("catalyst_commit") != manifest["baseline"]["catalyst_commit"]:
        raise ValueError("Catalyst hardware result uses the wrong source commit")
    if result.get("vivado") != manifest["reproduction_environment"]["vivado"]:
        raise ValueError("Catalyst hardware result uses the wrong Vivado version")
    if result.get("target_part") != manifest["catalyst_k26"]["upstream_target_part"]:
        raise ValueError("Catalyst hardware result uses the wrong target part")
    if result.get("physical_programming_source_supported") is not False:
        raise ValueError("Catalyst routed result must not claim a programmable source boundary")
    for resource in ("clb_luts", "clb_registers", "bram_tiles", "dsps"):
        if resource not in result.get("resources", {}):
            raise ValueError(f"Catalyst hardware result missing resource: {resource}")


def _format_resource(value: Any) -> str:
    if not isinstance(value, dict):
        return "n/a"
    used = value.get("used")
    available = value.get("available")
    relation = value.get("relation", "")
    if used is None:
        return "n/a"
    used_text = f"{used:g}" if isinstance(used, float) else str(used)
    prefix = relation if relation else ""
    if available is None:
        return f"{prefix}{used_text}"
    available_text = f"{available:g}" if isinstance(available, float) else str(available)
    return f"{prefix}{used_text} / {available_text}"
