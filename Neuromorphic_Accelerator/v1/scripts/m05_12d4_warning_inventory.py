#!/usr/bin/env python3
"""M05.12d.4 D4.1: read-only, fail-closed original Vivado warning inventory.

This verifies original D3 output-file hashes, not AXI protocol correctness.
Synthetic unit-test fixtures must never be presented as owner Vivado evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

from m05_12d3_ip_output_audit import check as check_d3_products

ORIGINAL = "neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
ORIGINAL_COMMIT = "fc17906e95c727d9091a443e2082fe00c95d4e0c"
PREFIX = "neuromorphic_v1_m05_12d4_warning_inventory_"
RELEVANT = {"2384", "237", "3281", "1629"}
WARNING = re.compile(r"^(WARNING|CRITICAL WARNING): \[BD 41-(\d+)\]\s*(.*)$")
PIN = re.compile(
    r"Width mismatch when connecting pin:\s*'(?P<source>/[^']+)'\s*"
    r"\((?P<source_width>\d+)\)\s*to pin:\s*'(?P<destination>/[^']+)'\s*"
    r"\((?P<destination_width>\d+)\)")
PROPERTY = re.compile(
    r"Bus Interface property\s+(?P<property>[A-Z][A-Z_0-9]+)\s+"
    r"does not match between\s+(?P<source>/[^\s(]+)\((?P<source_width>\d+)\)"
    r"\s+and\s+(?P<destination>/[^\s(]+)\((?P<destination_width>\d+)\)")
FIELDS = ("AWUSER", "ARUSER", "WUSER", "RUSER", "BUSER", "AWID", "ARID",
          "BID", "RID", "WDATA", "RDATA", "WSTRB", "BRESP", "RRESP",
          "AWLEN", "ARLEN", "AWSIZE", "ARSIZE", "WLAST", "RLAST",
          "AWADDR", "ARADDR", "AWLOCK", "ARLOCK")
CHANNEL = re.compile(r"(?:^|[_/])(?:S_SC_|M_SC_|S_AXI_|M_AXI_)?(AW|AR|W|R|B)(?:[_/]|$)", re.I)


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def strict_parent(path: Path) -> Path:
    parent = path.parent.resolve(strict=True)
    if (not parent.is_dir() or not parent.name.startswith(PREFIX)
            or path.name != "02_warning_inventory.json" or path.exists()):
        raise ValueError("output must be NEW 02_warning_inventory.json inside fresh D4 evidence")
    return parent


def parse_warnings(log: str) -> list[dict]:
    """Keep every BD warning occurrence and line number; never deduplicate."""
    records = []
    for line_no, line in enumerate(log.splitlines(), 1):
        match = WARNING.match(line)
        if not match:
            continue
        severity, code, message = match.groups()
        item = {
            "line": line_no, "id": "BD 41-" + code, "severity": severity,
            "message": message, "source_pin": None, "destination_pin": None,
            "source_width": None, "destination_width": None,
            "narrowed_bits": None, "channel_hint": None, "field_hint": [],
            "parent": "UNATTRIBUTED", "classification": "UNRESOLVED_BLOCKER",
            "reason": "no independently established generated-IP hierarchy/packed field semantics",
        }
        widths = PIN.search(message) if code == "2384" else PROPERTY.search(message) if code == "237" else None
        if widths:
            groups = widths.groupdict()
            item["source_pin"], item["destination_pin"] = groups["source"], groups["destination"]
            item["source_width"] = int(groups["source_width"])
            item["destination_width"] = int(groups["destination_width"])
            if code == "2384":
                # Direction is explicitly stated by Vivado "to pin"; widening
                # does NOT mean high-order source bits were lost.
                item["narrowed_bits"] = max(0, item["source_width"] - item["destination_width"])
                if item["narrowed_bits"]:
                    item["reason"] = "source high bits could be discarded; field layout unproved"
            if code == "237":
                item["field_hint"] = [groups["property"]]
                item["reason"] = "interface property disagreement; endpoint semantics require review"
        pins = " ".join(x for x in (item["source_pin"], item["destination_pin"]) if x)
        uppercase = (pins + " " + message).upper()
        item["field_hint"] = sorted(set(item["field_hint"]) |
                                    {field for field in FIELDS if re.search(r"\b" + field + r"\b", uppercase)})
        channels = set()
        for path in (item["source_pin"], item["destination_pin"]):
            if path:
                channels.update(m.upper() for m in CHANNEL.findall(path))
        if len(channels) == 1:
            item["channel_hint"] = next(iter(channels))
        # Only explicit /ctrl_sc/ or /mem_sc/ endpoints are sufficient to
        # assign a parent from this warning alone. Bare /m00_nodes is not.
        owners = set()
        for p in (item["source_pin"], item["destination_pin"]):
            if p:
                for name in ("ctrl_sc", "mem_sc"):
                    if re.search(r"(^|/)" + name + r"(/|$)", p):
                        owners.add(name)
        if len(owners) == 1:
            item["parent"] = next(iter(owners))
        elif len(owners) > 1:
            item["parent"] = "AMBIGUOUS"
        if code not in RELEVANT:
            item["reason"] = "unrecognized BD warning ID; human review mandatory"
        elif not widths and code in ("2384", "237"):
            item["reason"] = "unparsed warning endpoints/widths; do not infer dropped bits"
        if code == "1629":
            item["reason"] = "OCM exclusion may be intentional but requires exact evidence correlation"
        if code == "3281":
            item["reason"] = "SmartConnect auto-configuration needs exact IP property readback"
        records.append(item)
    return records


def inspect_original(evidence: Path) -> dict:
    root = evidence.resolve(strict=True)
    if root.name != ORIGINAL or not root.is_dir() or evidence.is_symlink():
        raise ValueError("only the immutable named original 2025.2 D3 evidence is accepted")
    required = ("commit.txt", "result.txt", "03_vivado.log",
                "15_ip_output_width_readback.txt", "16_ip_output_sha256_manifest.txt",
                "source_sha256.txt", "07_full_bd_validation.txt")
    paths = {name: root / name for name in required}
    if any(not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(root)
           for p in paths.values()):
        raise ValueError("missing or unsafe original D3 provenance artifact")
    if paths["commit.txt"].read_text().strip() != ORIGINAL_COMMIT:
        raise ValueError("unexpected original owner-verified source commit")
    if paths["result.txt"].read_text().strip() != "exit_status=0":
        raise ValueError("original D3 result is not exit_status=0")
    log = paths["03_vivado.log"].read_text()
    status, hashes = check_d3_products(
        root, paths["15_ip_output_width_readback.txt"].read_text(), log)
    if status["generated"] != 382 or status["mem_sc"] != 118:
        raise ValueError("genuine D3 generated IP cardinality drift")
    actual_manifest = ["META|scope|REAL_VIVADO_OUTPUT_PRODUCT_SHA256"]
    actual_manifest += [f"SHA256|{digest}|{rel}" for rel, digest in hashes]
    actual_manifest += ["META|synthesis|NOT_RUN", "META|physical_board|NOT_AUTHORIZED"]
    if paths["16_ip_output_sha256_manifest.txt"].read_text().splitlines() != actual_manifest:
        raise ValueError("original generated-IP SHA256 manifest differs from actual files")
    records = parse_warnings(log)
    if not any(r["id"] == "BD 41-2384" for r in records):
        raise ValueError("original generated-IP warning family absent; wrong or incomplete log")
    counts = Counter(r["id"] for r in records)
    return {
        "scope": "READ_ONLY_ORIGINAL_VIVADO_2025_2_D3_WARNING_INVENTORY",
        "source_commit": ORIGINAL_COMMIT, "original_evidence": str(root),
        "original_file_sha256": {name: sha(p) for name, p in sorted(paths.items())},
        "generated_products_verified": status, "warnings_by_id": dict(sorted(counts.items())),
        "warnings": records, "unresolved_count": len(records),
        "d4_1_inventory": "COMPLETE_ORIGINAL_FILES_HASH_VERIFIED",
        "protocol_integrity": "BLOCKED_UNRESOLVED_WARNINGS",
        "hierarchy_and_packed_field_proof": "NOT_ESTABLISHED_BY_PATH_NAMES",
        "d4_2": "NOT_RUN", "d4_3": "NOT_RUN",
        "synthesis": "NOT_RUN", "physical_board": "NOT_AUTHORIZED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-d3", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        strict_parent(args.output)
        result = inspect_original(args.original_d3)
        with args.output.open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2, sort_keys=True)
            f.write("\n")
    except (ValueError, OSError, UnicodeError) as exc:
        print(f"FAIL: D4.1 original Vivado warning inventory: {exc}", file=sys.stderr)
        return 2
    print("INVENTORY COMPLETE: original D3 products/hashes verified; "
          f"{result['unresolved_count']} warnings require hierarchy/field proof; "
          "AXI PROTOCOL GATE BLOCKED (not an RTL or hardware PASS)")
    # Deliberately nonzero: do not allow shell/CI to upgrade unresolved
    # warning classification to an accepted AXI protocol-integrity gate.
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
