"""B4.5 signed four-report latency synthesis and 1024 raw A53 phase replay.

All synthetic sources; NO KV260 or JTAG. Both genuine optimized modes
must pass scalar/FNV, all27 backup equality and exact input SHA pins.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b45_full1024_latency_synthesis as syn

HZ=99_999_001
COPIED=14155776

def checksum(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()
def writejson(p:Path,obj)->None:
    p.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
def pack(w):
    w[63]=syn.timing.DONE
    v=struct.pack("<64I",*w)
    w[61]=zlib.crc32(v[:244])
    return struct.pack("<64I",*w)
def sidecars(root:Path,mode:str)->tuple[dict,dict]:
    capture=root/"performance1024_capture"
    capture.mkdir(parents=True)
    timer=bytearray()
    prof=bytearray()
    start=1_000_000_000
    vals=[]
    for index in range(1024):
        # 26-tick mixed software+PL interval intentionally dominates.
        six=[880000,1850000,22700000,693500000+(index%7)*1000,120,2553000]
        total=sum(six)
        w=[0]*64
        w[0:4]=[syn.timing.TIMING_MAGIC,1,index,syn.timing.PASS]
        w[4]=HZ
        w[6],w[7]=start&0xffffffff,start>>32
        committed=start+total
        w[8],w[9]=committed&0xffffffff,committed>>32
        w[10],w[11]=total&0xffffffff,total>>32
        for j,v in enumerate(six):
            w[12+2*j]=v
        timer.extend(pack(w))
        start=committed+1_000
        r=[0]*64
        r[0:4]=[syn.reset.MAGIC[mode],1,index,syn.reset.PASS]
        r[4]=syn.reset.MODE[mode]
        r[5]=index+1
        r[6]=27
        r[7]=COPIED
        for j in (8,9,10,11):
            r[j]=27 if mode=="once" else 0
        r[13]=HZ
        r[15]=876700 if mode=="once" else 873200
        r[17]=2_000_000 if mode=="once" else 1000
        r[20]=26
        r[21]=702
        prof.extend(pack(r))
        if index<1023:
            vals.append(total*1000/HZ)
    tp=capture/"timing1024_physical.bin"
    rp=capture/"reset_profile1024_physical.bin"
    tp.write_bytes(timer)
    rp.write_bytes(prof)
    rsummary=syn.reset.audit(bytes(prof),mode=mode,expected_rows=1024,
                             observed_hz=HZ,require_protection=False)
    return {
        "schema":"p08-b45-unprotected-full1024-independent-real-jtag-v1",
        "experiment":mode,
        "new_real_JTAG_A53_halt_P03_programming_six_original_DDR_sources_readback":True,
        "new_all_1024_original_classifier_spikes_26tick_FNV_equal_scalar":True,
        "new_all_1024_A53_timing_and_reset_profiles_valid":True,
        "new_all_27_post_run_backup_records_identical_to_original":True,
        "last_trace_ordinal_1023_excluded_from_ordinary_performance":True,
        "one_unprotected_session_descriptive_only":True,
        "hardware_DDR_backup_protection_proven":False,
        "transient_backup_mutation_excluded":False,
        "original_OFFICIAL_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "original_complete1024_scalar_SHA256":syn.ORACLE_SHA,
        "prior_accepted_original_B4_1024_physical_sha256":syn.ORIGINAL_B4_SHA,
        "prior_accepted_original_B44_single_session_timing_sha256":
            syn.SHA["original_service"],
        "new_original_backup_per_core_sha256":{str(j):"a"*64 for j in range(27)},
        "timing_sha256":checksum(tp),
        "reset_sidecar_sha256":checksum(rp),
        "actual_A53_CNTFRQ_hz":HZ,
        "reset_descriptive":rsummary,
        "whole_image_service_descriptive_1023":syn.summary(vals),
    },rsummary

@pytest.fixture
def signed_inputs(tmp_path,monkeypatch):
    a=tmp_path/"original_service.json"
    b=tmp_path/"original_reset.json"
    once=tmp_path/"once.json"
    unchecked=tmp_path/"unchecked.json"
    c=tmp_path/"once_capture"
    d=tmp_path/"unchecked_capture"
    x={
        "schema":"p08-b4-4-original-full1024-single-physical-session-timing-descriptive-v1",
        "ordinary_frame_count":1023,
        "full_original_frame_count":1024,
        "service_scope":"original_full_A53_image_service_entry_to_after_journal_commit_excluding_timing_sidecar_and_setup",
        "independent_physical_full1024_report_sha256":syn.ORIGINAL_B4_SHA,
        "full1024_original_scalar_oracle_sha256":syn.ORACLE_SHA,
        "ordinary_complete_service":{
            "n":1023,"median_ms":13034.111500773894,
            "p95_nearest_rank_ms":13167.109029419204,
        },
    }
    y={
        "schema":"p08-b44-original1024-independent-physical-reset-profile-jtag-v1",
        "first_original_1024_B4_2_independent_report_sha256":syn.ORIGINAL_B4_SHA,
        "accepted_original_1023_B4_4_timing_report_sha256":syn.SHA["original_service"],
        "original_1024_scalar_oracle_sha256":syn.ORACLE_SHA,
        "one_genuine_1024_physical_profile_session_numerical_equivalence_accepted":True,
        "all_1024_new_27core_reset_profiles_sha_copy_cache_crc_and_clock_valid":True,
        "new_five_phase_timer_instrumentation_changes_execution_cost":True,
        "new_1023_ordinary_reset_profile_descriptive":{
            "n_ordinary":1023,
            "ordinary_reset_service":{
                "n":1023,"median_ms":5826.767549,
                "p95_nearest_rank_ms":5826.881051,
            },
        },
    }
    writejson(a,x);writejson(b,y)
    od,_=sidecars(c,"once")
    ud,_=sidecars(d,"unchecked")
    writejson(once,od);writejson(unchecked,ud)
    for key,path in (("original_service",a),("original_reset",b),
                     ("once",once),("unchecked",unchecked)):
        monkeypatch.setitem(syn.SHA,key,checksum(path))
    return a,b,once,unchecked,c,d,tmp_path/"review.json",tmp_path/"review.md"

def test_complete_original_synthetic_four_report_and_1024_A53_profile(signed_inputs):
    r=syn.analyze(*signed_inputs)
    assert r["schema"]==syn.SCHEMA
    assert r["baseline"]["reset_median_ms"]==5826.767549
    assert r["baseline"]["service_median_ms"]==13034.111500773894
    assert 650<r["descriptive_ratios"]["once"]["reset_ratio"]<680
    assert 1.7<r["descriptive_ratios"]["once"]["service_ratio"]<1.9
    for mode in ("once","unchecked"):
        obj=r["per_mode"][mode]
        assert obj["whole_service_descriptive"]["ordinary_frames"]==1023
        assert obj["dominant_measured_A53_phase"]=="all_26_ticks_702_dispatches_paging_routing"
        assert obj["1024_classifier_spike_FNV_and_27_backup_endpoints_verified"] is True
        assert obj["reset_descriptive"]["backing_backup_guard_provisioned_flag"]==0
    assert r["paired_randomized_repeated_session_speedup_proven"] is False
    assert r["hardware_or_JTAG_access_performed"] is False
    assert signed_inputs[-2].is_file() and signed_inputs[-1].is_file()
    assert "different" in signed_inputs[-1].read_text().lower()

def test_bad_original_evidence_hash_fails_closed(signed_inputs):
    a,*rest=signed_inputs
    a.write_text(a.read_text()+"\n")
    with pytest.raises(syn.SynthesisNoGo,match="report SHA drift"):
        syn.analyze(*signed_inputs)
    assert not signed_inputs[-2].exists()

def test_real_reset_sidecar_changed_after_independent_report_rejected(signed_inputs):
    t=signed_inputs[4]/"performance1024_capture"/"reset_profile1024_physical.bin"
    altered=bytearray(t.read_bytes())
    altered[300]^=0x20
    t.write_bytes(altered)
    with pytest.raises(syn.SynthesisNoGo,match="saved raw A53 capture hashes"):
        syn.analyze(*signed_inputs)
    assert not signed_inputs[-2].exists()

def test_false_protection_or_neural_claim_rejected(signed_inputs,monkeypatch):
    obj=signed_inputs[2]
    values=json.loads(obj.read_text())
    values["hardware_DDR_backup_protection_proven"]=True
    writejson(obj,values)
    monkeypatch.setitem(syn.SHA,"once",checksum(obj))
    with pytest.raises(syn.SynthesisNoGo,match="integrity and unprotected scope"):
        syn.analyze(*signed_inputs)

def test_sealed_output_noclobber_and_no_board_import(signed_inputs):
    out=signed_inputs[-2]
    out.write_text("DO_NOT_OVERWRITE")
    with pytest.raises(syn.SynthesisNoGo,match="no-overwrite"):
        syn.analyze(*signed_inputs)
    assert out.read_text()=="DO_NOT_OVERWRITE"
    src=(ROOT/"scripts"/"p08_b45_full1024_latency_synthesis.py").read_text()
    assert "import subprocess" not in src
    assert "xsdb " not in src
    assert "devmem " not in src
    assert "open_serial(" not in src
    assert "hardware_or_JTAG_access_performed" in src

def test_argparse_keeps_8_explicit_readonly_paths(tmp_path,monkeypatch,capsys):
    called=[]
    def fake(*args):
        called.append(args)
        raise syn.SynthesisNoGo("HOST_ONLY_SENTINEL")
    monkeypatch.setattr(syn,"analyze",fake)
    flags=[
        "--original-service","--original-profile",
        "--once-report","--unchecked-report",
        "--once-evidence","--unchecked-evidence",
        "--out","--markdown-out",
    ]
    args=[]
    for flag in flags:
        args.extend([flag,str(tmp_path/(flag.lstrip("-")+".data"))])
    assert syn.main(args)==3
    assert len(called)==1
    assert "HOST_ONLY_SENTINEL" in capsys.readouterr().err
