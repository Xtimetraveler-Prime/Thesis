#!/usr/bin/env python3
"""M05 D4.2 evidence-based AXI risk review; original files are READ ONLY.

Never call this a configuration PASS: no original generated payload packing,
internal SmartConnect arbitration, remapping or downsize behavior is proven.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

from m05_12d4_readonly_bd_audit import (
    PAIRS, PROPS, PREFIX, SUCCESS, parse, verify_original_and_inventory,
)
from m05_12d4_warning_inventory import sha

NEW_PREFIX = "neuromorphic_v1_m05_12d4_protocol_gate_"
SIDE = ("CONFIG.AWUSER_WIDTH", "CONFIG.ARUSER_WIDTH", "CONFIG.WUSER_WIDTH",
        "CONFIG.RUSER_WIDTH", "CONFIG.BUSER_WIDTH", "CONFIG.ID_WIDTH")
CRITICAL = ("CONFIG.PROTOCOL", "CONFIG.DATA_WIDTH", "CONFIG.ADDR_WIDTH",
            "CONFIG.MAX_BURST_LENGTH", "CONFIG.SUPPORTS_NARROW_BURST",
            "CONFIG.HAS_BURST", "CONFIG.HAS_WSTRB", "CONFIG.HAS_BRESP",
            "CONFIG.HAS_RRESP", "CONFIG.READ_WRITE_MODE")


def review(original: Path, d4old: Path, d4bd: Path) -> dict:
    orig = verify_original_and_inventory(original, d4old / "02_warning_inventory.json")
    old = d4bd.resolve(strict=True)
    if (not old.is_dir() or d4bd.is_symlink()
            or not old.name.startswith(PREFIX)
            or (old / "result.txt").read_text().strip() != "exit_status=3"):
        raise ValueError("exact prior ORIGINAL successful-but-BLOCKED D4.1b folder required")
    before = (old / "source_sha256.txt").read_bytes()
    after = (old / "07_source_sha256_after.txt").read_bytes()
    if not before or before != after:
        raise ValueError("D4.1b original source pre/post hash manifest mismatch")
    for row in before.decode().splitlines():
        digest, _, name = row.partition("  ")
        if not digest or len(digest) != 64 or not name or not Path(name).is_file():
            raise ValueError("D4.1b pre/post SHA manifest incomplete or input missing")
        if sha(Path(name)) != digest:
            raise ValueError("D4.1b original source or evidence changed: " + name)
    logpath = old / "04_vivado_readonly.log"
    reportpath = old / "03_bd_interface_properties.txt"
    auditpath = old / "06_independent_bd_audit.json"
    vendor_log = logpath.read_text()
    if sum(line.strip() == SUCCESS for line in vendor_log.splitlines()) != 1 or "ERROR:" in vendor_log:
        raise ValueError("D4.1b genuine Vivado original property query did not complete")
    parsed = parse(reportpath.read_text(), original)
    audit = json.loads(auditpath.read_text())
    expected = {
        **parsed,
        "original_d3_sha256": orig["original_file_sha256"],
        "original_warning_occurrences": len(orig["warnings"]),
        "documented_ocm_exclusion": orig["documented_ocm_exclusion"],
        "original_dma_ocm_evidence_sha256": orig["original_dma_ocm_evidence_sha256"],
        "warning_classifications": {"documented_intentional_ocm": 1, "unresolved": 63},
        "read_only_vivado_log_sha256": sha(logpath),
    }
    if audit != expected:
        raise ValueError("D4.1b independent original 23-endpoint JSON does not match genuine raw report")
    properties = parsed["properties"]
    links = []
    for a, b in PAIRS:
        lhs, rhs = properties[a], properties[b]
        diffs = {
            prop: {"a": lhs[prop], "b": rhs[prop]}
            for prop in SIDE + CRITICAL if lhs[prop] != rhs[prop]
        }
        links.append({
            "a": a, "b": b, "net": parsed["interface_nets"][a],
            "mismatched_original_interface_properties": diffs,
            "axi_semantics": "BLOCKED_UNTIL_VENDOR_BEHAVIOR_OBSERVED",
            "property_match_is_not_proof_of_packed_field_mapping": True,
        })
    rows = []
    for w in orig["warnings"]:
        row = {
            "line": w["line"], "id": w["id"], "severity": w["severity"],
            "message": w["message"], "source_pin": w["source_pin"],
            "destination_pin": w["destination_pin"],
            "source_width": w["source_width"],
            "destination_width": w["destination_width"],
            "possible_high_bits_lost": w["narrowed_bits"],
            "original_parent_from_unqualified_path": w["parent"],
            "field_hint": w["field_hint"],
            "classification": "UNRESOLVED_BLOCKER",
            "reason": w["reason"],
        }
        if w["id"] == "BD 41-1629":
            if w["line"] != orig["documented_ocm_exclusion"]["original_log_line"]:
                raise ValueError("OCM warning differs from independently witnessed original")
            row["classification"] = "DOCUMENTED_INTENTIONAL_OCM_EXCLUSION_ONLY"
            row["reason"] = "four genuine excluded OCM segments independently audited"
        elif w["id"] == "BD 41-237":
            # Explicit upstream/downstream original interface facts are useful,
            # but do NOT make disappearing USER bits or conversion permissible.
            row["original_memory_interface_user_and_id"] = {
                end: {k: properties[end][k] for k in SIDE}
                for end in ("mem_sc/M00_AXI", "ps/S_AXI_HP0_FPD")
            }
            row["reason"] = "original USER property mismatch; keep even if unused suspected"
        elif w["id"] == "BD 41-3281":
            row["reason"] = "automatic configuration warning; actual endpoint properties now captured, not simulated"
        elif w["id"] == "BD 41-2384":
            row["reason"] = "original internal payload pin truncation; exact containing IP/packed offsets not proven"
        rows.append(row)
    counts = Counter(x["classification"] for x in rows)
    if len(rows) != 64 or counts != {"UNRESOLVED_BLOCKER": 63,
                                   "DOCUMENTED_INTENTIONAL_OCM_EXCLUSION_ONLY": 1}:
        raise ValueError("unexpected original warning count or classification drift")
    return {
        "scope": "M05_D4_2_GENUINE_ORIGINAL_READONLY_RISK_AND_NO_AUTOMATIC_CHANGE",
        "original_d3": str(original.resolve()),
        "d4_1_inventory": str(d4old.resolve()),
        "d4_1b_property_evidence": str(old),
        "authenticated_d4_1b_sha256": {
            n: sha(old / n) for n in ("03_bd_interface_properties.txt",
                                     "04_vivado_readonly.log",
                                     "06_independent_bd_audit.json",
                                     "source_sha256.txt",
                                     "07_source_sha256_after.txt")
        },
        "original_source_commit": orig["source_commit"],
        "source_hash_verified": True,
        "smartconnects": parsed["smartconnect"],
        "data_widths": parsed["memory_readback_widths"],
        "warning_counts": dict(counts),
        "interface_pairs": links,
        "original_warnings": rows,
        "decision": "NO_MUTATION_JUSTIFIED_FROM_CONFIGURATION_READBACK_ALONE",
        "d4_2_correction": "NOT_APPLIED_BECAUSE_FIELD_PROOF_AND_VENDOR_FUNCTIONAL_PROOF_MISSING",
        "vendor_generated_payload_parent": "NOT_PROVEN",
        "vendor_generated_axi_mm_downsize": "NOT_PROVEN",
        "d4_3_vendor_xsim": "NOT_RUN",
        "synthesis": "NOT_RUN", "physical_board": "NOT_AUTHORIZED",
        "m05_exit": "OPEN", "m06": "NOT_STARTED",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-d3", type=Path, required=True)
    p.add_argument("--d4-inventory", type=Path, required=True)
    p.add_argument("--d4-bd", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        parent = args.output.parent.resolve(strict=True)
        if (args.output.name != "02_original_axi_risk.json"
                or not parent.name.startswith(NEW_PREFIX)
                or args.output.exists() or parent == args.original_d3.resolve()):
            raise ValueError("new original evidence-local D4 protocol-gate report required")
        data = review(args.original_d3, args.d4_inventory, args.d4_bd)
        with args.output.open("x", encoding="utf-8") as fp:
            json.dump(data, fp, sort_keys=True, indent=2)
            fp.write("\n")
    except (OSError, ValueError, KeyError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"FAIL: D4.2 original config and warning risk review: {exc}", file=sys.stderr)
        return 2
    print("D4.2 original warning-by-warning risk review COMPLETE; 1 documented "
          "intentional OCM exclusion, 63 still unresolved; zero configuration "
          "changes justified from readbacks alone; AXI PROTOCOL BLOCKED")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
