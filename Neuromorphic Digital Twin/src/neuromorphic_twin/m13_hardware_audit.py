"""M13.5 Catalyst K26-class hardware reproduction and report parsing.

This module validates the frozen M13.5 hardware-comparison contract, checks that
Catalyst remains at the exact M13.1 pin, and parses only vendor-generated report
quantities. It does not alter Catalyst RTL or the thesis computational core.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable

from .m13_reference_manifest import M13_CATALYST_COMMIT, verify_catalyst_checkout

M13_5_HARDWARE_SCHEMA = "neuromorphic-twin-m13-hardware-comparison-v1"
M13_5_RESULT_SCHEMA = "neuromorphic-twin-m13-hardware-result-v1"
EXPECTED_VIVADO_VERSION = "2025.2"


@dataclass(frozen=True, slots=True)
class UtilizationValue:
    used: float
    available: float | None
    utilization_percent: float | None


def default_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "references" / "m13_5_hardware_manifest.json"


def load_hardware_manifest(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path is not None else default_manifest_path()
    data = json.loads(p.read_text(encoding="utf-8"))
    validate_hardware_manifest(data)
    return data


def validate_hardware_manifest(data: dict[str, Any]) -> None:
    if data.get("schema") != M13_5_HARDWARE_SCHEMA:
        raise ValueError(f"unexpected M13.5 schema: {data.get('schema')!r}")
    if data.get("status") != "preflight_frozen_pending_vivado_reproduction":
        raise ValueError("M13.5 manifest must remain at the pre-vendor frozen boundary")

    baseline = _obj(data, "baseline")
    if baseline.get("catalyst_commit") != M13_CATALYST_COMMIT:
        raise ValueError("M13.5 Catalyst commit differs from the M13.1 pin")
    if baseline.get("m13_4_main_merge") != "54c7840dff765d585e7ff236845b085007405c05":
        raise ValueError("M13.5 must start from the merged M13.4 baseline")

    env = _obj(data, "reproduction_environment")
    if env.get("vivado") != EXPECTED_VIVADO_VERSION:
        raise ValueError("M13.5 reproduction Vivado version changed")
    if env.get("clock_target_hz") != 100_000_000 or env.get("clock_period_ns") != 10.0:
        raise ValueError("M13.5 clock boundary changed")

    catalyst = _obj(data, "catalyst_k26")
    expected = {
        "upstream_target_part": "xczu5ev-sfvc784-2-i",
        "configured_cores": 2,
        "neurons_per_core": 256,
        "total_configured_neurons": 512,
        "pool_depth_per_core": 4096,
        "clock_hz": 100_000_000,
    }
    for key, value in expected.items():
        if catalyst.get(key) != value:
            raise ValueError(f"M13.5 Catalyst K26 field changed: {key}")
    if catalyst.get("source_directory_files_at_pin") != [
        "build_kria.tcl",
        "kria_neuromorphic.v",
        "kria_neuromorphic_8core_backup.v",
        "run_impl.tcl",
    ]:
        raise ValueError("M13.5 pinned Kria directory inventory changed")
    if _obj(catalyst, "physical_programming_boundary").get("source_supported") is not False:
        raise ValueError("M13.5 must not claim a pinned programmable KV260 image")

    project = _obj(data, "project_m12_physical")
    if project.get("target_part") != "xck26-sfvc784-2LV-c":
        raise ValueError("M12 project target part changed")
    if _obj(project, "behavioral_validation") != {"cases": 22, "ticks": 166, "mismatches": 0}:
        raise ValueError("M12.5 behavioral-validation baseline changed")
    timing = _obj(project, "timing")
    if timing.get("wns_ns") != 0.493 or timing.get("whs_ns") != 0.011:
        raise ValueError("M12.5 routed timing baseline changed")

    rules = data.get("fairness_rules")
    if not isinstance(rules, list) or len(rules) < 7:
        raise ValueError("M13.5 fairness rules are incomplete")
    joined = "\n".join(str(v) for v in rules)
    for required in (
        "not a performance contest",
        "xczu5ev-sfvc784-2-i",
        "xck26-sfvc784-2LV-c",
        "Do not compare M12 latency/throughput",
        "Do not compare power",
    ):
        if required not in joined:
            raise ValueError(f"M13.5 fairness boundary missing: {required}")


def verify_catalyst_k26_checkout(checkout: str | Path) -> dict[str, Any]:
    root = Path(checkout).resolve()
    verified = verify_catalyst_checkout(root, require_clean=True)
    manifest = load_hardware_manifest()
    catalyst = _obj(manifest, "catalyst_k26")

    kria_dir = root / catalyst["source_directory"]
    actual_files = sorted(p.name for p in kria_dir.iterdir() if p.is_file())
    if actual_files != catalyst["source_directory_files_at_pin"]:
        raise ValueError(
            "Catalyst pinned fpga/kria file inventory changed: "
            f"expected={catalyst['source_directory_files_at_pin']} actual={actual_files}"
        )

    build_text = (root / catalyst["build_script"]).read_text(encoding="utf-8")
    impl_text = (root / catalyst["implementation_script"]).read_text(encoding="utf-8")
    wrapper_text = (root / catalyst["wrapper"]).read_text(encoding="utf-8")

    required_build = (
        'set mode "full"',
        'if {$mode eq "synth_only"}',
        'launch_runs synth_1 -jobs 4',
        'report_utilization -file ${project_dir}/synth_utilization.rpt',
    )
    required_impl = (
        'open_checkpoint $synth_dcp',
        'create_clock -period 10.000 -name sys_clk',
        'route_design',
        'write_checkpoint -force ${out_dir}/kria_n1_impl.dcp',
        'report_timing_summary -file ${out_dir}/timing_summary.rpt',
        'report_utilization -file ${out_dir}/utilization.rpt',
    )
    required_wrapper = (
        'parameter NUM_CORES      = 2',
        'parameter NUM_NEURONS    = 256',
        'parameter POOL_DEPTH     = 4096',
        '.CLK_FREQ       (100_000_000)',
    )
    for text, fragments in (
        (build_text, required_build),
        (impl_text, required_impl),
        (wrapper_text, required_wrapper),
    ):
        for fragment in fragments:
            if fragment not in text:
                raise ValueError(f"Catalyst K26 source fragment missing: {fragment}")

    if "write_bitstream" in build_text.lower() or "write_bitstream" in impl_text.lower():
        raise ValueError("M13.5 physical-programming boundary changed: pinned Tcl now writes a bitstream")
    if any(p.suffix.lower() == ".xdc" for p in kria_dir.iterdir()):
        raise ValueError("M13.5 physical-programming boundary changed: pinned Kria XDC now exists")

    return {
        "checkout": str(root),
        "commit": verified.commit,
        "source_directory_files": actual_files,
        "upstream_target_part": catalyst["upstream_target_part"],
        "clock_period_ns": manifest["reproduction_environment"]["clock_period_ns"],
        "physical_programming_source_supported": False,
    }


def parse_vivado_version(text: str) -> str:
    match = re.search(r"Vivado(?:\s+Design\s+Suite)?\s+v?(\d{4}\.\d+)", text, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"Vivado\s+v(\d{4}\.\d+)", text, flags=re.IGNORECASE)
    if not match:
        raise ValueError("could not identify Vivado version")
    return match.group(1)


def require_vivado_2025_2(text: str) -> str:
    version = parse_vivado_version(text)
    if version != EXPECTED_VIVADO_VERSION:
        raise ValueError(f"M13.5 requires Vivado {EXPECTED_VIVADO_VERSION}; observed {version}")
    return version


def parse_utilization_report(text: str) -> dict[str, UtilizationValue]:
    rows: dict[str, UtilizationValue] = {}
    aliases = {
        "clb_luts": ("CLB LUTs", "Slice LUTs"),
        "clb_registers": ("CLB Registers", "Slice Registers"),
        "bram_tiles": ("Block RAM Tile", "Block RAM Tiles"),
        "dsps": ("DSPs", "DSP"),
        "uram": ("URAM", "URAMs"),
    }

    table_rows = list(_pipe_rows(text))
    for canonical, names in aliases.items():
        match = next((row for row in table_rows if row and row[0] in names), None)
        if match is None:
            continue
        numeric = [_number_or_none(cell) for cell in match[1:]]
        numeric = [value for value in numeric if value is not None]
        if not numeric:
            continue
        used = float(numeric[0])
        available = float(numeric[-2]) if len(numeric) >= 3 else None
        percent = float(numeric[-1]) if len(numeric) >= 2 else None
        rows[canonical] = UtilizationValue(used, available, percent)

    required = {"clb_luts", "clb_registers", "bram_tiles", "dsps"}
    missing = required - rows.keys()
    if missing:
        raise ValueError(f"Vivado utilization report missing required rows: {sorted(missing)}")
    return rows


def parse_timing_summary(text: str) -> dict[str, float]:
    lines = [line.strip() for line in text.splitlines()]
    for i, line in enumerate(lines):
        if "WNS(ns)" not in line or "WHS(ns)" not in line:
            continue
        header = line.split()
        try:
            wns_index = header.index("WNS(ns)")
            whs_index = header.index("WHS(ns)")
        except ValueError as exc:
            raise ValueError("timing header lacks WNS/WHS columns") from exc
        for candidate in lines[i + 1 : i + 8]:
            tokens = candidate.split()
            if len(tokens) <= max(wns_index, whs_index):
                continue
            try:
                return {
                    "wns_ns": float(tokens[wns_index]),
                    "whs_ns": float(tokens[whs_index]),
                }
            except ValueError:
                continue
    # Common alternate report wording.
    wns = re.search(r"Worst Negative Slack.*?(-?\d+(?:\.\d+)?)\s*ns", text, flags=re.I | re.S)
    whs = re.search(r"Worst Hold Slack.*?(-?\d+(?:\.\d+)?)\s*ns", text, flags=re.I | re.S)
    if wns and whs:
        return {"wns_ns": float(wns.group(1)), "whs_ns": float(whs.group(1))}
    raise ValueError("could not parse WNS/WHS from Vivado timing summary")


def build_catalyst_hardware_result(
    *,
    vivado_version: str,
    utilization_text: str,
    timing_text: str,
    source_reports: dict[str, str] | None = None,
) -> dict[str, Any]:
    if vivado_version != EXPECTED_VIVADO_VERSION:
        raise ValueError("refusing to freeze M13.5 result from a different Vivado version")
    manifest = load_hardware_manifest()
    utilization = parse_utilization_report(utilization_text)
    timing = parse_timing_summary(timing_text)
    return {
        "schema": M13_5_RESULT_SCHEMA,
        "status": "routed_implementation_observed",
        "catalyst_commit": manifest["baseline"]["catalyst_commit"],
        "vivado": vivado_version,
        "target_part": manifest["catalyst_k26"]["upstream_target_part"],
        "clock_period_ns": manifest["reproduction_environment"]["clock_period_ns"],
        "timing": timing,
        "timing_closed": timing["wns_ns"] >= 0.0 and timing["whs_ns"] >= 0.0,
        "resources": {
            name: {
                "used": value.used,
                "available": value.available,
                "utilization_percent": value.utilization_percent,
            }
            for name, value in utilization.items()
        },
        "source_reports": source_reports or {},
        "physical_programming_source_supported": False,
        "comparison_boundary": "Catalyst source-supported routed implementation; no physical KV260 execution claimed",
    }


def _pipe_rows(text: str) -> Iterable[list[str]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.count("|") < 3:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and not all(set(cell) <= {"-", "+", "="} for cell in cells if cell):
            yield cells


def _number_or_none(value: str) -> float | None:
    cleaned = value.strip().replace(",", "").replace("<", "").replace(">", "")
    cleaned = cleaned.rstrip("%")
    if not cleaned or cleaned in {"-", "N/A"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _obj(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"M13.5 field must be an object: {key}")
    return value
