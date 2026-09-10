"""Validate and promote M13.5 routed Catalyst hardware evidence.

The Vivado runner intentionally keeps bulky/vendor-specific products under the
ignored ``build/`` tree.  This module provides the M13.5.3 closure boundary:
it verifies the complete preserved evidence tree, regenerates the normalized
comparison to detect drift, and emits a compact machine-independent record that
can be committed under ``references/``.

No Catalyst RTL or thesis computational-core behavior is modified here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .m13_hardware_audit import (
    EXPECTED_VIVADO_VERSION,
    M13_5_RESULT_SCHEMA,
    load_hardware_manifest,
    require_vivado_2025_2,
)
from .m13_hardware_comparison import (
    M13_5_COMPARISON_SCHEMA,
    build_hardware_comparison,
    render_hardware_comparison_markdown,
)

M13_5_EVIDENCE_MANIFEST_SCHEMA = "neuromorphic-twin-m13-hardware-evidence-manifest-v1"
M13_5_CLOSURE_SCHEMA = "neuromorphic-twin-m13-hardware-closure-v1"

REQUIRED_NATIVE_REPORTS = (
    "synth_utilization.rpt",
    "synth_utilization_hier.rpt",
    "synth_timing.rpt",
    "kria_n1_impl.dcp",
    "timing_summary.rpt",
    "timing_paths.rpt",
    "utilization.rpt",
    "utilization_hier.rpt",
    "power.rpt",
    "clock_utilization.rpt",
    "design_analysis.rpt",
)

REQUIRED_EVIDENCE_FILES = (
    "catalyst-head.txt",
    "commands.txt",
    "vivado-version.txt",
    "synthesis.log",
    "implementation.log",
    "catalyst-hardware-result.json",
    "hardware-comparison.json",
    "hardware-comparison.md",
    "evidence-manifest.json",
    *(f"native_reports/{name}" for name in REQUIRED_NATIVE_REPORTS),
)


def verify_hardware_evidence_tree(evidence_dir: str | Path) -> dict[str, Any]:
    """Fail closed unless a preserved M13.5 Vivado evidence tree is self-consistent."""

    root = Path(evidence_dir).resolve()
    if not root.is_dir():
        raise ValueError(f"M13.5 evidence directory does not exist: {root}")

    missing = [rel for rel in REQUIRED_EVIDENCE_FILES if not (root / rel).is_file()]
    if missing:
        raise ValueError(f"M13.5 evidence tree missing required files: {missing}")

    frozen = load_hardware_manifest()
    result = _read_json(root / "catalyst-hardware-result.json")
    comparison = _read_json(root / "hardware-comparison.json")
    evidence = _read_json(root / "evidence-manifest.json")

    if result.get("schema") != M13_5_RESULT_SCHEMA:
        raise ValueError("unexpected M13.5 Catalyst hardware-result schema")
    if result.get("status") != "routed_implementation_observed":
        raise ValueError("M13.5 Catalyst result is not a routed implementation observation")
    if result.get("clock_period_ns") != frozen["reproduction_environment"]["clock_period_ns"]:
        raise ValueError("M13.5 Catalyst result changed the frozen clock period")
    if result.get("timing_closed") is not True:
        raise ValueError("M13.5 cannot close because routed Catalyst timing did not close")
    _validate_timing(result.get("timing"))
    _validate_resources(result.get("resources"))

    regenerated = build_hardware_comparison(result, manifest=frozen)
    if comparison != regenerated:
        raise ValueError("stored M13.5 hardware comparison does not match deterministic regeneration")
    if comparison.get("schema") != M13_5_COMPARISON_SCHEMA:
        raise ValueError("unexpected M13.5 hardware-comparison schema")
    if comparison.get("status") != "routed_hardware_comparison_available":
        raise ValueError("M13.5 routed comparison is not at the expected observed boundary")
    if comparison["latency_throughput"]["comparison_status"] != "withheld":
        raise ValueError("M13.5 fairness violation: latency/throughput was not withheld")
    if comparison["power_energy"]["comparison_status"] != "withheld":
        raise ValueError("M13.5 fairness violation: power/energy was not withheld")
    if comparison["physical_execution"]["catalyst"] is not False:
        raise ValueError("M13.5 fairness violation: routed Catalyst evidence was labeled physical")

    markdown = (root / "hardware-comparison.md").read_text(encoding="utf-8")
    if markdown != render_hardware_comparison_markdown(comparison):
        raise ValueError("stored M13.5 hardware-comparison Markdown does not match the JSON result")

    if evidence.get("schema") != M13_5_EVIDENCE_MANIFEST_SCHEMA:
        raise ValueError("unexpected M13.5 evidence-manifest schema")
    expected_evidence_fields = {
        "catalyst_commit": result["catalyst_commit"],
        "vivado": result["vivado"],
        "target_part": result["target_part"],
        "timing_closed": True,
        "strongest_catalyst_boundary": comparison["strongest_catalyst_boundary"],
        "latency_throughput_comparison": "withheld",
        "power_energy_comparison": "withheld",
        "physical_catalyst_execution": False,
    }
    for key, expected in expected_evidence_fields.items():
        if evidence.get(key) != expected:
            raise ValueError(f"M13.5 evidence-manifest field mismatch: {key}")

    if (root / "catalyst-head.txt").read_text(encoding="utf-8").strip() != result["catalyst_commit"]:
        raise ValueError("M13.5 catalyst-head.txt does not match the normalized result")
    if require_vivado_2025_2((root / "vivado-version.txt").read_text(encoding="utf-8")) != EXPECTED_VIVADO_VERSION:
        raise ValueError("M13.5 Vivado version evidence changed")

    commands = [line.strip() for line in (root / "commands.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    expected_commands = [
        frozen["catalyst_k26"]["source_supported_synthesis_command"],
        frozen["catalyst_k26"]["source_supported_implementation_command"],
    ]
    if commands != expected_commands:
        raise ValueError("M13.5 preserved vendor commands differ from the frozen reproduction commands")

    source_reports = result.get("source_reports")
    if not isinstance(source_reports, dict):
        raise ValueError("M13.5 result source_reports must be an object")
    if Path(str(source_reports.get("utilization", ""))).name != "utilization.rpt":
        raise ValueError("M13.5 utilization source-report identity changed")
    if Path(str(source_reports.get("timing", ""))).name != "timing_summary.rpt":
        raise ValueError("M13.5 timing source-report identity changed")

    hashes = evidence.get("files_sha256")
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("M13.5 evidence manifest has no file hashes")
    actual_files = {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and path.name != "evidence-manifest.json"
    }
    if set(hashes) != actual_files:
        missing_hashes = sorted(actual_files - set(hashes))
        stale_hashes = sorted(set(hashes) - actual_files)
        raise ValueError(
            "M13.5 evidence-manifest file set mismatch: "
            f"unhashed={missing_hashes} missing_files={stale_hashes}"
        )
    for rel, expected_digest in hashes.items():
        if not isinstance(expected_digest, str) or len(expected_digest) != 64:
            raise ValueError(f"invalid SHA-256 entry for M13.5 evidence file: {rel}")
        observed = _sha256(root / rel)
        if observed != expected_digest:
            raise ValueError(f"M13.5 evidence hash mismatch: {rel}")

    return {
        "root": root,
        "result": result,
        "comparison": comparison,
        "evidence_manifest": evidence,
        "evidence_manifest_sha256": _sha256(root / "evidence-manifest.json"),
    }


def build_hardware_closure(evidence_dir: str | Path) -> dict[str, Any]:
    """Build the compact tracked M13.5.3 closure artifact from validated evidence."""

    verified = verify_hardware_evidence_tree(evidence_dir)
    result = verified["result"]
    comparison = verified["comparison"]
    evidence = verified["evidence_manifest"]
    frozen = load_hardware_manifest()
    hashes = evidence["files_sha256"]

    native_hashes = {
        name: hashes[f"native_reports/{name}"]
        for name in REQUIRED_NATIVE_REPORTS
    }

    return {
        "schema": M13_5_CLOSURE_SCHEMA,
        "status": "validated_complete",
        "milestone": "M13.5",
        "strongest_catalyst_boundary": comparison["strongest_catalyst_boundary"],
        "source_pins": comparison["source_pins"],
        "reproduction": {
            "vivado": result["vivado"],
            "clock_hz": frozen["reproduction_environment"]["clock_target_hz"],
            "clock_period_ns": result["clock_period_ns"],
            "project_target_part": comparison["targets"]["project"],
            "catalyst_target_part": comparison["targets"]["catalyst"],
        },
        "configured_scope": comparison["configured_scope"],
        "routed_timing": comparison["routed_timing"],
        "resources": comparison["resources"],
        "behavioral_execution": comparison["behavioral_execution"],
        "comparison_limits": {
            "latency_throughput": comparison["latency_throughput"]["comparison_status"],
            "power_energy": comparison["power_energy"]["comparison_status"],
            "physical_catalyst_execution": comparison["physical_execution"]["catalyst"],
        },
        "evidence": {
            "local_layout": "build/m13_5/catalyst-k26-vivado",
            "evidence_manifest_sha256": verified["evidence_manifest_sha256"],
            "normalized_result_sha256": hashes["catalyst-hardware-result.json"],
            "normalized_comparison_sha256": hashes["hardware-comparison.json"],
            "normalized_comparison_markdown_sha256": hashes["hardware-comparison.md"],
            "native_reports_sha256": native_hashes,
        },
        "conclusion": (
            "The exact pinned Catalyst N1 K26-class RTL reproduced successfully through Vivado 2025.2 "
            "synthesis, placement, physical optimization, and routing at the frozen 100 MHz target. "
            "The pinned release does not provide a directly programmable KV260 integration, so routed "
            "implementation is the strongest source-supported Catalyst hardware boundary used by M13.5."
        ),
    }


def render_hardware_closure_markdown(closure: dict[str, Any]) -> str:
    if closure.get("schema") != M13_5_CLOSURE_SCHEMA:
        raise ValueError("unexpected M13.5 closure schema")
    timing = closure["routed_timing"]
    reproduction = closure["reproduction"]
    lines = [
        "# M13.5 Hardware Reproduction Closure",
        "",
        "**Status: validated complete at the source-supported routed-implementation boundary.**",
        "",
        f"- Catalyst pin: `{closure['source_pins']['catalyst_commit']}` (`{closure['source_pins']['catalyst_tag']}`)",
        f"- Vivado: {reproduction['vivado']}",
        f"- Clock target: {reproduction['clock_hz'] / 1_000_000:.0f} MHz / {reproduction['clock_period_ns']:.1f} ns",
        f"- Project target: `{reproduction['project_target_part']}`",
        f"- Catalyst target: `{reproduction['catalyst_target_part']}`",
        "",
        "## Routed timing",
        "",
        "| Metric | Project M12.5 | Catalyst N1 |",
        "| --- | ---: | ---: |",
        f"| WNS | {timing['project']['wns_ns']:+.3f} ns | {timing['catalyst']['wns_ns']:+.3f} ns |",
        f"| WHS | {timing['project']['whs_ns']:+.3f} ns | {timing['catalyst']['whs_ns']:+.3f} ns |",
        "",
        "Both values describe margin at the same nominal 10 ns constraint; neither is converted into a maximum-Fmax claim.",
        "",
        "## Resource context",
        "",
        "| Resource | Project M12.5 | Catalyst N1 |",
        "| --- | ---: | ---: |",
    ]
    for row in closure["resources"]:
        lines.append(
            f"| {row['resource']} | {_format_resource(row['project'])} | {_format_resource(row['catalyst'])} |"
        )
    lines.extend(
        [
            "",
            "Resource totals are contextual only: the target part strings, configured capacities, feature sets, and validation/debug infrastructure differ.",
            "",
            "## Evidence limits",
            "",
            "- Latency/throughput comparison remains withheld.",
            "- Power/energy comparison remains withheld.",
            "- Catalyst physical board execution remains false; routed implementation is not relabeled as physical execution.",
            "- The project retains its independent M12.5 physical 22-case / 166-tick / zero-mismatch evidence.",
            "",
            "## Closure conclusion",
            "",
            closure["conclusion"],
            "",
            f"Preserved evidence-manifest SHA-256: `{closure['evidence']['evidence_manifest_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_hardware_closure(
    evidence_dir: str | Path,
    *,
    output_json: str | Path,
    output_markdown: str | Path | None = None,
) -> dict[str, Any]:
    closure = build_hardware_closure(evidence_dir)
    json_path = Path(output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(closure, indent=2) + "\n", encoding="utf-8")
    if output_markdown is not None:
        md_path = Path(output_markdown)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(render_hardware_closure_markdown(closure), encoding="utf-8")
    return closure


def _validate_timing(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("M13.5 timing result must be an object")
    for key in ("wns_ns", "whs_ns"):
        observed = value.get(key)
        if not isinstance(observed, (int, float)):
            raise ValueError(f"M13.5 timing result missing numeric {key}")
        if observed < 0:
            raise ValueError(f"M13.5 routed timing is not closed: {key}={observed}")


def _validate_resources(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("M13.5 resources must be an object")
    for name in ("clb_luts", "clb_registers", "bram_tiles", "dsps"):
        resource = value.get(name)
        if not isinstance(resource, dict):
            raise ValueError(f"M13.5 result missing resource: {name}")
        used = resource.get("used")
        available = resource.get("available")
        percent = resource.get("utilization_percent")
        if not isinstance(used, (int, float)) or used < 0:
            raise ValueError(f"M13.5 resource has invalid used count: {name}")
        if available is not None and (not isinstance(available, (int, float)) or available <= 0):
            raise ValueError(f"M13.5 resource has invalid available count: {name}")
        if percent is not None and (not isinstance(percent, (int, float)) or not 0 <= percent <= 100):
            raise ValueError(f"M13.5 resource has invalid utilization percent: {name}")


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"M13.5 JSON artifact must contain an object: {path.name}")
    return data


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
