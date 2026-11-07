#!/usr/bin/env python3
"""P08-B3 pilot16 REAL new A53 ELF/map + original first16 oracle admission.

PC read-only, no XSDB/Vivado/programming. Rejects 1024-frame B2.3 ELF.
ELF PT_LOAD non-overlap is necessary but NOT sufficient for live DDR safety.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import p08_b2_3_elf_admission as base
import p08_b2_4_scalar_first16 as scalar
import p07_b4l1_stage_frozen_27core as old

SCHEMA="p08-b3-original16-image-only-real-a53-elf-preflight-v1"
IDENTITY=b"P08_B3_ORIGINAL_27CORE_FIRST16_PILOT_A53_V1"
TERMINAL=b"P08_B3_PILOT16_TERMINAL_DONE=1"
ORACLE_SHA="13e3e679110059c70f8cfd3d51014c37c62a2cb3ea9c85974e27360606d3b271"
FULL_1024_SHA=scalar.B23_ELF_SHA
FULL_1024_ID=b"P08_B2_3_ORIGINAL_27CORE_1024_IMAGE_ONLY_A53_V1"
EXPECTED_ORACLE_COUNT=16

class PilotNoGo(ValueError): pass

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1048576),b""): h.update(block)
    return h.hexdigest()

def require_regular(path:Path,name:str):
    if not path.is_file() or path.is_symlink():
        raise PilotNoGo("NO-GO: missing authentic regular "+name)

def source_oracle(oracle:Path)->dict:
    require_regular(oracle,"16-frame scalar original source")
    if sha(oracle)!=ORACLE_SHA:
        raise PilotNoGo("NO-GO: operator-accepted first16 scalar JSON SHA changed")
    o=json.loads(oracle.read_text())
    if (o.get("schema")!=scalar.SCHEMA or o.get("count")!=16 or
        o.get("operator_genuine_new_image_only_elf_sha256")!=FULL_1024_SHA or
        o.get("original_known_three_B23_witness_reproduced") is not True or
        o.get("original_p08_b2_1_raw_pool_sha256")!=scalar.RAW_POOL_SHA or
        o.get("original_p08_b2_1_ingress_manifest_sha256")!=scalar.B2_MANIFEST_SHA or
        o.get("original_input_routes_sha256")!=
            "380268c5e8faa2664a31f993683c6759316239932d96b8e681ddb458c81574e8" or
        o.get("original_full_27core_p02_sha256")!=
            "3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e" or
        o.get("official_MNIST_TEST")!="SEALED_NOT_ACCESSED" or
        o.get("physical_A53_executed") is not False or
        o.get("board_contact") is not False):
        raise PilotNoGo("NO-GO: original scalar authority metadata drift")
    rows=o.get("frames")
    if not isinstance(rows,list) or len(rows)!=16 or [
        row.get("ordinal") for row in rows
    ]!=list(range(16)):
        raise PilotNoGo("NO-GO: exactly ordered 16 original oracle references required")
    for i,row in enumerate(rows):
        if (row.get("expected_dispatches")!=702 or
            row.get("expected_barriers")!=26 or
            row.get("expected_trace_compartments_per_tick")!=1010 or
            len(row.get("expected_output_spike_counts",[]))!=10 or
            len(row.get("expected_per_tick_neuron_FNV64",[]))!=26):
            raise PilotNoGo(f"NO-GO: incomplete source oracle numerical frame {i}")
    return o

def analyse(elf:Path,map_file:Path,xsa:Path,header:Path,
            oracle:Path,out:Path)->dict:
    if (not out.is_absolute() or out.exists() or out.is_symlink() or
        not out.parent.is_dir() or
        out.resolve().is_relative_to(old.REPO.resolve())):
        raise PilotNoGo("NO-GO: NEW absolute external out JSON required")
    for name,p in (
        ("new pilot ELF",elf),("pilot linker map",map_file),
        ("accepted XSA",xsa),("B2.2 original 27 pins",header)):
        require_regular(p,name)
    expected=source_oracle(oracle)
    if sha(xsa)!=base.EXPECTED_XSA_SHA or sha(header)!=base.EXPECTED_PINS_SHA:
        raise PilotNoGo("NO-GO: original accepted P03 routed XSA or 27 SHA pins changed")
    raw=elf.read_bytes()
    if (IDENTITY not in raw or TERMINAL not in raw or
        FULL_1024_ID in raw or sha(elf)==FULL_1024_SHA):
        raise PilotNoGo("NO-GO: bounded separately identified pilot16 ELF required")
    link=map_file.read_bytes()
    if any(x not in link for x in (
        b"Linker script and memory map",b".text",b".bss",b"main",
        b"p08_b2_reset_image",b"p08_b2_encode_frame",
        b"p07_b4m_full_run",b"p08_b2_meter_finish")):
        raise PilotNoGo("NO-GO: pilot linker map missing real original/updated symbols")
    try:
        loads=base.load_segments(raw)
    except base.ElfNoGo as e: raise PilotNoGo("NO-GO: "+str(e)) from e
    # Program header span is a link-time check, not evidence about
    # the runtime A53 stack/heap, mailbox or boot loader memory mappings.
    record={
        "schema":SCHEMA,
        "operator_accepted_first16_scalar_oracle_sha256":ORACLE_SHA,
        "original_full_run_B23_ELF_sha256":FULL_1024_SHA,
        "distinct_new_original_B24_pilot16_ELF_sha256":sha(elf),
        "distinct_new_original_B24_pilot16_map_sha256":sha(map_file),
        "accepted_original_P03_routed_XSA_sha256":sha(xsa),
        "original_27_SHA_header_sha256":sha(header),
        "first16_original_heldout_TRAIN_source_ids":[
            row["TRAIN_source_index"] for row in expected["frames"]],
        "pilot_execute_images_exactly":16,
        "pilot_authenticate_original_raw_images_exactly":1024,
        "original_B24_pager_cores":27,
        "original_B24_pager_slots":3,
        "original_B24_inference_ticks_per_image":26,
        "original_B24_physical_dispatches_per_image":702,
        "expected_result_journal_bytes":16*256,
        "expected_latency_sidecar_bytes":16*256,
        "expected_terminal_mailbox_bytes":256,
        "proposed_27core_original_mutable_DDR":[
            "0x40000000","0x40D80000"],
        "proposed_27core_verified_backup_DDR":[
            "0x43000000","0x43D80000"],
        "proposed_1024_raw_image_pool_DDR":[
            "0x42100000","0x421C4000"],
        "pilot_elf_PT_LOAD_ranges":loads,
        "ELF_loads_outside_P03_proposed_64MiB":True,
        "PS_Linux_FSBL_ATF_RPU_PL_DMA_boot_reserved_DDR_exclusivity_PROVEN":False,
        "physical_context_backup_and_raw_staging_READBACK":False,
        "physical_pilot16_latency_and_neural_parity_ACCEPTED":False,
        "operator_destructive_JTAG_approval":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }
    with out.open("x",encoding="utf-8") as fd:
        json.dump(record,fd,indent=2,sort_keys=True);fd.write("\n")
    return record

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("elf","map","xsa","pins-header","oracle","out"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    try:
        row=analyse(a.elf,a.map,a.xsa,a.pins_header,a.oracle,a.out)
        print("P08_B3_PILOT16_REAL_A53_ELF_AND_ORACLE_OFFLINE_PASS=1")
        print("P08_B3_PILOT16_ELF_SHA256="+row[
            "distinct_new_original_B24_pilot16_ELF_sha256"])
        print("P08_B3_PILOT16_MAP_SHA256="+row[
            "distinct_new_original_B24_pilot16_map_sha256"])
        print("P08_B3_PILOT16_ORIGINAL_FIRST16_SCALAR_PIN_MATCH=1")
        print("P08_B3_PILOT16_RAW_SOURCE_AUTHENTICATED_COUNT=1024")
        print("P08_B3_PILOT16_EXECUTION_LIMIT=16")
        print("P08_B3_PILOT16_DDR_EXCLUSIVITY_INDEPENDENTLY_PROVEN=0")
        print("P08_B3_PILOT16_JTAG_AUTHORIZED=0")
        print("P08_B3_PILOT16_BOARD_VISITED=0")
        print("P08_B3_PILOT16_PREFLIGHT_REPORT="+str(a.out))
        return 0
    except (PilotNoGo,ValueError,KeyError,OSError,TypeError) as err:
        print("P08_B3_PILOT16_OFFLINE_NO_GO="+str(err),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
