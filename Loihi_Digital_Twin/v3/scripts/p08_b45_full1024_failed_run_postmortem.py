#!/usr/bin/env python3
"""B4.5 full1024 FAILED JTAG run postmortem: OFFLINE HOST FILES ONLY.

Decode saved terminal FAILURE mailbox, stage and original 3x256KiB
sidecars. Verify contiguous completed frames versus accepted frozen
1024 software scalar reference, without requiring 1024/1024 success.
Never access board, Vitis, JTAG, XSDB, PuTTY or modify evidence.
Report is intentionally FAILURE evidence, not physical PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import zlib

import p08_b2_4_verify_untrusted_first16 as records
import p08_b4_1_merge_scalar_1024 as fulloracle
import p08_b4_2_physical_run as pinned
import p08_b45_sidecar as reset

SIZE=256
COUNT=1024
MAILBOX_MAGIC=0x50384232
FAIL=0xDEAD0823
DONE=0xC0DEF00D
STATUS=0x600D0823
SCHEMA="p08-b45-unprotected-full1024-failed-run-offline-postmortem-v1"
BIND_DIAG_MAGIC=0x504D4244
BIND_DIAG={
    0:"CONFIG_OK; if bind rejected then state mutated after fresh startup check",
    1:"BAD_ARGS",
    2:"BAD_MODE",
    3:"MISSING_MEMORY_CALLBACK_OR_POINTER",
    4:"INVALID_CONTEXT_COPY_GEOMETRY",
    5:"ORIGINAL_SHA_HEADER_MISSING_FOR_AUTH_ONCE",
    6:"ADDRESS_OVERFLOW",
    7:"MUTABLE_BACKUP_DDR_OVERLAP",
    8:"RESET_STATE_OVERLAPS_CONTEXT_DDR",
    9:"PINNED_SHA_HASH_POINTER_OVERLAPS_MEMORY",
}
FAULTS={
    100:"PS width or hardware readiness",
    101:"A53 counter frequency unavailable",
    102:"original 1024 image raw-pool SHA mismatch",
    103:"initial frozen runtime initialization",
    104:"original input-route admission",
    105:"reset bind or initial authenticate-once SHA/header verification",
    200:"A53 service meter start",
    201:"optimized reset_image failed or counter went backward",
    202:"service meter mark after state restore",
    203:"original per-image input encoding",
    204:"service meter mark after encoded ingress",
    205:"per-image frozen runtime initialization",
    206:"scheduler preparation",
    207:"service meter mark after scheduler preparation",
    208:"26-tick 702-dispatch original neural inference",
    209:"service meter mark after 26-tick neural inference",
    210:"neural/hardware/reset receipt validation",
    211:"service meter mark after receipt validation",
    212:"journal commit",
    213:"service meter mark after journal commit",
    214:"A53 complete-service meter finish",
}

class PostmortemNoGo(ValueError):
    pass

def require(ok:bool,reason:str)->None:
    if not ok:raise PostmortemNoGo("NO-GO: "+reason)

def read(p:Path,bytes_expected:int|None=None)->bytes:
    require(p.is_file() and not p.is_symlink(),
            "regular original evidence file needed: "+str(p))
    data=p.read_bytes()
    require(bytes_expected is None or len(data)==bytes_expected,
            "exact evidence size mismatch: "+str(p))
    return data

def digest(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def decode_mailbox(blob:bytes)->dict:
    require(len(blob)==SIZE,"saved 256-byte terminal mailbox required")
    words=struct.unpack("<64I",blob)
    require(words[0]==MAILBOX_MAGIC and words[1]==1 and words[63]==DONE,
            "saved mailbox is not the expected original A53 format")
    require(words[2]==FAIL,"this is a FAILURE-only postmortem, no PASS claims")
    require(words[4] in FAULTS,"unsupported fault code: "+str(words[4]))
    frame=words[3]
    before_frame=frame==0xFFFFFFFF
    require(before_frame or frame<COUNT,"invalid failed image ordinal")
    require((before_frame and words[4]<200) or
            (not before_frame and 200<=words[4]<=214),
            "terminal fault code/frame stage contradict frozen A53 source")
    if not before_frame:
        require(words[5]==frame,
                "A53 complete-count must equal number of prior frames")
    diagnosis=None
    if words[14]==BIND_DIAG_MAGIC:
        require(before_frame and words[4]==105,
                "V2 bootstrap detailed failure is only valid before image 0")
        code=words[15]
        require(code in BIND_DIAG,
                "unknown V2 bind/geometry reason")
        diagnosis={
            "diagnostic_format":"p08-b45-v2-preloop-bind-details",
            "boot_geometry_reason_code":code,
            "boot_geometry_reason":BIND_DIAG[code],
            "reset_state_magic_before_explicit_clear_hex":f"0x{words[16]:08X}",
            "previous_reset_generation":words[17],
            "previous_reset_poison":words[18],
            "prior_pager_dispatches_before_explicit_zero":words[19],
            "prior_pager_barriers_before_explicit_zero":words[20],
            "new_reset_state_zeroed_after_geometry_check":words[21]==1,
            "original_P03_and_XMPU_protection_not_attested":True,
        }
    return {
        "terminal_failure":True,
        "v2_failure_only_bootstrap_diagnostic":diagnosis,
        "status_hex":f"0x{words[2]:08X}",
        "failing_frame_ordinal":None if before_frame else frame,
        "completed_frames_mailbox":words[5] if not before_frame else 0,
        "pre_loop_failure":before_frame,
        "pre_loop_bind_result_negative_code":words[5] if words[4]==105 else None,
        "fault_code":words[4],
        "fault_stage":FAULTS[words[4]],
        "reset_generation":words[8],
        "pager_dispatches_last":words[9],
        "pager_barriers_last":words[10],
        "scheduler_poisoned":words[11],
        "reset_poisoned":words[12],
        "hardware_last_error":words[13],
        "cntfrq_hz":words[6] | (words[7]<<32),
        "mailbox_sha256":digest(blob),
    }

def valid_row(raw:bytes,index:int,magic:int)->bool:
    if len(raw)!=SIZE or raw==bytes(SIZE):return False
    w=struct.unpack("<64I",raw)
    return (w[0],w[1],w[2],w[3],w[62],w[63]) == (
        magic,1,index,STATUS,0,DONE) and w[61]==zlib.crc32(raw[:244])

def scan_rows(blob:bytes,magic:int)->dict:
    require(len(blob)==COUNT*SIZE,"saved original complete 256KiB sidecar required")
    states=[]
    for i in range(COUNT):
        row=blob[i*SIZE:(i+1)*SIZE]
        states.append("valid" if valid_row(row,i,magic) else (
                      "zero" if row==bytes(SIZE) else "invalid_nonzero"))
    first_bad=next((i for i,v in enumerate(states) if v!="valid"),COUNT)
    return {
        "valid_prefix_rows":first_bad,
        "valid_rows_anywhere":states.count("valid"),
        "zero_rows":states.count("zero"),
        "invalid_nonzero_rows":states.count("invalid_nonzero"),
        "first_nonvalid_ordinal":None if first_bad==COUNT else first_bad,
        "any_nonzero_after_valid_prefix":any(
            v!="zero" for v in states[first_bad:]),
        "sha256":digest(blob),
    }

def examine(evidence:Path,oracle:Path,out:Path)->dict:
    require(evidence.is_absolute() and evidence.is_dir() and
            not evidence.is_symlink(),"original failed evidence root required")
    require(oracle.is_absolute() and oracle.is_file() and
            not oracle.is_symlink(),"original full1024 scalar oracle required")
    require(out.is_absolute() and out.parent.is_dir() and
            not out.exists() and not out.is_symlink() and
            not out.resolve().is_relative_to(fulloracle.shard.ROOT),
            "new external no-overwrite JSON output required")
    cap=evidence/"performance1024_capture"
    mail=decode_mailbox(read(cap/"mailbox_terminal_physical.bin",SIZE))
    require(digest(read(oracle))==pinned.ORIGINAL_FULL1024_ORACLE_SHA,
            "accepted complete 1024 original scalar oracle SHA drift")
    actual=json.loads(oracle.read_text())
    require(actual.get("schema")==fulloracle.SCHEMA and
            actual.get("count")==COUNT and
            actual.get("official_MNIST_TEST")=="SEALED_NOT_ACCESSED",
            "wrong original frozen TRAIN-derived scalar reference")
    rows=actual["frames"]
    require(isinstance(rows,list) and len(rows)==COUNT,
            "incomplete scalar reference rows")
    blobs={
        "journal":read(cap/"journal1024_physical.bin",COUNT*SIZE),
        "timing":read(cap/"timing1024_physical.bin",COUNT*SIZE),
        "reset":read(cap/"reset_profile1024_physical.bin",COUNT*SIZE),
    }
    scanned={
        "journal":scan_rows(blobs["journal"],records.JOURNAL_MAGIC),
        "timing":scan_rows(blobs["timing"],records.TIMING_MAGIC),
        "reset":scan_rows(blobs["reset"],reset.MAGIC["once"]),
    }
    completed=mail["completed_frames_mailbox"]
    # An interrupted A53 can commit a journal before the timing/
    # reset sidecars for that frame. The mailbox is published only
    # after ALL three. Therefore compare each contiguous prefix
    # independently, do not insist all prefixes equal completed.
    require(all(v["valid_prefix_rows"]>=completed for v in scanned.values()),
            "A53 mailbox claimed completed frames with missing/invalid sidecars")
    require(all(v["valid_prefix_rows"]<=completed+1 for v in scanned.values()),
            "unexpectedly published more than one unacknowledged frame")
    checked=0
    timing_prev=None
    for i in range(completed):
        rawj=blobs["journal"][i*SIZE:(i+1)*SIZE]
        rawt=blobs["timing"][i*SIZE:(i+1)*SIZE]
        rawr=blobs["reset"][i*SIZE:(i+1)*SIZE]
        try:
            records.verify_journal(rawj,i,rows[i])
            timing=records.verify_timing(rawt,i,timing_prev)
            timing_prev=timing["after_journal_commit_CNTVCT"]
        except (records.RecordNoGo,KeyError,TypeError,ValueError) as e:
            raise PostmortemNoGo(
                f"frame {i} prefix differs from frozen scalar/FNV/timing: {e}") from e
        r=struct.unpack("<64I",rawr)
        require(
            r[4]==reset.MODE["once"] and r[5]==i+1 and
            r[6]==27 and r[7]==14155776 and
            (r[8],r[9],r[10],r[11],r[12])==(27,27,27,27,0) and
            r[19]==0 and (r[20],r[21])==(26,702),
            f"frame {i} reset-sidecar original unprotected once counter mismatch")
        require((r[13] | (r[14]<<32))==timing["CNTFRQ_EL0_hz"],
                f"frame {i} reset/clock counter frequency drift")
        ticks=r[15] | (r[16]<<32)
        require(0<ticks<=timing["phase_counter_ticks"][0],
                f"frame {i} reset ticks exceed measured original service phase0")
        checked+=1
    stage_file=evidence/"stage.txt"
    stage=read(stage_file).decode("utf-8","replace").strip() if stage_file.exists() else None
    progress_file=cap/"progress_state.txt"
    progress=(read(progress_file).decode("utf-8","replace") if progress_file.exists()
              else None)
    info={
        "schema":SCHEMA,
        "original_failed_evidence_dir":str(evidence),
        "failure_mailbox":mail,
        "original_frozen_full1024_scalar_oracle_sha256":pinned.ORIGINAL_FULL1024_ORACLE_SHA,
        "three_saved_full1024_256KiB_sidecars":scanned,
        "contiguous_neural_FNV_spikes_and_reset_receipts_verified_before_failure":checked,
        "fault_is_original_A53_terminal_failure_not_host_poll_timeout":True,
        "postrun_27_backup_readbacks_available_or_verified":False,
        "physical_1024_complete_pass":False,
        "hardware_backup_immutability_proven":False,
        "A53_FPD128_owner_only_from_original_gated_transcript_not_rechecked":True,
        "new_JTAG_OR_board_contact":False,
        "source_stage_file":stage,
        "last_host_progress_snapshot":progress,
        "preserve_failure_raw_capture_and_reboot":True,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }
    with out.open("x",encoding="utf-8") as fd:
        json.dump(info,fd,indent=2,sort_keys=True)
        fd.write("\n")
    return info

def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--oracle",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        data=examine(args.evidence,args.oracle,args.out)
    except (PostmortemNoGo,ValueError,TypeError,KeyError,OSError) as e:
        print("P08_B45_FULL1024_FAILURE_POSTMORTEM_NO_GO="+str(e),
              file=sys.stderr,flush=True)
        return 3
    m=data["failure_mailbox"]
    print("P08_B45_FULL1024_REAL_A53_TERMINAL_FAILURE_CONFIRMED=1")
    print("P08_B45_FULL1024_FAILED_FRAME="+str(m["failing_frame_ordinal"]))
    print("P08_B45_FULL1024_FAULT_CODE="+str(m["fault_code"]))
    print("P08_B45_FULL1024_FAULT_STAGE="+m["fault_stage"])
    print("P08_B45_FULL1024_COMPLETED_IMAGES="+str(m["completed_frames_mailbox"]))
    print("P08_B45_FULL1024_FROZEN_SCALAR_FNV_PREFIX_VERIFIED="+str(
        data["contiguous_neural_FNV_spikes_and_reset_receipts_verified_before_failure"]))
    print("P08_B45_FULL1024_POSTBACKUP_PROVEN=0")
    print("P08_B45_FULL1024_SUCCESS_CLAIM=0")
    print("P08_B45_FULL1024_OFFLINE_POSTMORTEM="+str(args.out))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
