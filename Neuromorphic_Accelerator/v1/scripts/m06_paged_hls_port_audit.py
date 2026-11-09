#!/usr/bin/env python3
"""Read-only REAL generated Vitis paged-M05 RTL port/source contract.

Never substitutes HLS RTL, synthesizes IP, asserts PS DDR ownership, or
claims RTL integration from the mere presence of m_axi signal declarations.
Only a genuinely passed owner Vitis 2025.2 --synth/--cosim directory may
produce a SYNTHESIZED_HEADER_ONLY manifest. Original M05 stays immutable.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from m05_12d3_real_hls_contract import (
    PORT_DECL, PARAM_DECL, _constant_expression,
)

TOP="m06_paged_rolling_replay"
PART="xck26-sfvc784-2LV-c"
RDP="m_axi_gmem_read_"
WRP="m_axi_gmem_write_"
# HLS-generated data width is intentionally NOT guessed.
REQUIRED={
    RDP+"ARADDR":"output",RDP+"ARVALID":"output",
    RDP+"ARREADY":"input",RDP+"RDATA":"input",
    RDP+"RVALID":"input",RDP+"RREADY":"output",
    WRP+"AWADDR":"output",WRP+"AWVALID":"output",
    WRP+"AWREADY":"input",WRP+"WDATA":"output",
    WRP+"WSTRB":"output",WRP+"WVALID":"output",
    WRP+"WREADY":"input",WRP+"BRESP":"input",
    WRP+"BVALID":"input",WRP+"BREADY":"output",
    "ap_clk":"input","ap_rst_n":"input",
}
SOURCES=(
    "hls/m04_lif_eval/m04_eval.cpp",
    "hls/m05_rolling/m05_rolling.cpp",
    "hls/m06_paged_rolling/m06_paged_rolling.cpp",
    "hls/m06_paged_rolling/m06_paged_rolling.hpp",
)


def parse_top(verilog: str) -> dict[str,tuple[str,int]]:
    tops=list(re.finditer(r"\bmodule\s+"+TOP+r"\s*\(",verilog))
    if len(tops)!=1:
        raise ValueError("exactly one real paged HLS RTL top is required")
    body=verilog[tops[0].start():]
    end=re.search(r"\bendmodule\b",body)
    if end is None:
        raise ValueError("generated HLS top missing endmodule")
    body=body[:end.start()]
    head=re.match(r"module\s+"+TOP+r"\s*\((.*?)\)\s*;",body,re.S)
    if not head:
        raise ValueError("generated HLS module header unsupported")
    port_names=[]
    for item in head.group(1).split(","):
        m=re.search(r"([a-zA-Z_]\w*)\s*$",item.strip())
        if m is None:
            raise ValueError("malformed generated HLS port name")
        port_names.append(m.group(1))
    if len(port_names)!=len(set(port_names)):
        raise ValueError("duplicate generated HLS port")
    parameters={}
    for m in PARAM_DECL.finditer(body):
        key,expr=m.groups()
        if key in parameters:
            raise ValueError("duplicate generated HLS parameter")
        parameters[key]=expr
    found={}
    for m in PORT_DECL.finditer(body):
        direction,high,low,name=m.groups()
        if name in found:
            raise ValueError("duplicate generated HLS pin declaration")
        width=1
        if high is not None:
            width=abs(_constant_expression(high,parameters)-
                      _constant_expression(low,parameters))+1
        if width<1 or width>65536:
            raise ValueError("unreasonable generated HLS bus width")
        found[name]=(direction,width)
    if set(port_names)!=set(found):
        raise ValueError("generated HLS declared and named pins disagree")
    return found


def audit(root: Path) -> dict:
    original=root.resolve(strict=True)
    if not original.is_dir() or not original.name.startswith(
        "m06_paged_rolling_hls_"):
        raise ValueError("expected genuine unique M06 paged HLS evidence dir")
    if (original/"result.txt").read_text().strip()!="exit_status=0":
        raise ValueError("owner Vitis HLS synthesis result was not successful")
    if (original/"mode.txt").read_text().strip() not in ("synth","cosim"):
        raise ValueError("header scan requires generated C SYNTHESIS, not CSim")
    if (original/"top.txt").read_text().strip()!=TOP or \
       (original/"part.txt").read_text().strip()!=PART or \
       "2025.2" not in (original/"vitis_version.txt").read_text():
        raise ValueError("wrong HLS top/target/toolchain")
    before=(original/"source_before_sha256.txt").read_text()
    after=(original/"source_after_sha256.txt").read_text()
    if before!=after:
        raise ValueError("genuine owner source was mutated by Vitis")
    lookup={}
    for row in before.strip().splitlines():
        m=re.fullmatch(r"([0-9a-f]{64})\s+(\S+)",row)
        if m is None or m.group(2) in lookup:
            raise ValueError("malformed or repeated source digest")
        lookup[m.group(2)]=m.group(1)
    if any(item not in lookup for item in SOURCES):
        raise ValueError("canonical M04/M05/M06 source identity missing")
    rtl=original/"work/hls/syn/verilog"/(TOP+".v")
    if not rtl.is_file():
        raise ValueError("Vitis did not generate expected paged rolling RTL top")
    pins=parse_top(rtl.read_text(encoding="utf-8",errors="replace"))
    for name,direction in REQUIRED.items():
        if name not in pins or pins[name][0]!=direction:
            raise ValueError(f"new m_axi HLS pin missing/role mismatch: {name}")
    streams={}
    for stem in ("neurons","synapses","external_events","trace","metrics"):
        for suffix,role in (("_TDATA","input" if stem in (
            "neurons","synapses","external_events") else "output"),
                             ("_TVALID","input" if stem in (
            "neurons","synapses","external_events") else "output"),
                             ("_TREADY","output" if stem in (
            "neurons","synapses","external_events") else "input")):
            key=stem+suffix
            if key not in pins or pins[key][0]!=role:
                raise ValueError("generated HLS stream handshake mismatch: "+key)
        streams[stem]=pins[stem+"_TDATA"][1]
    if pins[RDP+"RDATA"][1] not in (8,16,32,64,128,256,512):
        raise ValueError("unrecognized read master data width")
    if pins[WRP+"WDATA"][1] not in (8,16,32,64,128,256,512):
        raise ValueError("unrecognized write master data width")
    rtl_sources=sorted(
        path for path in rtl.parent.iterdir()
        if path.is_file() and path.suffix.lower() in (".v",".sv"))
    return {
        "schema":"m06-paged-hls-synthesized-port-readback-v1",
        "status":"GENUINE_GENERATED_RTL_HEADER_ONLY_NOT_PL_CONNECTED",
        "tool_version":"2025.2",
        "hls_evidence_folder":str(original),
        "source_digest_subset":{item:lookup[item] for item in SOURCES},
        "generated_rtl_count":len(rtl_sources),
        "generated_top_sha256":hashlib.sha256(rtl.read_bytes()).hexdigest(),
        "generated_rtl_sources":[{
            "name":p.name,
            "sha256":hashlib.sha256(p.read_bytes()).hexdigest()
        } for p in rtl_sources],
        "read_axi_master":{
            "prefix":RDP,"data_width":pins[RDP+"RDATA"][1],
            "addr_width":pins[RDP+"ARADDR"][1],
            "role":"READ_ONLY_SOURCE",},
        "write_axi_master":{
            "prefix":WRP,"data_width":pins[WRP+"WDATA"][1],
            "addr_width":pins[WRP+"AWADDR"][1],
            "role":"WRITE_ONLY_SOURCE",},
        "original_s00_s03_width":256,
        "read_width_converter_needed":pins[RDP+"RDATA"][1]!=256,
        "write_width_converter_needed":pins[WRP+"WDATA"][1]!=256,
        "stream_data_widths":streams,
        "header_port_count":len(pins),
        "physical_base_addresses":"NOT_ALLOCATED",
        "original_mem_sc_axi_connected":"NOT_PROVEN",
        "actual_board":"NOT_ACCESSED",
        "m06_complete":False,
    }


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hls-evidence",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    try:
        if args.output.exists() or not args.output.parent.is_dir():
            raise ValueError("new exclusive output JSON path required")
        report=audit(args.hls_evidence)
        with args.output.open("x",encoding="utf-8") as fp:
            json.dump(report,fp,sort_keys=True,indent=2)
            fp.write("\n")
    except (OSError,ValueError,json.JSONDecodeError) as e:
        print("M06 REAL generated paged HLS header REJECTED: "+str(e),
              file=sys.stderr)
        return 2
    print("M06 REAL generated paged HLS pins READ-ONLY VERIFIED; "
          "AXI width/PS memory address and original SmartConnect link NOT TESTED")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
