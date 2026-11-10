#!/usr/bin/env python3
"""Read original Vitis-generated HLS AXI-Lite register offsets exactly.

Never infer HLS register offsets from C++ pragmas. The generated
control_s_axi.v must match accepted source-inventory SHA before used.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

CONTROL="m06_paged_rolling_replay_control_s_axi.v"
DEFINITION=re.compile(
    r"\b(?:parameter|localparam)\s+(?:\[[^\]]+\]\s*)?"
    r"ADDR_([A-Za-z0-9_]+)\s*=\s*(?:7|8|32)'h([0-9a-fA-F]+)\s*;",
    re.M,
)


def control_map(inventory: dict, hls_directory: Path) -> dict:
    entries=inventory.get("hls_rtl_file_inventory")
    if not isinstance(entries,list):
        raise ValueError("missing accepted HLS source inventory")
    records=[item for item in entries if item.get("name")==CONTROL]
    if len(records)!=1:
        raise ValueError("missing exact original HLS control RTL")
    root=hls_directory.resolve(strict=True)
    if root.name!="verilog" or root.parent.name!="syn":
        raise ValueError("require original Vitis HLS syn/verilog folder")
    path=(root/CONTROL).resolve(strict=True)
    if path.parent!=root or not path.is_file() or path.is_symlink():
        raise ValueError("HLS control RTL outside original verified folder")
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=records[0]["sha256"]:
        raise ValueError("original HLS AXI-Lite control module SHA drift")
    source=path.read_text(errors="replace")
    pairs=DEFINITION.findall(source)
    if len(pairs)<10:
        raise ValueError("cannot parse generated HLS control-register address constants")
    regs={}
    for name,hexval in pairs:
        value=int(hexval,16)
        if name in regs or not 0<=value<128 or value%4:
            raise ValueError("duplicated/nonaligned/out-of-range HLS register: "+name)
        regs[name]=value
    if regs.get("AP_CTRL")!=0:
        raise ValueError("generated HLS control ap_ctrl offset not zero")
    returns=[(k,v) for k,v in regs.items() if k in ("AP_RETURN","AP_RETURN_0")]
    if len(returns)!=1:
        raise ValueError("generated HLS return register missing/ambiguous")
    if not 4<=returns[0][1]<128:
        raise ValueError("generated HLS return address outside AXI-Lite")
    return {
        "schema":"m06-g3-3-genuine-generated-hls-control-map-v1",
        "status":"REAL_HLS_AXILITE_CONTROL_OFFSETS_SHA_ATTESTED",
        "control_filename":CONTROL,
        "control_sha256":digest,
        "ap_ctrl":regs["AP_CTRL"],
        "ap_return":returns[0][1],
        "register_offsets":dict(sorted(regs.items())),
        "generated_hls_xsim_functional":False,
        "board_ddr":False,
    }


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--accepted-inventory",required=True,type=Path)
    p.add_argument("--hls-verilog",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    try:
        if a.output.exists() or not a.output.parent.is_dir():
            raise ValueError("control-map output must be new file")
        inv=json.loads(a.accepted_inventory.read_text())
        result=control_map(inv,a.hls_verilog)
        a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    except (OSError,ValueError,KeyError,TypeError) as error:
        print("M06_G3_3_HLS_CONTROL_MAP_REJECTED:",error,file=sys.stderr)
        return 2
    print("M06_G3_3_ORIGINAL_HLS_AXILITE_CONTROL_MAP_VERIFIED "
          "ap_ctrl="+hex(result["ap_ctrl"])+" ap_return="+hex(result["ap_return"])+
          " NO_HLS_XSIM_NO_BOARD")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
