#!/usr/bin/env python3
"""Owner G3.3 genuine generated HLS + original AMD offline XSim gates.

Modes: accepted idle and invalid geometry, accepted positive16 smoke,
plus prospective independent M02/M03 parity32 simulation. This last mode
is NOT accepted until a genuine owner Vivado 2025.2 run. No fault acceptance,
physical DDR, JTAG, or M07. Original Vitis/AMD sources remain read-only,
SHA-attested before and after; source-only CI never substitutes vendor IP.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_g3_2_connected_evidence_audit import verify_zip
from m06_g3_3_generate_actual_hls_idle_tb import validate_inventory

SOURCE_FILES=(
    "scripts/run_m06_g3_3_actual_hls_idle_xsim.py",
    "scripts/m06_g3_3_generate_actual_hls_idle_tb.py",
    "scripts/m06_g3_3_hls_inventory.py",
    "scripts/m06_g3_2_connected_evidence_audit.py",
    "scripts/m06_g3_3_stage_actual_hls_dat.py",
    "scripts/m06_g3_3_hls_control_map.py",
    "scripts/m06_g3_3_active_axilite_tb.py",
    "scripts/m06_g3_3_positive16_axilite_tb.py",
    "scripts/m06_g3_3_m02_m03_owner_vectors.py",
    "scripts/m06_g3_3_m02_m03_parity_tb.py",
    "scripts/m06_g3_merge_vendor_sources.py",
    "scripts/m06_g3_real_amd_compile_order_audit.py",
    "rtl/m06/m06_axi64_to32_guards.sv",
    "rtl/m06/m06_axi128_scratch_mem.sv",
)
SUCCESS="M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_IDLE_XSIM_PASS"
ACTIVE_PASS="M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_AXILITE_BAD_GEOMETRY_XSIM_PASS"
POSITIVE_PASS="M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_POSITIVE16_XSIM_PASS"
PARITY_PASS="M06_G3_3_ACTUAL_HLS_AMD_M02_M03_TRACE_STATE_PARITY_XSIM_PASS"

def _sha_lines(files: list[Path]) -> str:
    return "".join(hashlib.sha256(p.read_bytes()).hexdigest()+"  "+str(p)+"\n"
                   for p in files)

def _run(label: str,command: list[str],out: Path,*,cwd: Path=ROOT,
         timeout: int=600) -> None:
    log=out/label
    with log.open("w",encoding="utf8",errors="replace") as fp:
        try:
            p=subprocess.run(command,cwd=cwd,stdout=fp,stderr=subprocess.STDOUT,
                             timeout=timeout,check=False)
        except subprocess.TimeoutExpired as e:
            print("G3.3.1 TIMEOUT",label,"(log preserved)",file=sys.stderr)
            raise ValueError("owner process timed out: "+label) from e
    print("M06_G3_3_1_OWNER_STAGE",label,"rc",p.returncode,flush=True)
    if p.returncode!=0:
        raise ValueError(label+" actual original-tool exit="+str(p.returncode))

def run(hls: Path,d3: Path,ports: Path,headers: Path,dwc: Path,
        exported: Path,inventory: Path,*,mode: str="invalid_geometry") -> Path:
    if mode not in ("idle","invalid_geometry","positive16","m02_m03_parity"):
        raise ValueError("unsupported actual-HLS connected mode")
    args=(hls,d3,ports,headers,dwc,exported,inventory)
    hls,d3,ports,headers,dwc,exported,inventory=[
        path.expanduser().resolve(strict=True) for path in args]
    checks=(
        (hls.name.startswith("m06_paged_rolling_hls_cosim_"),"genuine HLS cosim"),
        (d3.name=="neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ","original D3"),
        (ports.name=="02_original_mem_sc_ports.txt","D3 port report"),
        (headers.name=="08_mem_sc_wrapper_headers_nonansi_fixed.json","D3 headers"),
        (dwc.name.startswith("m06_g3_real_amd_dwc_"),"real AMD DWC"),
        (exported.name.startswith("m06_g3_amd_sim_export_"),"real AMD export"),
        (inventory.name.startswith("m06_g3_3_hls_source_inventory_"),"accepted G3.3 inventory"),
    )
    for passed,label in checks:
        if not passed:
            raise ValueError("wrong owner provenance: "+label)
    for cmd in ("python3","git","xvlog","xvhdl","xelab","xsim","sha256sum"):
        if shutil.which(cmd) is None:
            raise ValueError("missing genuine owner command: "+cmd)
    version=subprocess.run(["xvlog","-version"],capture_output=True,
                           text=True,check=False,timeout=15)
    if version.returncode!=0 or "2025.2" not in version.stdout+version.stderr:
        raise ValueError("must use real original AMD Vivado 2025.2")
    vivado=Path(os.environ.get("XILINX_VIVADO","/NOT_SET"))
    glbl=(vivado/"data/verilog/src/glbl.v").resolve(strict=True)
    if not re.search(r"\bmodule\s+glbl\b",glbl.read_text(errors="replace")):
        raise ValueError("genuine Vivado glbl not found")
    for owner in (hls,exported,inventory):
        if (owner/"result.txt").read_text().strip()!="exit_status=0":
            raise ValueError("prior owner source gate did not pass: "+owner.name)
    if (hls/"mode.txt").read_text().strip()!="cosim":
        raise ValueError("HLS genuine C/RTL cosim was not accepted")
    for file,expected in (
        ("original_hls_folder.txt",hls),
        ("original_d3_folder.txt",d3),
        ("original_dwc_folder.txt",dwc),
    ):
        if (inventory/file).read_text().strip()!=str(expected):
            raise ValueError("read-only G3.3 source inventory identity mismatch: "+file)
    inv=json.loads((inventory/"01_g3_3_hls_interface_inventory.json").read_text())
    rtl=hls/"work/hls/syn/verilog"
    validate_inventory(inv,rtl)
    g32zip=Path((inventory/"original_g3_2_zip_path.txt").read_text().strip())
    accepted=verify_zip(g32zip)
    if accepted["evidence_zip_sha256"]!=inv["g3_2_evidence_sha256"]:
        raise ValueError("prior G3.2 genuine original AMD evidence identity mismatch")
    original_hls=sorted(p for p in rtl.glob("*.v") if p.is_file())
    original_sources=[ROOT/f for f in SOURCE_FILES]
    if len(original_hls)!=40:
        raise ValueError("40 verified generated Vitis HLS Verilog files required")
    home=Path.home()/"Thesis_Evidence"
    home.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(
        prefix="m06_g3_3_actual_hls_"+mode+"_xsim_",dir=str(home)))
    tracked=(out/"source_before_sha256.txt")
    tracked.write_text(_sha_lines(original_sources))
    (out/"hls_sources_before_sha256.txt").write_text(_sha_lines(original_hls))
    (out/"commit.txt").write_text(subprocess.check_output(
        ["git","rev-parse","HEAD"],cwd=ROOT,text=True))
    (out/"worktree_status.txt").write_text(subprocess.check_output(
        ["git","status","--porcelain=v1"],cwd=ROOT,text=True))
    for name,value in (
        ("original_hls_folder.txt",hls),("original_d3_folder.txt",d3),
        ("original_dwc_folder.txt",dwc),
        ("original_dwc_compile_order_folder.txt",exported),
        ("original_g3_3_inventory_folder.txt",inventory),
        ("original_g3_2_zip_path.txt",g32zip)):
        (out/name).write_text(str(value)+"\n")
    (out/"00_accepted_hls_interface_inventory.json").write_text(
        json.dumps(inv,indent=2,sort_keys=True)+"\n")
    vendor_files=[]
    dat_sources=[]
    result=1
    try:
        _run("01_reaudit_dwc_owner.log",
             [sys.executable,str(ROOT/"scripts/m06_g3_real_amd_compile_order_audit.py"),
              "--compile-order",str(exported/"02_genuine_dwc_sim_compile_order.tsv"),
              "--owner-dwc",str(dwc),
              "--output",str(out/"01_reaudit_dwc_sim_sources.json"),
              "--paths-output",str(out/"01_reaudit_dwc_sim_paths.txt")],out)
        if (out/"01_reaudit_dwc_sim_sources.json").read_bytes()!=(
            exported/"06_amd_sim_compile_order_audit.json").read_bytes():
            raise ValueError("original DWC compile-order evidence drift")
        _run("02_vendor_plan.log",
             [sys.executable,str(ROOT/"scripts/m06_vendor_compile_plan.py"),
              "--original",str(d3),"--report",str(ports),
              "--output",str(out/"02_original_sc_compile_plan.json")],out)
        _run("03_merge_plan.log",
             [sys.executable,str(ROOT/"scripts/m06_g3_merge_vendor_sources.py"),
              "--d3-plan",str(out/"02_original_sc_compile_plan.json"),
              "--dwc-audit",str(out/"01_reaudit_dwc_sim_sources.json"),
              "--output",str(out/"03_connected_vendor_compile_plan.json")],out)
        plan=json.loads((out/"03_connected_vendor_compile_plan.json").read_text())
        vendor_files=[Path(p).resolve(strict=True) for p in
                      plan["verilog_files"]+plan["vhdl_files"]]
        (out/"vendor_sha_before.txt").write_text(_sha_lines(vendor_files))
        (out/"verilog_sources.txt").write_text(
            "\n".join(plan["verilog_files"])+"\n")
        (out/"vhdl_sources.txt").write_text(
            "\n".join(plan["vhdl_files"])+"\n")
        (out/"hls_sources.txt").write_text(
            "\n".join(map(str,original_hls))+"\n")
        (out/"include_dirs.txt").write_text(
            "\n".join(plan["include_directories"])+"\n")
        _run("03_hls_original_dat_stage.log",
             [sys.executable,str(ROOT/"scripts/m06_g3_3_stage_actual_hls_dat.py"),
              "--hls-owner",str(hls),
              "--rtl-sources",str(out/"hls_sources.txt"),
              "--output-dir",str(out),
              "--manifest",str(out/"03_hls_original_dat_manifest.json")],out)
        dat_manifest=json.loads((out/"03_hls_original_dat_manifest.json").read_text())
        dat_sources=[Path(row["source"]) for row in dat_manifest["files"]]
        (out/"hls_dat_sources_before_sha256.txt").write_text(_sha_lines(dat_sources))
        if mode in ("invalid_geometry","positive16","m02_m03_parity"):
            _run("03_control_map.log",
                 [sys.executable,str(ROOT/"scripts/m06_g3_3_hls_control_map.py"),
                  "--accepted-inventory",str(inventory/"01_g3_3_hls_interface_inventory.json"),
                  "--hls-verilog",str(rtl),
                  "--output",str(out/"03_real_hls_axilite_control_map.json")],out)
        _run("03_generation.log",
             [sys.executable,str(ROOT/"scripts/m06_g3_3_generate_actual_hls_idle_tb.py"),
              "--inventory",str(inventory/"01_g3_3_hls_interface_inventory.json"),
              "--hls-verilog",str(rtl),
              "--original-d3",str(d3),"--original-headers",str(headers),
              "--original-dwc",str(dwc),
              "--output",str(out/"tb_m06_g3_3_actual_hls_original_amd_idle.sv")],out)
        idle_tb=out/"tb_m06_g3_3_actual_hls_original_amd_idle.sv"
        tb=idle_tb
        if mode=="invalid_geometry":
            tb=out/"tb_m06_g3_3_actual_hls_original_amd_active.sv"
            _run("03_active_control_generation.log",
                 [sys.executable,str(ROOT/"scripts/m06_g3_3_active_axilite_tb.py"),
                  "--idle-tb",str(idle_tb),
                  "--accepted-inventory",str(inventory/"01_g3_3_hls_interface_inventory.json"),
                  "--control-map",str(out/"03_real_hls_axilite_control_map.json"),
                  "--output",str(tb)],out)
        elif mode=="positive16":
            tb=out/"tb_m06_g3_3_actual_hls_original_amd_positive16.sv"
            _run("03_positive16_generation.log",
                 [sys.executable,str(ROOT/"scripts/m06_g3_3_positive16_axilite_tb.py"),
                  "--idle-tb",str(idle_tb),
                  "--accepted-inventory",str(inventory/"01_g3_3_hls_interface_inventory.json"),
                  "--control-map",str(out/"03_real_hls_axilite_control_map.json"),
                  "--output",str(tb)],out)
        elif mode=="m02_m03_parity":
            vectors=out/"m06_g3_3_m02_m03_owner_vectors.svh"
            _run("03_independent_m02_m03_vectors.log",
                 [sys.executable,str(ROOT/"scripts/m06_g3_3_m02_m03_owner_vectors.py"),
                  "--output",str(vectors)],out)
            tb=out/"tb_m06_g3_3_actual_hls_original_amd_parity32.sv"
            _run("03_m02_m03_parity_generation.log",
                 [sys.executable,str(ROOT/"scripts/m06_g3_3_m02_m03_parity_tb.py"),
                  "--idle-tb",str(idle_tb),
                  "--accepted-inventory",str(inventory/"01_g3_3_hls_interface_inventory.json"),
                  "--control-map",str(out/"03_real_hls_axilite_control_map.json"),
                  "--output",str(tb)],out)
        testbench_files=[tb]
        if mode=="m02_m03_parity":
            testbench_files.append(vectors)
        (out/"generated_hls_link_tb_sha256.txt").write_text(_sha_lines(testbench_files))
        if plan["vhdl_files"]:
            _run("04_xvhdl.log",["xvhdl","-2008",*plan["vhdl_files"]],out,cwd=out)
        flags=[]
        for folder in plan["include_directories"]:
            if not Path(folder).is_dir():
                raise ValueError("genuine original AMD include directory missing")
            flags.extend(("-i",folder))
        _run("05_xvlog.log",["xvlog","--relax","-sv",*flags,"-i",str(out),
                            *plan["verilog_files"],*map(str,original_hls),
                            str(ROOT/"rtl/m06/m06_axi64_to32_guards.sv"),
                            str(ROOT/"rtl/m06/m06_axi128_scratch_mem.sv"),
                            str(tb),str(glbl)],out,cwd=out)
        compile_log=(out/"05_xvlog.log").read_text(errors="replace")
        if re.search(r"WARNING: \[VRFC 10-(?:2938|3380)\].*tb_m06_g3_3_actual_hls",compile_log):
            raise ValueError("generated HLS binding has implicit or forward-declared nets")
        suffix={"idle":"idle","invalid_geometry":"active",
                "positive16":"positive16","m02_m03_parity":"parity32"}[mode]
        top="tb_m06_g3_3_actual_hls_original_amd_"+suffix
        snapshot="m06_g3_3_actual_hls_original_amd_"+suffix+"_snapshot"
        _run("06_xelab.log",["xelab","--relax","-debug","typical",
                             "-L","xpm","-L","unisims_ver","-L","secureip",
                             "work."+top,"work.glbl","-s",snapshot],out,cwd=out)
        _run("07_xsim.log",["xsim",snapshot,
                            "-R","--onfinish","quit"],out,cwd=out,timeout=300)
        xsim=(out/"07_xsim.log").read_text(errors="replace")
        required_marker={"idle":SUCCESS,"invalid_geometry":ACTIVE_PASS,
                         "positive16":POSITIVE_PASS,"m02_m03_parity":PARITY_PASS}[mode]
        if xsim.count(required_marker)!=1 or re.search(
            r"M06_G3_3_HLS_LINK_IDLE_FAIL|M06_G3_3_HLS_ACTIVE_FAIL"
            r"|M06_G3_3_HLS_POSITIVE_FAIL|M06_G3_3_PARITY_FAIL"
            r"|FATAL_ERROR|Fatal: |\$fatal"
            r"|WARNING: File .*\.dat referenced",xsim
        ):
            raise ValueError("real HLS/AMD XSim missing clean mode-specific PASS")
        print("M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_XSIM_PASS mode="+mode+
              " NO_NEURAL_PARITY_NO_DDR_NO_BOARD")
        result=0
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as error:
        print("M06_G3_3_1_OWNER_REAL_XSIM_FAILED:",error,file=sys.stderr)
        (out/"owner_error.txt").write_text(str(error)+"\n")
        result=1
    finally:
        (out/"source_after_sha256.txt").write_text(_sha_lines(original_sources))
        (out/"hls_sources_after_sha256.txt").write_text(_sha_lines(original_hls))
        if dat_sources:
            (out/"hls_dat_sources_after_sha256.txt").write_text(_sha_lines(dat_sources))
        if vendor_files:
            (out/"vendor_sha_after.txt").write_text(_sha_lines(vendor_files))
        for name in ("source","hls_sources","hls_dat_sources","vendor"):
            before=out/(name+"_before_sha256.txt")
            after=out/(name+"_after_sha256.txt")
            if before.is_file() and (not after.is_file() or
                                     before.read_bytes()!=after.read_bytes()):
                result=3
                print("M06_G3_3_1_SOURCE_MUTATION_REJECTED:",name,file=sys.stderr)
        with (out/"original_xci_after_sha_check.txt").open("w") as fp:
            xci=subprocess.run(
                ["sha256sum","-c",str(dwc/"04_real_amd_dwc_xci_sha256.txt")],
                cwd=ROOT,stdout=fp,stderr=subprocess.STDOUT,check=False)
        if xci.returncode:
            result=3
        (out/"result.txt").write_text("exit_status="+str(result)+"\n")
        print("M06_G3_3_1_OWNER_EVIDENCE",out,"exit="+str(result),flush=True)
    if result!=0:
        raise ValueError("G3.3 original HLS/AMD "+mode+" XSim failed; preserve first evidence")
    return out

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ("hls-cosim","original-d3","original-report","original-headers",
                 "original-dwc","amd-export","accepted-inventory"):
        ap.add_argument("--"+name,required=True,type=Path)
    ap.add_argument("--mode",choices=("idle","invalid_geometry","positive16","m02_m03_parity"),
                    default="invalid_geometry")
    a=ap.parse_args()
    try:
        run(a.hls_cosim,a.original_d3,a.original_report,a.original_headers,
            a.original_dwc,a.amd_export,a.accepted_inventory,mode=a.mode)
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        print("M06_G3_3_1_OWNER_PRECHECK_OR_XSIM_FAILURE:",error,file=sys.stderr)
        return 2
    return 0

if __name__=="__main__":
    raise SystemExit(main())
