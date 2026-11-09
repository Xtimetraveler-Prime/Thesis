"""M05.12d.3: audit six REAL Vivado-assigned PS AXI4-Lite segment readbacks.

The plan is explicit and OFFLINE-ONLY. An accepted owner HLS RTL contract
establishes register offsets, not an OS/FPGA/PS-DDR MMIO permission. This
reader does not create address segments, change RTL, or talk to hardware.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m05_12d2_control_map import (
    BANKS, ProposedAperture, ProposedControlMap, AddressAdmissionError,
)
from m05_12d3_native_axis_candidate_audit import SLAVE_INTERFACES

PLAN_HEADER = "META|scope|OFFLINE_CANDIDATE_SIX_PS_AXI_LITE_APERTURES_NOT_OS_APPROVED"
MAP_HEADER = "META|scope|OFFLINE_VIVADO_PS_CONTROL_SIX_SLAVE_ADDRESS_READBACK"
MASTER_SPACE = "/ps/Data"
HLS_NATIVE_OFFSETS = {
    "AP_CTRL": 0x00, "AP_RETURN": 0x10, "NEURON_COUNT_DATA": 0x18,
    "SYNAPSE_COUNT_DATA": 0x20, "EXTERNAL_COUNT_DATA": 0x28,
    "TICKS_DATA": 0x30, "DECAY_NUM_DATA": 0x38,
    "DECAY_DEN_DATA": 0x40,
}
HEX = re.compile(r"0x[0-9a-fA-F]{1,16}\Z")


def parse_hex(value: str) -> int:
    if not HEX.fullmatch(value):
        raise ValueError("address value must be bounded explicit hexadecimal")
    return int(value, 16)


def parse_plan(source: str) -> ProposedControlMap:
    if type(source) is not str or len(source) > 5000 or not source.endswith("\n"):
        raise ValueError("missing or oversized six-bank offline address proposal")
    rows = source.splitlines()
    if len(rows) != 7 or rows[0] != PLAN_HEADER:
        raise ValueError("exact proposed plan scope and six bank records required")
    items = []
    for bank, row in zip(BANKS, rows[1:], strict=True):
        fields = row.split("|")
        if len(fields) != 4 or fields[:2] != ["BANK", bank]:
            raise ValueError("wrong or reordered six original control banks")
        base, size = map(parse_hex, fields[2:])
        if size & (size - 1) or base % size:
            raise ValueError("Vivado candidate aperture must be power-of-two aligned")
        items.append(ProposedAperture(bank, base, size))
    return ProposedControlMap(tuple(items))


def audit_original_hls_registers(report: str, plan: ProposedControlMap) -> None:
    if type(report) is not str or not report.endswith("\n") or len(report) > 20000:
        raise ValueError("original real HLS register evidence missing")
    rows = report.splitlines()
    if (not rows or rows[0] !=
            "META|scope|ORIGINAL_SIGNED32_GENERATED_RTL_ATTESTATION_NO_BD"):
        raise ValueError("cannot use non-original signed32 HLS register map")
    regs = {}
    for row in rows:
        if not row.startswith("REG|"):
            continue
        fields = row.split("|")
        if len(fields) != 3 or fields[1] in regs:
            raise ValueError("duplicate or malformed authentic HLS register")
        regs[fields[1]] = parse_hex(fields[2])
    if regs != HLS_NATIVE_OFFSETS:
        raise ValueError("HLS RTL original generated register offsets changed")
    if max(regs.values()) + 4 > plan.aperture("hls").length_bytes:
        raise ValueError("real HLS registers do not fit allocated control aperture")


def audit_six_assignments(report: str, plan: ProposedControlMap) -> dict[str, int]:
    if type(report) is not str or not report.endswith("\n") or len(report) > 20000:
        raise ValueError("missing or malformed actual Vivado address report")
    rows = report.splitlines()
    if len(rows) != 10 or rows[0] != MAP_HEADER:
        raise ValueError("exact real address report header, six mappings, and footer required")
    if rows[1] != "SPACE|ps/M_AXI_HPM0_FPD|/ps/Data":
        raise ValueError("actual mapped master must be genuine PS HPM0 /ps/Data")
    if rows[-2:] != ["META|address_assignment|SIX_EXPLICIT_VIVADO_ASSIGNMENTS_READ_BACK",
                     "META|physical_board|NOT_AUTHORIZED"]:
        raise ValueError("missing six real assignments or false physical authorization")
    seen_slave: set[str] = set()
    seen_master: set[str] = set()
    for bank, row in zip(BANKS, rows[2:8], strict=True):
        f = row.split("|")
        if len(f) != 6 or f[0:2] != ["READBACK", bank]:
            raise ValueError("missing, extra, or reordered actual PS slave mapping")
        _, _, slave, master, base_text, size_text = f
        expected_intf = SLAVE_INTERFACES[bank]
        if (not slave.startswith("/" + expected_intf + "/")
                or not slave[len(expected_intf) + 2:]):
            raise ValueError("real mapped slave is not original required AXI-Lite interface")
        if (not master.startswith(MASTER_SPACE + "/")
                or not master[len(MASTER_SPACE) + 1:]):
            raise ValueError("actual mapped segment is not in PS HPM0 address space")
        if slave in seen_slave or master in seen_master:
            raise ValueError("duplicate/reused real Vivado address segment identity")
        seen_slave.add(slave)
        seen_master.add(master)
        aperture = plan.aperture(bank)
        if parse_hex(base_text) != aperture.base or (
                parse_hex(size_text) != aperture.length_bytes):
            raise ValueError("actual Vivado master OFFSET/RANGE differs from explicit plan")
    return {"independent_ps_axi_lite_banks": 6, "master_mappings": len(seen_master),
            "plan_nonoverlap_verified": 1, "physical_board": 0}


def audit_validation(source: str) -> bool:
    if source == "VALIDATION|PASS|FULL_BD_VALIDATE_FORCE\n":
        return True
    if source == "VALIDATION|FAIL|FULL_BD_VALIDATE_FORCE\n":
        return False
    raise ValueError("missing or ambiguous actual full Vivado BD validation status")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--mapped", type=Path, required=True)
    p.add_argument("--validation", type=Path, required=True)
    p.add_argument("--hls-original-contract", type=Path, required=True)
    args = p.parse_args()
    try:
        plan = parse_plan(args.plan.read_text(encoding="utf-8"))
        audit_original_hls_registers(
            args.hls_original_contract.read_text(encoding="utf-8"), plan)
        result = audit_six_assignments(
            args.mapped.read_text(encoding="utf-8"), plan)
        validated = audit_validation(args.validation.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, AddressAdmissionError) as exc:
        print(f"ERROR: M05.12d.3 independent PS control address audit: {exc}",
              file=sys.stderr)
        return 2
    print("PASS: M05.12d.3 six ORIGINAL actual Vivado PS AXI-Lite "
          f"master/slave address mappings independently read back {result} "
          "(OFFLINE ONLY, NO OS/DDR/BOARD)")
    if not validated:
        print("INCOMPLETE: M05.12d.3 full Vivado validate_bd_design -force "
              "failed; preserve Vivado 03 log and 07 validation status",
              file=sys.stderr)
        return 1
    print("PASS: M05.12d.3 genuine Vivado full block-design validation "
          "(NO GENERATED WIDTH ADAPTER OR PHYSICAL DEVICE CLAIM)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
