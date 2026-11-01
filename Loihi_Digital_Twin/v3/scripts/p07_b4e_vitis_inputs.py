#!/usr/bin/env python3
"""P07-B.4e — PRE-BUILD, OFFLINE admission for real accepted Vitis inputs.

Check pinned original FPD128 routed XSA, BIT, LTX and metrics together,
including the XSA's ZIP/HWH structure, exactly matching original source
files and safe fresh build location. Does not invoke Vitis, XSDB, Vivado,
JTAG, hardware, firmware, or B2 official MNIST TEST.

A PASS means files are ready to ATTEMPT a real Vitis A53 build on the
user's workstation. It is never evidence that Vitis built an ELF or that
the XSA matches the actual live PL device.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

HERE=Path(__file__).resolve().parents[1]
REPO=HERE.parent.parent
METRICS={
    "p03_hpm0_data_width_bits=128",
    "p03_hpm0_transport=smartconnect_width_protocol",
    "p03_mmio_slave_data_width_bits=32",
    "p03_ps_mmio_master=FPD",
    "p03_mmio_base=0xA4000000",
}
P07_SRC={
    "p07_b4c_readonly_board.c",
    "p07_b4b_board_admission.c",
    "p07_b4b_xilinx_platform.c",
}
P03_SRC={"p03_hw_adapter.c","p03_hw_xilinx_io.c"}
P07_HEADERS={
    "p07_b4b_board_admission.h",
    "p07_b4b_xilinx_platform.h",
    "p07_b4a_current_ingress.h",
    "p07_b2_ingress.h",
    "p07_b3_pager.h",
}
P03_HEADERS={
    "p03_hw_adapter.h",
    "p03_hw_xilinx_io.h",
    "p03_runtime.h",
    "p03_mmio.h",
}
MANIFEST=P07_SRC|P03_SRC|P07_HEADERS|P03_HEADERS
HEX64=re.compile(r"[0-9a-fA-F]{64}\Z")


def normal_file(path:Path)->Path:
    if path.is_symlink() or not path.is_file() or path.stat().st_size==0:
        raise ValueError("missing, empty, or symlinked artifact: "+str(path))
    return path.resolve(strict=True)


def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as fd:
        for piece in iter(lambda:fd.read(1024*1024),b""):
            h.update(piece)
    return h.hexdigest()


def exact_source_hashes()->dict[str,str]:
    result={}
    for name in sorted(MANIFEST):
        folder="software/p03" if name in (P03_SRC|P03_HEADERS) else "software/p07"
        suffix="/include" if name in (P03_HEADERS|P07_HEADERS) else ""
        path=normal_file(HERE/(folder+suffix)/name)
        result[name]=digest(path)
    if len(result)!=14:
        raise ValueError("unexpected read-only source allowlist size")
    return result


def checked_fresh_dir(path:Path)->str:
    if not path.is_absolute():
        raise ValueError("build directory must be absolute")
    if path.exists() or path.is_symlink():
        raise ValueError("build directory must be fresh, not existing/symlinked")
    normalized=path.resolve(strict=False)
    if str(path)!=str(normalized):
        raise ValueError("build directory must use canonical absolute path")
    if normalized==REPO or REPO in normalized.parents:
        raise ValueError("build directory must be outside Thesis repository")
    return str(normalized)


def inspect_xsa(path:Path)->dict:
    # All accepted Vivado exported XSA packages are ZIP/HW platform archives;
    # no extracted, counterfeit extension-only file is admitted here.
    if not zipfile.is_zipfile(path):
        raise ValueError("XSA is not a valid Vivado hardware archive (ZIP)")
    with zipfile.ZipFile(path) as archive:
        members=archive.infolist()
        if len(members)>4096:
            raise ValueError("suspicious excessive XSA members")
        if archive.testzip() is not None:
            raise ValueError("XSA archive has corrupt members")
        names=[m.filename for m in members if not m.is_dir()]
        if not names or not any(name.lower().endswith(".hwh") for name in names):
            raise ValueError("XSA does not contain a hardware handoff HWH")
        if any(name.startswith("/") or "\\" in name or
               ".." in Path(name).parts for name in names):
            raise ValueError("unsafe XSA member paths")
        return {
            "xsa_archive_container":"ZIP",
            "member_count":len(names),
            "contains_hardware_handoff":True,
            "hwh_filenames":[name for name in names if name.lower().endswith(".hwh")],
            "archive_crc_integrity":"PASS",
        }


def evaluate(*,reports:Path,expected_xsa:str,expected_bit:str,
             build_dir:Path, require_tools:bool=False)->dict:
    if not reports.is_dir() or reports.is_symlink():
        raise ValueError("routed report directory unavailable or symlinked")
    names={
        "xsa":"p03_2_ps_mmio.xsa",
        "bit":"p03_2_ps_mmio.bit",
        "ltx":"p03_2_ps_mmio.ltx",
        "metrics":"p03_2_post_route_metrics.txt",
    }
    paths={k:normal_file(reports/v) for k,v in names.items()}
    for label,pin in (("XSA",expected_xsa),("BIT",expected_bit)):
        if not HEX64.fullmatch(pin):
            raise ValueError(label+" requires independently accepted 64-hex SHA256")
    sums={k:digest(path) for k,path in paths.items()}
    if sums["xsa"]!=expected_xsa.lower():
        raise ValueError("XSA pinned SHA256 mismatch")
    if sums["bit"]!=expected_bit.lower():
        raise ValueError("BIT pinned SHA256 mismatch")
    lines=paths["metrics"].read_text(encoding="utf-8").splitlines()
    absent=sorted(METRICS-set(lines))
    if absent:
        raise ValueError("accepted FPD128 route metrics missing: "+repr(absent))
    xsa_meta=inspect_xsa(paths["xsa"])
    safe_build=checked_fresh_dir(build_dir)
    sources=exact_source_hashes()
    found_tools={}
    for executable in ("vitis","aarch64-none-elf-gcc",
                       "aarch64-none-elf-readelf","aarch64-none-elf-nm"):
        found_tools[executable]=shutil.which(executable)
    if require_tools and any(x is None for x in found_tools.values()):
        raise ValueError("missing real Vitis/A53 toolchain commands: "+
                         ", ".join(k for k,v in found_tools.items() if v is None))
    return {
        "schema":"p07-b4e-vitis-real-inputs-preflight-v1",
        "scope":"OFFLINE ONLY, no external tools launched",
        "accepted_hardware_files":{k:str(v) for k,v in paths.items()},
        "accepted_hardware_sha256":sums,
        "hardware_archive":xsa_meta,
        "approved_readonly_build_sources_sha256":sources,
        "read_only_imported_c_count":5,
        "read_only_imported_header_count":9,
        "route_metrics":sorted(METRICS),
        "requested_fresh_build_dir":safe_build,
        "local_tool_paths":found_tools,
        "vitis_toolchain_detected":all(v is not None for v in found_tools.values()),
        "actual_ELF_built":False,
        "board_connected":False,
        "inference_authorized":False,
        "physical_acceptance":False,
        "B2_official_MNIST_TEST":"SEALED",
    }


def main()->None:
    arg=argparse.ArgumentParser(description=__doc__)
    arg.add_argument("--reports",type=Path,required=True,
                     help="accepted routed P03.2c report directory")
    arg.add_argument("--xsa-sha256",required=True,
                     help="independently recorded XSA SHA256, never inferred")
    arg.add_argument("--bit-sha256",required=True,
                     help="independently recorded bitstream SHA256")
    arg.add_argument("--build-dir",type=Path,required=True)
    arg.add_argument("--require-tools",action="store_true",
                     help="require actual Vitis/A53 binaries available on PATH")
    arg.add_argument("--json-out",type=Path,
                     help="existing parent directory, new output JSON only")
    opt=arg.parse_args()
    try:
        evidence=evaluate(reports=opt.reports,expected_xsa=opt.xsa_sha256,
                          expected_bit=opt.bit_sha256,build_dir=opt.build_dir,
                          require_tools=opt.require_tools)
        report=json.dumps(evidence,indent=2,sort_keys=True)+"\n"
        if opt.json_out:
            target=opt.json_out
            if target.exists() or target.is_symlink() or not target.parent.is_dir():
                raise ValueError("JSON output must be a NEW regular path with existing parent")
            target.write_text(report,encoding="utf-8")
        print(report,end="")
        print("P07_B4E_REAL_HARDWARE_INPUTS_OFFLINE_PREFLIGHT_PASS=1")
    except (OSError,ValueError,zipfile.BadZipFile) as exc:
        arg.error(str(exc))


if __name__=="__main__":
    main()
