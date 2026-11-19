#!/usr/bin/env python3
"""PC-only source+synthetic/owner-native audit for passive KV260 synthesis.

The ONLY permitted Vivado job is synth_1 on a fresh D3.1 fan-only/no-HPM0
project. No implementation, bitstream, DTBO, JTAG, MMIO or physical signoff.
This reader never launches Vivado, opens any hardware, or writes evidence.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "scripts/m08_d3_2_passive_synth_only.tcl"
D3A_GATE = ROOT / "scripts/m08_d3a_passive_candidate_source_gate.py"
KNOWN = {
    "schema": "m08-d3-2-passive-synth-only-v1",
    "candidate": "m08-d3a-passive-fan-v1",
    "part": "xck26-sfvc784-2LV-c",
    "synth_run_progress": "100%",
    "ps_to_pl_axi": "DISABLED",
    "smartconnect": "ABSENT",
    "identity_slave": "ABSENT",
    "page_slave": "ABSENT",
    "fan_port": "M08_FAN_PWM",
    "fan_pin": "A12",
    "fan_iostandard": "LVCMOS33",
    "timing_report": "GENERATED_NOT_ROUTED",
    "implementation": "NOT_RUN",
    "bitstream": "NOT_GENERATED",
    "linux_dtbo": "NOT_GENERATED",
    "physical_fan_cooling": "NOT_PROVEN",
    "boot_atb4_aib13_afi_clock_ownership": "UNKNOWN",
    "hardware_programmed": "NO",
    "hardware_mmio_authorized": "NO",
}
FORBIDDEN_ACTIVE = (
    "write_bitstream", "launch_runs impl_1", "program_hw_devices",
    "open_hw_manager", "open_hw_target", "connect_hw_server", "source ",
    "exec ", "set_property PROGRAM.FILE", "write_hw_platform",
    "write_device_image", "write_cfgmem", "write_hw_ila_data",
    "write_bd_tcl -force", "create_project ", "connect_bd_intf_net",
)


class SynthRejected(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SynthRejected(message)


def safe_read(path: Path, cap: int = 2_000_000) -> tuple[str, str]:
    require(path.is_file() and not path.is_symlink(),
            "missing/symlinked PC evidence: " + str(path))
    blob = path.read_bytes()
    require(0 < len(blob) <= cap, "unbounded/empty PC evidence: " + str(path))
    return blob.decode("utf-8"), sha256(blob).hexdigest()


def source_gate(root: Path = ROOT) -> dict:
    # Dynamic import to avoid a separate package dependency.
    name = "m08_passive_source_gate"
    spec = importlib.util.spec_from_file_location(
        name, root / "scripts/m08_d3a_passive_candidate_source_gate.py")
    require(spec is not None and spec.loader is not None, "missing D3A source gate")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parent = module.verify_source(root)
    require(parent["ps_to_pl_master_ports_exposed"] == 0
            and parent["physical_programming_allowed"] is False,
            "parent D3A image not a passive no-AXI source")
    text, digest = safe_read(root / "scripts/m08_d3_2_passive_synth_only.tcl")
    active = [line.strip() for line in text.splitlines()
              if line.strip() and not line.lstrip().startswith("#")]
    for line in active:
        for bad in FORBIDDEN_ACTIVE:
            require(not line.startswith(bad),
                    "forbidden live/implementation Tcl command: " + bad)
        if line.startswith("launch_runs "):
            require(re.fullmatch(r"launch_runs synth_1 -jobs 2", line) is not None,
                    "only synth_1 may be launched")
    require(sum(line == "launch_runs synth_1 -jobs 2" for line in active) == 1,
            "exactly one synthesis-only run is required")
    for literal in (
        "m08_d3_2_passive_synth_",
        "2025.2",
        "10_d3a_passive_bd_readback.txt",
        "12_d3a_fan_a12.xdc",
        "11_d3a_passive_bd_export.tcl",
        "m08_d3a_passive_fan.xpr",
        "ps_hpm0_fpd=DISABLED",
        "ps_hpm1_fpd=DISABLED",
        "ps_hpm0_lpd=DISABLED",
        "get_property $prop [get_bd_cells ps]",
        "get_bd_intf_pins -quiet $iface",
        "validate_bd_design -force",
        "generate_target all $bd_files",
        "make_wrapper -files $bd_files -top",
        "set_property top m08_d3a_passive_fan_wrapper",
        "wait_on_run synth_1",
        "open_run synth_1",
        "report_utilization -file $util_report",
        "report_timing_summary -file $timing_report",
        "get_property PACKAGE_PIN [get_ports M08_FAN_PWM]",
        "get_property IOSTANDARD [get_ports M08_FAN_PWM]",
        "implementation=NOT_RUN",
        "bitstream=NOT_GENERATED",
        "hardware_mmio_authorized=NO",
        "M08_D3_2_PASSIVE_SYNTH_COMPLETE_NO_AXI_NO_IMPL_NO_BITSTREAM_NO_BOARD",
    ):
        require(literal in text, "missing passive synthesis source assertion: " + literal)
    return {
        "status": "M08_D3_2_PASSIVE_SYNTH_SOURCE_APPROVED_FOR_PC_OFFLINE_ONLY",
        "stage_tcl_sha256": digest,
        "parent": parent["status"],
        "native_synth_proven": False,
        "native_route_proven": False,
        "physical_programming_authorized": False,
        "hpm0_interface_present": False,
        "protected_hpm0_bitstream_authorized": False,
    }


def native_report(folder: Path) -> dict:
    require(folder.is_dir() and not folder.is_symlink(),
            "missing/symlinked fresh synthesis evidence folder")
    require(re.fullmatch(r"m08_d3_2_passive_synth_[a-zA-Z0-9]+",
                         folder.parent.name) is not None
            and folder.name == "output",
            "not an exclusively named new D3.2 synthesis folder")
    # Checking parent native BD proves only a fresh reported D3A scaffold.
    name = "m08_d3a_native_auditor"
    spec = importlib.util.spec_from_file_location(
        name, D3A_GATE)
    require(spec is not None and spec.loader is not None, "missing D3A native auditor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parent = module.verify_native(folder)
    body, report_sha = safe_read(folder / "20_passive_synth_readback.txt")
    entries = [line.split("=", 1) for line in body.splitlines()]
    require(all(len(pair) == 2 for pair in entries)
            and len(entries) == len(dict(entries)),
            "duplicate/invalid synthesis summary")
    report = dict(entries)
    for key, value in KNOWN.items():
        require(report.get(key) == value, "unsupported native synthesis field: " + key)
    require(re.fullmatch(r"2025\.2(?:\..+)?", report.get("vivado_version", "")) is not None,
            "unsupported Vivado version")
    require(report.get("board_part", "").startswith("xilinx.com:kv260_som:part0:"),
            "missing genuine KV260 board part")
    require("Complete!" in report.get("synth_run_status", ""),
            "native synthesis did not report completion")
    utilization, u_sha = safe_read(folder / "21_passive_synth_utilization.rpt")
    timing, t_sha = safe_read(folder / "22_passive_synth_timing.rpt")
    require("utilization" in utilization.lower()
            and "timing" in timing.lower(),
            "native reports not recognizable")
    return {
        "status": "M08_D3_2_REPORTED_PC_SYNTH_ONLY_EVIDENCE_REVIEWED_NOT_ROUTED",
        "sha256": {
            "20_passive_synth_readback.txt": report_sha,
            "21_passive_synth_utilization.rpt": u_sha,
            "22_passive_synth_timing.rpt": t_sha,
        },
        "parent_native": parent["status"],
        "native_reported_synth_complete": True,
        "routed_timing_validated": False,
        "bitstream_generated": False,
        "physical_fan_continuity_proven": False,
        "physical_mmio_authorized": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--native-output-dir", type=Path,
                    help="NEW owner-PC output folder, after running genuine Vivado synth_1")
    args = ap.parse_args()
    try:
        result = source_gate()
        if args.native_output_dir is not None:
            result["native"] = native_report(args.native_output_dir)
    except (SynthRejected, UnicodeError, ValueError, OSError, KeyError) as exc:
        print("M08_D3_2_PASSIVE_SYNTH_GATE_REJECTED_NO_BOARD: " + str(exc),
              file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
