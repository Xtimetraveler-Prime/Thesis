#!/usr/bin/env python3
"""Independent SOURCE/RECEIPT review of owner-original M08.5 offline PSPL BD.

Read-only: no Vivado, board, MMIO, kernel, JTAG or source/evidence writes.
Verifies exact original SHA ledger AND independently checks current first-party
builder/RTL bytes and the declared zero-trust, source-only native receipt.
A passed receipt is NOT an implemented/booted/physically owned DDR device.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m08_m085_pspl_quarantine_bd.tcl"
RTL_ROOT = ROOT / "rtl"
M08_RTL = RTL_ROOT / "m08"
SOURCE_NAMES = (
    "m08_host_staged_page_bank.sv",
    "m08_paged_m06_lif_engine.v",
    "m08_m085_ddr_page_admission.v",
    "m08_m085_axi128_page_engine.v",
    "m08_m085_axi128_page_candidate.v",
    "m08_m085_axi_bank_bridge.v",
    "m08_m085_axi_neural_shell.v",
    "m08_m085_kernel_dma_lease_fence.v",
    "m08_m085_trusted_control_abi.v",
    "m08_m085_work_command_sequencer.v",
    "m08_m085_axil_control_candidate.v",
    "m08_m085_axil_managed_neural_candidate.v",
)
BASE_NAMES = (
    "00_vivado.log", "01_vivado.jou", "02_vivado_exit_status.txt",
    "03_builder_source.tcl", "04_stdout.txt", "05_stderr.txt",
    "06_context.txt", "reports/10_fan_a12.xdc",
    "reports/20_quarantined_bd_observation.txt",
)
EXPECTED = set(BASE_NAMES) | {
    "source_snapshot/" + n for n in SOURCE_NAMES
} | {"source_snapshot/m08_d3c_fabric_por.v"}
assert len(EXPECTED) == 22
STATUS = {
    "schema": "m08-m085-kv260-pspl-quarantine-bd-v1",
    "status": "OFFLINE_BD_TOPOLOGY_ONLY_NEVER_DMA_READY",
    "target_part": "xck26-sfvc784-2LV-c",
    "vivado_version": "2025.2",
    "ps_master": "ps/M_AXI_HPM0_FPD",
    "ps_slave": "ps/S_AXI_HP0_FPD",
    "ps_hpm0_width": "128",
    "ps_hp0_width": "128",
    "pl_control_protocol": "AXI4LITE",
    "pl_control_width": "32",
    "pl_data_protocol": "AXI4",
    "pl_data_width": "128",
    "pl0_nominal_hz": "100000000",
    "mmio_map": "0xA4000000/0x1000_SOURCE_ONLY",
    "hp0_route_map": "0x00000000/0x80000000_NOT_DMA_OWNERSHIP",
    "csr_trusted": "HARDWIRED_ZERO",
    "driver_bound_verified": "HARDWIRED_ZERO",
    "control_route_verified": "HARDWIRED_ZERO",
    "interconnect_drain_ack": "HARDWIRED_ZERO",
    "native_synth": "NOT_RUN",
    "native_route": "NOT_RUN",
    "bitstream": "NOT_CREATED",
    "linux_dma_driver": "NOT_PRESENT",
    "board_programming": "NOT_PERFORMED",
}
MAX_BYTES = 32 * 1024 * 1024


class EvidenceRejected(ValueError):
    pass


def regular_file(path: Path, max_bytes: int = MAX_BYTES) -> bytes:
    if path.is_symlink():
        raise EvidenceRejected("symlink in original receipt: " + str(path))
    try:
        s = path.lstat()
    except OSError as exc:
        raise EvidenceRejected("missing original file: " + str(path)) from exc
    if not stat.S_ISREG(s.st_mode) or not (0 < s.st_size <= max_bytes):
        raise EvidenceRejected("unsafe original file size/type: " + str(path))
    return path.read_bytes()


def evidence_text(blob: bytes, label: str) -> str:
    try:
        return blob.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EvidenceRejected("nontext evidence: " + label) from exc


def properties(blob: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in evidence_text(blob, "native observation").splitlines():
        if raw.count("=") != 1:
            raise EvidenceRejected("malformed native observation")
        key, value = raw.split("=", 1)
        if key in result or not re.fullmatch(r"[a-z0-9_]+", key):
            raise EvidenceRejected("duplicate or invalid observation property")
        result[key] = value
    if result != STATUS:
        bad = [k for k in set(result) | set(STATUS)
               if result.get(k) != STATUS.get(k)]
        raise EvidenceRejected("native source-only observation drift: " +
                               ",".join(sorted(bad)))
    return result


def verify(original: Path, expected_root: Path = ROOT) -> dict:
    if original.is_symlink() or not original.is_dir():
        raise EvidenceRejected("not a regular original evidence directory")
    if not re.fullmatch(r"m08_m085_pspl_bd_[A-Za-z0-9_]+", original.name):
        raise EvidenceRejected("unrecognized native evidence directory name")
    manifest = evidence_text(regular_file(original / "99_evidence_sha256.txt"),
                             "SHA256 ledger")
    records: dict[str, str] = {}
    for line in manifest.splitlines():
        m = re.fullmatch(r"([a-f0-9]{64})  \./([^\\\n\r]+)", line)
        if not m:
            raise EvidenceRejected("invalid original SHA256 entry")
        digest, rel = m.groups()
        if rel in records or rel not in EXPECTED:
            raise EvidenceRejected("extra or duplicate original SHA256 path: " + rel)
        records[rel] = digest
    if set(records) != EXPECTED:
        raise EvidenceRejected("original SHA256 manifest is not exactly 22 source items")
    blobs = {}
    for rel, claimed in records.items():
        path = original / rel
        for directory in (path.parent, path.parent.parent):
            if directory != original and directory.is_relative_to(original) and directory.is_symlink():
                raise EvidenceRejected("symlinked source or reports directory")
        raw = regular_file(path)
        if hashlib.sha256(raw).hexdigest() != claimed:
            raise EvidenceRejected("SHA256 mismatch in original: " + rel)
        blobs[rel] = raw

    # Detect a convenience bitstream slipped into the unledgered project
    # cache: the original native builder was forbidden to create any.
    for path in original.rglob("*"):
        if path.is_symlink():
            raise EvidenceRejected("symlink in evidence tree")
        if path.is_file() and path.suffix.lower() in (".bit", ".bin"):
            raise EvidenceRejected("unexpected bit/bin in offline BD candidate")

    comparisons = {
        "03_builder_source.tcl": expected_root / "scripts/m08_m085_pspl_quarantine_bd.tcl",
        "source_snapshot/m08_d3c_fabric_por.v": expected_root / "rtl/m08_d3c_fabric_por.v",
    }
    comparisons.update({
        "source_snapshot/" + leaf: expected_root / "rtl/m08" / leaf
        for leaf in SOURCE_NAMES
    })
    for rel, path in comparisons.items():
        source_bytes = regular_file(path)
        if blobs[rel] != source_bytes:
            raise EvidenceRejected("native snapshot differs from current first-party source: " + rel)

    if blobs["02_vivado_exit_status.txt"] != b"vivado_exit_status=0\n":
        raise EvidenceRejected("owner Vivado process did not exit successfully")
    stdout = evidence_text(blobs["04_stdout.txt"], "Vivado stdout")
    if sum(line.strip() == "M08_M085_QUARANTINED_PSPL_BD_COMPLETE_NO_DMA_NO_BITSTREAM" for line in stdout.splitlines()) != 1:
        raise EvidenceRejected("unique successful native BD marker absent from stdout")
    log = evidence_text(blobs["00_vivado.log"], "Vivado original log")
    if "Vivado v2025.2" not in log or "M08_M085_QUARANTINED_PSPL_BD_COMPLETE_NO_DMA_NO_BITSTREAM" not in log:
        raise EvidenceRejected("Vivado original log/version or completion marker absent")
    props = properties(blobs["reports/20_quarantined_bd_observation.txt"])
    xdc = evidence_text(blobs["reports/10_fan_a12.xdc"], "fan source XDC")
    if ("PACKAGE_PIN A12" not in xdc or "IOSTANDARD LVCMOS33" not in xdc or
            "M08_FAN_PWM" not in xdc):
        raise EvidenceRejected("fan A12 native XDC source drift")
    context = evidence_text(blobs["06_context.txt"], "owner context")
    if "scope=QUARANTINED_PSPL_BD_ONLY_NO_DMA" not in context or "vivado=vivado v2025.2" not in context:
        raise EvidenceRejected("native owner context/version/scope missing")
    return {
        "schema": "m08-m085-original-owner-native-bd-receipt-review-v1",
        "status": "OWNER_RECEIPT_CONSISTENT_SOURCE_ONLY_NATIVE_BD_NOT_DMA_RELEASE",
        "files_sha256_verified": len(EXPECTED),
        "snapshot_and_builder_match_current_source": True,
        "owner_original_evidence_path": str(original),
        "declared_ps_hpm0_to_32_axil": props["pl_control_width"] == "32",
        "declared_ps_hp0_128": props["pl_data_width"] == "128",
        "four_trust_and_drain_signals_hardwired_zero": True,
        "physical_dma_allowed": False,
        "independent_vivado_replay_performed": False,
        "rtl_synthesis_or_route_performed": False,
        "board_access_performed": False,
        "caveat": "Owner receipt cross-check, not independent PS/FPD/DDR/boot proof",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-evidence", required=True, type=Path)
    args = p.parse_args()
    evidence = args.original_evidence
    expected_parent = Path.home() / "Thesis_Evidence/M08"
    if evidence.is_symlink() or evidence.resolve().parent != expected_parent.resolve():
        print("M08_5_ORIGINAL_BD_RECEIPT_REJECTED: outside owner M08 original root",
              file=sys.stderr)
        return 2
    try:
        print(json.dumps(verify(evidence), sort_keys=True, indent=2))
    except (EvidenceRejected, OSError) as exc:
        print("M08_5_ORIGINAL_BD_RECEIPT_REJECTED: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
