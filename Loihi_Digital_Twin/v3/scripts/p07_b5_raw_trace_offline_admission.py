#!/usr/bin/env python3
"""PC-ONLY signed B5.3 raw A53 candidate source+ELF admission.

NO FPGA access, NO real DDR ownership proven, NO physical launch approval.
Original B4m V3 ELF/map and P03 PL remain immutable. No official TEST access.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import p07_b4m_offline_admission as prior
import p07_b4l1_stage_frozen_27core as frozen27
import p07_b4m_frozen_inputs as original

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"software/p07/build_p07_b5_raw_trace.py"
IDENTITY=b"P07_B5_A53_TRAIN_RAW_TRACE_DIAGNOSTIC_V1"
APP="p07_b5_raw_trace_v1"
XSA_SHA="52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f"
TRACE_BASE=0x42000000
TRACE_END=0x420CD280
TRACE_SIZE=840320
B5_MAILBOX_START=0x43FF0100
B5_MAILBOX_END=0x43FF0200

class AdmissionNoGo(ValueError):
    pass

LEGACY_FIRMWARE_IDENTITIES=(
    b"P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V3",
    b"P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V2",
    b"P07_B4M_A53_TRAIN_26_TICK_CANDIDATE_V1",
)

def reject_legacy_firmware_identity(data:bytes)->None:
    """Reject old V3/V2/V1 runtime strings, even if new B5 ID is present."""
    for identifier in LEGACY_FIRMWARE_IDENTITIES:
        if identifier in data:
            raise AdmissionNoGo(
                "NO-GO: new B5 ELF contains original firmware identity: "+
                identifier.decode()
            )


def sha(path:Path)->str:
    if path.is_symlink() or not path.is_file():
        raise AdmissionNoGo("NO-GO: missing real regular source/ELF/XSA "+str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()

def builder():
    spec=importlib.util.spec_from_file_location("p07_b5_new_vitis",CONTRACT)
    if spec is None or spec.loader is None:
        raise AdmissionNoGo("NO-GO: B5 Vitis build contract missing")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if (mod.IDENTITY.encode()!=IDENTITY or mod.APP!=APP or
        mod.SOURCES[0]!="p07_b5_full_board_raw_trace_v1.c" or
        "p07_b4m_full_board_diag_v3.c" in mod.SOURCES or
        "p07_b4m_spike_trace.c" in mod.SOURCES or
        "p07_b5_spike_trace.c" not in mod.SOURCES or
        "p07_b5_raw_capture.c" not in mod.SOURCES or
        "p07_b5_raw_capture.h" not in mod.HEADERS or
        "p07_b5_trace_hook.h" not in mod.HEADERS):
        raise AdmissionNoGo("NO-GO: B5 Vitis source contract includes old firmware or lacks capture")
    return mod

def verify_source(stage:Path)->dict[str,str]:
    if (not stage.is_absolute() or stage.is_symlink() or
        not stage.is_dir() or stage.resolve().is_relative_to(ROOT.resolve())):
        raise AdmissionNoGo("NO-GO: new external B5 Vitis build source must be absolute")
    b=builder()
    b.check_stage(stage)
    recorded={}
    for name in (*b.SOURCES,*b.HEADERS):
        if name.endswith(".c"):
            path=ROOT/("software/p03" if name.startswith("p03_hw_")
                       else "software/p07")/name
        elif name.startswith("p03_"):
            path=ROOT/"software/p03/include"/name
        elif name=="p05_deployment.h":
            path=ROOT/"software/p05/include"/name
        else:
            path=ROOT/"software/p07/include"/name
        expected=path.read_bytes()
        if name=="p07_a2_sha256.c":
            before=b'#include "include/p07_a2_sha256.h"'
            if expected.count(before)!=1:
                raise AdmissionNoGo("NO-GO: original SHA source transformation no longer unique")
            expected=expected.replace(before,b'#include "p07_a2_sha256.h"')
        if name=="p07_b2_packet.h":
            before=b"#define P07_B2_MAX_ROUTE_BINDINGS 8192u"
            if expected.count(before)!=1:
                raise AdmissionNoGo("NO-GO: original route cap transformation no longer unique")
            expected=expected.replace(before,b"#define P07_B2_MAX_ROUTE_BINDINGS 10000u")
        if (stage/name).read_bytes()!=expected:
            raise AdmissionNoGo("NO-GO: staged B5 source differs from pinned repository "+name)
        recorded[name]=hashlib.sha256(expected).hexdigest()
    return recorded

def boundaries()->dict:
    original_ranges={
        "original_27x512KiB_P02":(0x40000000,0x40D80000),
        "original_input_routes":(0x41000000,0x410E0000),
        "original_train_frame_reserved":(0x41100000,0x411E0000),
        "original_binding_descriptor":(0x43FC0000,0x43FC4000),
        "original_output_routes":(0x43FC4000,0x43FD8000),
        "original_v3_mailbox":(0x43FF0000,0x43FF0100),
    }
    trace=(TRACE_BASE,TRACE_END)
    mailbox=(B5_MAILBOX_START,B5_MAILBOX_END)
    if not (TRACE_END-TRACE_BASE==TRACE_SIZE and
        all(trace[1]<=a or trace[0]>=b for a,b in original_ranges.values()) and
        all(mailbox[1]<=a or mailbox[0]>=b for a,b in original_ranges.values()) and
        trace[1]<=mailbox[0] and len(original_ranges)==6):
        raise AdmissionNoGo("NO-GO: B5 physical sidecar overlaps pinned original ranges")
    return {
        "trace_candidate_address_range_hex":[hex(v) for v in trace],
        "raw_trace_exact_bytes":TRACE_SIZE,
        "new_B5_mailbox_candidate_address_range_hex":[hex(v) for v in mailbox],
        "known_original_software_ranges_disjoint":True,
        "actual_DDR_physical_ownership_independently_proven":False,
        "boot_firmware_low_DDR_exclusivity_independently_proven":False,
    }

def admit(*,frozen:Path,routes:Path,build:Path,reports:Path)->dict:
    if (not build.is_absolute() or build.is_symlink() or
        not build.is_dir() or build.resolve().is_relative_to(ROOT.resolve())):
        raise AdmissionNoGo("NO-GO: NEW external absolute B5 Vitis build required")
    frozen27.admit_freeze(frozen)
    source=verify_source(build/"source")
    routes_record=prior.require_routes(routes,frozen)
    if routes_record["input_routes"]!=20384 or routes_record["output_routes"]!=1000:
        raise AdmissionNoGo("NO-GO: original signed model routes changed")
    if sha(reports/"p03_2_ps_mmio.xsa")!=XSA_SHA:
        raise AdmissionNoGo("NO-GO: original accepted P03 XSA identity changed")
    metrics= (reports/"p03_2_post_route_metrics.txt").read_text().splitlines()
    for line in ("p03_hpm0_data_width_bits=128",
                 "p03_hpm0_transport=smartconnect_width_protocol",
                 "p03_mmio_slave_data_width_bits=32",
                 "p03_ps_mmio_master=FPD",
                 "p03_mmio_base=0xA4000000"):
        if line not in metrics:
            raise AdmissionNoGo("NO-GO: original accepted FPD128 HLS shell identity changed")
    elf=build/"vitis_workspace"/(APP+".elf")
    linked_map=build/"vitis_workspace"/(APP+".map")
    identity=prior.require_elf(elf,expected_name=APP+".elf",expected_id=IDENTITY)
    # Deliberate strict rejection, retained after the first B5 build
    # exposed a stale V3 xil_printf() in the *new* C main.
    reject_legacy_firmware_identity(elf.read_bytes())
    linker=linked_map.read_text()
    if (not linked_map.is_file() or linked_map.is_symlink() or
        "Linker script and memory map" not in linker or
        ".text" not in linker or ".bss" not in linker or "main" not in linker):
        raise AdmissionNoGo("NO-GO: missing GENUINE GNU linker memory map")
    load_end=int(identity["pt_load_end_exclusive"],16)
    if (identity["pt_load_start"]!="0x00000000" or
        load_end>0x01000000 or load_end<=0 or
        identity["pt_load_memsz"]<=0):
        raise AdmissionNoGo("NO-GO: genuine standalone B5 A53 LOAD layout changed")
    return {
        "schema":"p07-b5-new-raw-trace-real-vitis-source-elf-offline-admission-v1",
        "new_distinct_a53_firmware_identity":IDENTITY.decode(),
        "new_distinct_source_files_sha256":source,
        "new_genuine_b5_ELF":identity,
        "new_genuine_b5_linker_map_sha256":sha(linked_map),
        "original_B24_compiled_fingerprint":original.PINNED_SHA,
        "original_immutable_routes":routes_record,
        "accepted_original_P03_XSA_sha256":XSA_SHA,
        "capture_geometry":boundaries(),
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "original_frozen_model_or_P03_PL_changed":False,
        "accepted_original_V3_elf_or_map_changed":False,
        "separate_new_B5_JTAG_launcher_implemented":False,
        "actual_raw_840320B_FPGA_captured":False,
        "direct_neuron_by_neuron_physical_parity_verified":False,
        "independent_actual_B5_DDR_owners_verified":False,
        "actual_B5_physical_launch_authorized":False,
        "board_accessed":False,
    }

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for x in ("frozen-dir","routes-dir","build-dir","reports","out"):
        p.add_argument("--"+x,type=Path,required=True)
    args=p.parse_args()
    try:
        if (not args.out.is_absolute() or args.out.exists() or
            args.out.is_symlink() or
            args.out.resolve().is_relative_to(ROOT.resolve()) or
            not args.out.parent.is_dir()):
            raise AdmissionNoGo("NO-GO: new absolute out-of-repo B5 offline report")
        record=admit(frozen=args.frozen_dir,routes=args.routes_dir,
                     build=args.build_dir,reports=args.reports)
        with args.out.open("x") as output:
            json.dump(record,output,indent=2,sort_keys=True)
            output.write("\n")
        print("P07_B5_GENUINE_RAW_CAPTURE_VITIS_SOURCE_ELF_OFFLINE_PREFLIGHT_PASS=1")
        print("P07_B5_SIDE_CAR_PHYSICAL_DDR_OWNERSHIP_PROVEN=0")
        print("P07_B5_REAL_PHYSICAL_LAUNCH_AUTHORIZED=0")
        print("P07_B5_BOARD_ACCESSED=0")
        print("P07_B5_B5_3_RAW_FPGA_TRACE_VERIFIED=0")
        print("P07_B5_NEW_RAW_OFFLINE_REPORT="+str(args.out))
        return 0
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as e:
        print("P07_B5_NEW_RAW_OFFLINE_NO_GO="+str(e),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
