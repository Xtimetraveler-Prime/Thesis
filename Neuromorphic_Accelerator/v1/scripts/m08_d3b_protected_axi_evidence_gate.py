#!/usr/bin/env python3
"""D3.2 read-only PC evidence gate: verify D3.1 native run, NEVER authorize MMIO.

All run materials are *original text artifacts* with pinned SHA256, not the
Vivado project binary or a physical K26 clock/ATB state. The D3.2 PS ATB4,
AIB13, Linux and 128-bit AFI requirements are deliberately left BLOCKED.
No subprocess, board access, hardware registers, or file writes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/M08_D3B_PROTECTED_AXI_ARCHITECTURE_CONTRACT.json"
RECEIPT = "99_evidence_sha256.txt"
STATUS = "D3B_CONTRACT_CREATED_PROTECTED_AXI_HARDWARE_BLOCKED"
ALLOWED_FIELDS = {
    "ATB4_RESP_EN", "ATB4_RESP_TYPE", "ATB4_TIMEOUT_PRESCALE",
    "ATB4_ERROR_TELEMETRY", "AIB13_ISOLATION", "OUTSTANDING_AR_R_AW_W_B",
    "PL0_CLOCK_RESET", "FPD_HPM0_AFI_WIDTH", "UIO_ENUMERATION",
    "FAN_CONTINUITY", "LEGACY_XLSLICE",
}
XDC_LINES = [
    "# KV260 K26 original TTC0 channel-2 fan PWM route -> A12",
    "set_property PACKAGE_PIN A12 [get_ports {M08_FAN_PWM}]",
    "set_property IOSTANDARD LVCMOS33 [get_ports {M08_FAN_PWM}]",
    "set_property SLEW SLOW [get_ports {M08_FAN_PWM}]",
    "set_property DRIVE 4 [get_ports {M08_FAN_PWM}]",
]


class EvidenceRejected(ValueError):
    pass


def demand(predicate: bool, reason: str) -> None:
    if not predicate:
        raise EvidenceRejected(reason)


def text_and_sha(path: Path) -> tuple[str, str]:
    demand(path.is_file() and not path.is_symlink(), "missing or symlinked original PC file: " + str(path))
    raw = path.read_bytes()
    demand(0 < len(raw) < 4_000_000, "unreviewed input size: " + str(path))
    return raw.decode("utf-8"), sha256(raw).hexdigest()


def audit_contract(manifest_path: Path = MANIFEST) -> tuple[dict, str]:
    raw, digest = text_and_sha(manifest_path)
    m = json.loads(raw)
    demand(m.get("schema") == "m08-d3b-protected-axi-contract-v1"
           and m.get("candidate_id") == "m08-d3b-protected-axi-v1"
           and m.get("phase") == "D3.2A_ARCHITECTURE_AND_OFFLINE_POLICY_MODEL"
           and m.get("parent_candidate") == "m08-d3a-passive-fan-v1",
           "wrong D3B manifest identity")
    parent = m.get("parent_d3a_native_evidence", {})
    expected = parent.get("sha256", {})
    demand(isinstance(expected, dict) and len(expected) == 4
           and all(re.fullmatch("[0-9a-f]{64}", value or "") for value in expected.values())
           and parent.get("status") == "ORIGINAL_OWNER_TEXTS_SHA_VERIFIED"
           and parent.get("native_vivado_bd_validated") is True
           and parent.get("native_routed_implementation") is False
           and parent.get("hardware_runtime_proven") is False,
           "D3A native evidence provenance incomplete")
    demand("xlslice:1.0" in parent.get("vivado_advisory", "")
           and "ilslice:1.0" in parent.get("vivado_advisory", ""),
           "legacy Vivado slice migration advisory missing")
    path = m.get("proposed_interconnect", {})
    for k, required in (
        ("upstream_ps_timeout_block", "FPD_ATB_INSTANCE_4"),
        ("upstream_ps_isolation_block", "FPD_AIB_INSTANCE_13"),
        ("hpm0_width_bits_requested", 128),
        ("linux_exposure", "BLOCKED_UNTIL_BOOT_FIRMWARE_AND_FPGA_REGION_LIFECYCLE_PROVEN"),
        ("max_first_diagnostic_reads", 1),
        ("first_fault_policy", "LATCH_AND_STOP_NO_RETRY_REQUIRE_INDEPENDENT_RESTART"),
        ("physical_programming_authorized", False),
        ("physical_mmio_authorized", False),
    ):
        demand(path.get(k) == required, "D3B protected-interface requirement invalid: " + k)
    proof = m.get("protection_requirements", {})
    demand(set(proof) == ALLOWED_FIELDS
           and all(isinstance(value, str) and
                   (value.startswith("REQUIRES_") or value.endswith("_NOT_IMPLEMENTED"))
                   for value in proof.values()),
           "D3B cannot claim any PS ATB4/AIB13/clock/AFI/driver proof")
    model = m.get("source_model", {})
    demand(model.get("rtl") == "rtl/m08/tb_m08_d3b_ps_linux_release_policy.sv"
           and model.get("semantics") == "ABSTRACT_PS_CLOCKED_ADMISSION_POLICY_ONLY"
           and all(model.get(k) is False for k in (
               "can_prove_physical_timeout", "can_prove_hardware_clock_alive",
               "can_prove_software_qualified_status",
               "is_ps_atb_configuration", "is_synthesizable_for_recovery",
           )),
           "D3B model must never be confused with actual PS protection")
    clock = m.get("clock_diagnostic", {})
    demand(clock.get("rtl") == "rtl/m08/m08_d3b_clock_liveness_probe.v"
           and clock.get("tb") == "rtl/m08/tb_m08_d3b_clock_liveness_probe.sv"
           and clock.get("type") == "TWO_CLOCK_SYNTHESIZABLE_BUT_NOT_INTEGRATED_DIAGNOSTIC"
           and all(clock.get(k) is False for k in (
               "ps_independent_monitor_clock_proven",
               "ps_to_pl_axil_protected",
               "synchronizer_cdc_native_verified",
               "fan_cooling_native_verified",
               "hardware_bitstream_integrated",
           )), "unintegrated D3B clock monitor must NOT claim PS clock/ATB or physical proof")
    state = m.get("evidence_status", {})
    demand(state.get("D3A_OWNER_NATIVE_BD_SOURCE") == "ACCEPTED_WITH_LEGACY_SLICE_WARNING"
           and state.get("D3B_BOOT_ATB_AIB_CONFIG") == "NOT_SUPPLIED"
           and state.get("D3B_STOCK_BASE_DEVICE_TREE_OR_BOOT_FIRMWARE") == "NOT_SUPPLIED"
           and state.get("D3B_PROTECTED_BITSTREAM") == "NOT_BUILT"
           and state.get("D3B_PROTECTED_DTBO") == "NOT_BUILT"
           and state.get("D3B_NATIVE_HPM0_BUILD") == "NOT_RUN"
           and state.get("D3B_OWNER_HARDWARE_APPROVAL") is False
           and state.get("original_m08_image_quarantined") is True
           and state.get("stock_k26_left_untouched") is True,
           "D3B status illegally grants hardware approval")
    return m, digest


def audit_owner_run(run: Path, manifest: dict) -> dict:
    demand(run.is_dir() and not run.is_symlink(), "original owner run folder missing or symlinked")
    original = manifest["parent_d3a_native_evidence"]["sha256"]
    receipt_text, receipt_sha = text_and_sha(run / RECEIPT)
    listed = {}
    for line in receipt_text.splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_./-]+)", line)
        demand(match is not None, "invalid owner SHA receipt line")
        digest, relative = match.groups()
        demand(relative in original and relative not in listed, "unexpected/duplicate native evidence file")
        listed[relative] = digest
    demand(listed == original, "owner 99_evidence_sha256 receipt differs from pinned files")
    documents = {}
    for relative, digest in original.items():
        body, observed = text_and_sha(run / relative)
        demand(digest == observed, "owner file SHA mismatch: " + relative)
        documents[relative] = body
    report = documents["output/10_d3a_passive_bd_readback.txt"]
    readback = dict(x.split("=", 1) for x in report.splitlines())
    demand(len(readback) == len(report.splitlines()), "D3A duplicate report keys")
    for key, value in (
        ("schema", "m08-d3a-kv260-passive-fan-bd-v1"),
        ("candidate", "m08-d3a-passive-fan-v1"),
        ("vivado_version", "2025.2"),
        ("part", "xck26-sfvc784-2LV-c"),
        ("board_part", "xilinx.com:kv260_som:part0:1.4"),
        ("ps_preset", "YES"),
        ("ps_hpm0_fpd", "DISABLED"),
        ("ps_hpm1_fpd", "DISABLED"),
        ("ps_hpm0_lpd", "DISABLED"),
        ("smartconnect", "ABSENT"),
        ("identity_slave", "ABSENT"),
        ("page_slave", "ABSENT"),
        ("linux_uio_devices", "ZERO"),
        ("ps_pl0_native_frequency_hz", "99999001"),
        ("fan_pin", "A12"),
        ("fan_iostandard", "LVCMOS33"),
        ("validated_bd", "YES"),
        ("ps_atb4_configuration", "UNKNOWN"),
        ("ps_timeout_protection", "NOT_PROVEN"),
        ("physical_fan_cooling", "NOT_PROVEN"),
        ("synthesis", "NOT_RUN"),
        ("implementation", "NOT_RUN"),
        ("bitstream", "NOT_GENERATED"),
        ("hardware_programmed", "NO"),
        ("hardware_mmio_authorized", "NO"),
    ):
        demand(readback.get(key) == value, "original D3A readback changed: " + key)
    demand(documents["output/12_d3a_fan_a12.xdc"].splitlines() == XDC_LINES,
           "original D3A fan constraints changed")
    export = documents["output/11_d3a_passive_bd_export.tcl"]
    for entry in (
        "CONFIG.PSU__USE__M_AXI_GP0 {0}", "CONFIG.PSU__USE__M_AXI_GP1 {0}",
        "CONFIG.PSU__USE__M_AXI_GP2 {0}",
        "CONFIG.PSU__TTC0__WAVEOUT__IO {EMIO}",
        "M08_FAN_PWM", "m08_d3a_ttc0_fan_slice",
    ):
        demand(entry in export, "D3A exported BD missing key: " + entry)
    demand("connect_bd_intf_net" not in export,
           "unexpected original D3A PS->PL AXI interface connection")
    log = documents["01_native_vivado.log"]
    demand("Vivado v2025.2" in log
           and "M08_D3A_PASSIVE_FAN_ONLY_BD_VALIDATED_NO_AXI_NO_BITSTREAM_NO_BOARD" in log
           and "INFO: [BD 5-1043]" in log
           and "xilinx.com:inline_hdl:ilslice:1.0" in log
           and "Exiting Vivado at" in log
           and not any(line.startswith(("ERROR:", "CRITICAL WARNING:", "WARNING:"))
                       for line in log.splitlines()),
           "original owner Vivado log has failure, lacks native finish, or lacks slice advisory")
    return {
        "status": "D3A_NATIVE_OWNER_FILES_SHA256_AND_SEMANTICS_ACCEPTED",
        "sha256_receipt": receipt_sha,
        "original_text_sha256": original,
        "native_vivado_bd_reported_validated": True,
        "original_legacy_xlslice_deprecation_notice": True,
        "source_or_native_physical_atb4_proof": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--owner-d3a-run", type=Path,
                    help="Optional existing D3A PC native run root; never touch the board")
    args = ap.parse_args()
    try:
        manifest, digest = audit_contract()
        result = {
            "schema": "m08-d3b-offline-protected-axi-evidence-gate-v1",
            "status": STATUS,
            "manifest_sha256": digest,
            "ps_hpm0_protected_image_created": False,
            "atb4_enabled_or_safe_runtime_proven": False,
            "aib13_quiescence_or_no_outstanding_proven": False,
            "Linux_boot_clock_afi_config_proven": False,
            "hardware_mmio_authorized": False,
            "original_m08_image_quarantined": True,
        }
        if args.owner_d3a_run:
            result["D3A_original_native"] = audit_owner_run(args.owner_d3a_run, manifest)
    except (EvidenceRejected, UnicodeError, OSError, ValueError, KeyError) as exc:
        print("M08_D3B_PROTECTED_AXI_GATE_REJECTED_NO_BOARD: " + str(exc),
              file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
