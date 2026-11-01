#!/usr/bin/env python3
"""PC-only original TRAIN0 independent integer-oracle vs real V3 mailbox audit.

No FPGA/JTAG access, no MNIST TEST, no frozen asset changes.
Rebuild 64-bit HLS trace FNV from original scalar oracle; matching this
noncryptographic fingerprint does NOT prove direct raw per-neuron parity.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import p07_b4l1_stage_frozen_27core as b4l1
import p07_b4l_physical_model_deploy as physical_model
import p07_b4l_b3_physical_epoch as bindings
import p07_b4m_frozen_inputs as original
import p07_b4m_offline_admission as original_routes
import p07_b4m_verify_full_receipt as verifier
import p07_b4m_diag_v3_physical_run as v3

ROOT=Path(__file__).resolve().parents[1]
MAILBOX_SHA="5a2d9c9645b79144ef20f5ed7f26e5ed1ad3745aaf929713cf89fcb7f8718eda"
TRAIN0_SHA="2aa772efd381805bab24fea145186d22f3550b156f155a9ab51dcef10e6d8126"
EVIDENCE_NAME="p07_b4m_diag_v3_real_20261101T041302Z"
FNV_SEED=14695981039346656037
FNV_PRIME=1099511628211
MASK64=(1<<64)-1

class ParityNoGo(ValueError):
    pass

def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def read(path:Path,bytes_expected:int|None=None)->bytes:
    if path.is_symlink() or not path.is_file():
        raise ParityNoGo("NO-GO: missing/symlinked evidence: "+str(path))
    if bytes_expected is not None and path.stat().st_size!=bytes_expected:
        raise ParityNoGo("NO-GO: incorrect evidence length: "+str(path))
    return path.read_bytes()

def fnv_bytes(initial:int,data:bytes)->int:
    h=initial
    for b in data:
        h=((h^b)*FNV_PRIME)&MASK64
    return h

def fnv_words(words,initial:int=FNV_SEED)->int:
    h=initial
    for word in words:
        if type(word) is not int or not 0<=word<(1<<32):
            raise ParityNoGo("NO-GO: malformed HLS uint32 trace")
        h=fnv_bytes(h,word.to_bytes(4,"little"))
    return h

def state_word(state)->int:
    if not(-(1<<23)<=state.current<(1<<23) and
           -(1<<23)<=state.voltage<(1<<23) and
           0<=state.refractory_remaining<(1<<16)):
        raise ParityNoGo("NO-GO: oracle state outside HLS 24/24/16-bit representation")
    return (state.current&0xFFFFFF)|((state.voltage&0xFFFFFF)<<24)|(
        state.refractory_remaining<<48)

def trace_fingerprint(oracle,placement)->tuple[str,list[str]]:
    """P07 C: FNV64 of 8 LE uint32 per compartment, then 26 LE uint64 hashes."""
    positions=sorted((p.core_id,p.compartment_id,(p.population,p.neuron_index))
                     for p in placement)
    keys={key for _,_,key in positions}
    if (len(positions)!=1010 or len({(c,n) for c,n,_ in positions})!=1010
            or len(keys)!=1010 or len(oracle.ticks)!=26 or
            any(c not in range(27) or n not in range(1024)
                for c,n,_ in positions)):
        raise ParityNoGo("NO-GO: original 27-core 1010-neuron 26-tick placement changed")
    combined=FNV_SEED
    tick_hashes=[]
    for t,tick in enumerate(oracle.ticks):
        before=dict(tick.before)
        inputs=dict(tick.synaptic_inputs)
        after=dict(tick.after)
        fired=set(tick.spikes)
        if tick.tick!=t or set(before)!=keys or set(after)!=keys or set(inputs)!=keys:
            raise ParityNoGo("NO-GO: incomplete original independent scalar trace")
        h=FNV_SEED
        for _,_,key in positions:
            b=state_word(before[key])
            i=inputs[key]&MASK64
            a=state_word(after[key])
            h=fnv_words((b&0xFFFFFFFF,b>>32,i&0xFFFFFFFF,i>>32,
                         a&0xFFFFFFFF,a>>32,1 if key in fired else 0,0),h)
        tick_hashes.append(f"0x{h:016X}")
        combined=fnv_bytes(combined,h.to_bytes(8,"little"))
    return f"0x{combined:016X}",tick_hashes

def expected_counters(oracle,schedule,compiled)->dict:
    fanout_in=Counter()
    for route in compiled.ingress_routes:
        # Frozen B1.2 uses IngressRoute(input_population, input_index,
        # destination_core, destination_axon), not the legacy/mock names
        # source_input/source_index. Verify the exact original ABI.
        if route.input_population!="pixels" or not 0<=route.input_index<784:
            raise ParityNoGo("NO-GO: unexpected original pixel input route")
        if not 0<=route.destination_core<27 or not 0<=route.destination_axon<4096:
            raise ParityNoGo("NO-GO: original physical ingress destination invalid")
        fanout_in[route.input_index]+=1
    external=sum(fanout_in[pixel] for tick in schedule for pixel in tick)
    positions={(p.population,p.neuron_index):(p.core_id,p.compartment_id)
               for p in compiled.placement}
    fanout_out={(cfg.core_id,desc.source_compartment):len(desc.routes)
                for cfg in compiled.logical_deployment.core_configs
                for desc in cfg.output_routes}
    packets=sum(fanout_out.get(positions[spike],0)
                for tick in oracle.ticks for spike in tick.spikes)
    return {
        "external_current_events":external,
        "source_spikes_from_P03_trace_bank7":oracle.spike_count,
        "P03_packet_words_captured":packets,
        "NEXT_packets_physically_inserted":packets,
        "trained_readout_prediction":oracle.predicted_class,
        "readout_spike_counts":list(oracle.readout_spike_counts),
    }

def compare(physical:dict,reference:dict,reference_hash:str)->dict:
    checks={key:physical[key]==value for key,value in reference.items()}
    checks["all_26_tick_trace_fingerprint"]=(
        physical["all_26_tick_trace_hash"]==reference_hash)
    return checks

def check_physical(evidence:Path,staged:Path,routes:Path,index:dict)->dict:
    if (not evidence.is_absolute() or evidence.is_symlink() or
            not evidence.is_dir() or evidence.name!=EVIDENCE_NAME):
        raise ParityNoGo("NO-GO: require exact 2026-11-01 accepted V3 TRAIN0 evidence")
    if read(evidence/"stage.txt").strip()!=(
        b"P07_B4M_DIAG_V3_STRUCTURAL_RECEIPT_ACCEPTED_REBOOT_REQUIRED"):
        raise ParityNoGo("NO-GO: original structural pass stage marker missing")
    contract=json.loads(read(evidence/"diag_v3_launch_contract.json"))
    if (contract.get("new_elf_sha256")!=v3.V3_ELF_SHA or
        contract.get("new_linker_map_sha256")!=v3.V3_MAP_SHA or
        contract.get("diagnostic_firmware_identity")!=v3.V3_ID or
        contract.get("original_TRAIN_validation_ordinal")!=0 or
        contract.get("original_TRAIN_frame_sha256")!=TRAIN0_SHA or
        contract.get("full_independent_neuron_numerical_parity_proven") is not False):
        raise ParityNoGo("NO-GO: V3 launch contract mismatch")
    receipt=json.loads(read(evidence/"independent_staging_receipt.json"))
    if (receipt.get("original_27core_contexts_sha256")!=physical_model.ACCEPTED_BUNDLE_SHA or
        receipt.get("original_descriptor_16k_sha256")!=bindings.ACCEPTED_DESCRIPTOR_SHA or
        receipt.get("validation_ordinal")!=0 or
        receipt.get("real_elf_downloaded") is not False or
        receipt.get("inference_executed") is not False or
        receipt.get("official_MNIST_TEST")!="SEALED_NOT_ACCESSED"):
        raise ParityNoGo("NO-GO: same-session physical stage identity mismatch")
    observed=physical_model.verify_physical_readback(
        staged,evidence/"physical_readback",index)
    if observed["physical_readback_sha256"]!=physical_model.ACCEPTED_BUNDLE_SHA:
        raise ParityNoGo("NO-GO: all-27 original model physical readback hash mismatch")
    if sha(read(evidence/"binding_readback_16k.bin",16384))!=bindings.ACCEPTED_DESCRIPTOR_SHA:
        raise ParityNoGo("NO-GO: original physical descriptor SHA mismatch")
    expected={
       "input_routes_896k_physical.bin":routes/original.IN_FILENAME,
       "output_routes_80k_physical.bin":routes/original.OUT_FILENAME,
       "original_TRAIN_ingress_physical.bin":routes/"p07_b4m_original_TRAIN_validation_0_ingress.bin",
    }
    records=receipt.get("original_B2_4_routes_and_train_physical_sha256")
    if not isinstance(records,dict) or set(records)!=set(expected):
        raise ParityNoGo("NO-GO: original route/ingress receipt incomplete")
    for name,src in expected.items():
        payload=read(src)
        if (read(evidence/"b4m_physical_route_readback"/name)!=payload or
            records[name].get("sha256")!=sha(payload) or
            records[name].get("byte_exact_vs_signed_host_input") is not True):
            raise ParityNoGo("NO-GO: actual JTAG readback differs from signed source: "+name)
    data=read(evidence/"diag_v3_physical_mailbox_256.bin",256)
    if sha(data)!=MAILBOX_SHA:
        raise ParityNoGo("NO-GO: physically captured V3 mailbox differs from original accepted hash")
    physical=verifier.verify(data)
    summary=json.loads(read(evidence/"diag_v3_structural_receipt.json"))
    if (summary.get("diagnostic_v3_A53_elf_sha256")!=v3.V3_ELF_SHA or
        summary.get("diagnostic_v3_firmware_identity")!=v3.V3_ID or
        summary.get("trained_original_validation_ordinal")!=0 or
        summary.get("physical_mailbox")!=physical or
        summary.get("full_26tick_trained_physical_execution_structurally_verified") is not True or
        summary.get("independent_full_neuron_numerical_parity_verified") is not False):
        raise ParityNoGo("NO-GO: V3 structural report differs from RAW physical mailbox")
    return physical

def audit(frozen:Path,staged:Path,routes:Path,evidence:Path)->dict:
    if str(ROOT/"src") not in sys.path:
        sys.path.insert(0,str(ROOT/"src"))
    from loihi_twin_v2.compiler import NetworkSpec
    from loihi_twin_v2.p06_b12_partition import B12Result
    from loihi_twin_v2.p06_b14_monolithic import (
        pixel_schedule_independent,simulate_monolithic
    )
    from loihi_twin_v2.p06_b24_freeze import (
        PINNED_B23_SOURCE_SHA256,PINNED_B23_DEPLOYMENT_SHA256,PINNED_B23_FRAMES
    )
    b4l1.admit_freeze(frozen)
    index=physical_model.prepare_verified_contexts(frozen,staged)
    original_routes.require_routes(routes,frozen)
    physical=check_physical(evidence,staged,routes,index)
    network=NetworkSpec.from_json(read(frozen/"network_source.json").decode("utf-8"))
    packed=B12Result.from_json(read(frozen/"packed_deployment.json").decode("utf-8"))
    if (network.fingerprint!=PINNED_B23_SOURCE_SHA256 or
        packed.compiled.fingerprint!=PINNED_B23_DEPLOYMENT_SHA256 or
        packed.compiled.source_fingerprint!=network.fingerprint):
        raise ParityNoGo("NO-GO: frozen source network/compiled placement hashes disagree")
    image=read(routes/"p07_b4m_original_TRAIN_validation_0_ingress.bin",123216)
    if sha(image)!=TRAIN0_SHA or sha(image[-784:])!=original.FRAME_SHA[0]:
        raise ParityNoGo("NO-GO: original pinned TRAIN0 frame/pixels changed")
    saved=json.loads(read(frozen/"b23_validation_parity.json"))
    rows=saved.get("validation_frames")
    if (not isinstance(rows,list) or
        [r.get("validation_ordinal") for r in rows]!=[0,1,2]):
        raise ParityNoGo("NO-GO: B2.3 original 3-frame numerical report missing")
    baseline=rows[0]
    if (baseline.get("canonical_train_idx")!=original.FRAME_IDX[0] or
        baseline.get("image_sha256")!=original.FRAME_SHA[0] or
        baseline.get("monolithic_trace_sha256")!=PINNED_B23_FRAMES[0][3] or
        baseline.get("partitioned_trace_sha256")!=PINNED_B23_FRAMES[0][4] or
        baseline.get("all_26_ticks_full_neuron_parity") is not True):
        raise ParityNoGo("NO-GO: historical original B2.3 validated reference changed")
    schedule=pixel_schedule_independent(bytes(image[-784:]))
    oracle=simulate_monolithic(network,{"pixels":schedule},readout_population="readout")
    if (oracle.trace_sha256!=baseline["monolithic_trace_sha256"] or
        oracle.predicted_class!=baseline["predicted_class"] or
        list(oracle.readout_spike_counts)!=baseline["readout_spike_counts"]):
        raise ParityNoGo("NO-GO: independent current scalar oracle no longer reproduces B2.3 freeze")
    host=expected_counters(oracle,schedule,packed.compiled)
    host_hash,per_tick=trace_fingerprint(oracle,packed.compiled.placement)
    checks=compare(physical,host,host_hash)
    return {
      "schema":"p07-b4m-v3-TRAIN0-independent-scalar-vs-physical-FNV64-v1",
      "source":"ORIGINAL_HASH_VERIFIED_FROZEN_B2_4_AND_SIGNED_V3_PHYSICAL_READBACK",
      "original_train_validation_ordinal":0,
      "original_canonical_train_index":original.FRAME_IDX[0],
      "original_label":baseline["label"],
      "signed_v3_mailbox_sha256":MAILBOX_SHA,
      "physical":{key:physical[key] for key in (*host.keys(),"all_26_tick_trace_hash")},
      "independent_original_scalar":{**host,
            "all_26_tick_trace_hash":host_hash,
            "per_tick_trace_FNV64":per_tick,
            "frozen_B23_monolithic_trace_SHA256":oracle.trace_sha256},
      "comparisons":checks,
      "all_available_independent_counters_and_trace_fingerprint_equal":all(checks.values()),
      "direct_raw_per_neuron_physical_trace_bytewise_compared":False,
      "strict_full_neuron_physical_numeric_parity_proven":False,
      "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
      "actual_board_access":False,
      "source_model_changed":False,
    }

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("frozen-dir","staged-dir","routes-dir","evidence","out"):
        p.add_argument("--"+name,type=Path,required=True)
    args=p.parse_args()
    try:
        if (not args.out.is_absolute() or args.out.is_symlink() or args.out.exists()
            or args.out.resolve().is_relative_to(b4l1.REPO.resolve())
            or not args.out.parent.is_dir()):
            raise ParityNoGo("NO-GO: report must be NEW, absolute and outside Thesis repository")
        record=audit(args.frozen_dir,args.staged_dir,args.routes_dir,args.evidence)
        with args.out.open("x") as f:
            json.dump(record,f,sort_keys=True,indent=2)
            f.write("\n")
        print("P07_B4M_V3_ORACLE_PHYSICAL_REPORT="+str(args.out))
        print("P07_B4M_V3_ORACLE_VS_PHYSICAL_ALL_CHECKS_MATCH="+
              ("1" if record["all_available_independent_counters_and_trace_fingerprint_equal"] else "0"))
        print("P07_B4M_DIRECT_FULL_RAW_NEURON_PARITY_VERIFIED=0")
        print("P07_B4M_BOARD_ACCESSED=0")
        return 0 if record["all_available_independent_counters_and_trace_fingerprint_equal"] else 4
    except (ParityNoGo,OSError,ValueError,KeyError,TypeError,RuntimeError) as err:
        print("P07_B4M_V3_ORACLE_PARITY_NO_GO="+str(err),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
