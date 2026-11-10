#!/usr/bin/env python3
"""Fail-closed genuine AMD XSim G3.2 owner ZIP audit, BFM-only scope.

Does not run AMD models or claim generated HLS, neural G4, real DDR or board.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile

PASS = "M06_G3_REAL_DWC_ORIGINAL_SC_32TO256_XSIM_PASS"
SOURCE_COMMIT = "9241042486981b8d83c978e6c3153460b64ebff1"
STAGES = {
    "RD_SI32": {"AR": 10, "R_HS": 10},
    "RD_MI256_SC_S00": {"AR": 10, "R_HS": 10},
    "SC_M00_RAM128": {"AR": 10, "R_HS": 10, "AW": 3, "W": 3, "B_HS": 3},
    "WR_SI32": {"AW": 3, "W": 3, "B_HS": 3},
    "WR_MI256_SC_S03": {"AW": 3, "W": 3, "B_HS": 3},
}
REQUIRED = (
    "result.txt", "commit.txt", "07_xsim.log", "08_axi_handshake_trace.log",
    "09_axi_probe_summary.json", "generated_bfm_sha256.txt",
    "tb_m06_g3_real_dwc_original_sc.sv", "04_xvhdl.log", "05_xvlog.log",
    "06_xelab.log", "source_before_sha256.txt", "source_after_sha256.txt",
    "vendor_sha_before.txt", "vendor_sha_after.txt",
    "original_xci_after_sha_check.txt", "03_connected_vendor_compile_plan.json",
)

def _entries(text: str) -> list[dict[str, str]]:
    events = []
    for line in text.splitlines():
        if not line.startswith("M06_G3_AXI_TRACE "):
            continue
        attrs = {}
        for part in line.split()[1:]:
            if part.count("=") != 1:
                raise ValueError("malformed trace token")
            key, value = part.split("=", 1)
            if key in attrs or not key or not value:
                raise ValueError("duplicate/empty trace field")
            attrs[key] = value
        if not attrs.get("t", "").isdigit():
            raise ValueError("trace timestamp invalid")
        events.append(attrs)
    return events

def verify_zip(path: Path) -> dict:
    if not path.is_file():
        raise ValueError("owner evidence ZIP missing")
    with ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or any(
            name.startswith("/") or ".." in Path(name).parts or "/" in name
            for name in names
        ):
            raise ValueError("duplicated or non-flat ZIP member")
        if not set(REQUIRED).issubset(names):
            raise ValueError("missing required owner XSim evidence: " +
                             str(sorted(set(REQUIRED)-set(names))))
        if len(names) > 45 or any(i.file_size > 8_000_000 for i in z.infolist()):
            raise ValueError("oversized/unexpected owner archive")
        def txt(name: str) -> str:
            return z.read(name).decode("utf-8", errors="strict")
        if txt("result.txt").strip() != "exit_status=0":
            raise ValueError("original owner XSim runner did not pass")
        commit = txt("commit.txt").strip()
        if commit != SOURCE_COMMIT:
            raise ValueError("G3.2 evidence not from accepted corrected source")
        for before, after, count in (
            ("source_before_sha256.txt", "source_after_sha256.txt", 5),
            ("vendor_sha_before.txt", "vendor_sha_after.txt", 67),
        ):
            rows = txt(before).strip().splitlines()
            if len(rows) != count or len(set(rows)) != count or any(
                not re.fullmatch(r"[0-9a-f]{64}\s+\S+", line) for line in rows
            ) or z.read(before) != z.read(after):
                raise ValueError("changed/invalid source or vendor SHA manifest")
        xci = txt("original_xci_after_sha_check.txt").strip().splitlines()
        if len(xci) != 2 or not all(s.endswith(".xci: OK") for s in xci) or not all(
            any(f"m06_g3_{role}_dwc" in v for v in xci)
            for role in ("read", "write")
        ):
            raise ValueError("both original AMD width-converter XCI checks must pass")
        tb = z.read("tb_m06_g3_real_dwc_original_sc.sv")
        recorded = txt("generated_bfm_sha256.txt").strip().split()[0]
        if recorded != hashlib.sha256(tb).hexdigest():
            raise ValueError("generated BFM hash mismatch")
        for name in ("04_xvhdl.log", "05_xvlog.log", "06_xelab.log"):
            if re.search(r"(?mi)^\s*(ERROR:|FATAL:|Fatal:)", txt(name)):
                raise ValueError("genuine AMD compile/elaboration errors")
        xsim = txt("07_xsim.log")
        if "xsim v2025.2" not in xsim or xsim.count(PASS) != 1 or (
            "write=3 read=10 m00_w=3 m00_r=10" not in xsim or
            "high_byte=65535 shared_64k=1" not in xsim or
            re.search(r"M06_G3_REAL_DWC_SC_FAIL|M06_G3_AXI_FIRST_DECERR|\bFatal:|\bFATAL_ERROR\b", xsim)
        ):
            raise ValueError("genuine XSim failed/missing original G3.2 PASS")
        trace = txt("08_axi_handshake_trace.log")
        events = _entries(trace)
        if len(events) != 126 or trace.count("M06_G3_AXI_FIRST_DECERR") != 0:
            raise ValueError("incomplete/rejected handshake trace")
        stats = Counter((e.get("stage"), e.get("kind")) for e in events)
        for stage, required in STAGES.items():
            for kind, expected in required.items():
                if stats[(stage, kind)] != expected:
                    raise ValueError(f"wrong accepted handshakes: {stage} {kind}")
        if any(e.get("resp", "00") != "00" or e.get("ram_bad", "0") == "1"
               for e in events):
            raise ValueError("response or RAM-reject trace error")
        addresses = [int(e["addr"], 16) for e in events
                     if e.get("stage") == "RD_SI32" and e.get("kind") == "AR"]
        if addresses != [0, 0xffc, 0x1000, 0xfffc, 0xfffc,
                         0xfff8, 0x1000, 0xffc, 0xff00, 0xfffc]:
            raise ValueError("independent ten-read address sequence changed")
        if [int(e["addr"],16) for e in events if
                e.get("stage")=="WR_SI32" and e.get("kind")=="AW"] != [
                    0xfffc, 0x1000, 0xff00]:
            raise ValueError("three-write address sequence changed")
        if [e["strb"].lower() for e in events if
                e.get("stage")=="SC_M00_RAM128" and e.get("kind")=="W"] != [
                    "5000", "000f", "000f"]:
            raise ValueError("physical M00 byte lanes not verified")
        for e in events:
            if e["kind"] in ("AR", "AW") and (
                int(e["len"]) != 0 or int(e["size"]) != 2 or e["burst"] != "01"
            ):
                raise ValueError("original single 4-byte AXI traffic changed")
        summary = json.loads(txt("09_axi_probe_summary.json"))
        if summary.get("event_count") != len(events) or summary.get("first_decerr") is not None or (
            summary.get("trace_truncated_or_incomplete") is not False or
            summary.get("counter_summary", {}).get("first_decerr") != "0"
        ):
            raise ValueError("XSim probe JSON inconsistent with raw trace")
        for stage, required in STAGES.items():
            for kind, n in required.items():
                if summary["by_stage_kind"][stage][kind] != n:
                    raise ValueError("XSim probe JSON count mismatch")
        return {
            "schema": "m06-g3-2-original-amd-connected-evidence-acceptance-v1",
            "status": "PASS_G3_2_BFM_ONLY_ORIGINAL_AMD_XSIM_2025_2",
            "source_commit": commit,
            "evidence_zip_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "vendor_sha_lines": 67,
            "source_sha_lines": 5,
            "read32_pass": 10,
            "write32_pass": 3,
            "handshake_trace_events": len(events),
            "original_amd_converter_and_smartconnect_exercised": True,
            "generated_hls_neural_rtl_connected": False,
            "physical_ddr_or_board_tested": False,
            "g3_3_complete": False,
            "g4_complete": False,
            "m06_complete": False,
        }

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zip", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    try:
        if a.output.exists() or not a.output.parent.is_dir():
            raise ValueError("output must be new file in existing directory")
        result = verify_zip(a.zip)
        a.output.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    except (OSError, KeyError, ValueError, UnicodeError) as exc:
        print("M06_G3_2_OWNER_EVIDENCE_REJECTED:", exc, file=sys.stderr)
        return 2
    print("M06_G3_2_OWNER_EVIDENCE_ACCEPTED_BFM_ONLY reads=10 writes=3 ORIGINAL_AMD_XSIM NO_HLS_NO_BOARD")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
