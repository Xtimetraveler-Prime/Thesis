#!/usr/bin/env python3
"""Read-only auditor of a genuine original AMD SmartConnect Stage A-E XSim run.

This checker rejects missing, mutated and contradictory owner evidence. It is
NOT a substitute for actual XSim, generated HLS IP, connected DDR, or a board.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

PREFIX = "m06_original_vendor_mem_sc_xsim_"
ORIGINAL_D3 = "neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
LOG_MARKERS = {
    "05_xsim.log": ("M06_ORIGINAL_SMARTCONNECT_VENDOR_XSIM_PASS",),
    "07_paged_xsim.log": ("M06_ORIGINAL_VENDOR_PAGED_RTL_PASS",
                           "M06_ORIGINAL_VENDOR_PAGED_FAULT_QUARANTINE_PASS"),
    "09_neural_paged_xsim.log": ("M06_ORIGINAL_VENDOR_NEURAL_PAGED_M02_PARITY_PASS",
                                  "M06_ORIGINAL_VENDOR_NEURAL_PAGED_FAULT_PASS"),
    "11_lru8_xsim.log": ("M06_ORIGINAL_VENDOR_LRU8_RTL_PASS",
                           "M06_ORIGINAL_VENDOR_LRU8_FAULT_PASS"),
    "13_4096_xsim.log": ("M06_ORIGINAL_VENDOR_4096_RANGE_PASS",
                           "M06_ORIGINAL_VENDOR_4096_OUT_OF_RANGE_QUARANTINE_PASS"),
}
BAD = re.compile(r"M06_VENDOR_(?:4096|NEURAL|LRU8)_FAIL|M06_ORIGINAL_PAGED_FAIL|"
                 r"M06_VENDOR_FAIL|FATAL_ERROR|\bFatal:|\$fatal\b|\bERROR:\b")
REQUIRED_RANGE = re.compile(
    r"^M06_ORIGINAL_VENDOR_4096_RANGE_PASS "
    r"highest_page=255 last_neuron=4095 last_byte=65535 "
    r"dirty_wb=1 M00_write=16 M00_read=48\s*$", re.M)
REQUIRED_QUARANTINE = re.compile(
    r"^M06_ORIGINAL_VENDOR_4096_OUT_OF_RANGE_QUARANTINE_PASS "
    r"block256_rejected=1 no_physical_DDR=1\s*$", re.M)
REQUIRED_TB = (
    "module tb_m06_original_vendor_4096;",
    "m06_axi256_block_transfer #(.MAX_BLOCKS(256)",
    "m06_axi128_scratch_mem #(.SCRATCH_BYTES(65536))",
    "M06_ORIGINAL_VENDOR_4096_RANGE_PASS",
    "M06_ORIGINAL_VENDOR_4096_OUT_OF_RANGE_QUARANTINE_PASS",
    "M06_VENDOR_4096_FAIL",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(text: str) -> dict[Path, str]:
    found: dict[Path, str] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  (/\S+)", line)
        if match is None:
            raise ValueError("malformed SHA256 manifest")
        path = Path(match.group(2))
        if path in found:
            raise ValueError("duplicate SHA256 path")
        found[path] = match.group(1)
    if len(found) != 2:
        raise ValueError("expected exactly two original AMD source digests")
    return found


def audit(folder: Path) -> dict:
    folder = folder.resolve(strict=True)
    if not folder.is_dir() or not folder.name.startswith(PREFIX):
        raise ValueError("expected an original AMD XSim evidence folder")
    if (folder / "result.txt").read_text().strip() != "exit_status=0":
        raise ValueError("owner vendor XSim exit status not successful")
    commit = (folder / "commit.txt").read_text().strip()
    if re.fullmatch(r"[a-f0-9]{40}", commit) is None:
        raise ValueError("original run commit SHA missing or invalid")
    original = Path((folder / "original_directory.txt").read_text().strip())
    if original.name != ORIGINAL_D3 or not original.is_dir():
        raise ValueError("original D3 owner source directory missing/wrong")
    original = original.resolve(strict=True)
    before = (folder / "sha_before.txt").read_text()
    after = (folder / "sha_after.txt").read_text()
    if before != after:
        raise ValueError("original AMD source SHA manifests differ")
    sources = manifest(before)
    names = {path.name for path in sources}
    if len(names) != 2 or not any(name.endswith("mem_sc_0.sv") for name in names) or "bd_13bd.v" not in names:
        raise ValueError("original AMD IP top/submodule identity mismatch")
    for path, expected in sources.items():
        if not path.is_file() or not path.resolve().is_relative_to(original):
            raise ValueError("original AMD source path escaped owner D3")
        if sha256(path) != expected:
            raise ValueError("original AMD source content no longer matches owner SHA")
    glbl = (folder / "installed_vivado_glbl_sha256.txt").read_text()
    gm = re.fullmatch(r"([a-f0-9]{64})  (/\S+)(?:\n)?", glbl)
    if gm is None or Path(gm.group(2)).name != "glbl.v":
        raise ValueError("original Vivado glbl provenance missing")
    glbl_path = Path(gm.group(2))
    if not glbl_path.is_file() or sha256(glbl_path) != gm.group(1):
        raise ValueError("installed Vivado glbl content has changed")
    generated_tb = (folder / "tb_m06_original_vendor_4096.sv").read_text()
    for token in REQUIRED_TB:
        if token not in generated_tb:
            raise ValueError("original Stage E generated bench contract missing: " + token)
    xvlog = (folder / "03_xvlog.log").read_text(errors="replace")
    if "2025.2" not in xvlog or "tb_m06_original_vendor_4096" not in xvlog:
        raise ValueError("original AMD vendor RTL/Stage E compile provenance missing")
    xelab = (folder / "12_4096_xelab.log").read_text(errors="replace")
    if "2025.2" not in xelab or "m06_original_vendor_4096_snapshot" not in xelab:
        raise ValueError("Stage E genuine XSim elaboration evidence missing")
    for name, markers in LOG_MARKERS.items():
        log = (folder / name).read_text(errors="replace")
        if "xsim v2025.2" not in log:
            raise ValueError("original 2025.2 xsim version missing: " + name)
        if BAD.search(log):
            raise ValueError("original XSim log reports a failure: " + name)
        if re.findall(r"(?m)^exit[ \t]+[0-9]+[ \t]*$", log) != ["exit 0"]:
            raise ValueError("original XSim log lacks unique clean exit: " + name)
        for marker in markers:
            if len(re.findall(r"(?m)^" + re.escape(marker) + r"\b", log)) != 1:
                raise ValueError("missing/duplicate original vendor marker: " + marker)
        if name == "13_4096_xsim.log":
            if not REQUIRED_RANGE.search(log) or not REQUIRED_QUARANTINE.search(log):
                raise ValueError("Stage E exact byte/range/quarantine scoreboard mismatch")
    return {
        "schema": "m06-original-amd-stage-a-e-evidence-audit-v1",
        "status": "ORIGINAL_VENDOR_A_E_XSIM_VERIFIED_OFFLINE_SCRATCH_ONLY",
        "owner_commit": commit,
        "evidence_folder": str(folder),
        "original_d3": str(original),
        "original_sources_sha256": {str(p): digest for p, digest in sources.items()},
        "stage_e_log_sha256": sha256(folder / "13_4096_xsim.log"),
        "stage_e_bench_sha256": sha256(folder / "tb_m06_original_vendor_4096.sv"),
        "stages": {name: "ORIGINAL_AMD_XSIM_2025_2_PASS" for name in LOG_MARKERS},
        "legal_last_page": 255,
        "illegal_first_page": 256,
        "canonical_memory_bytes": 65536,
        "hls_engine_instantiated": False,
        "generated_hls_to_original_smartconnect": "NOT_TESTED",
        "physical_ddr": "NOT_ACCESSED",
        "m06_complete": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists() or not args.output.parent.is_dir():
            raise ValueError("output must be a fresh JSON in an existing directory")
        data = audit(args.evidence)
        with args.output.open("x", encoding="utf-8") as out:
            json.dump(data, out, indent=2, sort_keys=True)
            out.write("\n")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print("M06 ORIGINAL Stage A-E owner evidence REJECTED: " + str(error), file=sys.stderr)
        return 2
    print("M06 original AMD Stage A-E owner-source and XSim logs VERIFIED; generated HLS/DDR NOT TESTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
