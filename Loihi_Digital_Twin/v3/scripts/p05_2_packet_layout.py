#!/usr/bin/env python3
"""Correct only the P05.2e composite PHYSICAL output-packet RAM ordering.

The accepted logical Loihi Python model sorts packets by destination to
normalize its communication trace. Physical HLS packet-bank addresses
are indexed by the source core's OUTPUT ROUTE DESCRIPTOR order. When
routes wrap around the logical ID modulo five (core 3: [4,0]), the
sequences differ; neural state, routed multiset, spike counts and all
events do NOT.

Create a separate, immutable physically ordered golden beside the
ORIGINAL independent P02 LogicalChip golden. NEVER edit the latter,
the P05G descriptor, existing dumps, or the A53 mailbox. This
derivation uses ONLY the pre-existing model vectors and the actual
registered output-route configuration; it never reads physical DDR to
select or alter expected bytes.

Can run on an existing failed P05.2e evidence folder without
re-running or reprogramming the KV260.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
GEN=ROOT/"scripts/p05_2_composite_fixture.py"
OUTPUT_DIR="composite_physical_golden"
LEDGER="p05_2_packet_layout_ledger.json"
RECORD_BYTES=0x80000
PACKET_OFFSET=0x64000
PACKET_WORD_BYTES=8
PACKET_BANK_WORDS=4096


def _load():
    spec=importlib.util.spec_from_file_location("p05_2_packet_layout_model",GEN)
    assert spec is not None and spec.loader is not None
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def derive(directory:Path)->dict:
    """Fail-closed, idempotent non-destructive derivation from original oracle."""
    directory=directory.resolve()
    model=_load()
    logical=directory/"composite_golden"
    physical=directory/OUTPUT_DIR
    orig_man_file=logical/"manifest.json"
    manifest=json.loads(orig_man_file.read_text())
    if (manifest["logical_core_ids"]!=list(model.CORES) or
        manifest["timesteps"]!=model.TIMESTEPS or
        manifest["service_order"]!=list(model.ORDER) or
        manifest["dispatch_count"]!=model.TIMESTEPS*len(model.CORES)):
        raise ValueError("original neural model is not accepted P05.2e composite")
    if len(manifest["expected_final_record_sha256"])!=len(model.CORES):
        raise ValueError("original model complete DDR SHA mapping is incomplete")

    oracle=model.model()
    configs=oracle.make_workload()
    config_map={c.core_id:c for c in configs}
    # Cross-check the physical order against the actual compiled
    # 32-bit route RAM words, not only the high-level route tuple.
    packed=oracle.export_paged_hardware_image(
        configs,resident_context_count=model.SLOTS
    ).backing_by_logical_core
    if set(config_map)!=set(model.CORES):
        raise ValueError("model neural configuration IDs differ")
    logical_words=model.vectors(logical,"P02B_EXPECT_PACKETS")
    logical_totals=sum(len(w) for w in logical_words.values())
    if logical_totals!=manifest["expected_packet_count_total"]:
        raise ValueError("original LogicalChip packet vectors not intact")

    # Route destination ID is encoded at bits [6:0] of P03 output
    # packet word; route descriptor order is part of the physical
    # packet-memory ABI, unlike the normalized logical packet trace.
    routes={}
    for cid in model.CORES:
        config=config_map[cid]
        if len(config.output_routes)!=1:
            raise ValueError("composite expects exactly one output descriptor")
        route=tuple(config.output_routes[0].routes)
        ids=tuple(dest.destination_core for dest in route)
        if len(ids)!=2 or len(set(ids))!=2:
            raise ValueError(f"core {cid} is not two-destination fanout")
        if ids!=((cid+1)%5,(cid+2)%5):
            raise ValueError(f"composite output route sequence changed core {cid}")
        route_words=packed[cid].image.route_words
        if (tuple(word&0x7F for word in route_words)!=ids or
            any(((word>>7)&0xFFF)!=10+(word&0x7F)
                for word in route_words)):
            raise ValueError(f"core {cid} 32-bit hardware route RAM order differs")
        routes[cid]=ids

    final_normal={}
    final_hardware={}
    per_core_reorder={}
    for cid in model.CORES:
        normalized=[0]*PACKET_BANK_WORDS
        hardware=[0]*PACKET_BANK_WORDS
        converted_steps=[]
        for step in range(model.TIMESTEPS):
            row=logical_words[step,cid]
            if len(row) not in (0,2):
                raise ValueError(
                    f"step={step} core={cid} packet width not 0 or 2"
                )
            dests=[word & 0x7F for word in row]
            if len(row):
                # Independent logical model sorts by destination, while
                # HLS traverses registered physical route RAM order.
                if dests!=sorted(routes[cid]):
                    raise ValueError(f"oracle packet multiset disagrees with core {cid} routes at t{step}")
                packet_by_dest={word&0x7F:word for word in row}
                source_order=[packet_by_dest[d] for d in routes[cid]]
                if sorted(source_order)!=sorted(row):
                    raise ValueError("packet order conversion altered traffic")
                for i,word in enumerate(row):normalized[i]=word
                for i,word in enumerate(source_order):hardware[i]=word
                converted_steps.append({
                    "timestep":step,"logical_destinations":dests,
                    "physical_destinations":[w&0x7F for w in source_order],
                })
        initial=(logical/f"core{cid}_initial.bin").read_bytes()
        original=(logical/f"core{cid}_expected.bin").read_bytes()
        if len(initial)!=RECORD_BYTES or len(original)!=RECORD_BYTES:
            raise ValueError(f"core {cid} original DDR record not 512KiB")
        if _sha(original)!=manifest["expected_final_record_sha256"][str(cid)]:
            raise ValueError(f"core {cid} normalized original model SHA drift")
        # Fail if original Python golden's packet bank does not equal its
        # *own* normalized model vectors. No rewriting around unknown data.
        for idx,want in enumerate(normalized):
            got=struct.unpack_from("<Q",original,PACKET_OFFSET+8*idx)[0]
            if got!=want:
                raise ValueError(f"core {cid} original logical packet[{idx}] unexpected")
        corrected=bytearray(original)
        for idx,word in enumerate(hardware):
            if word!=normalized[idx]:
                struct.pack_into("<Q",corrected,PACKET_OFFSET+8*idx,word)
        candidate=bytes(corrected)
        # Strict surgical change: all non-packet bytes identical.
        assert candidate[:PACKET_OFFSET]==original[:PACKET_OFFSET]
        assert candidate[PACKET_OFFSET+PACKET_BANK_WORDS*8:]==(
            original[PACKET_OFFSET+PACKET_BANK_WORDS*8:]
        )
        final_normal[cid]=original
        final_hardware[cid]=candidate
        per_core_reorder[str(cid)]={
            "physical_route_destinations":list(routes[cid]),
            "normalized_final_packet0_dest":normalized[0]&0x7F,
            "physical_final_packet0_dest":hardware[0]&0x7F,
            "original_sha256":_sha(original),
            "physical_sha256":_sha(candidate),
            "changed_word_indices":[i for i in range(PACKET_BANK_WORDS)
                                    if normalized[i]!=hardware[i]],
            "source_route_order_spikes":converted_steps,
        }

    # Explicit proof of reported core3 mismatch follows exclusively
    # from configuration/model, not physical evidence.
    if not (
        routes[3]==(4,0) and
        per_core_reorder["3"]["normalized_final_packet0_dest"]==0 and
        per_core_reorder["3"]["physical_final_packet0_dest"]==4 and
        per_core_reorder["3"]["changed_word_indices"]==[0,1]
    ):
        raise ValueError("composite does not reproduce modeled 0x04-vs-0x00 packet ordering discrepancy")
    for cid in (0,1,2,4):
        if final_normal[cid]!=final_hardware[cid]:
            raise ValueError("unexpected non-wraparound packet ordering change")

    revised_manifest=dict(manifest)
    revised_manifest["schema"]=manifest["schema"]+"-physical-route-ram-v1"
    revised_manifest["expected_final_record_sha256"]={
        str(c):_sha(final_hardware[c]) for c in model.CORES
    }
    revised_manifest["physical_packet_order"]="output-route-ram-descriptor-order"
    revised_manifest["logical_reference_manifest_sha256"]=_sha(
        orig_man_file.read_bytes()
    )
    revised_manifest.pop("manifest_fingerprint",None)
    revised_manifest["manifest_fingerprint"]=_sha(json.dumps(
        revised_manifest,sort_keys=True,separators=(",",":")
    ).encode())
    ledger={
        "schema":"p05-2e-physical-packet-layout-v1",
        "status":"DERIVED_INDEPENDENT_REFERENCE_NOT_HARDWARE_PASS",
        "original_logical_manifest_sha256":_sha(orig_man_file.read_bytes()),
        "total_model_packets":logical_totals,
        "original_logical_trace_sha256":manifest["trace_fingerprint"],
        "derivation":"physical HLS packet indices follow configured output route order, not the logical model's sorted packet trace",
        "per_core":per_core_reorder,
        "physical_full_record_sha256":revised_manifest["expected_final_record_sha256"],
        "only_modified_region":"packet bank 0x64000..0x6BFFF",
    }
    if physical.exists():
        # Idempotent reruns must not silently overwrite an earlier or
        # different corrected oracle in an evidence folder.
        existing=json.loads((directory/LEDGER).read_text())
        if existing!=ledger:
            raise ValueError("existing physical-layout ledger differs")
        if json.loads((physical/"manifest.json").read_text())!=revised_manifest:
            raise ValueError("existing physical-layout manifest differs")
        for cid in model.CORES:
            if (physical/f"core{cid}_expected.bin").read_bytes()!=final_hardware[cid]:
                raise ValueError(f"existing physical-layout core {cid} differs")
        return ledger
    if (directory/LEDGER).exists():
        raise ValueError("existing ledger without physical golden is invalid")
    physical.mkdir()
    for cid in model.CORES:
        (physical/f"core{cid}_expected.bin").write_bytes(final_hardware[cid])
    (physical/"manifest.json").write_text(
        json.dumps(revised_manifest,sort_keys=True,indent=2)+"\n"
    )
    (directory/LEDGER).write_text(
        json.dumps(ledger,sort_keys=True,indent=2)+"\n"
    )
    return ledger


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--directory",type=Path,required=True)
    args=p.parse_args()
    try:
        result=derive(args.directory)
    except (OSError,ValueError,AssertionError,KeyError,TypeError) as e:
        p.exit(2,"FAIL: P05.2e route-ordered physical packet oracle: "+str(e)+"\n")
    core3=result["per_core"]["3"]
    print(
        "PASS: P05.2e independent physical packet memory layout "
        "CORE3 logical normalized packet0=0x00 "
        "FPGA route-order packet0=0x04; only packet RAM words 0/1 changed"
    )
    print("P05_2E_PACKET_LAYOUT="+json.dumps({
        "core3":core3,"physical_record_sha256":
        result["physical_full_record_sha256"]
    },sort_keys=True))


if __name__=="__main__":
    main()
