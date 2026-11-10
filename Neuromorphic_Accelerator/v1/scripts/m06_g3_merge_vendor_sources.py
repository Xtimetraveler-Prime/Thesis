#!/usr/bin/env python3
"""G3 genuine AMD DWC + original D3 SmartConnect compile-order merger.

Strictly source provenance/simulation input preparation. Two AMD converter
projects share bit-identical underlying library HDL: compile each unique
library file ONCE; compile the two distinct read/write SIM wrapper tops.
If an original D3 source has the same basename but different SHA, fail
closed, never silently pick an implementation. No Vivado/HLS/board invoked.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

from m06_g3_real_amd_compile_order_audit import IP_ROLES


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def merge(original: dict, dwc: dict) -> dict:
    if original.get("schema") != "m06-original-vivado-compile-plan-v2" or (
        original.get("vendor_XSim_executed") is not False
    ):
        raise ValueError("not authenticated original D3 compile plan")
    if dwc.get("schema") != "m06-g3-real-amd-read-only-compile-order-audit-v1" or (
        dwc.get("status") != "REAL_AMD_XSIM_SOURCES_RECORDED_NOT_EXPORTED_NOT_COMPILED"
    ) or dwc.get("m06_complete") is not False:
        raise ValueError("not real untouched AMD converter source audit")
    ips=dwc.get("instances",{})
    if set(ips)!=set(IP_ROLES):
        raise ValueError("not exactly the two real AMD DWC modes")
    d3=Path(original["original_D3"]).resolve(strict=True)
    ipbase=Path(dwc["owner_original_ip_folder"]).resolve(strict=True)
    if not d3.is_dir() or not ipbase.is_dir() or d3==ipbase:
        raise ValueError("wrong saved original AMD vendor source roots")
    original_vlog=[str(x) for x in original["verilog_files"]]
    original_vhdl=[str(x) for x in original["vhdl_files"]]
    if len(original_vlog) < 40 or not original_vhdl:
        # Original Vivado vendor layout may have zero VHDL sources; do not
        # guess. A genuine XSim compile plan with >40 Verilog is required.
        if len(original_vlog) < 40:
            raise ValueError("incomplete original SmartConnect module set")
    vlog=[]
    vhdl=[]
    headers=[]
    seen_basename:dict[str,tuple[str,str]]={}
    duplicates=[]
    originals={str(Path(p).resolve(strict=True)) for p in original_vlog+original_vhdl}
    for text in original_vlog+original_vhdl:
        path=Path(text).resolve(strict=True)
        if str(path) not in originals or not path.is_relative_to(d3):
            raise ValueError("original D3 source escaped project")
        _add(path,"ORIGINAL_D3",seen_basename,vlog,vhdl,headers,duplicates)
    for ip,role in IP_ROLES.items():
        row=ips[ip]
        if row.get("role")!=role or not row.get("real_vendor_wrapper_found") or (
            not row.get("real_vendor_include_found")
        ):
            raise ValueError("wrong generated AMD SIM wrapper role")
        for file in row["ordered_simulation_files"]:
            path=Path(file["path"]).resolve(strict=True)
            if not path.is_relative_to(ipbase) or digest(path)!=file["sha256"]:
                raise ValueError("generated AMD converter source hash or origin mismatch")
            _add(path,ip,seen_basename,vlog,vhdl,headers,duplicates,
                 source_type=file["language"])
    for name in IP_ROLES:
        if not any(Path(path).name==name+".v" for path in vlog):
            raise ValueError("actual AMD converter top not selected: "+name)
    include_dirs=list(dict.fromkeys(
        [str(Path(p)) for p in original["include_directories"]] +
        [str(Path(p).parent) for p in headers]
    ))
    for incl in include_dirs:
        if not Path(incl).is_dir():
            raise ValueError("original vendor header/include directory missing: "+incl)
    return {
        "schema":"m06-g3-real-2xdwc-original-smartconnect-compile-plan-v1",
        "status":"REAL_VENDOR_SOURCE_PATHS_VERIFIED_NOT_CONNECTED_NOT_XSIM",
        "original_d3":str(d3),
        "original_dwc":str(ipbase),
        "verilog_files":vlog,
        "vhdl_files":vhdl,
        "include_directories":include_dirs,
        "deduplicated_same_name_same_sha":duplicates,
        "two_real_dwc_tops":list(IP_ROLES),
        "original_smartconnect_compiled":False,
        "hls_core_bound":False,
        "genuine_combined_xsim":False,
        "m06_complete":False,
    }


def _add(path:Path,origin:str,seen:dict,vlog:list,vhdl:list,
         headers:list,duplicates:list,*,source_type:str|None=None)->None:
    if not path.is_file() or path.is_symlink() or path.stat().st_size==0:
        raise ValueError("missing/empty/symlinked vendor source: "+str(path))
    suffix=path.suffix.lower()
    if source_type is not None:
        expected={"Verilog":".v","SystemVerilog":".sv",
                  "VHDL":".vhd","Verilog Header":".vh"}
        if source_type not in expected or suffix!=expected[source_type]:
            raise ValueError("generated AMD source type/suffix mismatch: "+str(path))
    if suffix not in (".v",".sv",".vhd",".vh",".svh"):
        raise ValueError("unsupported original vendor source suffix")
    sha=digest(path)
    previous=seen.get(path.name)
    if previous is not None:
        if previous[0]!=sha:
            raise ValueError("vendor module name collision with DIFFERENT SHA: "+
                             path.name+"; earlier="+previous[1]+
                             " new="+str(path))
        duplicates.append({"basename":path.name,"source":str(path),
                           "kept_source":previous[1],"same_sha256":sha})
        return
    seen[path.name]=(sha,str(path))
    if suffix in (".vh",".svh"):
        headers.append(str(path))
    elif suffix in (".vhd",".vhdl"):
        vhdl.append(str(path))
    else:
        vlog.append(str(path))


def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--d3-plan",required=True,type=Path)
    ap.add_argument("--dwc-audit",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path)
    args=ap.parse_args()
    try:
        if args.output.exists() or not args.output.parent.is_dir():
            raise ValueError("must use new result path")
        result=merge(json.loads(args.d3_plan.read_text()),
                     json.loads(args.dwc_audit.read_text()))
        with args.output.open("x",encoding="utf8") as fp:
            json.dump(result,fp,sort_keys=True,indent=2)
            fp.write("\n")
    except (OSError,ValueError,KeyError,TypeError) as e:
        print("M06 G3 original AMD vendor RTL merger REJECTED: "+str(e),
              file=sys.stderr)
        return 2
    print("M06 REAL original AMD 2x DWC + SmartConnect SOURCE PLAN VERIFIED, NOT RUN")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
