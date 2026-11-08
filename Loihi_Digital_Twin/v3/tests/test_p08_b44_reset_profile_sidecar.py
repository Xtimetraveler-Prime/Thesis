"""P08-B4.4.2 1024 experimental reset-sidecar CRC/no-JTAG negative CI."""
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
import p08_b44_reset_profile_sidecar as p

HZ=99999001

def make_row(i:int,*,sha_counts:int=27,other:int=40)->bytes:
    w=[0]*64
    w[:9]=[p.MAGIC,p.VERSION,i,p.PASS,i+1,27,p.COPIED,
           sha_counts,27]
    w[9]=HZ
    # one dummy deterministic 27-context reference with 5 disjoint phases
    phases=[20+i%3,220,15,30,120]
    total=sum(phases)+other
    w[11]=total
    for j,v in enumerate(phases):
        w[13+2*j]=v
    w[23]=other
    w[61]=zlib.crc32(struct.pack("<61I",*w[:61]))
    w[63]=p.DONE
    return struct.pack("<64I",*w)

@pytest.fixture
def synthetic_1024():
    return b"".join(make_row(i) for i in range(1024))

def test_all_original_1024_structural_only_profile_and_1023_scope(synthetic_1024,tmp_path):
    out=p.audit(synthetic_1024,HZ)
    assert out["schema"]==p.SCHEMA
    assert out["n_capture_rows"]==1024
    assert out["n_ordinary"]==1023
    assert out["selected_trace_ordinal_excluded"]==1023
    assert out["selected_trace_1023"]["ordinal"]==1023
    assert out["ordinary_reset_service"]["median_ticks"]>0
    assert len(out["ordinary_five_reset_subphases"])==5
    assert out["actual_KV260_physical_provenance_independently_proven"] is False
    assert out["full1024_original_FNV_classifier_parity_proven"] is False
    assert out["accepted_multisession_A_v_B_comparison"] is False
    shares=sum(x["share_of_total_reset_ticks_pct"]
               for x in out["ordinary_five_reset_subphases"].values())
    shares+=out["ordinary_unattributed_counter_overhead"][
        "share_of_total_reset_ticks_pct"]
    assert shares==pytest.approx(100)
    filepath=tmp_path/"new_synthetic_profile.bin"
    filepath.write_bytes(synthetic_1024)
    output=tmp_path/"fresh.json"
    assert p.main(["--profile",str(filepath),"--actual-hz",str(HZ),
                   "--out",str(output)])==0
    assert output.is_file()
    assert p.main(["--profile",str(filepath),"--actual-hz",str(HZ),
                   "--out",str(output)])==3

@pytest.mark.parametrize("change",[
    "partial","wrong_crc","wrong_source_count","wrong_generation",
    "nonadditive","wrong_clock","missing_done","malformed_terminal",
    "reserved_nonzero","row_reorder","invalid_magic"
])
def test_all_1024_reset_profile_fail_closed(synthetic_1024,change):
    raw=bytearray(synthetic_1024)
    if change=="partial":
        raw=raw[:-256]
    else:
        pos=800*256
        words=list(struct.unpack("<64I",raw[pos:pos+256]))
        if change=="wrong_crc":
            raw[pos+20]^=0x80
        else:
            if change=="wrong_source_count":words[7]=26
            if change=="wrong_generation":words[4]=800
            if change=="nonadditive":words[13]=10000
            if change=="wrong_clock":words[9]=100000000
            if change=="missing_done":words[63]=0
            if change=="malformed_terminal":words[3]=p.FAIL if hasattr(p,"FAIL") else 0
            if change=="reserved_nonzero":words[25]=1
            if change=="row_reorder":words[2]=801
            if change=="invalid_magic":words[0]=0
            words[61]=zlib.crc32(struct.pack("<61I",*words[:61]))
            raw[pos:pos+256]=struct.pack("<64I",*words)
    with pytest.raises(p.ProfileNoGo):
        p.audit(bytes(raw),HZ)

def test_distinct_a53_profile_source_does_not_rewrite_original():
    new=(ROOT/"software/p08/p08_b44_profile_full1024_a53.c").read_text()
    old=(ROOT/"software/p08/p08_b2_3_image_only_a53.c").read_text()
    assert 'P08_B2_3_ORIGINAL_27CORE_1024_IMAGE_ONLY_A53_V1' in old
    assert 'P08_B44_ORIGINAL_27CORE_RESET_PROFILE_1024_A53_V1' in new
    assert 'P08_B44_ORIGINAL_27CORE_RESET_PROFILE_1024_A53_V1' not in old
    assert "p08_b44_profile_reset_image(" in new
    assert "p08_b2_reset_image(&reset_state,&reset_receipt)" in old
    assert "p08_b44_profile_reset_image(" not in old
    assert "#define B44_PROFILE_BASE UINT32_C(0x42400000)" in new
    assert "commit_reset_profile(index,&reset_profile,cntfrq)" in new
    assert "B44_PROFILE_BYTES==262144u" in new
    assert "B44_PROFILE_END<=B23_BACKUP" in new
    assert "P08_B44_RESET_PROFILE_1024_TERMINAL_DONE=1" in new
    assert 'P08_B2_3_IMAGE_ONLY_1024_TERMINAL_DONE=1' in old
    assert 'P08_B2_3_IMAGE_ONLY_1024_TERMINAL_DONE=1' not in new
    for needed in ("P08_B44_SOURCE_CACHE_INVALIDATE","P08_B44_SOURCE_SHA256",
                   "P08_B44_MUTABLE_MEMCPY","P08_B44_MUTABLE_CACHE_CLEAN_INVALIDATE",
                   "P08_B44_MUTABLE_SHA256"):
        assert needed in (ROOT/"software/p08/p08_b4_4_profile_reset.c").read_text()
