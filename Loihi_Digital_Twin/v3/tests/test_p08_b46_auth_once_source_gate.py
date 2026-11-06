"""P08-B4.6 A original vs B_AUTH_ONCE V2 source gate; PC ONLY synthetic tests."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b46_auth_once_source_gate as gate

def hashfile(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def writejson(p:Path,doc):
    p.write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n")

@pytest.fixture
def inputs(tmp_path,monkeypatch):
    aelf=tmp_path/"p08_a2_board.elf"
    aelf.write_bytes(b"synthetic-original-Track-A2.1-ELF")
    belf=tmp_path/"p08_b45_perf_once_full1024.elf"
    belf.write_bytes(
        gate.b45elf.IDENTITIES["once"]+
        b"\0synthetic-real-A53-terminal\0"+
        gate.b45elf.TERMINAL["once"])
    oracle=tmp_path/"b1024.json"
    frame_ledger=[
        {"frame":i,"TRAIN_source_index":i+50,"raw_pixels_sha256":hashlib.sha256(str(i).encode()).hexdigest(),
         "in_B_training_partition":False,"selected_trace":i==1023}
        for i in range(1024)
    ]
    writejson(oracle,{"count":1024,"official_MNIST_TEST":"SEALED_NOT_ACCESSED",
                      "frames":[{"ordinal":r["frame"],"TRAIN_source_index":r["TRAIN_source_index"],
                                 "raw_pixels_sha256":r["raw_pixels_sha256"]} for r in frame_ledger]})
    once=tmp_path/"once.json"
    writejson(once,{
        "schema":"p08-b45-unprotected-full1024-independent-real-jtag-v1",
        "experiment":"once",
        "genuine_new_mode_specific_A53_ELF_sha256":hashfile(belf),
        "original_complete1024_scalar_SHA256":hashfile(oracle),
        "new_all_1024_original_classifier_spikes_26tick_FNV_equal_scalar":True,
        "new_all_27_post_run_backup_records_identical_to_original":True,
        "hardware_DDR_backup_protection_proven":False,
        "original_OFFICIAL_MNIST_TEST":"SEALED_NOT_ACCESSED"})
    syn=tmp_path/"synthesis.json"
    writejson(syn,{
        "schema":"p08-b45-physical-cross-session-quantitative-synthesis-v1",
        "both_modes_neural_parity_and_original_backup_endpoints_pass":True,
        "hardware_or_JTAG_access_performed":False,
        "paired_randomized_repeated_session_speedup_proven":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "source_sha256":{
            "once":hashfile(once),
            "original_full1024_scalar_oracle":hashfile(oracle),
        }})
    monkeypatch.setattr(gate,"A_ELF_SHA",hashfile(aelf))
    monkeypatch.setattr(gate,"B_ELF_SHA",hashfile(belf))
    monkeypatch.setattr(gate,"B_ORACLE_SHA",hashfile(oracle))
    monkeypatch.setattr(gate,"B_ONCE_INDEPENDENT_SHA",hashfile(once))
    monkeypatch.setattr(gate,"B45_SYNTHESIS_SHA",hashfile(syn))
    def valid_B1(a_stage,train,frozen):
        return {
            "schema":"p08-b1-canonical-matched-a-stage-b24-train-audit-v1",
            "original_track_A_frame_count":1024,
            "original_frame_order_preserved":True,
            "B24_original_33_assets_verified":True,
            "B24_compiled_model_sha256":gate.b1.B24_COMPILED_SHA,
            "original_MNIST_TEST":"SEALED_NOT_ACCESSED",
            "frames":frame_ledger,
            "track_A_stage":{"original_A_manifest_sha256":"1"*64},
        }
    monkeypatch.setattr(gate.b1,"generate_report",valid_B1)
    stage=tmp_path/"stage";stage.mkdir()
    train=tmp_path/"train";train.mkdir()
    frozen=tmp_path/"frozen";frozen.mkdir()
    return [aelf,belf,stage,train,frozen,oracle,once,syn,tmp_path/"out.json"],frame_ledger

def test_A_vs_B_AUTH_ONCE_1024_source_and_exact_six_run_sheet(inputs):
    args,_=inputs
    obj=gate.audit(*args)
    assert obj["arm_B"]==gate.B_ARM
    assert obj["arm_A"]==gate.A_ARM
    assert obj["B_hardware_immutable_backup_write_protection_proven"] is False
    assert obj["B_original_full_SHA_every_image"] is False
    assert obj["identical_original_TRAIN_1024_source_index_and_raw_pixel_SHA"] is True
    assert [x["arm"] for x in obj["planned_six_independently_rebooted_sessions"]]==list(gate.ARM_ORDER)
    assert [x["pair"] for x in obj["planned_six_independently_rebooted_sessions"]]==[1,1,2,2,3,3]
    assert all(x["individual_physical_JTAG_permission_granted"] is False for x in
               obj["planned_six_independently_rebooted_sessions"])
    assert obj["six_new_physical_JTAG_runs_authorized"] is False
    assert obj["A_and_B_have_demonstrably_IDENTICAL_service_boundaries"] is False
    assert obj["official_MNIST_TEST"]=="SEALED_NOT_ACCESSED"
    assert args[-1].is_file()

def test_altered_source_pixel_identity_fails_closed(inputs):
    args,ledger=inputs
    ledger[903]["raw_pixels_sha256"]="0"*64
    with pytest.raises(gate.GateNoGo,match="pixel/order/source mismatch at image 903"):
        gate.audit(*args)
    assert not args[-1].exists()

def test_modified_B_signing_report_fails_closed(inputs):
    args,_=inputs
    args[6].write_text(args[6].read_text()+" ")
    with pytest.raises(gate.GateNoGo,match="signed source SHA drift"):
        gate.audit(*args)

def test_B_signing_report_cannot_claim_XMPU(inputs,monkeypatch):
    args,_=inputs
    once=json.loads(args[6].read_text())
    once["hardware_DDR_backup_protection_proven"]=True
    writejson(args[6],once)
    monkeypatch.setattr(gate,"B_ONCE_INDEPENDENT_SHA",hashfile(args[6]))
    with pytest.raises(gate.GateNoGo,match="signed V2 once"):
        gate.audit(*args)

def test_B_unchanged_1024_oracle_frozen_test_seal_required(inputs,monkeypatch):
    args,_=inputs
    b=json.loads(args[5].read_text())
    b["official_MNIST_TEST"]="USED"
    writejson(args[5],b)
    monkeypatch.setattr(gate,"B_ORACLE_SHA",hashfile(args[5]))
    with pytest.raises(gate.GateNoGo,match="TEST seal"):
        gate.audit(*args)

def test_A_and_B_identical_model_not_claimed_and_B_unchecked_rejected(inputs):
    args,_=inputs
    bad=gate.b45elf.IDENTITIES["unchecked"]+gate.b45elf.TERMINAL["once"]
    args[1].write_bytes(bad)
    with pytest.raises(gate.GateNoGo,match="real accepted V2 authenticate-once"):
        gate.audit(*args)

def test_no_existing_output_overwrite(inputs):
    args,_=inputs
    args[-1].write_text("KEEP")
    with pytest.raises(gate.GateNoGo,match="no-overwrite"):
        gate.audit(*args)
    assert args[-1].read_text()=="KEEP"

def test_real_source_has_no_xsdb_subprocess_or_execute_permission():
    src=(ROOT/"scripts"/"p08_b46_auth_once_source_gate.py").read_text()
    assert "import subprocess" not in src
    assert "subprocess.run" not in src
    assert "xsdb " not in src
    assert "devmem " not in src
    assert "six_new_physical_JTAG_runs_authorized" in src
    assert "B_AUTH_ONCE" in src and "P08-B4.5" in src
    assert "B45_SYNTHESIS_SHA=" in src
