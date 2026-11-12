#!/usr/bin/env python3
"""Independent ORIGINAL Vivado K26 TTC0-fan+M08-AXI post-route artifact audit.

This is an OFFLINE evidence-consistency audit. It does NOT sign off DRC,
unconstrained paths, physical fan continuity, FPGA programming or PS AXI.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys

SOURCES = (
    "rtl/m08/m08_axil_readonly_identity.v",
    "rtl/m08/m08_host_staged_page_bank.sv",
    "rtl/m08/m08_axil_page_control.sv",
    "rtl/m08/m08_ps_page_safe_shell.v",
    "scripts/m08_page_ps_bd_candidate.tcl",
    "scripts/m08_path_a_baseline_report_gate.tcl",
    "scripts/m08_path_a_fan_bd_candidate.tcl",
    "scripts/m08_path_a_fan_bd_audit.py",
    "scripts/run_m08_path_a_fan_bd.sh",
    "scripts/m08_path_a_fan_post_route.tcl",
    "scripts/m08_path_a_fan_post_route_audit.py",
    "scripts/run_m08_path_a_fan_post_route.sh",
)
NATIVE = (
    "01_vivado_fan_route.log",
    "02_vivado_page_bd_readback.txt",
    "03_page_bd_export.tcl",
    "20_m08_fan_bd_readback.txt",
    "21_m08_fan_pwm_a12.xdc",
    "22_m08_fan_bd_export.tcl",
    "40_fan_route_metrics.txt",
    "41_fan_timing_post_route.rpt",
    "42_fan_utilization_post_route.rpt",
    "43_fan_drc_post_route.rpt",
    "44_fan_methodology_post_route.rpt",
    "45_fan_clock_utilization_post_route.rpt",
    "46_fan_io_post_route.rpt",
    "47_fan_route_status_post_route.rpt",
    "48_fan_post_route.dcp",
)
MARKERS = (
    "M08_PAGE_GENUINE_VIVADO_BD_VALIDATED_NO_BITSTREAM_NO_BOARD",
    "M08_PATH_A_ORIGINAL_DUAL_AXI_REPORT_EXACT_SCOPE_OK",
    "M08_PATH_A_K26_FAN_BD_OFFLINE_VALIDATED_NO_BOARD_NO_BITSTREAM",
    "M08_PATH_A_FAN_NATIVE_WRAPPER_GENERATED=1",
    "M08_PATH_A_FAN_NATIVE_SYNTH_AND_ROUTE_COMPLETE=1",
    "M08_PATH_A_FAN_ROUTED_IO_A12_LVCMOS33_OUT=1",
    "M08_PATH_A_FAN_NATIVE_POST_ROUTE_NONNEGATIVE_SLACK=1",
    "M08_PATH_A_FAN_ROUTE_REPORTS_GENERATED_DRC_UNREVIEWED_NO_BITSTREAM_NO_BOARD",
)
METRIC_KEYS = (
    "scope", "part", "vivado_version", "synthesis_status", "implementation_status",
    "synthesis_progress", "implementation_progress", "wns_ns", "whs_ns",
    "clock_count", "fan_port", "fan_pin", "fan_iostandard", "fan_direction",
    "fan_slew", "fan_drive", "no_bitstream", "no_board_programming",
    "compute_enabled", "physical_fan_continuity", "linux_overlay", "ps_axi",
    "physical_ddr",
)


def original(folder: Path, name: str) -> bytes:
    path = folder / name
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing/symlinked ORIGINAL artifact: " + name)
    contents = path.read_bytes()
    if not contents:
        raise ValueError("empty ORIGINAL artifact: " + name)
    return contents


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def independent_audit(folder: Path, root: Path) -> dict:
    if not folder.is_dir() or folder.is_symlink() or not root.is_dir():
        raise ValueError("invalid original evidence directory or source root")
    if original(folder, "03_route_status.txt") != b"vivado_exit_status=0\n":
        raise ValueError("native Vivado route did not exit successfully")
    manifest = "".join(
        f"{sha(root / name)}  {name}\n" for name in SOURCES
    ).encode()
    if original(folder, "00_source_sha256_before.txt") != manifest:
        raise ValueError("original source SHAs do not match current checkout")
    if original(folder, "04_source_sha256_after.txt") != manifest:
        raise ValueError("source changed during genuine route")
    log = original(folder, NATIVE[0]).decode("utf-8", errors="replace")
    if "ERROR:" in log or "CRITICAL WARNING:" in log or "Common 17-39" in log:
        raise ValueError("severe native Vivado error/critical warning")
    for marker in MARKERS:
        if sum(line.strip() == marker for line in log.splitlines()) != 1:
            raise ValueError("missing or duplicate WHOLE native marker: " + marker)
    bd = original(folder, NATIVE[1]).decode("utf-8")
    for marker in (
        "META|scope|M08_GENUINE_LOCAL_KV260_PS_TO_IDENTITY_AND_SAFE_PAGE_BD",
        "META|compute_enabled|NO", "META|validated_bd|YES",
        "META|physical_kv260|NOT_PROGRAMMED",
    ):
        if bd.splitlines().count(marker) != 1:
            raise ValueError("invalid original M08 baseline BD line: " + marker)
    fan = original(folder, NATIVE[3]).decode("utf-8")
    for marker in (
        "fan_source=ps/emio_ttc0_wave_o[2]", "fan_pin=A12",
        "fan_iostandard=LVCMOS33", "fan_output_width=1",
        "fan_ttc0_enable=1", "fan_ttc0_io=EMIO",
        "validated_bd=YES", "board_programmed=NO",
        "physical_fan_pwm_verified=NO",
    ):
        if fan.splitlines().count(marker) != 1:
            raise ValueError("invalid original M08 fan BD contract: " + marker)
    windows = {}
    for prefix, address in (("APERTURE_IDENTITY", 0xA0000000),
                            ("APERTURE_PAGE", 0xA0001000)):
        for report in (bd, fan):
            lines = [line for line in report.splitlines()
                     if line.startswith(prefix + "|")]
            if len(lines) != 1:
                raise ValueError("missing or ambiguous original mapped " + prefix)
            fields = lines[0].split("|")
            if (len(fields) != 4 or not fields[1] or
                not re.fullmatch(r"0x[0-9A-Fa-f]+", fields[2]) or
                not re.fullmatch(r"0x[0-9A-Fa-f]+", fields[3]) or
                int(fields[2], 16) != address or int(fields[3], 16) != 4096):
                raise ValueError("changed M08 PS aperture: " + prefix)
        windows[prefix] = f"0x{address:08x}"
    from m08_path_a_fan_bd_audit import EXPECTED_FAN_XDC
    xdc = original(folder, NATIVE[4]).decode("utf-8")
    active_xdc = [
        line.strip() for line in xdc.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if tuple(active_xdc) != EXPECTED_FAN_XDC:
        raise ValueError("original K26 A12 fan XDC mutated")
    export = original(folder, NATIVE[5]).decode("utf-8")
    if not all(x in export for x in ("M08_FAN_PWM", "emio_ttc0_wave_o",
                                    "m08_ttc0_fan_slice")):
        raise ValueError("genuine fan connection not in BD export")
    metrics = {}
    for line in original(folder, NATIVE[6]).decode("utf-8").splitlines():
        fields = line.split("|")
        if len(fields) != 3 or fields[0] != "META" or fields[1] in metrics:
            raise ValueError("malformed or duplicate route metrics")
        metrics[fields[1]] = fields[2]
    if set(metrics) != set(METRIC_KEYS):
        raise ValueError("missing or extra route metrics")
    for name, value in (
        ("scope", "M08_PATH_A_NATIVE_K26_FAN_AND_DUAL_AXI_POST_ROUTE"),
        ("part", "xck26-sfvc784-2LV-c"),
        ("synthesis_progress", "100%"),
        ("implementation_progress", "100%"),
        ("fan_port", "M08_FAN_PWM"), ("fan_pin", "A12"),
        ("fan_iostandard", "LVCMOS33"), ("fan_direction", "OUT"),
        ("fan_slew", "SLOW"), ("fan_drive", "4"),
        ("no_bitstream", "YES"), ("no_board_programming", "YES"),
        ("compute_enabled", "NO"),
        ("physical_fan_continuity", "NOT_VERIFIED"),
        ("linux_overlay", "NOT_INSTALLED"), ("ps_axi", "NOT_ACCESSED"),
        ("physical_ddr", "NOT_ACCESSED"),
    ):
        if metrics[name] != value:
            raise ValueError("invalid route evidence metric " + name)
    if (not metrics["vivado_version"].startswith("2025.2") or
        "Complete" not in metrics["synthesis_status"] or
        "Complete" not in metrics["implementation_status"]):
        raise ValueError("route did not finish using expected genuine Vivado")
    slacks = {}
    for name in ("wns_ns", "whs_ns"):
        try:
            value = float(metrics[name])
        except ValueError as exc:
            raise ValueError("invalid route timing slack " + name) from exc
        if not math.isfinite(value) or value < 0 or value > 1000:
            raise ValueError("route timing slack negative or nonfinite " + name)
        slacks[name] = value
    if not metrics["clock_count"].isdigit() or int(metrics["clock_count"]) < 1:
        raise ValueError("no genuine route clocks")
    for name in NATIVE[7:14]:
        if len(original(folder, name)) < 50:
            raise ValueError("implausibly short vendor report: " + name)
    if len(original(folder, NATIVE[14])) < 1024:
        raise ValueError("missing/implausibly small routed DCP")
    return {
        "schema": "m08-path-a-fan-route-evidence-v1",
        "status": "ORIGINAL_K26_FAN_AND_M08_DUAL_AXI_ROUTE_CONSISTENT_DRC_AND_UNCONSTRAINED_REVIEW_PENDING",
        "native_vivado_routed": True,
        "post_route_slack_ns": slacks,
        "actual_fan_port_pin": "A12",
        "original_m08_address_windows": windows,
        "original_native_sha256": {name: sha(folder / name) for name in NATIVE},
        "source_manifest_sha256": sha(folder / "00_source_sha256_before.txt"),
        "drc_waived": False,
        "drc_signoff": "NOT_DONE",
        "unconstrained_path_signoff": "NOT_DONE",
        "bitstream_generated": False,
        "linux_overlay_installed": False,
        "board_programmed": False,
        "fan_continuity_verified": False,
        "ps_axi_readback_verified": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence", type=Path, required=True)
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("audit output must be new")
        if args.output.parent.resolve() != args.evidence.resolve():
            raise ValueError("audit output must be inside original evidence directory")
        receipt = independent_audit(args.evidence, args.source_root)
        with args.output.open("x", encoding="utf-8") as dest:
            json.dump(receipt, dest, indent=2, sort_keys=True)
            dest.write("\n")
    except (ValueError, OSError, UnicodeError, KeyError) as exc:
        print("M08_PATH_A_FAN_ROUTE_AUDIT_REJECTED:", exc, file=sys.stderr)
        return 2
    print("M08_PATH_A_FAN_NATIVE_ROUTED_SHA_AUDITED_DRC_UNCONSTRAINED_PENDING_NO_BOARD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
