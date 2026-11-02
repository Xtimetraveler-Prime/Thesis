#!/usr/bin/env python3
"""P08-B2.4 untrusted 16-frame journal/timing vs original scalar verifier.

This checks syntax, CRC, exact geometry, 16x per-image original frozen
scalar counters and full-26-tick trace FNV. NO original trusted physical
JTAG transcript is accepted by this entry point; even equality does NOT
prove KV260 provenance. A future verified same-session JTAG readback
attestation is mandatory before claiming physical numerical acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

import p08_b2_4_scalar_first16 as oracle_stage

SCHEMA="p08-b2-4-unverified-journal-timing-vs-independent-scalar-16-v1"
COUNT=16
ROW_BYTES=256
JOURNAL_MAGIC=0x4A423832
TIMING_MAGIC=0x54423832
MAILBOX_MAGIC=0x50384232
PASS=0x600D0823
DONE=0xC0DEF00D
RECEIPT_MAGIC=0x42344D46  # accepted P07 full receipt (verify import below)
JOURNAL_NAME="p08_b2_4_first16_journal_unverified.bin"
TIMING_NAME="p08_b2_4_first16_timing_unverified.bin"
MAILBOX_NAME="p08_b2_4_first16_mailbox_unverified.bin"

class RecordNoGo(ValueError):pass

def ensure(ok:bool,msg:str)->None:
    if not ok:raise RecordNoGo("NO-GO: "+msg)

def read_regular(path:Path,size:int|None=None)->bytes:
    ensure(path.is_file() and not path.is_symlink(),
           "missing or symlinked evidence "+str(path))
    raw=path.read_bytes()
    ensure(size is None or len(raw)==size,"incorrect binary size "+str(path))
    return raw

def u64(w:tuple[int,...],at:int)->int:
    return w[at] | w[at+1]<<32

def unpack_row(raw:bytes,index:int,magic:int)->tuple[int,...]:
    ensure(len(raw)==ROW_BYTES,f"frame {index} row must be 256 bytes")
    w=struct.unpack("<64I",raw)
    ensure((w[0],w[1],w[2],w[3],w[63])==(magic,1,index,PASS,DONE),
           f"frame {index} header/index/PASS/DONE drift")
    ensure(w[62]==0 and w[61]==zlib.crc32(raw[:244]),
           f"frame {index} reserved byte or CRC32 drift")
    return w

def verify_journal(raw:bytes,index:int,expected:dict)->dict:
    w=unpack_row(raw,index,JOURNAL_MAGIC)
    ensure(w[4]==index+1,"frame reset generation drift")
    # P07_B4M_FULL_MAGIC sourced from accepted header's literal 0x4D344642.
    ensure(w[5]==0x4D344642,"original 26-tick engine receipt magic mismatch")
    expect={
        6:expected["expected_prediction"],
        7:702,8:26,9:1010,
        10:expected["expected_external_current"],
        11:expected["expected_source_spikes"],
        12:expected["expected_captured_packets"],
        13:expected["expected_inserted_next"],
        14:702,15:699,16:3,23:123216,
    }
    for word,value in expect.items():
        ensure(w[word]==value,f"frame {index}: physical scalar/pager word[{word}] != independent oracle")
    fnv=u64(w,17)
    ensure(f"0x{fnv:016X}"==expected["expected_all_26_ticks_1010_neuron_FNV64"],
           f"frame {index}: 26-tick 1010-neuron FNV differs from original frozen scalar oracle")
    ensure(list(w[24:34])==expected["expected_output_spike_counts"],
           f"frame {index}: readout spike vector differs")
    ensure(raw[34*4:42*4].hex()==expected["raw_pixels_sha256"],
           f"frame {index}: journal raw SHA identity differs")
    ensure(raw[42*4:50*4].hex()==expected["original_27core_ingress_sha256"],
           f"frame {index}: journal B1.3 original encoded SHA differs")
    ensure(all(w[i]==0 for i in range(50,61)),
           f"frame {index}: journal reserved fields nonzero")
    assert (w[19],w[20],w[21],w[22]) == (
        (u64(w,19)&0xffffffff),(u64(w,19)>>32),
        (u64(w,21)&0xffffffff),(u64(w,21)>>32))
    read_bytes=u64(w,19)
    write_bytes=u64(w,21)
    ensure(read_bytes==702*438272 and write_bytes==702*106496,
           f"frame {index}: context paging bytes incorrect")
    return {
        "ordinal":index,
        "TRAIN_source_index":expected["TRAIN_source_index"],
        "prediction":w[6],
        "readout_spikes":list(w[24:34]),
        "trace_fnv64":f"0x{fnv:016X}",
        "page_in_bytes":read_bytes,
        "page_out_bytes":write_bytes,
        "raw_sha256":raw[34*4:42*4].hex(),
        "frame_sha256":raw[42*4:50*4].hex(),
    }

def verify_timing(raw:bytes,index:int,prior_commit:int|None)->dict:
    w=unpack_row(raw,index,TIMING_MAGIC)
    ensure(all(v==0 for v in w[24:61]),
           f"frame {index}: unexpected nonzero timing reserved fields")
    hz=u64(w,4)
    begin=u64(w,6)
    committed=u64(w,8)
    total=u64(w,10)
    stages=[u64(w,12+2*i) for i in range(6)]
    ensure(1_000_000<=hz<=2_000_000_000,
           f"frame {index}: implausible observed A53 CNTFRQ")
    ensure(begin>0 and committed>=begin and total==committed-begin and
           sum(stages)==total and total>0,
           f"frame {index}: inaccurate additive CNTVCT service accounting")
    if prior_commit is not None:
        ensure(begin>=prior_commit,
               f"frame {index}: A53 service timestamps overlap/backtrack")
    return {"frame":index,"CNTFRQ_EL0_hz":hz,
            "service_start_CNTVCT":begin,"after_journal_commit_CNTVCT":committed,
            "complete_service_counter_ticks":total,
            "phase_counter_ticks":stages}

def verify_mailbox(raw:bytes,count:int)->dict:
    ensure(len(raw)==ROW_BYTES,"mailbox must be exactly 256 bytes")
    w=struct.unpack("<64I",raw)
    ensure((w[0],w[1],w[2],w[3],w[4],w[5],w[63])==
           (MAILBOX_MAGIC,1,PASS,count-1,0,count,DONE),
           "pilot mailbox does not show exact 16-frame terminal complete PASS")
    ensure(w[6] | (w[7]<<32)>0 and w[8]==count and
           w[9]==702 and w[10]==26 and
           w[11]==0 and w[12]==0 and w[13]==0 and
           all(x==0 for x in w[14:63]),
           "pilot mailbox reset/engine counters/status or reserved fields drift")
    return {"last_frame":w[3],"completed":w[5],
            "observed_CNTFRQ_EL0_hz":u64(w,6)}

def verify(oracle_path:Path,journal_path:Path,timing_path:Path,
           mailbox_path:Path,out:Path)->dict:
    ensure(out.is_absolute() and not out.exists() and not out.is_symlink() and
           out.parent.is_dir() and not out.resolve().is_relative_to(oracle_stage.ROOT),
           "NEW external absolute verification report required")
    orig=read_regular(oracle_path)
    expected=json.loads(orig)
    ensure(expected["schema"]==oracle_stage.SCHEMA and
           expected["count"]==COUNT and
           expected["original_known_three_B23_witness_reproduced"] is True and
           expected["original_p08_b2_1_raw_pool_sha256"]==oracle_stage.RAW_POOL_SHA and
           expected["operator_genuine_new_image_only_elf_sha256"]==oracle_stage.B23_ELF_SHA and
           expected["original_compiled_sha256"]==
                "02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a" and
           expected["official_MNIST_TEST"]=="SEALED_NOT_ACCESSED",
           "independent original scalar reference identity invalid")
    frames=expected["frames"]
    ensure(len(frames)==COUNT and
           [v["ordinal"] for v in frames]==list(range(COUNT)),
           "first16 original source identities missing")
    journals=read_regular(journal_path,COUNT*ROW_BYTES)
    timings=read_regular(timing_path,COUNT*ROW_BYTES)
    final=read_regular(mailbox_path,ROW_BYTES)
    mail=verify_mailbox(final,COUNT)
    verified=[]
    time_records=[]
    prior=None
    for i,item in enumerate(frames):
        verified.append(verify_journal(journals[i*ROW_BYTES:(i+1)*ROW_BYTES],i,item))
        t=verify_timing(timings[i*ROW_BYTES:(i+1)*ROW_BYTES],i,prior)
        ensure(t["CNTFRQ_EL0_hz"]==mail["observed_CNTFRQ_EL0_hz"],
               f"frame {i}: A53 clock frequency differs from final mailbox")
        prior=t["after_journal_commit_CNTVCT"]
        time_records.append(t)
    result={
        "schema":SCHEMA,
        "independent_scalar_oracle_sha256":hashlib.sha256(orig).hexdigest(),
        "unverified_input_journal_sha256":hashlib.sha256(journals).hexdigest(),
        "unverified_input_timing_sha256":hashlib.sha256(timings).hexdigest(),
        "unverified_input_mailbox_sha256":hashlib.sha256(final).hexdigest(),
        "verified_frames":COUNT,
        "all_16_independent_scalar_counters_match":True,
        "all_16_full_26tick_trace_FNV_match":True,
        "all_16_end_to_end_timers_internally_consistent":True,
        "end_mailbox":mail,
        "neural_frames":verified,
        "timing_frames":time_records,
        "authenticated_real_JTAG_same_session_readback":False,
        "actual_physical_KV260_neural_parity_proven":False,
        "physical_latency_measurement_accepted":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }
    with out.open("x",encoding="utf-8") as fp:
        json.dump(result,fp,indent=2,sort_keys=True);fp.write("\n")
    return result

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ("oracle","journal","timing","mailbox","out"):
        p.add_argument("--"+flag,required=True,type=Path)
    a=p.parse_args()
    try:
        result=verify(a.oracle,a.journal,a.timing,a.mailbox,a.out)
        print("P08_B2_4_UNVERIFIED_FIRST16_BYTES_VS_SCALAR_EQUAL=1")
        print("P08_B2_4_16_TIMESTAMP_ACCOUNTING_SELF_CONSISTENT=1")
        print("P08_B2_4_JTAG_PHYSICAL_AUTHENTICITY_VERIFIED=0")
        print("P08_B2_4_PHYSICAL_LATENCY_ACCEPTED=0")
        print("P08_B2_4_UNVERIFIED_REPORT="+str(a.out))
        return 0
    except (RecordNoGo,ValueError,TypeError,OSError,KeyError,AssertionError) as e:
        print("P08_B2_4_RECORD_NO_GO="+str(e),file=sys.stderr)
        return 3

if __name__=="__main__":
    raise SystemExit(main())
