#!/usr/bin/env python3
"""Package one immutable original-owner G3.3/G4 evidence ZIP on PASS/FAIL.

Only a known allowlist of generated logs, candidate TBs and SHA manifests;
never copies original proprietary AMD/Vitis RTL, .xci or init payload bytes.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import os
import sys

NAMES = (
    "result.txt", "commit.txt", "worktree_status.txt", "owner_error.txt",
    "00_accepted_hls_interface_inventory.json",
    "01_reaudit_dwc_owner.log", "01_reaudit_dwc_sim_sources.json",
    "01_reaudit_dwc_sim_paths.txt",
    "02_vendor_plan.log", "02_original_sc_compile_plan.json",
    "03_merge_plan.log", "03_connected_vendor_compile_plan.json",
    "03_hls_original_dat_stage.log", "03_hls_original_dat_manifest.json",
    "03_control_map.log", "03_real_hls_axilite_control_map.json",
    "03_generation.log", "03_positive16_generation.log",
    "03_independent_m02_m03_vectors.log", "03_m02_m03_parity_generation.log",
    "03_g4_first_b_fault_generation.log",
    "03_g4_first_r_slverr_generation.log",
    "03_g4_stalled_b_generation.log",
    "04_xvhdl.log", "05_xvlog.log", "06_xelab.log", "07_xsim.log",
    "tb_m06_g3_3_actual_hls_original_amd_idle.sv",
    "tb_m06_g3_3_actual_hls_original_amd_positive16.sv",
    "tb_m06_g3_3_actual_hls_original_amd_parity32.sv",
    "tb_m06_g4_actual_hls_original_amd_first_b_slverr.sv",
    "tb_m06_g4_actual_hls_original_amd_first_r_slverr.sv",
    "tb_m06_g4_actual_hls_original_amd_stalled_b.sv",
    "m06_g3_3_m02_m03_owner_vectors.svh",
    "generated_hls_link_tb_sha256.txt",
    "source_before_sha256.txt", "source_after_sha256.txt",
    "hls_sources_before_sha256.txt", "hls_sources_after_sha256.txt",
    "hls_dat_sources_before_sha256.txt", "hls_dat_sources_after_sha256.txt",
    "vendor_sha_before.txt", "vendor_sha_after.txt",
    "original_xci_after_sha_check.txt",
    "verilog_sources.txt", "vhdl_sources.txt", "hls_sources.txt",
    "include_dirs.txt", "original_hls_folder.txt", "original_d3_folder.txt",
    "original_dwc_folder.txt", "original_dwc_compile_order_folder.txt",
    "original_g3_3_inventory_folder.txt", "original_g3_2_zip_path.txt",
)

def package(evidence: Path | None, invocation: Path | None, output: Path) -> None:
    if output.exists():
        raise ValueError("refuse to overwrite existing immutable owner ZIP")
    if not output.parent.is_dir():
        raise ValueError("output parent must already exist")
    folder = evidence if evidence is not None and evidence.is_dir() else None
    with ZipFile(output, "x", ZIP_DEFLATED) as archive:
        if folder:
            for name in NAMES:
                source = folder / name
                if source.is_file() and not source.is_symlink():
                    archive.write(source, arcname=name)
                    print("ADDED:", name)
                else:
                    print("NOT GENERATED:", name)
        else:
            print("No new owner evidence directory was created.")
        if invocation is not None and invocation.is_file() and not invocation.is_symlink():
            archive.write(invocation, arcname="08_operator_invocation_console.log")
        else:
            print("Invocation console log unavailable")
        archive.writestr("operator_evidence_path.txt",
                         (str(evidence) if evidence is not None else "NOT_CREATED") + "\n")
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    print("UPLOAD EXACTLY THIS ZIP:", output)
    print("SIZE:", output.stat().st_size, "bytes")
    print("SHA256:", digest)

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("positive16","m02_m03_parity","g4_first_b_slverr","g4_first_r_slverr","g4_stalled_b"),default="positive16")
    parser.add_argument("--link",default=os.environ.get("LINK", ""))
    parser.add_argument("--invocation-log",default=os.environ.get("INVOCATION_LOG", ""))
    parser.add_argument("--output",type=Path,default=None)
    args=parser.parse_args()
    timestamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix=({"positive16":"M06_G3_3_POSITIVE16_HLS_AMD_REVIEW_",
             "m02_m03_parity":"M06_G3_3_M02_M03_PARITY_HLS_AMD_REVIEW_",
             "g4_first_b_slverr":"M06_G4_FIRST_B_SLVERR_HLS_AMD_REVIEW_",
             "g4_first_r_slverr":"M06_G4_FIRST_R_SLVERR_HLS_AMD_REVIEW_",
             "g4_stalled_b":"M06_G4_STALLED_B_HLS_AMD_REVIEW_"}
            [args.mode])
    output=args.output or (Path.home()/"Thesis_Evidence"/
        (prefix+timestamp+".zip"))
    folder=Path(args.link) if args.link else None
    invocation=Path(args.invocation_log) if args.invocation_log else None
    try:
        package(folder,invocation,output)
    except (OSError,ValueError) as error:
        print("M06_G3_3_POSITIVE16_EVIDENCE_PACKAGING_FAILED:",error,file=sys.stderr)
        return 2
    return 0

if __name__=="__main__":
    raise SystemExit(main())
