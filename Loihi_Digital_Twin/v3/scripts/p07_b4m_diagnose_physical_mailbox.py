#!/usr/bin/env python3
"""Inspect a captured B4m physical A53 mailbox after a NO-GO (PC ONLY).

This tool NEVER contacts the KV260 or treats DONE as successful inference.
It prints every raw field and source-based interpretations of the original
operator-built p07_b4m_full_board.c memory-mapped 64-word mailbox.
Output is diagnostics, never a success receipt or independent numerical parity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import p07_b4m_verify_full_receipt as accepted

WORD_NAMES={
    0:"magic",1:"schema_version",2:"firmware_status",
    3:"firmware_first_fault",4:"ps_fpd128_ready",
    5:"p03_hw_init",6:"p03_hw_identify",
    7:"original_B24_binding_status",8:"frozen_route_mount_status",
    9:"pager_init_status",10:"scheduler_init_status",
    11:"full_inference_return_status",
    12:"full_inference_receipt_magic",
    13:"completed_barriers",14:"completed_dispatches",
    15:"page_ins",16:"runtime_page_outs",17:"final_page_outs",
    18:"external_current_events",19:"physical_neuron_source_spikes",
    20:"p03_packet_count",21:"next_inserted",
    22:"predicted_class",23:"registered_original_axons",
    24:"trace_compartments",25:"trace_hash_low",
    26:"trace_hash_high",27:"page_read_bytes_low",
    28:"page_read_bytes_high",29:"page_write_bytes_low",
    30:"page_write_bytes_high",31:"train_input_frame_bytes",
    42:"pager_failed",43:"scheduler_poisoned",
    44:"p03_hardware_last_error",45:"inference_receipt_first_fault",
    46:"p03_physical_completed_dispatch_register",
    63:"terminal_done"
}
for _i in range(10):
    WORD_NAMES[32+_i]=f"readout_neuron_{_i}_spike_count"

# First-fault numeric values in software/p07/p07_b4m_full_inference.c.
FIRST_FAULT={
    1:"initial source/ingress/pager/MMIO argument and frozen binding precheck",
    2:"original destination neuron/packet binding sanity",
    3:"physical trace source initialization, expected 1,010 compartments",
    4:"B2.4 per-core compartment geometry vs P03 metadata",
    5:"register B3c2 physical trace callback",
    6:"epoch cursor/tick/trace initial invariants",
    7:"B4a prepare original TRAIN CURRENT ingress / merge event banks",
    8:"B4a commit CURRENT event-banks / CRCs",
    9:"B3c2 per-core PL paging/dispatch before barrier",
    10:"B3c2 expected barrier did not appear",
    11:"live bank7 source-spike trace finalize / 1010-neuron check",
    12:"readout source-spike neuron ID exceeded 10",
    13:"B2 packet capture, next-bank route insertion, barrier acknowledgment",
    14:"advance live source-neuron trace to next tick",
    15:"final dirty resident-slot flush",
    16:"complete 26 ticks / 702 dispatches / 26 barriers / final flush totals",
}

def signed32(x:int)->int:
    return x if x<0x80000000 else x-0x100000000

def diagnose(data:bytes)->dict:
    if len(data)!=256:
        raise ValueError(
            f"NO-GO: exactly 256 raw physical mailbox bytes required; got {len(data)}"
        )
    w=struct.unpack("<64I",data)
    status=(
        "B4M_FIRMWARE_PASS" if w[2]==accepted.PASS else
        "B4M_FIRMWARE_FAIL" if w[2]==0xDEAD0000 else
        "B4M_FIRMWARE_IN_PROGRESS" if w[2]==0xC0DE0000 else
        "UNKNOWN_OR_INVALID"
    )
    try:
        accepted.verify(data)
    except accepted.FullReceiptError as exc:
        rejection=str(exc)
        verified=False
    else:
        rejection=None
        verified=True
    fault=w[45] or w[3]
    return {
        "schema":"p07-b4m-failed-or-partial-original-physical-mailbox-diagnostic-v1",
        "source":"UNTRUSTED_SUPPLIED_256B_MAILBOX_NOT_INDEPENDENT_BOARD_PROOF",
        "sha256":hashlib.sha256(data).hexdigest(),
        "bytes":len(data),
        "firmware_identity_magic_valid":w[0]==accepted.MAGIC,
        "firmware_schema_valid":w[1]==1,
        "firmware_terminal_DONE_marker_seen":w[63]==accepted.DONE,
        "firmware_terminal_status":status,
        "all_structural_inference_receipt_checks_pass":verified,
        "independent_verifier_rejection":rejection,
        "source_reported_first_fault_stage":fault,
        "source_reported_first_fault_interpretation":
            FIRST_FAULT.get(fault,"none recorded or outside 1..16"),
        "signed_return_codes":{
            key:signed32(w[index])
            for index,key in [
                (4,"ps_fpd128_ready"),(5,"p03_hw_init"),
                (6,"p03_hw_identify"),(7,"original_B24_binding_status"),
                (8,"frozen_route_mount_status"),(9,"pager_init_status"),
                (10,"scheduler_init_status"),
                (11,"full_inference_return_status"),
                (44,"p03_hardware_last_error"),
            ]
        },
        "physical_dispatch_counter_snapshot":w[46],
        "mailbox_words":[
            {
                "index":i,"field":WORD_NAMES.get(i,f"reserved_{i}"),
                "hex":f"0x{value:08X}","uint32":value,
                **({"signed_int32":signed32(value)} if i in (4,5,6,7,8,9,10,11,44) else {}),
            }
            for i,value in enumerate(w)
        ],
        "original_official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "not_a_physical_inference_acceptance_receipt":True,
        "independent_full_neuron_numerical_parity_verified":False,
    }

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mailbox",type=Path,required=True)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    try:
        if a.mailbox.is_symlink() or not a.mailbox.is_file():
            raise ValueError("NO-GO: physical mailbox input must be a real existing file")
        record=diagnose(a.mailbox.read_bytes())
        if a.out is not None:
            if not a.out.is_absolute() or a.out.is_symlink() or a.out.exists():
                raise ValueError("NO-GO: diagnostic destination must be a NEW absolute path")
            with a.out.open("x",encoding="utf-8") as f:
                json.dump(record,f,sort_keys=True,indent=2)
                f.write("\n")
        print(json.dumps({k:v for k,v in record.items() if k!="mailbox_words"},sort_keys=True,indent=2))
        print("P07_B4M_PHYSICAL_MAILBOX_DIAGNOSTIC_ONLY_NO_BOARD_CONTACT=1")
        print("P07_B4M_DIAGNOSTIC_NOT_AN_ACCEPTANCE_RECEIPT=1")
        return 0
    except (OSError,ValueError,struct.error) as exc:
        print("P07_B4M_MAILBOX_DIAGNOSTIC_NO_GO="+str(exc),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
