#!/usr/bin/env python3
"""Read-only exact generated AMD AXI Data Width Converter SIM wrapper pin probe.

Consumes an INDEPENDENTLY AUDITED original owner Vivado 2025.2 DWC scratch
project. Extracts only signal names, widths, directions and real top SHA,
not proprietary IP RTL contents. Never claims a connected system or XSim.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from m05_12d3_real_hls_contract import PORT_DECL, PARAM_DECL, _constant_expression
from m06_g3_amd_dwc_evidence_audit import IPS, audit as audit_owner


def parse_module(verilog: str, name: str) -> dict[str, tuple[str,int]]:
    if not re.fullmatch(r"m06_g3_(?:read|write)_dwc", name):
        raise ValueError("wrong original AMD converter top")
    matches = list(re.finditer(r"\bmodule\s+"+re.escape(name)+r"\s*\(", verilog))
    if len(matches) != 1:
        raise ValueError("exactly one true AMD DWC top module expected: "+name)
    body = verilog[matches[0].start():]
    end = re.search(r"\bendmodule\b", body)
    if end is None:
        raise ValueError("AMD DWC top has no endmodule")
    body = body[:end.start()]
    header = re.match(r"module\s+"+re.escape(name)+r"\s*\((.*?)\)\s*;",body,re.S)
    if not header:
        raise ValueError("AMD DWC top header syntax unsupported; supply generated SIM wrapper header")
    names = []
    for field in header.group(1).split(","):
        match = re.search(r"([a-zA-Z_]\w*)\s*$",field.strip())
        if not match:
            raise ValueError("malformed DWC top pin in header")
        names.append(match[1])
    if len(names)!=len(set(names)):
        raise ValueError("duplicate AMD DWC top port names")
    parameters={}
    for match in PARAM_DECL.finditer(body):
        if match[1] in parameters:
            raise ValueError("duplicate DWC top width parameter")
        parameters[match[1]]=match[2]
    pins={}
    for match in PORT_DECL.finditer(body):
        direction,hi,lo,pin = match.groups()
        if pin in pins:
            raise ValueError("duplicate DWC pin declaration: "+pin)
        width=1 if hi is None else (
            abs(_constant_expression(hi,parameters)-
                _constant_expression(lo,parameters))+1)
        if not 1<=width<=1024:
            raise ValueError("invalid AMD converter signal width")
        pins[pin]=(direction,width)
    if set(names)!=set(pins):
        raise ValueError("AMD DWC top named pins and declarations differ")
    if not any(key.lower().startswith("s_axi_") for key in pins) or (
        not any(key.lower().startswith("m_axi_") for key in pins)):
        raise ValueError("not genuine SI/MI AXI DWC wrapper pins")
    return pins


# Actual converter-side widths; verify from real generated simulation wrapper,
# never assume the XCI parameter readback guarantees every signal connection.
EXPECTED = {
    "READ_ONLY": {
        "s_axi_araddr": ("input",32),
        "s_axi_arvalid": ("input",1),
        "s_axi_arready": ("output",1),
        "s_axi_rdata": ("output",32),
        "m_axi_araddr": ("output",32),
        "m_axi_rdata": ("input",256),
        "m_axi_rresp": ("input",2),
    },
    "WRITE_ONLY": {
        "s_axi_awaddr": ("input",32),
        "s_axi_wdata": ("input",32),
        "s_axi_wstrb": ("input",4),
        "s_axi_bresp": ("output",2),
        "m_axi_awaddr": ("output",32),
        "m_axi_wdata": ("output",256),
        "m_axi_wstrb": ("output",32),
        "m_axi_bresp": ("input",2),
    },
}


def verify_role_pins(pins: dict[str,tuple[str,int]], role: str) -> None:
    if role not in EXPECTED:
        raise ValueError("unrecognized original AMD DWC role")
    lower={k.lower():v for k,v in pins.items()}
    for name,wanted in EXPECTED[role].items():
        if lower.get(name)!=wanted:
            raise ValueError("actual original AMD DWC role/pin/width mismatch: "+name)


def capture(dw: Path) -> dict:
    owner=audit_owner(dw)
    dw=dw.resolve(strict=True)
    project=dw/"new_scratch_project"
    entries={}
    for ip,role in IPS.items():
        choices=sorted(
            p for p in project.rglob(ip+".v")
            if p.is_file() and "sim" in p.parts and not p.is_symlink()
            and p.resolve().is_relative_to(project)
        )
        if len(choices)!=1:
            raise ValueError("expected one real AMD Verilog simulation wrapper for "+
                             ip+"; observed "+str(len(choices)))
        path=choices[0]
        text=path.read_text(errors="replace")
        pins=parse_module(text,ip)
        verify_role_pins(pins,role)
        entries[ip]={
            "role":role,
            "original_sim_wrapper":str(path),
            "original_sim_wrapper_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "port_count":len(pins),
            "pins":{k:{"direction":v[0],"width_bits":v[1]} for k,v in sorted(pins.items())},
        }
    return {
        "schema":"m06-real-amd-dwc-sim-wrapper-port-readback-v1",
        "status":"GENUINE_OWNER_SIM_HEADER_ONLY_NOT_CONNECTED_NOT_XSIM",
        "original_dwc_evidence_folder":str(dw),
        "original_dwc_commit":owner["source_commit"],
        "instances":entries,
        "hls_core_bound":False,
        "original_smartconnect_bound":False,
        "actual_vendor_xsim":False,
        "m06_complete":False,
    }


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--owner-dwc",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path)
    args=ap.parse_args()
    try:
        if args.output.exists() or not args.output.parent.is_dir():
            raise ValueError("new output path required")
        result=capture(args.owner_dwc)
        with args.output.open("x",encoding="utf8") as fp:
            json.dump(result,fp,indent=2,sort_keys=True)
            fp.write("\n")
    except (ValueError,OSError,TypeError) as e:
        print("M06 original AMD DWC generated SIM header rejected: "+str(e),
              file=sys.stderr)
        return 2
    print("M06 ORIGINAL AMD DWC SIM WRAPPER PINS MEASURED, NOT CONNECTED AND NOT SIMULATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
