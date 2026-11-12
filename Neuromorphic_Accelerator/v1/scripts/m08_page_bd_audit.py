#!/usr/bin/env python3
"""Independent *consistency* audit of an ORIGINAL native M08.2b.3 Vivado BD.

This checks files against the exact checkout, genuine vendor log markers,
actual 2-slave Vivado-exported interconnect, two distinct 4KiB PS addresses,
clock propagation and declared no-physical-work boundaries. It does not
cryptographically attest a vendor machine or qualify Linux MMIO, HLS, DDR,
route, bitstream, FPGA inference or performance.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

SCOPE = "M08_GENUINE_LOCAL_KV260_PS_TO_IDENTITY_AND_SAFE_PAGE_BD"
MARKER = "M08_PAGE_GENUINE_VIVADO_BD_VALIDATED_NO_BITSTREAM_NO_BOARD"
DISTINCT_MARKER = "M08_PAGE_BD_DISTINCT_ID_AND_PAGE_4K_ADDRESS_SEGMENTS=1"
FILES = (
    "rtl/m08/m08_axil_readonly_identity.v",
    "rtl/m08/m08_host_staged_page_bank.sv",
    "rtl/m08/m08_axil_page_control.sv",
    "rtl/m08/m08_ps_page_safe_shell.v",
    "scripts/m08_page_ps_bd_candidate.tcl",
    "scripts/m08_page_bd_audit.py",
    "scripts/run_m08_page_bd.sh",
)
REPORT = "02_vivado_page_bd_readback.txt"
LOG = "01_vivado_page_bd.log"
EXPORT = "03_page_bd_export.tcl"


def digest(p: Path) -> str:
    return sha256(p.read_bytes()).hexdigest()


def _read_original(folder: Path, filename: str) -> bytes:
    p = folder / filename
    if p.is_symlink() or not p.is_file():
        raise ValueError("missing or symlinked original evidence: " + filename)
    return p.read_bytes()


def audit_evidence(folder: Path, root: Path) -> dict:
    if folder.is_symlink() or not folder.is_dir() or not root.is_dir():
        raise ValueError("original evidence and source root must be directories")
    if _read_original(folder, "result.txt") != b"exit_status=0\n":
        raise ValueError("original Vivado process did not exit successfully")
    before = _read_original(folder, "source_sha256_before.txt")
    after = _read_original(folder, "source_sha256_after.txt")
    if not before or before != after:
        raise ValueError("original source before/after SHA manifest mismatch")
    expected = "".join(
        f"{digest(root / name)}  {name}\n" for name in FILES
    ).encode("ascii")
    if before != expected:
        raise ValueError("source SHA256 does not match current exact checkout")
    report = _read_original(folder, REPORT).decode("utf-8").strip().splitlines()
    required = (
        "META|scope|" + SCOPE,
        "META|part|xck26-sfvc784-2LV-c",
        "META|vivado_version|2025.2",
        "META|board_part|xilinx.com:kv260_som:part0:",
        "META|ps_preset|YES",
        "META|requested_clock_hz|100000000",
        "META|actual_clock_hz|",
        "META|page_source|rtl/m08/m08_ps_page_safe_shell.v",
        "META|compute_enabled|NO",
        "MASTER|",
        "SLAVE_IDENTITY|",
        "SLAVE_PAGE|",
        "APERTURE_IDENTITY|",
        "APERTURE_PAGE|",
        "META|validated_bd|YES",
        "META|routed_implementation|NOT_RUN",
        "META|bitstream|NOT_GENERATED",
        "META|linux_mmio|NOT_ACCESSED",
        "META|physical_ddr|NOT_ACCESSED",
        "META|physical_kv260|NOT_PROGRAMMED",
    )
    if len(report) != len(required):
        raise ValueError(f"unexpected Vivado report rows: {len(report)}")
    for i, (line, prefix) in enumerate(zip(report, required)):
        if not line.startswith(prefix):
            raise ValueError(f"wrong original report row {i}: {line!r}")
    clock_text = report[6].split("|")
    if len(clock_text) != 3 or not re.fullmatch(r"[1-9][0-9]*", clock_text[2]):
        raise ValueError("actual native PS clock is not an integer")
    clock = int(clock_text[2])
    if abs(clock - 100_000_000) > 1000:
        raise ValueError("actual clock outside bounded PS preset tolerance")
    master = report[9].split("|")
    identity = report[10].split("|")
    page = report[11].split("|")
    for row in (master, identity, page):
        if len(row) != 3 or not all(row):
            raise ValueError("missing original physical AXI master or slave")
    if "M_AXI_HPM0_FPD" not in master[1] or master[2] != "/ps/Data":
        raise ValueError("not original PS FPD HPM0 AXI master/space")
    if "identity/S_AXI" not in identity[1] or "page/S_AXI" not in page[1]:
        raise ValueError("PS-connected identity or SAFE page slave absent")
    if identity[2] == page[2]:
        raise ValueError("two different slaves alias a single BD segment")
    addresses = {}
    for name, row in (("identity", report[12]), ("page", report[13])):
        parts = row.split("|")
        if len(parts) != 4 or not all(parts):
            raise ValueError("missing original address report row " + name)
        if any(not re.fullmatch(r"0x[0-9a-fA-F]+", s) for s in parts[2:]):
            raise ValueError("non-hex native BD aperture")
        address = int(parts[2], 16)
        size = int(parts[3], 16)
        if size != 4096 or address % 4096 != 0 or address+size > 2**32:
            raise ValueError("page or identity region not 4KiB aligned/in PS 32-bit address")
        if "/ps/Data/" not in parts[1]:
            raise ValueError("aperture not in intended PS HPM0 address space")
        if name == "identity" and "identity" not in parts[1]:
            raise ValueError("identity address segment mismatched")
        if name == "page" and "page" not in parts[1]:
            raise ValueError("page address segment mismatched")
        addresses[name] = (address, size)
    ia, ilen = addresses["identity"]
    pa, plen = addresses["page"]
    if ia < pa + plen and pa < ia + ilen:
        raise ValueError("original identity and SAFE page address windows overlap")

    log = _read_original(folder, LOG).decode("utf-8", errors="replace")
    # Genuine Vivado echoes Tcl 'puts' commands; only standalone *printed*
    # marker lines are proof, not a substring match of echoed Tcl text.
    for marker in (MARKER, DISTINCT_MARKER):
        if sum(line.strip() == marker for line in log.splitlines()) != 1:
            raise ValueError("genuine vendor log printed marker missing/duplicated: " + marker)
    for marker in (
        "M08_KV260_PS_BOARD_PRESET_APPLIED=1",
        f"M08_GENUINE_PS_PL0_CLOCK_HZ={clock}",
        f"M08_GENUINE_AXI_CLOCK_PROPAGATION_MATCH_HZ={clock}",
    ):
        if sum(line.strip() == marker for line in log.splitlines()) != 1:
            raise ValueError("genuine PS board/clock output marker missing: " + marker)
    if "ERROR:" in log or "CRITICAL WARNING:" in log or "Common 17-55" in log:
        raise ValueError("genuine Vivado log contains an unaccepted severe warning or error")

    exported = _read_original(folder, EXPORT).decode("utf-8", errors="replace")
    if len(exported) < 512:
        raise ValueError("genuine Vivado BD Tcl export absent or empty")
    for term in (
        "ps/M_AXI_HPM0_FPD", "ctrl_sc/S00_AXI",
        "ctrl_sc/M00_AXI", "ctrl_sc/M01_AXI",
        "identity/S_AXI", "page/S_AXI",
        "m08_ps_page_safe_shell",
    ):
        if term not in exported:
            raise ValueError("original Vivado export lacks native PS-to-page connection: " + term)
    if "assign_bd_address" not in exported:
        raise ValueError("original exported Vivado address map absent")
    # Each required pair must coexist in a *real exported net connection*.
    # Merely mentioning both objects somewhere in a Tcl file is not proof
    # they were connected in the validated IP Integrator diagram.
    flattened = exported.replace(chr(92) + chr(10), " ")
    connections = (
        line for line in flattened.splitlines()
        if line.lstrip().startswith("connect_bd_intf_net")
    )
    connected_lines = list(connections)
    for lhs, rhs in (
        ("ps/M_AXI_HPM0_FPD", "ctrl_sc/S00_AXI"),
        ("ctrl_sc/M00_AXI", "identity/S_AXI"),
        ("ctrl_sc/M01_AXI", "page/S_AXI"),
    ):
        if not any(lhs in line and rhs in line for line in connected_lines):
            raise ValueError("actual exported PS AXI interface connection missing: "
                             + lhs + "->" + rhs)

    return {
        "status": "ORIGINAL_OWNER_KV260_PS_TO_SAFE_PAGE_BD_EVIDENCE_CONSISTENT",
        "scope": SCOPE,
        "model_only": False,
        "source_sha256_manifest": digest(folder / "source_sha256_before.txt"),
        "vivado_log_sha256": digest(folder / LOG),
        "report_sha256": digest(folder / REPORT),
        "vivado_bd_export_sha256": digest(folder / EXPORT),
        "requested_clock_hz": 100_000_000,
        "actual_clock_hz": clock,
        "actual_clock_deviation_hz": abs(clock - 100_000_000),
        "identity_aperture": f"0x{ia:08x}",
        "page_aperture": f"0x{pa:08x}",
        "both_apertures_bytes": 4096,
        "distinct_address_segments": True,
        "safe_compute_disabled": True,
        "routed_implementation": False,
        "bitstream_programmed": False,
        "physical_kv260": False,
        "linux_mmio_performed": False,
        "physical_ddr": False,
        "kernel_dma_ownership": False,
        "neural_inference_verified": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence-dir", required=True, type=Path)
    ap.add_argument("--source-root", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    a = ap.parse_args()
    try:
        if (a.output.is_symlink() or a.output.exists() or
                a.output.parent.resolve() != a.evidence_dir.resolve()):
            raise ValueError("independent audit must write a NEW file in its original evidence dir")
        receipt = audit_evidence(a.evidence_dir, a.source_root)
        with a.output.open("x", encoding="utf-8") as dest:
            json.dump(receipt, dest, indent=2, sort_keys=True)
            dest.write("\n")
    except (ValueError, OSError, UnicodeError) as err:
        print("M08_PAGE_BD_AUDIT_REJECTED:", err, file=sys.stderr)
        return 2
    print("M08_PAGE_BD_SOURCE_AND_ORIGINAL_VIVADO_RECEIPT_AUDITED_NOT_PHYSICAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
