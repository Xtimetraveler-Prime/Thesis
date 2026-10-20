#!/usr/bin/env python3
"""P07-B.4d: OFFLINE operator evidence preparation and log adjudication.

Never invokes Vitis, XSDB, Vivado, SSH, JTAG or the board. The read-only Tcl
is an optional *separate* operator action requiring approved DDR/PS ownership.
Evidence parser cannot independently authenticate user-supplied UART/XSDB
logs, and its reported PASS is NOT physical project acceptance or inference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE/"software/p07"))
from build_p07_b4c import SOURCES, HEADERS, check_stage
from p07_b4c_verify_elf import verify as verify_elf

METRICS = (
    "p03_hpm0_data_width_bits=128",
    "p03_hpm0_transport=smartconnect_width_protocol",
    "p03_mmio_slave_data_width_bits=32",
    "p03_ps_mmio_master=FPD",
    "p03_mmio_base=0xA4000000",
)
APP = "p07_b4c_readonly_probe"
IDENTITY = "P07_B4C_A53_READONLY_FPD128_SHELL_PROBE_V1"
REGISTERS = {
    "FPD_RAW": None,   # static FPD[9:8] == 2
    "P03_ID": 0x4C543302,
    "P03_VERSION": 0x00010000,
    "P03_CAPABILITIES": 0x0001031F,
    "P03_GLOBAL_STATUS": 0,
    "P03_PAGE_PENDING": 0,
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fd:
        for part in iter(lambda: fd.read(1024*1024), b""):
            h.update(part)
    return h.hexdigest()


def normal_file(path: Path) -> Path:
    if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
        raise ValueError("missing, empty or symlinked input: " + str(path))
    return path.resolve(strict=True)


def sha_expected(value: str, label: str) -> str:
    if not re.fullmatch(r"[a-fA-F0-9]{64}",value):
        raise ValueError(label + " expected SHA256 must be exactly 64 hex")
    return value.lower()


def source_gate(stage: Path) -> dict[str,str]:
    check_stage(stage)
    result = {}
    for name in (*SOURCES, *HEADERS):
        original = (HERE/("software/p03" if name.startswith("p03_") else
                           "software/p07")/
                    ("" if name.endswith(".c") else "include")/name)
        if not original.is_file() or original.is_symlink():
            raise ValueError("missing authoritative source " + name)
        staged = stage/name
        if digest(staged)!=digest(original):
            raise ValueError("staged source drift: "+name)
        result[name] = digest(staged)
    return result


def admission_inputs(build_dir: Path,xsa: Path,bit: Path,ltx: Path,
                     metrics: Path,sha_xsa: str,sha_bit: str,
                     stack: str,heap: str,
                     readelf: str,nm: str) -> dict:
    normal_file(xsa);normal_file(bit);normal_file(ltx);normal_file(metrics)
    dx,db=digest(xsa),digest(bit)
    if dx != sha_expected(sha_xsa,"XSA"):
        raise ValueError("pinned XSA SHA256 mismatch")
    if db != sha_expected(sha_bit,"BIT"):
        raise ValueError("pinned BIT SHA256 mismatch")
    present=set(metrics.read_text(errors="replace").splitlines())
    missing=sorted(set(METRICS)-present)
    if missing:
        raise ValueError("accepted routed FPD128 metrics missing: "
                         + ", ".join(missing))
    workspace=build_dir/"vitis_workspace"
    elf=workspace/(APP+".elf")
    linker=workspace/(APP+".map")
    stage=build_dir/"source"
    normal_file(elf);normal_file(linker)
    src_sha=source_gate(stage)
    xpfm=workspace/"p07_b4c_readonly_platform"/"export"/"p07_b4c_readonly_platform"/"p07_b4c_readonly_platform.xpfm"
    normal_file(xpfm)
    elf_admission=verify_elf(elf,linker,stack,heap,readelf=readelf,nm=nm)
    if not elf_admission["read_only_firmware_identity_present"] or elf_admission["inference_authorized"]:
        raise ValueError("real ELF failed strict read-only admission")
    paths={
        "elf":elf,"linker_map":linker,"xpfm":xpfm,
        "xsa":xsa,"bit":bit,"ltx":ltx,"route_metrics":metrics,
    }
    return {
        "schema":"p07-b4d-offline-hardware-operator-preflight-v1",
        "scope":"read-only shell register observation, no DDR/PL writes",
        "paths":{k:str(v.resolve(strict=True)) for k,v in paths.items()},
        "sha256":{k:digest(v) for k,v in paths.items()},
        "source_sha256":src_sha,
        "stack_declared":stack,"heap_declared":heap,
        "elf_admission":elf_admission,
        "actual_board_execution":"NOT_RUN",
        "operator_approval":"REQUIRED_SEPARATELY",
        "physical_acceptance":False,
        "inference_authorized":False,
        "B2_official_MNIST_TEST":"SEALED",
    }


def prepare(args: argparse.Namespace) -> dict:
    base=args.out.resolve(strict=False)
    if args.out.exists() or args.out.is_symlink():
        raise ValueError("evidence directory already exists")
    project=HERE.parent.parent
    if base == project or project in base.parents:
        raise ValueError("evidence directory must be outside Thesis repository")
    proof=admission_inputs(
        args.build_dir,args.xsa,args.bit,args.ltx,args.route_metrics,
        args.xsa_sha256,args.bit_sha256,args.stack,args.heap,
        args.readelf,args.nm)
    base.mkdir(parents=True,exist_ok=False)
    data=json.dumps(proof,indent=2,sort_keys=True)+"\n"
    manifest=base/"offline_preflight.json"
    manifest.write_text(data)
    (base/"offline_preflight.sha256").write_text(digest(manifest)+"\n")
    (base/"README_NO_BOARD_RUN.txt").write_text(
        "P07-B.4d offline preflight only. NO board connected or executed.\n"
        "Before any JTAG/UART interaction independently approve live XSA/PL,\n"
        "stop concurrent Linux/DDR writers by approved method, establish A53\n"
        "ELF LOAD/stack/heap and 64MiB DDR ownership, and plan a reboot.\n"
        "The optional vivado/p07_b4d_readonly_shell.tcl only READS six registers.\n"
        "Separately captured UART and XSDB logs are untrusted operator evidence;\n"
        "verification cannot authenticate their origin. Never infer 27-core GO.\n"
    )
    return proof


def exactly_once(log: str, name: str, value: str | None = None) -> str:
    matches=re.findall(r"(?m)^"+re.escape(name)+r"=([^\r\n]*)\r?$",log)
    if len(matches)!=1:
        raise ValueError("missing/duplicate observation: "+name)
    observed=matches[0].strip()
    if value is not None and observed!=value:
        raise ValueError("unexpected observation "+name+": "+observed)
    return observed


def parse_observations(uart: str,xsdb: str) -> dict:
    if "P07_B4C_READONLY_ADMISSION_PROBE_FAIL=" in uart or \
       "P07_B4D_READONLY_PS_PL_SNAPSHOT_FAIL=" in xsdb:
        raise ValueError("explicit fail marker present")
    if uart.count(IDENTITY)!=1:
        raise ValueError("UART firmware identity missing or ambiguous")
    exactly_once(uart,"P07_B4C_READONLY_ADMISSION_PROBE_PASS","1")
    exactly_once(xsdb,"P07_B4D_READONLY_PS_PL_SNAPSHOT_PASS","1")
    exactly_once(xsdb,"P07_B4D_INFERENCE_AUTHORIZED","0")
    target=exactly_once(xsdb,"P07_B4D_PHYSICAL_TARGET")
    if target not in ("PSU","APU"):
        raise ValueError("unexpected XSDB physical target "+target)
    values={}
    for name,want in REGISTERS.items():
        value=exactly_once(xsdb,"P07_B4D_"+name)
        if not re.fullmatch(r"0x[0-9A-Fa-f]{8}",value):
            raise ValueError("malformed register capture "+name)
        parsed=int(value,16)
        if want is not None and parsed!=want:
            raise ValueError("physical register mismatch "+name)
        values[name]=value
    if (int(values["FPD_RAW"],16)>>8)&3 != 2:
        raise ValueError("physical FPD128 selector wrong")
    return {
        "user_supplied_uart_marker":"MATCHED",
        "user_supplied_xsdb_register_capture":"MATCHED",
        "fpd128_observed":True,
        "registers":values,
        "logs_authenticity":"NOT_INDEPENDENTLY_ESTABLISHED",
        "board_physical_acceptance":False,
        "inference_authorized":False,
    }


def verify_logs(args: argparse.Namespace) -> dict:
    root=args.evidence_dir
    pre=normal_file(root/"offline_preflight.json")
    stored=normal_file(root/"offline_preflight.sha256")
    if stored.read_text().strip()!=digest(pre):
        raise ValueError("preflight manifest checksum drift")
    proof=json.loads(pre.read_text())
    if proof.get("schema")!="p07-b4d-offline-hardware-operator-preflight-v1" or \
       proof.get("physical_acceptance") is not False or \
       proof.get("inference_authorized") is not False:
        raise ValueError("wrong or unsafe offline manifest")
    for name,pathname in proof["paths"].items():
        p=normal_file(Path(pathname))
        if digest(p)!=proof["sha256"][name]:
            raise ValueError("evidence artifact drift: "+name)
    for name,expected in proof["source_sha256"].items():
        source=normal_file(args.build_dir/"source"/name)
        if digest(source)!=expected:
            raise ValueError("staged source drift after preflight: "+name)
    uart=normal_file(args.uart).read_text(errors="replace")
    xsdb=normal_file(args.xsdb).read_text(errors="replace")
    accepted=parse_observations(uart,xsdb)
    return {
        "schema":"p07-b4d-untrusted-operator-logs-adjudication-v1",
        "offline_preflight_sha256":digest(pre),
        "uart_sha256":digest(args.uart),
        "xsdb_sha256":digest(args.xsdb),
        **accepted,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="mode",required=True)
    a=sub.add_parser("prepare",help="offline artifacts gate; no board commands")
    for flag in ("--build-dir","--xsa","--bit","--ltx","--route-metrics","--out"):
        a.add_argument(flag,type=Path,required=True)
    for flag in ("--xsa-sha256","--bit-sha256","--stack","--heap"):
        a.add_argument(flag,required=True)
    a.add_argument("--readelf",default="aarch64-none-elf-readelf")
    a.add_argument("--nm",default="aarch64-none-elf-nm")
    v=sub.add_parser("review-logs",help="inspect separately captured operator logs; no JTAG")
    for flag in ("--build-dir","--evidence-dir","--uart","--xsdb"):
        v.add_argument(flag,type=Path,required=True)
    args=p.parse_args()
    try:
        result=prepare(args) if args.mode=="prepare" else verify_logs(args)
    except (OSError,ValueError,RuntimeError) as err:
        p.error(str(err))
    print(json.dumps(result,indent=2,sort_keys=True))
    if args.mode=="prepare":
        print("P07_B4D_OFFLINE_PREFLIGHT_PASS_NO_BOARD_RUN=1")
    else:
        print("P07_B4D_OPERATOR_LOG_FORMAT_PASS_NOT_PHYSICAL_ACCEPTANCE=1")

if __name__=="__main__":
    main()
