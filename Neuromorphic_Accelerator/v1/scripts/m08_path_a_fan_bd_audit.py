#!/usr/bin/env python3
"""Fail-closed original Vivado M08.2b Path A fan BD artifact auditor.

This reviews first-party source identities and original Vivado TEXT artifacts.
It does not test hardware fan continuity, route, bitstream, Linux or PS MMIO.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

SOURCE_FILES = (
    "rtl/m08/m08_axil_readonly_identity.v",
    "rtl/m08/m08_host_staged_page_bank.sv",
    "rtl/m08/m08_axil_page_control.sv",
    "rtl/m08/m08_ps_page_safe_shell.v",
    "scripts/m08_page_ps_bd_candidate.tcl",
    "scripts/m08_path_a_fan_bd_candidate.tcl",
    "scripts/run_m08_path_a_fan_bd.sh",
)
EXPECTED_FAN_XDC = (
    "set_property PACKAGE_PIN A12 [get_ports {M08_FAN_PWM}]",
    "set_property IOSTANDARD LVCMOS33 [get_ports {M08_FAN_PWM}]",
    "set_property SLEW SLOW [get_ports {M08_FAN_PWM}]",
    "set_property DRIVE 4 [get_ports {M08_FAN_PWM}]",
)
ID = 0xA0000000
PAGE = 0xA0001000


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def audit(evidence: Path, source_root: Path) -> dict:
    require(evidence.is_dir() and source_root.is_dir(), "missing evidence/source directory")
    before = evidence / "00_source_sha256_before.txt"
    after = evidence / "04_source_sha256_after.txt"
    require(before.read_bytes() == after.read_bytes(), "checkout mutated during vendor tool run")
    expected_rows = [
        f"{digest(source_root / name)}  {name}" for name in SOURCE_FILES
    ]
    require(before.read_text().splitlines() == expected_rows, "source manifest drift/tamper")
    require((evidence / "03_run_result.txt").read_text().strip()
            == "vivado_exit_status=0", "Vivado reported failure")
    log = (evidence / "01_vivado_fan_bd.log").read_text()
    require("M08_PAGE_GENUINE_VIVADO_BD_VALIDATED_NO_BITSTREAM_NO_BOARD" in log,
            "original M08 real BD validation marker missing")
    require("M08_PATH_A_K26_FAN_BD_OFFLINE_VALIDATED_NO_BOARD_NO_BITSTREAM" in log,
            "new M08 real fan BD validation marker missing")
    require("ERROR:" not in log and "CRITICAL WARNING:" not in log,
            "Vivado vendor log reports error/critical warning")
    baseline = (evidence / "02_vivado_page_bd_readback.txt").read_text()
    fan = (evidence / "20_m08_fan_bd_readback.txt").read_text()
    def check_unique(text: str, key: str, value: str) -> None:
        require(text.splitlines().count(f"{key}={value}") == 1,
                f"missing/ambiguous {key}={value}")
    for token in (
        "META|validated_bd|YES", "META|compute_enabled|NO",
        "META|physical_kv260|NOT_PROGRAMMED",
    ):
        require(baseline.splitlines().count(token) == 1, f"invalid baseline: {token}")
    check_unique(fan, "schema", "m08-path-a-kv260-fan-bd-offline-v1")
    check_unique(fan, "fan_source", "ps/emio_ttc0_wave_o[2]")
    check_unique(fan, "fan_route", "ps/emio_ttc0_wave_o->m08_ttc0_fan_slice[2]->M08_FAN_PWM")
    check_unique(fan, "fan_pin", "A12")
    check_unique(fan, "fan_iostandard", "LVCMOS33")
    check_unique(fan, "fan_ttc0_enable", "1")
    check_unique(fan, "fan_ttc0_io", "EMIO")
    check_unique(fan, "original_compute_enabled", "NO")
    for key, val in (
        ("validated_bd", "YES"),
        ("physical_fan_pwm_verified", "NO"),
        ("routed", "NO"),
        ("bitstream_generated", "NO"),
        ("linux_overlay_installed", "NO"),
        ("board_programmed", "NO"),
    ):
        check_unique(fan, key, val)
    require(fan.count("fan_output_width=1") == 1,
            "fan must be exactly one PS TTC0 wave output bit")
    addresses = {}
    for text in (baseline, fan):
        for name, expected in (("APERTURE_IDENTITY", ID), ("APERTURE_PAGE", PAGE)):
            matches = [line for line in text.splitlines() if line.startswith(name + "|")]
            require(len(matches) == 1, f"missing/ambiguous {name}")
            chunks = matches[0].split("|")
            require(len(chunks) == 4, f"bad {name} format")
            _, address_obj, offset, size = chunks
            require(address_obj != "" and re.fullmatch(r"0x[0-9a-fA-F]+", offset)
                    is not None and re.fullmatch(r"0x[0-9a-fA-F]+", size)
                    is not None and int(offset, 16) == expected and int(size, 16) == 4096,
                    f"{name} mapped outside original accepted 4KiB aperture")
            addresses[(name, len(addresses)//2)] = (offset, size)
    xdc = (evidence / "21_m08_fan_pwm_a12.xdc").read_text()
    active = [line.strip() for line in xdc.splitlines()
              if line.strip() and not line.lstrip().startswith("#")]
    require(active == list(EXPECTED_FAN_XDC), "A12 XDC changed/unexpected constraint")
    export = (evidence / "22_m08_fan_bd_export.tcl").read_text()
    require("m08_ttc0_fan_slice" in export and "M08_FAN_PWM" in export
            and "emio_ttc0_wave_o" in export,
            "exported native BD does not contain complete TTC0 fan route")
    require((evidence / "03_page_bd_export.tcl").is_file(),
            "original BD export absent")
    return {
        "schema": "m08-path-a-fan-bd-audit-v1",
        "status": "ORIGINAL_VIVADO_FAN_BD_EVIDENCE_CONSISTENT_NOT_ROUTED_NOT_PROGRAMMED",
        "source_sha256_verified": len(SOURCE_FILES),
        "original_ps_axi_windows_verified": True,
        "fan_waveout": "emio_ttc0_wave_o[2]",
        "fan_pin": "A12",
        "fan_iostandard": "LVCMOS33",
        "native_bd_validated": True,
        "post_route_timing": "NOT_RUN",
        "physical_fan_control": "NOT_VERIFIED",
        "bitstream_generated": False,
        "physical_board_programmed": False,
        "linux_device_tree_loaded": False,
        "ps_axi_readback": "NOT_VERIFIED",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", required=True, type=Path)
    ap.add_argument("--source-root", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    require(not args.output.exists(), "audit must not overwrite original evidence")
    data = audit(args.evidence, args.source_root)
    with args.output.open("x", encoding="utf-8") as out:
        json.dump(data, out, indent=2, sort_keys=True)
        out.write("\n")
    print(data["status"])


if __name__ == "__main__":
    main()
