#!/usr/bin/env python3
"""Audit genuine Vivado output products; this cannot prove synthesized adapter internals."""
import argparse
import hashlib
from pathlib import Path
import sys

WIDTHS = (("dma_neurons/M_AXI_MM2S",256),("mem_sc/S00_AXI",256),
          ("dma_synapses/M_AXI_MM2S",256),("mem_sc/S01_AXI",256),
          ("dma_external/M_AXI_MM2S",256),("mem_sc/S02_AXI",256),
          ("dma_trace/M_AXI_S2MM",256),("mem_sc/S03_AXI",256),
          ("mem_sc/M00_AXI",128),("ps/S_AXI_HP0_FPD",128))
SCOPE="META|scope|OFFLINE_REAL_VIVADO_BD_OUTPUT_PRODUCTS_WIDTH_CONTRACT"
TAIL=["GENERATE_TARGET|all|PASS","META|physical_board|NOT_AUTHORIZED",
      "META|synthesis|NOT_RUN","META|converter_internals|NOT_PROVEN_BY_OUTPUT_PRODUCTS"]
SUCCESS="M05_D3_IP_OUTPUT_TARGET_PASS|GENUINE_FILE_BACKED_BD_PRODUCTS|WIDTH_ENDPOINTS=10|SYNTHESIS=NOT_RUN"

def check(evidence: Path, report: str, log: str):
    root=evidence.resolve(strict=True)
    if not root.is_dir() or not root.name.startswith("neuromorphic_v1_m05_12d3_ip_output_"):
        raise ValueError("genuine owner IP-output evidence directory required")
    lines=report.strip().splitlines()
    if len(lines)!=3+len(WIDTHS)+len(TAIL) or lines[0]!=SCOPE or lines[-4:]!=TAIL:
        raise ValueError("truncated, duplicate or forged width/generation report")
    def path_from(prefix, row):
        if not row.startswith(prefix):raise ValueError("expected vendor output record "+prefix)
        p=Path(row[len(prefix):])
        if not p.is_absolute():raise ValueError("expected absolute vendor path")
        p=p.resolve(strict=True)
        if not p.is_file() or not p.is_relative_to(root):
            raise ValueError("vendor output missing or outside owner evidence")
        return p
    xpr=path_from("PROJECT|",lines[1]); bd=path_from("BD|",lines[2])
    if xpr.parent.name!="13_file_backed_project" or xpr.name!="m05_d3_output_products.xpr":
        raise ValueError("genuine file-backed project identity missing")
    if bd.suffix!=".bd" or not bd.is_relative_to(xpr.parent) or "m05_12d3_real_signed32_hls_six_control_address_candidate" not in bd.name:
        raise ValueError("genuine saved current BD missing")
    for row,(name,bits) in zip(lines[3:13],WIDTHS):
        if row!=f"WIDTH|{name}|{bits}":raise ValueError("genuine vendor endpoint width mismatch "+name)
    if SUCCESS not in log or "ERROR:" in log:
        raise ValueError("Vivado generation success marker absent or genuine vendor error present")
    gen=xpr.parent/"m05_d3_output_products.gen"
    if not gen.is_dir():raise ValueError("actual Vivado .gen folder missing")
    products=sorted(p for p in gen.rglob("*") if p.is_file() and p.suffix.lower() in {".v",".sv",".vhd",".vhdl",".vp",".xci"})
    if not products or not any("mem_sc" in p.relative_to(gen).as_posix().lower() for p in products):
        raise ValueError("generated memory SmartConnect HDL/IP file missing")
    hashes=[]
    for p in products:
        if p.is_symlink() or not p.resolve(strict=True).is_relative_to(root):
            raise ValueError("generated file escapes evidence boundary")
        with p.open("rb") as file: digest=hashlib.file_digest(file,"sha256").hexdigest()
        hashes.append((p.relative_to(root).as_posix(),digest))
    return dict(generated=len(products),mem_sc=sum("mem_sc" in p.as_posix().lower() for p in products),board=0,synthesis=0,adapter_internals=0),hashes

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir",type=Path,required=True)
    parser.add_argument("--width-report",type=Path,required=True)
    parser.add_argument("--vivado-log",type=Path,required=True)
    parser.add_argument("--generated-manifest",type=Path,required=True)
    a=parser.parse_args()
    try:
        if a.generated_manifest.exists() or a.generated_manifest.parent.resolve()!=a.evidence_dir.resolve():
            raise ValueError("hash manifest must be NEW and located in owner evidence")
        status,hashes=check(a.evidence_dir,a.width_report.read_text(),a.vivado_log.read_text())
        with a.generated_manifest.open("x",encoding="utf-8") as output:
            output.write("META|scope|REAL_VIVADO_OUTPUT_PRODUCT_SHA256\n")
            for path,digest in hashes:output.write(f"SHA256|{digest}|{path}\n")
            output.write("META|synthesis|NOT_RUN\nMETA|physical_board|NOT_AUTHORIZED\n")
    except (OSError,ValueError) as e:
        print(f"FAIL: genuine Vivado IP output-products independent audit: {e}",file=sys.stderr);return 1
    print(f"PASS: M05.12d.3 real file-backed generated memory SmartConnect IP products and 256/128 interface contract {status} (NO SYNTHESIS/BOARD/ADAPTER INTERNALS)");return 0
if __name__=="__main__":raise SystemExit(main())
