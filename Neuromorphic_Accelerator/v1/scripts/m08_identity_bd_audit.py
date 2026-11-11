#!/usr/bin/env python3
"""Independently audit a local genuine M08 PS→PL identity BD validation.

Do not conflate a Vivado BD validate PASS with synth/implementation,
bitstream, XSA, Linux MMIO, JTAG, real neural inference or PS DDR.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

SCOPE="M08_GENUINE_LOCAL_VIVADO_PS_TO_READONLY_PL_ID_BD_CANDIDATE"
MARKER="M08_IDENTITY_GENUINE_VIVADO_BD_VALIDATED_NO_BITSTREAM_NO_BOARD"
FILES=("rtl/m08/m08_axil_readonly_identity.v",
       "scripts/m08_identity_ps_bd_candidate.tcl",
       "scripts/m08_identity_bd_audit.py",
       "scripts/run_m08_identity_bd.sh")


def _hash(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def audit_evidence(folder:Path,root:Path)->dict:
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("existing nonsymlink evidence directory required")
    result=(folder/"result.txt").read_text().strip()
    if result!="exit_status=0":
        raise ValueError("original Vivado returned nonzero or result missing")
    before=(folder/"source_sha256_before.txt").read_bytes()
    after=(folder/"source_sha256_after.txt").read_bytes()
    if before!=after or not before:
        raise ValueError("before/after source fingerprint mismatch")
    expected="".join(f"{_hash(root/name)}  {name}\n" for name in FILES).encode()
    if before!=expected:
        raise ValueError("source SHA manifest not for current M08 checkout")
    lines=(folder/"02_vivado_identity_bd_readback.txt").read_text().strip().splitlines()
    if len(lines)!=14:
        raise ValueError("unexpected M08 original Vivado report row count")
    required_prefixes=(
        "META|scope|"+SCOPE,
        "META|part|xck26-sfvc784-2LV-c",
        "META|vivado_version|2025.2",
        "META|requested_clock_hz|100000000",
        "META|identity_source|rtl/m08/m08_axil_readonly_identity.v",
        "MASTER|", "SLAVE|", "APERTURE|",
        "META|validated_bd|YES",
        "META|routed_implementation|NOT_RUN",
        "META|bitstream|NOT_GENERATED",
        "META|ps_linux_memory_driver|NOT_CONNECTED",
        "META|physical_ddr|NOT_ACCESSED",
        "META|physical_kv260|NOT_PROGRAMMED",
    )
    for index,(line,prefix) in enumerate(zip(lines,required_prefixes)):
        if not line.startswith(prefix):
            raise ValueError(f"M08 original Vivado report line {index} mismatch")
    for index in (5,6):
        fields=lines[index].split("|")
        if len(fields)!=3 or not all(fields):
            raise ValueError("original PS master/PL slave interface not witnessed")
        if index==5 and "M_AXI_HPM0_FPD" not in fields[1]:
            raise ValueError("not connected to original PS HPM0")
        if index==6 and "S_AXI" not in fields[1]:
            raise ValueError("not connected to read-only identity slave")
    addr=lines[7].split("|")
    if len(addr)!=4 or not all(addr):
        raise ValueError("Vivado assigned address aperture report malformed")
    for value in addr[2:]:
        if not re.fullmatch(r"0x[0-9a-fA-F]+",value):
            raise ValueError("Vivado aperture offset/range not original hex")
    base,length=(int(addr[i],16) for i in (2,3))
    if length<32 or base%4 or length%4 or base+length>2**32:
        raise ValueError("Vivado assigned aperture not bounded/word aligned")
    log=(folder/"01_vivado_identity_bd.log").read_text(errors="replace")
    if log.count(MARKER)!=1:
        raise ValueError("genuine Vivado success marker missing or duplicated")
    if ("ERROR:" in log or "CRITICAL WARNING:" in log or
            "Common 17-55" in log):
        raise ValueError("Vivado generated errors or unreviewed critical warning")
    script=(folder/"03_identity_bd_export.tcl")
    if not script.is_file() or script.stat().st_size<100:
        raise ValueError("original Vivado BD export was not generated")
    # The report is real only if its source proof and original Vivado
    # invocation both exist; we still cannot cryptographically attest the
    # machine/user to GitHub-hosted automated tests.
    return {
        "status":"ORIGINAL_OWNER_VIVADO_BD_VALIDATION_EVIDENCE_CONSISTENT",
        "scope":SCOPE,
        "model_only":False,
        "source_sha256_manifest":_hash(folder/"source_sha256_before.txt"),
        "report_sha256":_hash(folder/"02_vivado_identity_bd_readback.txt"),
        "vivado_log_sha256":_hash(folder/"01_vivado_identity_bd.log"),
        "vivado_bd_export_sha256":_hash(script),
        "ps_axi_addr_observed_in_bd":True,
        "ps_axi_aperture_offset":f"0x{base:08x}",
        "ps_axi_aperture_range":f"0x{length:x}",
        "physical_mmio_performed":False,
        "routed_implementation":False,
        "bitstream_programmed":False,
        "physical_ddr":False,
        "neural_inference_verified":False,
    }


def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence-dir",type=Path,required=True)
    ap.add_argument("--source-root",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    try:
        if (a.output.exists() or a.output.is_symlink() or
                a.output.parent.resolve()!=a.evidence_dir.resolve()):
            raise ValueError("independent audit must write new file inside evidence folder")
        report=audit_evidence(a.evidence_dir,a.source_root)
        with a.output.open("x",encoding="utf-8") as f:
            json.dump(report,f,sort_keys=True,indent=2)
            f.write("\n")
    except (ValueError,OSError) as exc:
        print("M08_IDENTITY_BD_AUDIT_REJECTED:",exc,file=sys.stderr)
        return 2
    print("M08_IDENTITY_BD_SOURCE_AND_ORIGINAL_VIVADO_RECEIPT_AUDITED_NOT_PHYSICAL")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
