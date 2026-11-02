"""P08-B2.4 independent original scalar 16 / untrusted physical-file gates."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import struct
import sys
import zlib

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b2_4_scalar_first16 as oracle
import p08_b2_4_verify_untrusted_first16 as checker


def fake_ref(i):
    return {
        "ordinal":i,
        "TRAIN_source_index":37384+i,
        "raw_pixels_sha256":hashlib.sha256(bytes([i])*784).hexdigest(),
        "original_27core_ingress_sha256":hashlib.sha256(bytes([i+1])*123216).hexdigest(),
        "expected_prediction":i%10,
        "expected_external_current":10+i,
        "expected_source_spikes":50+i,
        "expected_captured_packets":100+i,
        "expected_inserted_next":100+i,
        "expected_output_spike_counts":[i+j for j in range(10)],
        "expected_all_26_ticks_1010_neuron_FNV64":f"0x{(1000+i):016X}",
        "expected_per_tick_neuron_FNV64":[f"0x{t:016X}" for t in range(26)],
        "expected_dispatches":702,"expected_barriers":26,
        "expected_trace_compartments_per_tick":1010,
    }

def serialize(words):
    words[61]=zlib.crc32(struct.pack("<61I",*words[:61]))
    words[63]=checker.DONE
    return struct.pack("<64I",*words)

def journal(i,ref):
    w=[0]*64
    w[0:10]=[checker.JOURNAL_MAGIC,1,i,checker.PASS,i+1,
              0x464D3442,ref["expected_prediction"],702,26,1010]
    w[10:17]=[ref["expected_external_current"],
              ref["expected_source_spikes"],
              ref["expected_captured_packets"],ref["expected_inserted_next"],
              702,699,3]
    w[17:19]=[1000+i,0]
    w[19:23]=[702*438272,0,702*106496,0]
    w[23]=123216
    w[24:34]=ref["expected_output_spike_counts"]
    w[34:42]=struct.unpack("<8I",bytes.fromhex(ref["raw_pixels_sha256"]))
    w[42:50]=struct.unpack("<8I",bytes.fromhex(ref["original_27core_ingress_sha256"]))
    return serialize(w)

def timing(i,hz=99999001):
    w=[0]*64
    w[:4]=[checker.TIMING_MAGIC,1,i,checker.PASS]
    w[4]=hz
    w[6]=1000+i*10000
    w[8]=9500+i*10000
    w[10]=8500
    w[12:24]=[100,0,200,0,300,0,7500,0,200,0,200,0]
    return serialize(w)

def mailbox(count=16,hz=99999001):
    w=[0]*64
    w[:6]=[checker.MAILBOX_MAGIC,1,checker.PASS,count-1,0,count]
    w[6]=hz
    w[8:14]=[count,702,26,0,0,0]
    w[63]=checker.DONE
    return struct.pack("<64I",*w)

def sample_oracle():
    return {
        "schema":oracle.SCHEMA,
        "count":16,
        "original_known_three_B23_witness_reproduced":True,
        "original_p08_b2_1_raw_pool_sha256":oracle.RAW_POOL_SHA,
        "operator_genuine_new_image_only_elf_sha256":oracle.B23_ELF_SHA,
        "original_compiled_sha256":
            "02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a",
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "frames":[fake_ref(i) for i in range(16)],
    }

def test_source_files_do_not_contact_board():
    for script in (ROOT/"scripts/p08_b2_4_scalar_first16.py",
                   ROOT/"scripts/p08_b2_4_verify_untrusted_first16.py"):
        data=script.read_text()
        assert "import xsdb" not in data
        assert "subprocess.run" not in data
        assert "standalone\x00" not in data

def test_first16_correct_synthetic_journal_parity_is_only_unverified(tmp_path):
    refs=sample_oracle()
    source=tmp_path/"untrusted_oracle.json"
    source.write_text(json.dumps(refs))
    jr=tmp_path/"untrusted_journal.bin"
    jr.write_bytes(b"".join(journal(i,ref) for i,ref in enumerate(refs["frames"])))
    ts=tmp_path/"untrusted_timing.bin"
    ts.write_bytes(b"".join(timing(i) for i in range(16)))
    mb=tmp_path/"untrusted_mailbox.bin"
    mb.write_bytes(mailbox())
    report=checker.verify(source,jr,ts,mb,tmp_path/"check.json")
    assert report["verified_frames"]==16
    assert report["all_16_independent_scalar_counters_match"] is True
    assert report["authenticated_real_JTAG_same_session_readback"] is False
    assert report["actual_physical_KV260_neural_parity_proven"] is False
    assert report["timing_frames"][3]["complete_service_counter_ticks"]==8500
    assert report["neural_frames"][0]["page_in_bytes"]==702*438272

def test_single_corrupt_journal_crc_denied():
    a=bytearray(journal(0,fake_ref(0)))
    a[7*4]^=0x01
    with pytest.raises(checker.RecordNoGo):
        checker.verify_journal(bytes(a),0,fake_ref(0))

@pytest.mark.parametrize("field,newvalue",[
    (4,2),(5,0),(6,5),(7,701),(8,25),(9,1000),
    (10,11),(11,88),(12,90),(13,90),(14,701),(15,698),
    (16,4),(17,500),(23,16),(24,7),(34,1),(42,1),(60,1)
])
def test_valid_crc_but_numerically_different_must_fail(field,newvalue):
    w=list(struct.unpack("<64I",journal(0,fake_ref(0))))
    w[field]=newvalue
    with pytest.raises(checker.RecordNoGo):
        checker.verify_journal(serialize(w),0,fake_ref(0))

def test_clock_backtrack_or_wrong_additive_phases_denied():
    w=list(struct.unpack("<64I",timing(0)))
    w[8]=999
    with pytest.raises(checker.RecordNoGo):
        checker.verify_timing(serialize(w),0,None)
    w=list(struct.unpack("<64I",timing(0)))
    w[12]=9000
    with pytest.raises(checker.RecordNoGo):
        checker.verify_timing(serialize(w),0,None)
    with pytest.raises(checker.RecordNoGo):
        checker.verify_timing(timing(1),1,99999999)

def test_unverified_terminal_16_gate_requires_exact_count_and_result():
    checker.verify_mailbox(mailbox(),16)
    bad=bytearray(mailbox())
    bad[5*4]=15
    with pytest.raises(checker.RecordNoGo):
        checker.verify_mailbox(bytes(bad),16)
    bad=bytearray(mailbox())
    bad[2*4]=0
    with pytest.raises(checker.RecordNoGo):
        checker.verify_mailbox(bytes(bad),16)

def test_original_operator_artifact_sha_pins_frozen():
    assert oracle.B2_MANIFEST_SHA=="996d48b1d4e83ec2433d445a4be37cff8ef50b599d07db23c165f1be10337e6e"
    assert oracle.B23_ELF_SHA=="0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1"
    assert oracle.B23_MAP_SHA=="f7ce75a736b6b093066b8df09a8b02aaa41b490fd48c36c23151b4ac22125efc"
    assert oracle.B2_INGRESS_LEDGER_SHA=="5f21aa4e64f31918272b4d7ef84830bc309c6c205744f6735cec4bc69a1a719e"

def test_negative_reference_incorrect_source_wont_claim_physical(tmp_path):
    r=sample_oracle()
    r["operator_genuine_new_image_only_elf_sha256"]="0"*64
    src=tmp_path/"bad.json"
    src.write_text(json.dumps(r))
    jr=tmp_path/"j.bin"
    jr.write_bytes(b"".join(journal(i,ref) for i,ref in enumerate(r["frames"])))
    tt=tmp_path/"t.bin"
    tt.write_bytes(b"".join(timing(i) for i in range(16)))
    mb=tmp_path/"mb.bin";mb.write_bytes(mailbox())
    with pytest.raises(checker.RecordNoGo):
        checker.verify(src,jr,tt,mb,tmp_path/"denied.json")
