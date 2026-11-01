#!/usr/bin/env python3
"""P07-B.5.3 ORIGINAL scalar 26x1010 x32B trace: PC-only reference/diagnosis.

Outputs exact 840,320B expected P03 bank7 trace in canonical
(tick, logical core ID, compartment ID) order for a pre-frozen TRAIN
validation ordinal. Optionally compare an UNAUTHENTICATED binary and locate
first mismatch (tick/core/neuron/field). Until the separate P07-B5 hardware
sidecar, ownership, and independently checked XSDB readback exist, a match
does NOT constitute physical trace parity.

No actual JTAG / FPGA tool, no official MNIST TEST, no changes to signed B2.4,
P03 HLS, original accepted V3 binary, routes or frozen checkpoint.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import p07_b5_scaled_validation as b5
import p07_b4m_v3_train0_scalar_vs_physical as baseline

TRACE_NEURONS=1010
TRACE_TICKS=26
TRACE_WORD_BYTES=32
TRACE_BYTES=TRACE_NEURONS*TRACE_TICKS*TRACE_WORD_BYTES
FIELDS=((0,8,"before_state"),(8,16,"signed_64bit_synaptic_input"),
        (16,24,"after_state"),(24,28,"spike_bit"),(28,32,"reserved_bits"))

def expected_raw_trace(run,compiled)->tuple[bytes,list[tuple[int,int,int,tuple[str,int]]]]:
    """Independent P06 scalar LIF states -> exact original P03 256-bit trace ABI."""
    rows=sorted((p.core_id,p.compartment_id,(p.population,p.neuron_index))
                for p in compiled.placement)
    keys={key for _,_,key in rows}
    b5.ensure(len(rows)==TRACE_NEURONS and
              len({(core,comp) for core,comp,_ in rows})==TRACE_NEURONS and
              len(keys)==TRACE_NEURONS and len(run.ticks)==TRACE_TICKS,
              "expected original 26x1010 unique physical neuron placement")
    output=bytearray()
    coords=[]
    for n,tick in enumerate(run.ticks):
        before=dict(tick.before)
        inputs=dict(tick.synaptic_inputs)
        after=dict(tick.after)
        fired=set(tick.spikes)
        b5.ensure(tick.tick==n and set(before)==keys and
                  set(inputs)==keys and set(after)==keys,
                  "scalar reference trace missing original neuron identities")
        for core,comp,key in rows:
            initial=baseline.state_word(before[key])
            synaptic=inputs[key] & baseline.MASK64
            terminal=baseline.state_word(after[key])
            output.extend(struct.pack(
                "<QQQII",initial,synaptic,terminal,
                1 if key in fired else 0,0))
            coords.append((n,core,comp,key))
    b5.ensure(len(output)==TRACE_BYTES and len(coords)==TRACE_TICKS*TRACE_NEURONS,
              "unexpected P03 bank7 840320B raw oracle serialization")
    return bytes(output),coords

def first_mismatch(expected:bytes,observed:bytes,coords:list)->dict|None:
    b5.ensure(len(expected)==TRACE_BYTES and len(observed)==TRACE_BYTES and
              len(coords)==TRACE_NEURONS*TRACE_TICKS,
              "one complete 840320B trace and each original neuron location required")
    for idx,(tick,core,comp,neuron) in enumerate(coords):
        offset=idx*TRACE_WORD_BYTES
        if expected[offset:offset+TRACE_WORD_BYTES]!=observed[offset:offset+TRACE_WORD_BYTES]:
            for start,end,field in FIELDS:
                e=expected[offset+start:offset+end]
                a=observed[offset+start:offset+end]
                if e!=a:
                    return {
                        "tick":tick,"logical_core":core,"compartment":comp,
                        "population":neuron[0],"neuron_index":neuron[1],
                        "field":field,"absolute_byte_offset":offset+start,
                        "trace_word_index":idx,
                        "expected_field_little_endian_hex":e.hex(),
                        "observed_field_little_endian_hex":a.hex(),
                    }
            raise b5.ValidationNoGo("NO-GO: first byte mismatch not assigned to field")
    return None

def scalar_raw(frozen:Path,staged:Path,routes:Path,ordinal:int):
    if str(b5.ROOT/"src") not in sys.path:
        sys.path.insert(0,str(b5.ROOT/"src"))
    from loihi_twin_v2.p06_b14_monolithic import (
        pixel_schedule_independent,simulate_monolithic
    )
    network,packed,_index,rows=b5.load_original(frozen,staged,routes)
    pinned=b5.make_reference(ordinal,network,packed,rows,routes)
    frame=baseline.read(routes/pinned["frame_filename"])
    schedule=pixel_schedule_independent(bytes(frame[-784:]))
    scalar=simulate_monolithic(network,{"pixels":schedule},
                               readout_population="readout")
    b5.ensure(scalar.trace_sha256==pinned["independent_scalar_monolithic_sha256"],
              "independent scalar replay does not reproduce frozen B2.3 original")
    raw,coords=expected_raw_trace(scalar,packed.compiled)
    # The FNV trace proof must hash exactly this serialized full transcript.
    combined=baseline.FNV_SEED
    for t in range(TRACE_TICKS):
        tick_bytes=raw[t*TRACE_NEURONS*TRACE_WORD_BYTES:
                       (t+1)*TRACE_NEURONS*TRACE_WORD_BYTES]
        h=baseline.fnv_bytes(baseline.FNV_SEED,tick_bytes)
        b5.ensure(f"0x{h:016X}"==pinned["per_tick_trace_fingerprint_FNV64"][t],
                  "raw scalar bytes disagree with prior independent 26-tick FNV witness")
        combined=baseline.fnv_bytes(combined,h.to_bytes(8,"little"))
    b5.ensure(f"0x{combined:016X}"==pinned["trace_fingerprint_FNV64"],
              "raw scalar trace full FNV witness mismatch")
    return pinned,raw,coords

def run(args)->tuple[dict,int,bytes]:
    b5.ensure(args.mode in ("reference","compare-unverified"),
              "invalid raw scalar reference mode")
    pinned,expected,coords=scalar_raw(
        args.frozen_dir,args.staged_dir,args.routes_dir,args.ordinal)
    info={
        "schema":"p07-b5-raw-1010-neurons-26ticks-original-scalar-reference-v1",
        "ordinal":args.ordinal,
        "train_source_original_signed_frame_sha256":pinned["frame_sha256"],
        "signed_original_scalar_monolithic_sha256":pinned[
            "independent_scalar_monolithic_sha256"],
        "raw_trace_expected_byte_size":TRACE_BYTES,
        "raw_trace_expected_sha256":hashlib.sha256(expected).hexdigest(),
        "raw_trace_expected_FNV64":pinned["trace_fingerprint_FNV64"],
        "firmware_neuron_order":"tick-then-core-then-compartment",
        "direct_full_raw_26x1010_FPGA_trace_verified":False,
        "full_hardware_trace_capture_authenticated":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "board_contact":False,
    }
    if args.mode=="reference":
        b5.ensure(args.trace is None,"reference mode does not accept a physical trace")
        b5.ensure(args.expected_raw is not None,"reference requires --expected-raw")
        b5.require_external_report(args.expected_raw)
        info["expected_raw_output"]=str(args.expected_raw)
        return info,0,expected
    b5.ensure(args.trace is not None and args.expected_raw is None,
              "compare-unverified requires --trace and forbids output of expected raw")
    observed=baseline.read(args.trace,TRACE_BYTES)
    mismatch=first_mismatch(expected,observed,coords)
    info.update({
        "user_supplied_unverified_trace_file":str(args.trace),
        "user_supplied_unverified_trace_sha256":hashlib.sha256(observed).hexdigest(),
        "raw_bytes_equal_scalar_oracle":mismatch is None,
        "first_mismatch":mismatch,
        "hardware_trace_source_authenticity_verified":False,
        "full_hardware_trace_capture_authenticated":False,
        "direct_full_raw_26x1010_FPGA_trace_verified":False,
    })
    return info,0 if mismatch is None else 4,expected

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("reference","compare-unverified"),required=True)
    p.add_argument("--ordinal",type=int,choices=(0,1,2),required=True)
    for name in ("frozen-dir","staged-dir","routes-dir","out"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--expected-raw",type=Path)
    p.add_argument("--trace",type=Path)
    a=p.parse_args()
    try:
        b5.require_external_report(a.out)
        if a.expected_raw is not None:
            b5.require_external_report(a.expected_raw)
            b5.ensure(a.out.resolve()!=a.expected_raw.resolve(),
                      "expected raw reference path cannot overwrite its report")
        record,code,raw=run(a)
        if a.mode=="reference":
            with a.expected_raw.open("xb") as f:f.write(raw)
        b5.write_report(a.out,record)
        print("P07_B5_RAW_SCALAR_REFERENCE_REPORT="+str(a.out),flush=True)
        print("P07_B5_RAW_SCALAR_REFERENCE_SHA256="+record[
            "raw_trace_expected_sha256"],flush=True)
        print("P07_B5_FULL_RAW_PHYSICAL_TRACE_AUTHENTICATED=0",flush=True)
        if a.mode=="compare-unverified":
            print("P07_B5_UNVERIFIED_TRACE_BYTES_VS_SCALAR_EQUAL="+
                  ("1" if code==0 else "0"),flush=True)
        return code
    except (ValueError,TypeError,KeyError,OSError) as e:
        print("P07_B5_RAW_SCALAR_NO_GO="+str(e),file=sys.stderr,flush=True)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
