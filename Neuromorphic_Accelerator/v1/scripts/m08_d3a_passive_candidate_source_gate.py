#!/usr/bin/env python3
"""D3.1 PC-only fail-closed audit of the passive, NO-AXI, fan-first candidate.

This audits first-party source + versioned architecture manifest. Optional
native Vivado evidence can be checked after the owner runs Vivado offline.
No subprocess is launched, no files are written, no board is ever accessed.
A native report is an attestation of the owner's PC run, NOT physical proof.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_TCL = "scripts/m08_d3a_passive_fan_bd_candidate.tcl"
MANIFEST = "docs/M08_D3A_PASSIVE_CANDIDATE_MANIFEST.json"
ORIGINAL_FAN = "scripts/m08_path_a_fan_bd_candidate.tcl"
ORIGINAL_BD = "scripts/m08_page_ps_bd_candidate.tcl"
ORIGINAL_FAN_SHA256 = "56a6c7ed702abfcbe089ea09a145348559c3b48bd5a9f7b74861bbf85c3579b7"
ORIGINAL_BD_SHA256 = "ec2d43b84d84330f08a38e647470ba3b5a90d12a5ecc9518919479d5018d0ac2"
ORIGINAL_BAD_BIT_BIN_SHA256 = "a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b"
HPM = ("CONFIG.PSU__USE__M_AXI_GP0",
       "CONFIG.PSU__USE__M_AXI_GP1",
       "CONFIG.PSU__USE__M_AXI_GP2")
FORBIDDEN_TCL_CMDS = (
    "write_bitstream", "launch_runs", "program_hw_devices",
    "open_hw", "open_hw_manager", "connect_hw_server", "open_hw_target",
    "set_property PROGRAM.FILE", "source ", "exec ", "load_hw",
)
KNOWN_NATIVE = {
    "schema": "m08-d3a-kv260-passive-fan-bd-v1",
    "candidate": "m08-d3a-passive-fan-v1",
    "part": "xck26-sfvc784-2LV-c",
    "ps_preset": "YES",
    "ps_hpm0_fpd": "DISABLED",
    "ps_hpm1_fpd": "DISABLED",
    "ps_hpm0_lpd": "DISABLED",
    "smartconnect": "ABSENT",
    "identity_slave": "ABSENT",
    "page_slave": "ABSENT",
    "linux_uio_devices": "ZERO",
    "ps_pl0_runtime_enabled": "UNKNOWN",
    "afi_boot_ownership": "UNKNOWN",
    "ps_atb4_configuration": "UNKNOWN",
    "ps_timeout_protection": "NOT_PROVEN",
    "physical_fan_cooling": "NOT_PROVEN",
    "fan_source": "ps/emio_ttc0_wave_o[2]",
    "fan_route": "TTC0_WAVEOUT2_TO_A12",
    "fan_pin": "A12",
    "fan_iostandard": "LVCMOS33",
    "fan_slew": "SLOW",
    "fan_drive": "4",
    "validated_bd": "YES",
    "synthesis": "NOT_RUN",
    "implementation": "NOT_RUN",
    "bitstream": "NOT_GENERATED",
    "linux_dtbo": "NOT_GENERATED",
    "hardware_programmed": "NO",
    "hardware_mmio_authorized": "NO",
}
EXPECTED_XDC = (
    "# KV260 K26 original TTC0 channel-2 fan PWM route -> A12",
    "set_property PACKAGE_PIN A12 [get_ports {M08_FAN_PWM}]",
    "set_property IOSTANDARD LVCMOS33 [get_ports {M08_FAN_PWM}]",
    "set_property SLEW SLOW [get_ports {M08_FAN_PWM}]",
    "set_property DRIVE 4 [get_ports {M08_FAN_PWM}]",
)


class D3Rejected(ValueError):
    pass


def require(condition: bool, why: str) -> None:
    if not condition:
        raise D3Rejected(why)


def read_text(path: Path) -> tuple[str, str]:
    require(path.is_file() and not path.is_symlink(),
            "missing or symlinked D3 source/evidence: " + str(path))
    data = path.read_bytes()
    require(len(data) > 50 and len(data) < 1_000_000,
            "implausible D3 file length: " + str(path))
    return data.decode("utf-8"), sha256(data).hexdigest()


def verify_source(root: Path = ROOT) -> dict:
    source_sha = {}
    original, source_sha[ORIGINAL_BD] = read_text(root / ORIGINAL_BD)
    fan, source_sha[ORIGINAL_FAN] = read_text(root / ORIGINAL_FAN)
    script, source_sha[CANDIDATE_TCL] = read_text(root / CANDIDATE_TCL)
    manifest_text, source_sha[MANIFEST] = read_text(root / MANIFEST)
    require(source_sha[ORIGINAL_BD] == ORIGINAL_BD_SHA256,
            "original quarantined M08 PS BD changed; stop D3 source audit")
    require(source_sha[ORIGINAL_FAN] == ORIGINAL_FAN_SHA256,
            "original M08 TTC fan route changed; stop D3 source audit")
    require('CONFIG.PSU__TTC0__WAVEOUT__IO {EMIO}' in fan
            and 'PACKAGE_PIN A12' in fan
            and 'm08_ttc0_fan_slice' in fan,
            "original M08 trusted fan route not found")
    props = re.findall(
        r"CONFIG\.PSU__USE__M_AXI_GP[012]\s+([01])(?:\s|\\)",
        script,
    )
    require(len(props) == 3 and props == ["0", "0", "0"],
            "D3.1 must explicitly disable all three PS->PL AXI masters")
    for literal in (
        "create_project m08_d3a_passive_fan",
        "create_bd_design m08_d3a_passive_fan",
        "xck26-sfvc784-2LV-c",
        "xilinx.com:kv260_som:part0:*",
        "apply_board_preset",
        "CONFIG.PSU__FPGA_PL0_ENABLE 1",
        "CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ 100",
        "CONFIG.PSU__TTC0__WAVEOUT__ENABLE {1}",
        "CONFIG.PSU__TTC0__WAVEOUT__IO {EMIO}",
        "CONFIG.DIN_WIDTH 3 CONFIG.DIN_FROM 2 CONFIG.DIN_TO 2",
        "ps/emio_ttc0_wave_o",
        "M08_FAN_PWM",
        "PACKAGE_PIN A12",
        "IOSTANDARD LVCMOS33",
        "SLEW SLOW",
        "DRIVE 4",
        "get_bd_intf_pins -quiet $iface",
        "get_bd_pins -quiet $clockpin",
        "validate_bd_design -force",
        "write_bd_tcl -force $exported",
        "NO_BITSTREAM_NO_BOARD",
    ):
        require(literal in script, "D3.1 missing required source contract: " + literal)
    # Never permit an out-of-line source command, original HPM0 build, or
    # hardware operations in this independent passive generator.
    for line in script.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        for cmd in FORBIDDEN_TCL_CMDS:
            require(not trimmed.startswith(cmd),
                    "dangerous/inherited command in D3.1 generator: " + cmd)
        require("m08_page_ps_bd_candidate.tcl" not in trimmed
                and "m08_path_a_fan_bd_candidate.tcl" not in trimmed,
                "D3A must NOT source original active HPM0 generator")
    require("create_bd_cell -type ip -vlnv $ps_vlnv ps" in script
            and "create_bd_cell -type ip -vlnv $slice_vlnv m08_d3a_ttc0_fan_slice" in script,
            "D3A must instantiate PS and TTC fan slice only")
    require("create_bd_cell -type module" not in script
            and "connect_bd_intf_net" not in script
            and "assign_bd_address" not in script,
            "D3A must not generate any PS->PL AXI slave mapping")

    m = json.loads(manifest_text)
    require(m.get("schema") == "m08-d3a-passive-fan-candidate-manifest-v1"
            and m.get("candidate_id") == "m08-d3a-passive-fan-v1"
            and m.get("stage") == "D3.1_SOURCE_ONLY"
            and m.get("build_script") == CANDIDATE_TCL
            and m.get("expected_part") == "xck26-sfvc784-2LV-c",
            "D3 manifest identity/source drift")
    design = m.get("design", {})
    for key in ("ps_hpm0_fpd", "ps_hpm1_fpd", "ps_hpm0_lpd"):
        require(design.get(key) == "DISABLED", "D3A manifest AXI must be disabled: " + key)
    for key in ("smartconnect", "identity_axi_slave", "page_axi_slave"):
        require(design.get(key) == "ABSENT", "D3A manifest AXI slaves must be absent: " + key)
    require(design.get("linux_uio_windows") == 0
            and design.get("fan_pin") == "A12"
            and design.get("fan_source") == "PS_TTC0_EMIO_WAVEOUT_2"
            and design.get("ps_pl0_clock_requested_hz") == 100_000_000
            and design.get("ps_pl0_runtime_proven") is False
            and design.get("fan_native_fan_continuity_proven") is False,
            "D3A manifest fan/clock source-only contract drift")
    hw = m.get("hardware_safety", {})
    require(hw.get("original_m08_bitstream_quarantined") is True
            and hw.get("original_m08_bitstream_sha256") == ORIGINAL_BAD_BIT_BIN_SHA256
            and hw.get("stock_k26_remains_running") is True,
            "M08 original quarantine or stock recovery drift")
    for field in (
        "owner_hardware_programming_authorized", "owner_mmio_authorized",
        "D3_1_native_vivado_BD_validated", "D3_1_implementation_routed",
        "D3_1_bitstream_generated", "D3_1_linux_firmware_installed",
    ):
        require(hw.get(field) is False, "D3A manifest cannot claim hardware approval: " + field)
    blockers = m.get("D3_2_blocking_dependencies", {})
    require(len(blockers) == 7 and
            all(v in ("UNKNOWN", "NOT_AUTHORIZED") for v in blockers.values()),
            "D3.2 PS protection/clock/AFI/bridge/fan blockers must remain open")
    return {
        "schema": "m08-d3a-source-contract-audit-v1",
        "status": "D3A_PASSIVE_NO_PS_PL_AXI_SOURCE_CANDIDATE_ONLY",
        "source_sha256": source_sha,
        "ps_to_pl_master_ports_exposed": 0,
        "fan_route_pinned_in_source": "PS_TTC0_EMIO_WAVEOUT2_A12",
        "native_vivado_run": "NOT_CLAIMED",
        "physical_fan_or_clock_proof": False,
        "D3_2_protected_mmio_gate": "BLOCKED",
        "original_m08_bitstream_quarantined": True,
        "physical_programming_allowed": False,
    }


def verify_native(folder: Path) -> dict:
    require(folder.is_dir() and not folder.is_symlink(),
            "native Vivado PC evidence directory missing or symlinked")
    report, report_sha = read_text(folder / "10_d3a_passive_bd_readback.txt")
    xdc, xdc_sha = read_text(folder / "12_d3a_fan_a12.xdc")
    export, export_sha = read_text(folder / "11_d3a_passive_bd_export.tcl")
    require((folder / "d3a_project").is_dir(),
            "genuine Vivado project tree missing in evidence directory")
    lines = [line for line in report.splitlines() if line.strip()]
    require(all("=" in line for line in lines),
            "native report malformed")
    items = [line.split("=", 1) for line in lines]
    mapping = dict(items)
    require(len(items) == len(mapping), "native report duplicate keys")
    require(set(KNOWN_NATIVE).issubset(mapping), "native BD required field missing")
    for key, value in KNOWN_NATIVE.items():
        require(mapping[key] == value,
                "unsafe/incomplete native D3A report field: " + key)
    require(re.fullmatch(r"2025\.2(?:\..+)?", mapping.get("vivado_version", "")) is not None,
            "D3A native Vivado must be 2025.2")
    require(mapping.get("board_part", "").startswith("xilinx.com:kv260_som:part0:"),
            "D3A native board part is not the genuine K26 SOM")
    require(mapping.get("ps_pl0_nominal_request_mhz") in ("100", "100.0"),
            "D3A native PLL requested value changed")
    freq = mapping.get("ps_pl0_native_frequency_hz", "")
    require(freq.isdecimal() and abs(int(freq) - 100_000_000) <= 1000,
            "D3A native clock propagation deviated from original K26 preset")
    require(xdc.splitlines() == list(EXPECTED_XDC),
            "D3A fan A12 output constraints not exact")
    require("create_bd_design" in export and "m08_d3a_passive_fan" in export,
            "D3A exported genuine BD Tcl unexpected")
    return {
        "status": "D3A_NATIVE_OWNER_VIVADO_BD_READBACK_ACCEPTED_NOT_PHYSICAL",
        "native_pc_report_sha256": report_sha,
        "native_pc_fan_xdc_sha256": xdc_sha,
        "native_pc_bd_export_sha256": export_sha,
        "ps_pl0_hz_native_reported": int(freq),
        "native_clock_in_linux_proven": False,
        "physical_fan_continuity_proven": False,
        "PS_ATB4_timeout_proven": False,
        "hardware_bitstream_or_mmio_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-evidence-dir", type=Path,
                        help="Optional already-generated PC native Vivado D3A output")
    args = parser.parse_args()
    try:
        outcome = verify_source()
        if args.native_evidence_dir is not None:
            outcome["native"] = verify_native(args.native_evidence_dir)
    except (D3Rejected, UnicodeError, OSError, ValueError) as exc:
        print("M08_D3A_SOURCE_OR_NATIVE_GATE_REJECTED_NO_BOARD: " + str(exc),
              file=sys.stderr)
        return 2
    print(json.dumps(outcome, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
