#!/usr/bin/env python3
"""Read-only inventory of accepted Vitis-generated HLS RTL for G3.3 binding.

Requires verified original G1/G2 source evidence, original AMD DWC ABI and
independent G3.2 ZIP; never modifies vendor IP or claims connected HLS XSim.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

from m06_g3_original_link_inputs import verify as verify_hls_vendor
from m06_g3_exact_original_pin_matrix import matrix
from m06_g3_2_connected_evidence_audit import verify_zip
from m06_generate_original_mem_sc_bfm import original_ports
from m06_g3_capture_dwc_ports import capture
from m06_g3_generate_real_dwc_original_sc_bfm import exact_dwc_abi
from m06_paged_hls_port_audit import TOP, parse_top

def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_inventory(folder: Path) -> list[dict]:
    root=folder.resolve(strict=True)
    if root.name!="verilog" or root.parent.name!="syn":
        raise ValueError("must inventory genuine Vitis work/hls/syn/verilog")
    sources=[]
    for p in sorted(root.iterdir()):
        if p.is_symlink():
            raise ValueError("unexpected RTL symlink")
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".v",".sv",".vh",".svh"):
            continue
        if p.stat().st_size==0 or p.stat().st_size>8_000_000:
            raise ValueError("empty/oversized generated HLS file")
        sources.append({"name":p.name,"sha256":_hash(p),"bytes":p.stat().st_size,
                        "language":"verilog_header" if p.suffix.lower() in (".vh",".svh") else "verilog"})
    if not any(x["name"]==TOP+".v" for x in sources):
        raise ValueError("actual generated HLS top missing")
    if len(sources)>500 or not sources:
        raise ValueError("unexpected HLS generated RTL source set")
    return sources

def contract(hls_pins: dict, original: dict, dwc: dict, rtl_files: list[dict],
             accepted_g32: dict) -> dict:
    if accepted_g32.get("status")!="PASS_G3_2_BFM_ONLY_ORIGINAL_AMD_XSIM_2025_2" or (
        accepted_g32.get("generated_hls_neural_rtl_connected") is not False
    ):
        raise ValueError("G3.2 evidence does not establish BFM-only connected PASS")
    mapped=matrix(hls_pins,original)
    if mapped.get("status")!="REAL_HEADER_ROLES_AND_WIDTHS_ONLY_NOT_BOUND":
        raise ValueError("HLS pin role matrix changed")
    if len(mapped["paths"])!=2 or [x["original_si"] for x in mapped["paths"]]!=["S00","S03"]:
        raise ValueError("incorrect original SmartConnect roles")
    for ip,sc in (("m06_g3_read_dwc","S00"),("m06_g3_write_dwc","S03")):
        entry=dwc["instances"].get(ip)
        if not entry or entry["pins"]!=exact_dwc_abi(sc,original) or (
            entry.get("role")!=("READ_ONLY" if sc=="S00" else "WRITE_ONLY")
        ):
            raise ValueError("generated original AMD DWC ABI mismatch: "+ip)
    names=[r["name"] for r in rtl_files]
    if len(names)!=len(set(names)) or TOP+".v" not in names:
        raise ValueError("missing/duplicate HLS generated source")
    for name,(direction,width) in hls_pins.items():
        if direction not in ("input","output","inout") or not 1<=width<=65536:
            raise ValueError("invalid HLS generated pin "+name)
    interesting=sorted(k for k in hls_pins if k.startswith("m_axi_") or
                       k.startswith("s_axi_") or k in ("ap_clk","ap_rst_n"))
    return {
        "schema":"m06-g3-3-real-hls-rtl-interface-inventory-v1",
        "status":"REAL_HLS_RTL_AND_AMD_ABI_INVENTORIED_NOT_CONNECTED",
        "g3_2_evidence_sha256":accepted_g32["evidence_zip_sha256"],
        "g3_2_verified_bfm_only":True,
        "hls_top":TOP,
        "hls_port_count":len(hls_pins),
        "hls_complete_top_ports":{
            k:{"direction":v[0],"width_bits":v[1]} for k,v in sorted(hls_pins.items())
        },
        "hls_axi_control_clock_and_sideband_ports":interesting,
        "hls_rtl_file_inventory":rtl_files,
        "hls_pin_matrix":mapped["paths"],
        "required_64_to_32_guards":"ACTUAL_GUARD_BOTH_M_AXI_ROLES_NOT_YET_CONNECTED",
        "actual_original_amd_dwc":"READ_ONLY_AND_WRITE_ONLY_ABI_ATTESTED",
        "id_lock_user_region_adaptation":"REQUIRES_MEASURED_PIN_BY_PIN_RTL_VERIFICATION",
        "cross_master_B_to_AR_barrier":"NOT_PROVEN",
        "stream_and_axilite_host_drivers":"NOT_CONNECTED",
        "independent_neural_M02_M03_parity":"NOT_PROVEN",
        "original_vendor_xsim_with_actual_HLS":False,
        "physical_ddr_or_board":False,
        "g3_3_complete":False,
        "g4_complete":False,
        "m06_complete":False,
    }

def inventory(hls: Path,vendor_ae: Path,repo: Path,d3: Path,
              headers: Path,dwc_dir: Path,g32zip: Path) -> dict:
    accepted=verify_zip(g32zip)
    hls_attest=verify_hls_vendor(hls,vendor_ae,repo)
    rtldir=hls.resolve(strict=True)/"work/hls/syn/verilog"
    sources=source_inventory(rtldir)
    pins=parse_top((rtldir/(TOP+".v")).read_text(encoding="utf8",errors="replace"))
    original=original_ports(d3.resolve(strict=True),json.loads(headers.read_text()))
    vendor_pins={p["name"]:(p["direction"],p["packed_width"]) for p in original}
    actual_dwc=capture(dwc_dir)
    report=contract(pins,vendor_pins,actual_dwc,sources,accepted)
    if hls_attest["hls_generated_top_sha256"] != next(
        x["sha256"] for x in sources if x["name"]==TOP+".v"
    ):
        raise ValueError("HLS genuinely accepted top SHA differs from inventory")
    report["hls_owner_evidence_folder"]=hls_attest["hls_cosim_folder"]
    report["hls_source_commit"]=hls_attest["hls_commit"]
    report["hls_real_top_sha256"]=hls_attest["hls_generated_top_sha256"]
    report["original_vendor_stage_e_sha256"]=hls_attest["original_vendor_stage_e_sha256"]
    return report

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ("hls-cosim","vendor-a-e","repo","d3","headers","dwc","g3-2-zip","output"):
        ap.add_argument("--"+name,required=True,type=Path)
    a=ap.parse_args()
    try:
        if a.output.exists() or not a.output.parent.is_dir():
            raise ValueError("output must be fresh in an existing directory")
        out=inventory(a.hls_cosim,a.vendor_a_e,a.repo,a.d3,a.headers,a.dwc,a.g3_2_zip)
        a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as e:
        print("M06_G3_3_REAL_HLS_INVENTORY_REJECTED:",e,file=sys.stderr)
        return 2
    print("M06_G3_3_REAL_HLS_RTL_INVENTORY_READY NOT_CONNECTED_NO_NEURAL_XSIM_OR_BOARD")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
