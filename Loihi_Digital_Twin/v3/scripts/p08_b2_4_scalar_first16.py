#!/usr/bin/env python3
"""P08-B2.4 independent 16-image original B2.4 scalar oracle (PC ONLY).

Checks original 33 frozen P06 B2.4 assets, original 27-core routes, matched
P08-A 1024 TRAIN-only source, SHA-pinned original P08-B2.1 ingress stage.
Generates a separately signed immutable JSON oracle for ordinals 0..15.
No TEST, new training, physical board operation or acceptance of actual PL.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import p08_b1_matched_source_audit as b1
import p08_b2_stage_1024_ingress as b2
import p07_b4m_v3_train0_scalar_vs_physical as scalar_check
import p07_b4l1_stage_frozen_27core as frozen_check
import p07_b4m_offline_admission as route_check

COUNT=16
B23_ELF_SHA="0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1"
B23_MAP_SHA="f7ce75a736b6b093066b8df09a8b02aaa41b490fd48c36c23151b4ac22125efc"
RAW_POOL_SHA="739006f03b37c36d7aa11b6b68612338fc5249c7f48b9d854520ee7e3ea9c06e"
B2_MANIFEST_SHA="996d48b1d4e83ec2433d445a4be37cff8ef50b599d07db23c165f1be10337e6e"
B2_INGRESS_LEDGER_SHA="5f21aa4e64f31918272b4d7ef84830bc309c6c205744f6735cec4bc69a1a719e"
FROZEN_ORIGINAL_B23="b23_validation_parity.json"
ORACLE_NAME="p08_b2_4_original_scalar_first16.json"
SCHEMA="p08-b2-4-independent-original-b24-scalar-16-v1"
ROOT=Path(__file__).resolve().parents[3]

class OracleNoGo(ValueError):pass

def ensure(condition:bool,message:str)->None:
    if not condition:raise OracleNoGo("NO-GO: "+message)

def sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()

def read_exact(path:Path,n:int|None=None)->bytes:
    ensure(path.is_file() and not path.is_symlink(),"missing or symlink source "+str(path))
    data=path.read_bytes()
    ensure(n is None or len(data)==n,"unexpected byte length "+str(path))
    return data

def validate_stage(b2_dir:Path,raw:bytes,route_bytes:bytes)->list[dict]:
    source=read_exact(b2_dir/b2.MANIFEST_FILENAME)
    ensure(sha(source)==B2_MANIFEST_SHA,"original B2.1 stage manifest drift")
    meta=json.loads(source)
    ensure(meta["schema"]=="p08-b2-1-original27-matched1024-train-only-ingress-v1" and
           meta["count"]==1024 and meta["frame_bytes"]==123216 and
           meta["raw_pool_sha256"]==RAW_POOL_SHA and
           meta["original_input_route_896k_sha256"]==b2.ROUTE_SHA256 and
           meta["original_OFFICIAL_MNIST_TEST"]=="SEALED_NOT_ACCESSED",
           "original 1024 ingress source admission metadata invalid")
    pool=read_exact(b2_dir/b2.RAW_FILENAME,1024*784)
    ensure(sha(pool)==RAW_POOL_SHA and pool==raw,
           "raw pool differs from original matched A images")
    lines=read_exact(b2_dir/b2.HASH_FILENAME)
    ensure(sha(lines)==B2_INGRESS_LEDGER_SHA,"original 1024 ingress SHA ledger drift")
    enc=lines.decode("ascii").splitlines()
    ensure(len(enc)==1024 and len(meta["frames"])==1024,
           "original 1024 encoded frame count drift")
    for i in range(COUNT):
        frame=meta["frames"][i]
        pixel=raw[i*784:(i+1)*784]
        actual=sha(b2.wire_from_pinned_route_bytes(route_bytes,pixel))
        ensure(frame["frame"]==i and frame["raw_pixels_sha256"]==sha(pixel) and
               frame["B24_27core_B13_ingress_sha256"]==enc[i]==actual,
               f"original byte exact B ingress SHA differs at {i}")
    return meta["frames"][:COUNT]

def pure_reference(scalar, schedule,compiled,placement)->dict:
    """Only real independent P06 scalar data, not predicted from hardware."""
    metrics=scalar_check.expected_counters(scalar,schedule,compiled)
    fnv,ticks=scalar_check.trace_fingerprint(scalar,placement)
    ensure(len(ticks)==26 and len(metrics["readout_spike_counts"])==10,
           "incomplete 26-tick full scalar reference")
    ensure(metrics["trained_readout_prediction"]==scalar.predicted_class and
           metrics["source_spikes_from_P03_trace_bank7"]==scalar.spike_count,
           "scalar event accounting inconsistent")
    return {
        "original_scalar_trace_sha256":scalar.trace_sha256,
        "expected_all_26_ticks_1010_neuron_FNV64":fnv,
        "expected_per_tick_neuron_FNV64":ticks,
        "expected_external_current":metrics["external_current_events"],
        "expected_source_spikes":metrics["source_spikes_from_P03_trace_bank7"],
        "expected_captured_packets":metrics["P03_packet_words_captured"],
        "expected_inserted_next":metrics["NEXT_packets_physically_inserted"],
        "expected_prediction":metrics["trained_readout_prediction"],
        "expected_output_spike_counts":metrics["readout_spike_counts"],
        "expected_dispatches":702,
        "expected_barriers":26,
        "expected_trace_compartments_per_tick":1010,
    }

def generate(frozen:Path,a_stage:Path,data_dir:Path,routes_dir:Path,
             ingress_dir:Path,output:Path)->dict:
    ensure(output.is_absolute() and not output.exists() and
           not output.is_symlink() and output.parent.is_dir() and
           not output.resolve().is_relative_to(ROOT),
           "NEW out-of-repo absolute report required")
    if str(ROOT/"Loihi_Digital_Twin/v3/src") not in sys.path:
        sys.path.insert(0,str(ROOT/"Loihi_Digital_Twin/v3/src"))
    from loihi_twin_v2.compiler import NetworkSpec
    from loihi_twin_v2.p06_b12_partition import B12Result
    from loihi_twin_v2.p06_b14_monolithic import (
        pixel_schedule_independent,simulate_monolithic
    )
    from loihi_twin_v2.p06_b24_freeze import (
        PINNED_B23_SOURCE_SHA256,PINNED_B23_DEPLOYMENT_SHA256,
        PINNED_B23_FRAMES,
    )
    frozen_check.admit_freeze(frozen)
    frozen_check.source_index(frozen,json.loads(read_exact(
        frozen/"frozen_manifest.json")))
    route_check.require_routes(routes_dir,frozen)
    source=b1.generate_report(a_stage,data_dir,frozen)
    ensure(source["B24_original_33_assets_verified"] is True and
           len(source["frames"])==1024 and
           source["original_MNIST_TEST"]=="SEALED_NOT_ACCESSED",
           "original 1024 matched A source or B24 freeze gate failed")
    network=NetworkSpec.from_json(read_exact(
        frozen/"network_source.json").decode("utf-8"))
    packed=B12Result.from_json(read_exact(
        frozen/"packed_deployment.json").decode("utf-8"))
    ensure(network.fingerprint==PINNED_B23_SOURCE_SHA256 and
           packed.compiled.fingerprint==PINNED_B23_DEPLOYMENT_SHA256 and
           packed.compiled.source_fingerprint==network.fingerprint,
           "original signed B2.4 scalar model/compiled source mismatch")
    routes=b2.pinned_route_payload(
        routes_dir/b2.ROUTE_FILENAME,packed)
    pixels=b1.read_regular(a_stage,b1.STAGE_FILES["pixels"])
    frames=validate_stage(ingress_dir,pixels,routes)
    old=json.loads(read_exact(frozen/FROZEN_ORIGINAL_B23))
    witnesses=old["validation_frames"]
    ensure(len(witnesses)==3 and
           [r["validation_ordinal"] for r in witnesses]==[0,1,2],
           "original 3 known scalar numerical witness frames missing")
    output_frames=[]
    for i,row in enumerate(frames):
        raw=pixels[i*784:(i+1)*784]
        schedule=pixel_schedule_independent(raw)
        scalar=simulate_monolithic(network,{"pixels":schedule},
                                   readout_population="readout")
        ref=pure_reference(scalar,schedule,packed.compiled,
                           packed.compiled.placement)
        if i<3:
            witness=witnesses[i]
            ensure((witness["validation_ordinal"],witness["canonical_train_idx"],
                    witness["image_sha256"],witness["monolithic_trace_sha256"],
                    witness["partitioned_trace_sha256"])==PINNED_B23_FRAMES[i],
                   "original frozen first3 exact B23 scalar witness drift")
            ensure(witness["canonical_train_idx"]==row["TRAIN_source_index"] and
                   witness["image_sha256"]==row["raw_pixels_sha256"] and
                   witness["monolithic_trace_sha256"]==ref["original_scalar_trace_sha256"] and
                   witness["predicted_class"]==ref["expected_prediction"] and
                   witness["readout_spike_counts"]==ref["expected_output_spike_counts"],
                   f"first3 independent scalar no longer reproduces original frozen witness {i}")
        output_frames.append({
            "ordinal":i,"TRAIN_source_index":row["TRAIN_source_index"],
            "raw_pixels_sha256":row["raw_pixels_sha256"],
            "original_27core_ingress_sha256":row["B24_27core_B13_ingress_sha256"],
            **ref,
        })
    result={
        "schema":SCHEMA,
        "count":COUNT,
        "frozen_model_sha256":PINNED_B23_SOURCE_SHA256,
        "original_compiled_sha256":PINNED_B23_DEPLOYMENT_SHA256,
        "original_full_27core_p02_sha256":
            "3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e",
        "original_input_routes_sha256":b2.ROUTE_SHA256,
        "original_p08_b2_1_ingress_manifest_sha256":B2_MANIFEST_SHA,
        "original_p08_b2_1_1024_wire_sha_ledger_sha256":B2_INGRESS_LEDGER_SHA,
        "original_p08_b2_1_raw_pool_sha256":RAW_POOL_SHA,
        "operator_genuine_new_image_only_elf_sha256":B23_ELF_SHA,
        "operator_genuine_new_image_only_map_sha256":B23_MAP_SHA,
        "original_known_three_B23_witness_reproduced":True,
        "frames":output_frames,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "physical_A53_executed":False,
        "physical_oracle_parity_verified":False,
        "physically_authenticated_journal_present":False,
        "board_contact":False,
    }
    with output.open("x",encoding="utf-8") as fp:
        json.dump(result,fp,sort_keys=True,indent=2)
        fp.write("\n")
    return result

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ("frozen-dir","a-stage","train-data-dir",
                 "routes-dir","ingress-dir","out"):
        p.add_argument("--"+flag,required=True,type=Path)
    a=p.parse_args()
    try:
        result=generate(a.frozen_dir,a.a_stage,a.train_data_dir,
                        a.routes_dir,a.ingress_dir,a.out)
        print("P08_B2_4_ORIGINAL_SCALAR_FIRST16_INDEPENDENT_PASS=1")
        print("P08_B2_4_ORIGINAL_FIRST3_SIGNED_WITNESSES=REPRODUCED")
        print("P08_B2_4_SCALAR_FRAME_COUNT="+str(result["count"]))
        print("P08_B2_4_ACTUAL_HARDWARE_PARITY=NOT_TESTED")
        print("P08_B2_4_ORACLE_REPORT="+str(a.out))
        return 0
    except (OracleNoGo,ValueError,OSError,TypeError,KeyError,AssertionError) as exc:
        print("P08_B2_4_ORACLE_NO_GO="+str(exc),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
