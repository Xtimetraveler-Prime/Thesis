#!/usr/bin/env python3
"""Stage genuine HLS $readmemh/$readmemb .dat files for a NEW owner XSim run.

Vivado's XSim looks relative to its fresh run working directory, not to the
read-only original Vitis-HLS RTL source folder. This tool copies ONLY attested
existing HLS .dat files to the new run directory. It cannot create fallback
zero-filled/fictional initialization data or change original generated RTL.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

FILE_LITERAL = re.compile(r'["]([./A-Za-z0-9_+-]+[.]dat)["]')
MEM_CALL = re.compile(r'\$readmem(?:h|b)\b')
MAX_FILES=256
MAX_BYTES=16*1024*1024


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def stage(hls_owner: Path, rtl_sources: list[Path], out: Path) -> dict:
    owner=hls_owner.resolve(strict=True)
    out=out.resolve(strict=True)
    if not owner.is_dir() or not owner.name.startswith("m06_paged_rolling_hls_cosim_"):
        raise ValueError("expected original accepted Vitis HLS cosimulation folder")
    rtl=(owner/"work/hls/syn/verilog").resolve(strict=True)
    if not rtl.is_dir() or len(rtl_sources)!=40 or not out.is_dir():
        raise ValueError("40 original generated Verilog modules and an output dir required")
    if out.is_relative_to(owner):
        raise ValueError("staging output MUST be outside immutable original HLS folder")
    names=set()
    for p in rtl_sources:
        source=p.resolve(strict=True)
        if source.parent!=rtl or not source.is_file() or source.suffix!=".v":
            raise ValueError("generated HLS Verilog file outside attested source directory")
        content=source.read_text(errors="replace")
        literals=set(FILE_LITERAL.findall(content))
        if MEM_CALL.search(content) and not literals:
            raise ValueError("unresolved nonliteral HLS memory-initialization file: "+source.name)
        for name in literals:
            if name.startswith("./"):
                name=name[2:]
            if not name or Path(name).name!=name or name==".." or ".." in name:
                raise ValueError("untrusted HLS initialization path")
            names.add(name)
    if not names or len(names)>MAX_FILES:
        raise ValueError("missing or excessive generated HLS memory .dat dependencies")
    # Genuine HLS C/RTL cosim can stage .dat into work/hls/sim/verilog;
    # prefer syn/verilog only if matching content is found in all locations.
    candidates=(owner/"work/hls/syn/verilog",owner/"work/hls/sim/verilog",
                owner/"work/hls/sim",owner/"work/hls/syn",
                owner/"work",owner)
    result=[]
    for name in sorted(names):
        matches=[]
        for directory in candidates:
            source=directory/name
            if source.is_file() and not source.is_symlink():
                resolved=source.resolve(strict=True)
                if not resolved.is_relative_to(owner):
                    raise ValueError("HLS .dat escapes immutable owner root")
                if resolved not in matches:
                    matches.append(resolved)
        if not matches:
            # Do not fabricate a .dat: an uninitialized HLS RAM can make an
            # apparently passing neural result invalid.
            raise ValueError("missing original HLS .dat: "+name)
        hashes={_sha(p) for p in matches}
        if len(hashes)!=1:
            raise ValueError("ambiguous conflicting original HLS .dat copies: "+name)
        file=matches[0]
        if not 1<=file.stat().st_size<=MAX_BYTES:
            raise ValueError("invalid original HLS .dat size: "+name)
        dest=out/name
        if dest.exists():
            raise ValueError("refuse to overwrite existing staged simulation file: "+name)
        shutil.copyfile(file,dest)
        if _sha(dest)!=_sha(file):
            raise ValueError("staged original HLS .dat digest changed: "+name)
        result.append({"name":name,"source":str(file),"sha256":_sha(file),
                       "bytes":file.stat().st_size,"staged_sha256":_sha(dest)})
    return {"schema":"m06-actual-hls-vitis-dat-source-stage-v1",
            "status":"REAL_HLS_DAT_FILES_STAGED_ORIGINAL_BYTES_UNMODIFIED",
            "source_count":len(rtl_sources),"init_file_count":len(result),
            "files":result,"fabricated_or_zero_filled":False,
            "g3_3_neural_rtl_pass":False,"board_or_ddr":False}


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hls-owner",required=True,type=Path)
    ap.add_argument("--rtl-sources",required=True,type=Path,
                    help="40 paths, one per line, from genuine HLS inventory")
    ap.add_argument("--output-dir",required=True,type=Path)
    ap.add_argument("--manifest",required=True,type=Path)
    a=ap.parse_args()
    try:
        if a.manifest.exists() or not a.manifest.parent.is_dir():
            raise ValueError("output manifest must be new")
        sources=[Path(line) for line in a.rtl_sources.read_text().splitlines()]
        result=stage(a.hls_owner,sources,a.output_dir)
        a.manifest.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    except (OSError,ValueError,UnicodeError) as exc:
        print("M06_G3_3_HLS_DAT_STAGE_REJECTED:",exc,file=sys.stderr)
        return 2
    print("M06_G3_3_HLS_ORIGINAL_DAT_STAGED count="+str(result["init_file_count"])+
          " REAL_BYTES_NO_FABRICATED_INIT_NO_BOARD")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
