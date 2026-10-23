#!/usr/bin/env python3
"""PC-only original B2.4 first-physical-dispatch HLS input-semantics audit.

The real KV260 first full B4m ELF run reported hardware protocol -5 at
stage 9 with one completed PL dispatch. This re-evaluates original signed
TRAIN input 0 / core 0's first-tick CURRENT events against HLS source
requirements and original B2.4 packed axon/synapse model, NEVER the FPGA.
It cannot establish the actual P03 register/substage that failed.
Does not unseal original official MNIST TEST or produce physical parity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import p07_b4m_frozen_inputs as original
import p07_b4m_offline_admission as gate

V3=Path(__file__).resolve().parents[1]

class DispatchAuditNoGo(ValueError):
    pass

def fired(value:int,pixel:int,tick:int)->bool:
    if not 0<=value<=255 or not 0<=pixel<784 or not 0<=tick<26:
        raise DispatchAuditNoGo("invalid original TRAIN first-tick event source")
    if tick==25:
        return False
    phase=(tick+17*pixel)%25
    return ((phase+1)*value)//255 > (phase*value)//255


def check_first_core_hls_path(
    pixel_values:bytes,
    routes:list[tuple[int,int,int]],
    image,
    *,
    tick:int=0,
    core:int=0,
)->dict:
    """Pure source/HLS-side legality audit; independent of PL status CSRs."""
    n=image.compartment_count
    axons={w.index:w.word for w in image.axon_words}
    synapses=image.synapse_words
    violations=[]
    examples=[]
    source_events=0
    if not 1<=n<=1024 or len(synapses)>32768:
        violations.append("HLS per-core compartment/synapse table capacity")
    if any(w>>114 for w in image.config_words):
        violations.append("HLS compartment config reserved bits")
    if any(w>>64 for w in image.state_words):
        violations.append("HLS initial neuron state reserved bits")
    if any(w.word>>26 for w in image.route_descriptor_words):
        violations.append("HLS output route descriptor reserved bits")
    if any(w>>19 for w in image.route_words):
        violations.append("HLS output packet routing reserved bits")
    for pixel,dest,axon_id in routes:
        if dest!=core or not fired(pixel_values[pixel],pixel,tick):
            continue
        source_events+=1
        if len(examples)<12:
            examples.append({"pixel":pixel,"source_value":pixel_values[pixel],
                             "target_axon":axon_id})
        axon=axons.get(axon_id)
        if axon is None or ((axon>>41)&1)==0 or axon>>42:
            violations.append(f"first core event on invalid/reserved axon {axon_id}")
            continue
        first=axon&0x7fff
        count=(axon>>15)&0xffff
        offset=(axon>>31)&0x3ff
        if first+count>len(synapses) or first+count>32768:
            violations.append(f"first core axon {axon_id} synapse row out of bounds")
            continue
        for synapse in synapses[first:first+count]:
            if synapse>>48:
                violations.append(f"axon {axon_id} synapse reserved bits")
            if (synapse>>34)&0x3f:
                violations.append(f"axon {axon_id} unsupported HLS delay")
            if offset+(synapse&0x3ff)>=n:
                violations.append(f"axon {axon_id} synapse target out of bounds")
    if source_events>4096:
        violations.append("HLS event bank capacity")
    return {
        "tick":tick,"core":core,
        "HLS_source_compartments":n,
        "HLS_source_synapse_table_entries":len(synapses),
        "HLS_source_total_registered_axons":len(axons),
        "HLS_first_dispatch_expected_current_events":source_events,
        "first_12_expected_current_events":examples,
        "HLS_first_dispatch_input_semantics_violations":sorted(set(violations)),
        "HLS_first_dispatch_input_semantics_ok":not violations,
        "independent_real_PL_dispatch_protocol_or_trace_verified":False,
    }


def audit(frozen:Path,routes_dir:Path)->dict:
    # The source is ALWAYS the immutable B2.4 SNAPSHOT and exactly the
    # SHA-authenticated original operator-accepted TRAIN frame and routes.
    staged=gate.require_routes(routes_dir,frozen)
    if staged["input_routes"]!=20384 or staged["output_routes"]!=1000:
        raise DispatchAuditNoGo("original frozen B2.4 route cardinalities changed")
    source=frozen/"packed_deployment.json"
    if source.is_symlink() or not source.is_file():
        raise DispatchAuditNoGo("original B2.4 compiled network absent")
    if str(V3/"src") not in sys.path:sys.path.insert(0,str(V3/"src"))
    from loihi_twin_v2.p06_b12_partition import B12Result
    from loihi_twin_v2.hardware_p03 import export_one_core_image
    network=B12Result.from_json(source.read_text())
    if (network.compiled.fingerprint!=original.PINNED_SHA or
        network.capacity_audit["audit_sha256"]!=original.CAP_SHA):
        raise DispatchAuditNoGo("original immutable trained B2.4 identity mismatch")
    cfg=network.compiled.logical_deployment.core_configs
    if len(cfg)!=27 or cfg[0].core_id!=0:
        raise DispatchAuditNoGo("original trained 27-core layout changed")
    source_frame=routes_dir/"p07_b4m_original_TRAIN_validation_0_ingress.bin"
    raw=source_frame.read_bytes()
    if (len(raw)!=123216 or
        hashlib.sha256(raw).hexdigest()!=
        "2aa772efd381805bab24fea145186d22f3550b156f155a9ab51dcef10e6d8126"):
        raise DispatchAuditNoGo("operator original TRAIN ordinal 0 frame changed")
    pixels=raw[-784:]
    if hashlib.sha256(pixels).hexdigest()!=original.FRAME_SHA[0]:
        raise DispatchAuditNoGo("raw original TRAIN validation pixel SHA changed")
    table=routes_dir/original.IN_FILENAME
    buf=table.read_bytes()
    if buf[:8]!=b"B4MING01" or struct.unpack_from("<I",buf,20)[0]!=20384:
        raise DispatchAuditNoGo("original physical B4m input routes header drift")
    raw_routes=[struct.unpack_from("<3H",buf,128+i*6) for i in range(20384)]
    if len({pix for pix,core,axon in raw_routes if core==0})!=784:
        raise DispatchAuditNoGo("original B2.4 core0 pixel routing cardinality drift")
    output=check_first_core_hls_path(pixels,raw_routes,export_one_core_image(cfg[0]))
    return {
        "schema":"p07-b4m-original-TRAIN0-first-PL-dispatch-PC-HLS-input-audit-v1",
        "original_immutable_frozen_B24_compiled_SHA":original.PINNED_SHA,
        "original_pinned_TRAIN_frame_sha256":staged["staged_files_sha256"][source_frame.name],
        "physical_first_dispatch_failure_stage":9,
        "physical_hw_adapter_protocol_error":-5,
        "previous_physical_dispatch_counter":1,
        "frozen_PC_source_audit":output,
        "physical_board_access":False,
        "signed_source_modified":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "original_failure_root_cause_independently_proven":False,
    }


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--frozen-dir",type=Path,required=True)
    p.add_argument("--routes-dir",type=Path,required=True)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    try:
        result=audit(a.frozen_dir,a.routes_dir)
        if a.out:
            if a.out.exists() or not a.out.is_absolute() or a.out.is_symlink():
                raise DispatchAuditNoGo("NEW absolute PC-only report path required")
            a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print(json.dumps(result,indent=2,sort_keys=True))
        print("P07_B4M_FIRST_DISPATCH_SOURCE_HLS_AUDIT_PC_ONLY_PASS=1")
        print("P07_B4M_PHYSICAL_STAGE9_ERROR_ROOT_CAUSE_PROVEN=0")
        return 0
    except (OSError,ValueError,TypeError,KeyError,AssertionError) as exc:
        print("P07_B4M_FIRST_DISPATCH_PC_NO_GO="+str(exc),file=sys.stderr)
        return 3
if __name__=="__main__":
    raise SystemExit(main())
