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


# Rebuilt genuine-A2.1 branch: synthesize an ELF64/AArch64 binary and
# exact frozen-source Vitis staged byte copies. These are ONLY tests.
# No synthetic result may be treated as genuine operator firmware.
import shutil
import struct

@pytest.fixture
def rebuilt_A21(tmp_path,monkeypatch):
    build=tmp_path/"rebuilt"
    stage=build/"source"
    stage.mkdir(parents=True)
    (build/"vitis_workspace").mkdir()
    blob=bytearray(128+len(gate.rebuilt.ELF_ID))
    blob[:6]=b"\x7fELF\x02\x01"
    struct.pack_into("<HH",blob,16,2,183)
    struct.pack_into("<Q",blob,32,64)
    struct.pack_into("<HH",blob,54,56,1)
    struct.pack_into("<IIQQQQQQ",blob,64,1,5,128,0x20000000,0x20000000,
                     len(gate.rebuilt.ELF_ID),len(gate.rebuilt.ELF_ID),4096)
    blob[128:]=gate.rebuilt.ELF_ID
    elf=build/gate.rebuilt.A_BUILD_REL
    elf.write_bytes(blob)
    xsa=tmp_path/"p03_2_ps_mmio.xsa"
    xsa.write_bytes(b"synthetic-P03.2c-XSA")
    monkeypatch.setattr(gate.rebuilt,"NEW_A21_SHA",hashfile(elf))
    monkeypatch.setattr(gate.rebuilt,"P03_XSA_SHA",hashfile(xsa))
    monkeypatch.setattr(gate.rebuilt,"VOLATILE_PREFIXES",())
    lines=[
        "P08_A2_1_XSA_SHA256="+hashfile(xsa),
        "P08_A2_1_ELF="+str(elf),
        "P08_A2_1_ELF_SHA256="+hashfile(elf),
        "P08_A2_1_VITIS_BUILD_PASS=1",
        "P08_A2_1_KV260_LATENCY=NOT_RUN",
    ]
    (build/"build_identity.txt").write_text("\n".join(lines)+"\n")
    (build/"vitis_build.log").write_text("P08_A2_A53_VITIS_BUILD_PASS=1\n")
    (build/"elf_program_headers.txt").write_text(" LOAD synthetic AARCH64\n")
    for relative,names in gate.rebuilt.SOURCES.items():
        for name in names:
            original=ROOT/relative/name
            dest=stage/name
            shutil.copyfile(original,dest)
            if relative=="software/p07/include":
                dest=(stage/"include"/name)
                dest.parent.mkdir(exist_ok=True)
                shutil.copyfile(original,dest)
    # Actual Vitis builder imports all originals into the standalone
    # app/src and duplicates P07 headers under app/src/include.
    shutil.copytree(stage,build/"vitis_workspace"/"p08_a2_board"/"src")
    report=tmp_path/"rebuilt_pc_admission.json"
    return build,elf,xsa,report


def test_distinct_rebuilt_A21_original_frozen_source_host_pass(rebuilt_A21):
    build,elf,xsa,report=rebuilt_A21
    outcome=gate.rebuilt.attest(build,xsa,report)
    assert outcome["schema"]==gate.rebuilt.SCHEMA
    assert outcome["original_A2_1_source_files_byte_exact_to_rebuilt_stage"] is True
    assert outcome["Vitis_actual_imported_A2_1_C_and_header_source_byte_exact_to_stage"] is True
    assert outcome["new_A2_1_candidate_KV260_1024_neural_oracle_acceptance"] is False
    assert outcome["historical_original_A2_1_ELF_recovered"] is False
    assert outcome["ELF_header_and_PT_LOAD_checks"]["original_64MiB_DDR_disjoint"] is True
    assert len(outcome["source_Git_sha256_checks"])==len(
        [name for names in gate.rebuilt.SOURCES.values() for name in names])
    assert report.is_file()


def test_B46_explicit_candidate_source_manifest_but_NO_new_JTAG(inputs,rebuilt_A21):
    args,_=inputs
    build,elf,xsa,report=rebuilt_A21
    gate.rebuilt.attest(build,xsa,report)
    args[0]=elf
    out=gate.audit(*args,a_rebuilt_admission=report,a_rebuilt_xsa=xsa)
    assert out["schema"]==gate.REBUILT_SCHEMA
    assert out["selected_A_elf_provenance"]=="REBUILT_A21_NEW_SHA_PC_VALIDATED_PHYSICAL_PENDING"
    assert out["original_A_image_timing_elf_sha256"]==gate.A_ELF_SHA
    assert out["selected_A_real_elf_sha256"]==gate.rebuilt.NEW_A21_SHA
    assert out["new_A_rebuilt_candidate_KV260_neural_parity_and_timing_reaccepted"] is False
    assert out["six_new_physical_JTAG_runs_authorized"] is False
    assert out["arm_A"].startswith("A_REBUILT_A21_CANDIDATE")
    assert out["planned_six_independently_rebooted_sessions"][0]["arm"]==out["arm_A"]


def test_rebuilt_SHA_cannot_replace_historical_A21_default_gate(inputs,rebuilt_A21):
    args,_=inputs
    _,elf,_,_=rebuilt_A21
    args[0]=elf
    with pytest.raises(gate.GateNoGo,match="original accepted A2.1 ELF SHA"):
        gate.audit(*args)
    assert not args[-1].exists()


def test_signed_candidate_report_mutation_is_reaudited(inputs,rebuilt_A21):
    args,_=inputs
    build,elf,xsa,report=rebuilt_A21
    gate.rebuilt.attest(build,xsa,report)
    args[0]=elf
    body=json.loads(report.read_text())
    body["new_A2_1_candidate_KV260_1024_neural_oracle_acceptance"]=True
    writejson(report,body)
    with pytest.raises(gate.GateNoGo,match="manifest differs"):
        gate.audit(*args,a_rebuilt_admission=report,a_rebuilt_xsa=xsa)
    assert not args[-1].exists()


def test_built_original_source_mutation_detected_even_with_old_good_report(inputs,rebuilt_A21):
    args,_=inputs
    build,elf,xsa,report=rebuilt_A21
    gate.rebuilt.attest(build,xsa,report)
    args[0]=elf
    staged=build/"source"/"p08_a2_board.c"
    staged.write_bytes(staged.read_bytes()+b"\n/* TAMPER */")
    with pytest.raises(gate.rebuilt.CandidateNoGo,match="staged source differs"):
        gate.audit(*args,a_rebuilt_admission=report,a_rebuilt_xsa=xsa)
    assert not args[-1].exists()


def test_rebuilt_ELF_PT_LOAD_overlap_DENIED(rebuilt_A21,monkeypatch):
    build,elf,xsa,report=rebuilt_A21
    bad=bytearray(elf.read_bytes())
    # ELF64 program header p_vaddr offset = e_phoff(64)+16
    struct.pack_into("<Q",bad,80,0x40000000)
    elf.write_bytes(bad)
    monkeypatch.setattr(gate.rebuilt,"NEW_A21_SHA",hashfile(elf))
    # Match builder metadata updated just to prove independent header check:
    content=(build/"build_identity.txt").read_text()
    content=content.replace(
        next(x for x in content.splitlines() if x.startswith("P08_A2_1_ELF_SHA256=")),
        "P08_A2_1_ELF_SHA256="+hashfile(elf))
    (build/"build_identity.txt").write_text(content)
    with pytest.raises(gate.rebuilt.CandidateNoGo,match="PT_LOAD overlaps"):
        gate.rebuilt.attest(build,xsa,report)
    assert not report.exists()


def test_candidate_FPD_XSA_wrong_even_if_ELF_valid(rebuilt_A21):
    build,elf,xsa,report=rebuilt_A21
    xsa.write_bytes(xsa.read_bytes()+b"changed")
    with pytest.raises(gate.rebuilt.CandidateNoGo,match="hardware XSA SHA"):
        gate.rebuilt.attest(build,xsa,report)
    assert not report.exists()


def test_rebuilt_candidate_CANNOT_lie_or_write_to_temp_production(rebuilt_A21,monkeypatch):
    build,_,xsa,report=rebuilt_A21
    monkeypatch.setattr(gate.rebuilt,"VOLATILE_PREFIXES",(Path("/tmp"),))
    with pytest.raises(gate.rebuilt.CandidateNoGo,match="volatile"):
        gate.rebuilt.attest(build,xsa,report)
    assert not report.exists()


def test_new_rebuilt_candidate_no_overwrite_and_no_hardware(rebuilt_A21):
    build,elf,xsa,report=rebuilt_A21
    report.write_text("DO_NOT_OVERWRITE")
    with pytest.raises(gate.rebuilt.CandidateNoGo,match="no-overwrite"):
        gate.rebuilt.attest(build,xsa,report)
    assert report.read_text()=="DO_NOT_OVERWRITE"
    src=(ROOT/"scripts"/"p08_b46_a21_rebuild_admission.py").read_text()
    assert "import subprocess" not in src
    assert "xsdb " not in src
    assert "import vitis" not in src


def test_rebuilt_candidate_Vitis_imported_C_drift_detected_even_when_build_stage_exact(rebuilt_A21):
    build,_,xsa,report=rebuilt_A21
    import_source=build/"vitis_workspace/p08_a2_board/src/p08_a2_board.c"
    import_source.write_bytes(import_source.read_bytes()+b"\n/* VITIS IMPORT TAMPER */")
    with pytest.raises(gate.rebuilt.CandidateNoGo,match="Vitis imported app C/header"):
        gate.rebuilt.attest(build,xsa,report)
    assert not report.exists()


def test_rebuilt_candidate_Vitis_imported_extra_C_denied(rebuilt_A21):
    build,_,xsa,report=rebuilt_A21
    extra=build/"vitis_workspace/p08_a2_board/src/rogue.c"
    extra.write_bytes(b"int rogue(void){return 1;}")
    with pytest.raises(gate.rebuilt.CandidateNoGo,match="C-file set"):
        gate.rebuilt.attest(build,xsa,report)
    assert not report.exists()
