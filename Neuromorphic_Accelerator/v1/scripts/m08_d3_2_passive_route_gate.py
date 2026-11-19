#!/usr/bin/env python3
"""M08 D3.2 PASSIVE route-only source and native PC report audit: never hardware."""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TCL = ROOT / "scripts/m08_d3_2_passive_route_only.tcl"
SYNTH_GATE = ROOT / "scripts/m08_d3_2_passive_synth_gate.py"
RUNNER = ROOT / "scripts/run_m08_d3_2_passive_route_pc.sh"
EXPECT = {
    "schema": "m08-d3-2-passive-route-only-v1",
    "candidate": "m08-d3a-passive-fan-v1",
    "part": "xck26-sfvc784-2LV-c",
    "route_run_progress": "100%",
    "ps_to_pl_axi": "DISABLED",
    "fan_port": "M08_FAN_PWM",
    "fan_pin": "A12",
    "fan_iostandard": "LVCMOS33",
    "report_drc": "GENERATED_NOT_A_PASS_CLAIM",
    "report_timing": "GENERATED_NOT_A_PASS_CLAIM",
    "report_clocks": "GENERATED_NOT_A_PASS_CLAIM",
    "bitstream": "NOT_GENERATED",
    "dtbo": "NOT_GENERATED",
    "board_programmed": "NO",
    "hardware_mmio_authorized": "NO",
    "physical_fan_continuity": "NOT_PROVEN",
}
BAD_TCL = (
    "write_bitstream", "program_hw_devices", "open_hw", "connect_hw_server",
    "write_device_image", "write_cfgmem", "write_hw_platform", "source ",
    "exec ", "launch_runs impl_1 -to_step write_bitstream",
    "set_property PROGRAM.FILE", "connect_bd_intf_net",
)


class RouteRejected(ValueError):
    pass


def require(test: bool, reason: str):
    if not test:
        raise RouteRejected(reason)


def safe_read(path: Path, cap: int = 4_000_000) -> tuple[str, str]:
    require(path.is_file() and not path.is_symlink(),
            "missing or linked route evidence: " + str(path))
    raw = path.read_bytes()
    require(0 < len(raw) <= cap, "empty or oversized route evidence: " + str(path))
    return raw.decode("utf-8"), sha256(raw).hexdigest()


def import_synth(root: Path):
    spec = importlib.util.spec_from_file_location(
        "m08_d3_2_synth_gate_for_route", root / "scripts/m08_d3_2_passive_synth_gate.py")
    require(spec is not None and spec.loader is not None, "missing passive source gate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_gate(root: Path = ROOT) -> dict:
    parent = import_synth(root)
    try:
        source = parent.source_gate(root)
    except parent.SynthRejected as exc:
        raise RouteRejected("passive source gate rejected: " + str(exc)) from exc
    require(source["physical_programming_authorized"] is False,
            "parent unexpectedly hardware-authorized")
    tcl, digest = safe_read(root / "scripts/m08_d3_2_passive_route_only.tcl")
    commands = [ln.strip() for ln in tcl.splitlines()
                if ln.strip() and not ln.lstrip().startswith("#")]
    for line in commands:
        require(not any(line.startswith(bad) for bad in BAD_TCL),
                "forbidden Vivado command in route-only stage: " + line)
        if line.startswith("launch_runs"):
            require(line == "launch_runs impl_1 -to_step route_design -jobs 2",
                    "only route_design implementation step permitted")
    require(commands.count("launch_runs impl_1 -to_step route_design -jobs 2") == 1,
            "one route_design step required")
    for required in (
        "m08_d3_2_passive_synth_",
        "m08_d3a_passive_fan.xpr",
        "20_passive_synth_readback.txt",
        "ps_to_pl_axi=DISABLED",
        "get_property $prop [get_bd_cells ps]",
        "get_bd_intf_pins -quiet $iface",
        "wait_on_run impl_1",
        "open_run impl_1",
        "report_timing_summary -file $timing_file",
        "report_drc -file $drc_file",
        "report_utilization -file $util_file",
        "report_clocks -file $clock_file",
        "get_property PACKAGE_PIN [get_ports M08_FAN_PWM]",
        "get_property IOSTANDARD [get_ports M08_FAN_PWM]",
        "bitstream=NOT_GENERATED",
        "hardware_mmio_authorized=NO",
        "M08_D3_2_PASSIVE_ROUTE_COMPLETE_REPORTS_NOT_REVIEWED_NO_BITSTREAM_NO_BOARD",
    ):
        require(required in tcl, "route source missing safety contract: " + required)
    runner, runner_sha = safe_read(root / "scripts/run_m08_d3_2_passive_route_pc.sh")
    for required in (
        "set -euo pipefail",
        "run_m08_d3_2_passive_synth_pc.sh",
        "m08_d3_2_passive_route_only.tcl",
        "99_evidence_sha256.txt",
        "98_route_evidence_sha256.txt",
    ):
        require(required in runner, "route runner missing evidence contract: " + required)
    for bad in ("program_hw_devices", "write_bitstream -", "xmutil unloadapp",
                "/dev/mem", "/dev/uio", "git clean", "rm -rf"):
        require(bad not in runner, "unsafe route runner: " + bad)
    return {
        "status": "M08_D3_2_PASSIVE_ROUTE_SOURCE_ACCEPTED_FOR_PC_ONLY",
        "stage_sha256": digest,
        "runner_sha256": runner_sha,
        "parent_source_status": source["status"],
        "genuine_route_proven": False,
        "routed_timing_and_drc_accepted": False,
        "physical_fan_proven": False,
        "bitstream_created": False,
        "hardware_mmio_authorized": False,
    }


def audit_native(run: Path) -> dict:
    require(run.is_dir() and not run.is_symlink(),
            "missing or symlinked owner run directory")
    require(re.fullmatch(r"m08_d3_2_passive_synth_[A-Za-z0-9]+", run.name)
            and run.parent.name == "M08",
            "not a fresh D3.2 passive evidence directory")
    root = run / "output"
    parent = import_synth(ROOT)
    try:
        checked = parent.native_report(root)
    except parent.SynthRejected as exc:
        raise RouteRejected("synth native report invalid: " + str(exc)) from exc
    require(checked["native_reported_synth_complete"]
            and not checked["routed_timing_validated"],
            "parent source evidence inconsistent")
    report, report_sha = safe_read(root / "40_passive_route_readback.txt")
    lines = [line.split("=", 1) for line in report.splitlines()]
    require(all(len(line) == 2 for line in lines)
            and len(dict(lines)) == len(lines), "malformed/duplicate route fields")
    values = dict(lines)
    for name, required in EXPECT.items():
        require(values.get(name) == required,
                "route report field invalid: " + name)
    require(re.fullmatch(r"2025\.2(?:\..+)?", values.get("vivado_version", ""))
            is not None, "route vendor version mismatch")
    require(values.get("board_part", "").startswith("xilinx.com:kv260_som:part0:"),
            "route board part not KV260")
    require("Complete!" in values.get("route_run_status", ""),
            "route_design not recorded complete")
    files = {
        "41_passive_route_timing.rpt": "timing",
        "42_passive_route_drc.rpt": "drc",
        "43_passive_route_utilization.rpt": "utilization",
        "44_passive_route_clocks.rpt": "clock",
    }
    hashes = {"40_passive_route_readback.txt": report_sha}
    for name, needle in files.items():
        body, digest = safe_read(root / name)
        require(needle in body.lower(), "unrecognizable route report: " + name)
        hashes[name] = digest
    return {
        "status": "M08_D3_2_OWNER_PC_ROUTE_REPORTS_INTEGRITY_REVIEWED_NOT_HARDWARE",
        "synth_parent": checked["status"],
        "report_sha256": hashes,
        "genuine_route_reported_complete": True,
        "drc_violations_independently_cleared": False,
        "routed_timing_independently_accepted": False,
        "cooling_and_boot_rollback_proven": False,
        "bitstream_generated": False,
        "hardware_mmio_authorized": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--native-run-dir", type=Path)
    args = ap.parse_args()
    try:
        data = source_gate()
        if args.native_run_dir is not None:
            data["native"] = audit_native(args.native_run_dir)
    except (RouteRejected, ValueError, KeyError, OSError, UnicodeError) as exc:
        print("M08_D3_2_PASSIVE_ROUTE_AUDIT_REJECTED_NO_HARDWARE: " + str(exc),
              file=sys.stderr)
        return 2
    print(json.dumps(data, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
