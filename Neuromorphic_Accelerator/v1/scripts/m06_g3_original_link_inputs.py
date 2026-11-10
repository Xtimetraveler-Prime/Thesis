#!/usr/bin/env python3
"""Gate G3: verify both genuine owner source artifacts BEFORE vendor AXI binding.

Only reads owner files and emits a new immutable-style JSON report. No Vivado,
synthesis, IP mutation, memory allocation, board or JTAG operations. It does
NOT claim actual HLS-to-original-SmartConnect linkage or AXI coherency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from m06_paged_hls_port_audit import audit as hls_ports
from m06_original_stage_e_evidence_audit import audit as vendor_stages
from m06_paged_hls_axi_link_plan import plan as width_plan

CANONICAL_SOURCES = (
    "hls/m04_lif_eval/m04_eval.cpp",
    "hls/m05_rolling/m05_rolling.cpp",
    "hls/m06_paged_rolling/m06_paged_rolling.cpp",
    "hls/m06_paged_rolling/m06_paged_rolling.hpp",
    "hls/m06_paged_rolling/m06_paged_rolling_csim_tb.cpp",
)
PASS = "INFO: [COSIM 212-1000] *** C/RTL co-simulation finished: PASS ***"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_manifest(text: str) -> dict[str, str]:
    result = {}
    for line in text.strip().splitlines():
        row = re.fullmatch(r"([0-9a-f]{64})\s+(\S+)", line)
        if not row or row[2] in result:
            raise ValueError("invalid/repeated HLS source manifest entry")
        result[row[2]] = row[1]
    return result


def verify(owner_hls: Path, vendor: Path, repo: Path) -> dict:
    owner_hls = owner_hls.resolve(strict=True)
    repo = repo.resolve(strict=True)
    if not owner_hls.name.startswith("m06_paged_rolling_hls_cosim_"):
        raise ValueError("G3 requires a real cosim evidence directory, not synth or CSim alone")
    if (owner_hls/"result.txt").read_text().strip() != "exit_status=0" or (
        owner_hls/"mode.txt").read_text().strip() != "cosim":
        raise ValueError("genuine generated HLS RTL cosim not successful")
    commit = (owner_hls/"commit.txt").read_text().strip()
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("cosim owner commit is invalid")
    if (owner_hls/"source_before_sha256.txt").read_bytes() != (
        owner_hls/"source_after_sha256.txt").read_bytes():
        raise ValueError("HLS owner source digests changed during cosim")
    source_hashes = _read_manifest((owner_hls/"source_before_sha256.txt").read_text())
    for name in CANONICAL_SOURCES:
        f = repo / name
        if not f.is_file() or source_hashes.get(name) != _hash(f):
            raise ValueError("current canonical HLS source differs from genuine passed RTL: "+name)
    csim = (owner_hls/"01_csim.log").read_text(errors="replace")
    synth = (owner_hls/"02_csynth.log").read_text(errors="replace")
    cosim = (owner_hls/"03_cosim.log").read_text(errors="replace")
    if "v2025.2" not in csim or "CSim done with 0 errors" not in csim or (
        "M06_PAGED_ROLLING_HLS_CSIM_PASS" not in csim):
        raise ValueError("genuine Vitis 2025.2 CSim proof missing")
    if "v2025.2" not in synth or "Generating Verilog RTL" not in synth:
        raise ValueError("genuine Vitis 2025.2 synthesized RTL proof missing")
    for marker in (
        "Using XSIM for RTL simulation",
        "Starting C TB testing",
        "Starting verilog simulation",
        "Starting C post checking",
        PASS,
    ):
        if cosim.count(marker) != 1:
            raise ValueError("missing/duplicated genuine C/RTL cosim step: "+marker)
    if re.search(r"(?m)^M06_HLS_CSIM_(?:FAIL|DIAG)|"
                 r"\*\*\* C/RTL co-simulation finished: FAIL \*\*\*|"
                 r"COSIM 212-359|\bFATAL_ERROR\b", cosim):
        raise ValueError("cosim log contains a diagnostic or failed test")
    if (owner_hls/"work/hls/sim/report/m06_paged_rolling_replay_cosim.rpt").is_file():
        cosim_report = str(owner_hls/"work/hls/sim/report/m06_paged_rolling_replay_cosim.rpt")
    else:
        cosim_report = "OWNER_REPORT_NOT_PROVIDED"
    pins = hls_ports(owner_hls)
    widths = width_plan(pins)
    stages = vendor_stages(vendor)
    if stages.get("status") != "ORIGINAL_VENDOR_A_E_XSIM_VERIFIED_OFFLINE_SCRATCH_ONLY" or (
        stages.get("m06_complete") is not False):
        raise ValueError("original AMD Stage A-E evidence not independently attested")
    paths = widths["paths"]
    if len(paths) != 2 or any(
        path["generated_hls_data_width"] != 32 or
        path["generated_hls_address_width"] != 64 or
        path["original_smartconnect_data_width"] != 256 or
        path["required_width_adapter"] is not True
        for path in paths
    ):
        raise ValueError("measured AXI pins changed: 32-to-256 path needs re-design")
    if [path["original_smartconnect_slave"] for path in paths] != ["S00", "S03"]:
        raise ValueError("original SmartConnect READ/WRITE port role mismatch")
    return {
        "schema": "m06-g3-original-vendor-plus-real-hls-input-gate-v1",
        "status": "REAL_HLS_COSIM_AND_ORIGINAL_AMD_A_E_READY_FOR_UNPROVEN_LINK_TRIAL",
        "hls_cosim_folder": str(owner_hls),
        "hls_commit": commit,
        "hls_generated_top_sha256": pins["generated_top_sha256"],
        "hls_generated_verilog_source_count": pins["generated_rtl_count"],
        "cosim_log_sha256": _hash(owner_hls/"03_cosim.log"),
        "cosim_report_path": cosim_report,
        "original_vendor_folder": stages["evidence_folder"],
        "original_vendor_commit": stages["owner_commit"],
        "original_vendor_stage_e_sha256": stages["stage_e_log_sha256"],
        "required_adapters": [
            {"hls": "gmem_read", "width_in": 32, "width_out": 256,
             "original_si": "S00", "direction": "READ_ONLY"},
            {"hls": "gmem_write", "width_in": 32, "width_out": 256,
             "original_si": "S03", "direction": "WRITE_ONLY"},
        ],
        "canonical_scratch_bytes": 65536,
        "shared_memory": "MANDATORY_SAME_64K_BUT_NOT_YET_CONNECTED",
        "cross_master_B_response_to_AR_order": "NOT_PROVEN",
        "original_smartconnect_bound_to_hls": False,
        "genuine_connected_RTL_XSim": False,
        "m06_complete": False,
        "physical_board_or_DDR": "NOT_AUTHORIZED_NOT_TESTED",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hls-cosim", required=True, type=Path)
    ap.add_argument("--vendor-a-e", required=True, type=Path)
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    try:
        if not args.output.parent.is_dir() or args.output.exists():
            raise ValueError("G3 manifest requires a new filename in an existing directory")
        data = verify(args.hls_cosim, args.vendor_a_e, args.repo)
        with args.output.open("x", encoding="utf8") as fp:
            json.dump(data, fp, indent=2, sort_keys=True)
            fp.write("\n")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print("M06 G3 owner integration inputs REJECTED: "+str(error), file=sys.stderr)
        return 2
    print("M06 genuine HLS cosim + original AMD A-E inputs VERIFIED: 32-to-256 S00/S03 link STILL UNCONNECTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
