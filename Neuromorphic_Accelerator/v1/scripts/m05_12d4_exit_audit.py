#!/usr/bin/env python3
"""M05.12d.4 D4.4 truth-table audit, without closing M05 or entering M06.

This audit deliberately distinguishes verified provenance, original read-only
property/model availability, synthetic byte-oracle readiness and actual
on-chip inference / generated vendor AXI functional success (NOT PROVIDED).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from m05_12d4_protocol_risk import NEW_PREFIX


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def audit(evidence: Path) -> dict:
    root = evidence.resolve(strict=True)
    if not root.name.startswith(NEW_PREFIX):
        raise ValueError("only a newly created D4.2/D4.3 owner gate folder is accepted")
    riskp = root / "02_original_axi_risk.json"
    riskpost = root / "07_post_original_axi_risk.json"
    feasibilityp = root / "06_model_discovery_audit.json"
    before = root / "source_sha256.txt"
    after = root / "08_source_sha256_after.txt"
    if (not before.is_file() or not after.is_file() or before.read_bytes() != after.read_bytes()
            or not riskp.is_file() or not riskpost.is_file() or
            riskp.read_bytes() != riskpost.read_bytes() or not feasibilityp.is_file()):
        raise ValueError("previous authentic source or source risk proofs not immutable")
    risk, vendor = json.loads(riskp.read_text()), json.loads(feasibilityp.read_text())
    if (risk.get("scope") != "M05_D4_2_GENUINE_ORIGINAL_READONLY_RISK_AND_NO_AUTOMATIC_CHANGE"
            or risk.get("warning_counts") != {
                "UNRESOLVED_BLOCKER": 63, "DOCUMENTED_INTENTIONAL_OCM_EXCLUSION_ONLY": 1}
            or risk.get("decision") != "NO_MUTATION_JUSTIFIED_FROM_CONFIGURATION_READBACK_ALONE"
            or risk.get("m05_exit") != "OPEN"
            or vendor.get("scope") != "ORIGINAL_D3_READ_ONLY_VENDOR_SIM_SOURCE_DISCOVERY"
            or vendor.get("simulation") != "NOT_RUN"
            or vendor.get("vendor_downsize_axi_protocol") != "NOT_PROVEN"
            or vendor.get("original_d3") != risk.get("original_d3")
            or vendor.get("original_d4_1b") != risk.get("d4_1b_property_evidence")):
        raise ValueError("D4 source evidence or vendor-model result inconsistent/misrepresented")
    return {
        "scope": "M05_D4_4_EVIDENCE_EXIT_DECISION_NOT_M05_COMPLETION",
        "d4_1_original_2025_2_warning_inventory": "PASSED_PROVENANCE_64_WARNINGS",
        "d4_1b_original_2025_2_bd_axi_properties": "PASSED_23_ENDPOINTS_11_PAIRS",
        "d4_2_original_warning_by_warning_review": "COMPLETE_READONLY_1_INTENTIONAL_OCM_63_UNRESOLVED",
        "d4_2_configuration_correction": "NOT_APPLIED_63_WARNINGS_STILL_BLOCKED",
        "d4_3_independent_byte_oracle": "SOURCE_ONLY_NATIVE_TESTS_NOT_VENDOR_RTL",
        "d4_3_generated_smartconnect_model_file_discovery": vendor["compile_order_status"],
        "d4_3_genuine_vendor_simulation": "NOT_RUN",
        "d4_3_full_bd_synthesis_and_route": "NOT_RUN",
        "m05_acceptance_target": "INDEPENDENT_ONCHIP_EVENT_DRIVEN_INFERENCE_AND_COUNTERS_WITHOUT_DDR_VIRTUAL_PAGING",
        "m05_independent_onchip_acceptance": "NOT_ESTABLISHED_BY_D4_ORIGINAL_PROPERTY_PROBE",
        "m05_closure": "OPEN_REQUIRES_EVIDENCE_AND_USER_APPROVAL",
        "m06": "NOT_STARTED",
        "physical_board": "NOT_AUTHORIZED",
        "pr_79": "DRAFT_UNMERGED",
        "d4_protocol_risk_sha256": sha(riskp),
        "original_vendor_model_discovery_sha256": sha(feasibilityp),
        "decision": "STOP_AT_GENUINE_OFFLINE_VENDOR_SIMULATION_AND_M05_ACCEPTANCE_BOUNDARY",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        folder = a.evidence.resolve(strict=True)
        if (a.output.parent.resolve(strict=True) != folder or a.output.name != "09_m05_exit_audit.json"
                or a.output.exists()):
            raise ValueError("D4.4 must write one fresh evidence-local audit")
        result = audit(a.evidence)
        with a.output.open("x", encoding="utf-8") as fp:
            json.dump(result, fp, indent=2, sort_keys=True)
            fp.write("\n")
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as err:
        print(f"FAIL: original M05.12d.4 exit audit: {err}", file=sys.stderr)
        return 2
    print("D4.4 original evidence-based exit audit COMPLETE: M05 OPEN, "
          "63 AXI warnings unresolved, M06 NOT STARTED, no FPGA authorization")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
