"""P07-B.5.3 real B5 launcher and independent physical bytewise verifier safety.

Host-only negative tests: never emulate or invent physical hardware evidence,
never call XSDB, and never mark physical equality without original readbacks.
"""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b5_raw_physical_capture as runner
import p07_b5_raw_physical_verify as verifier
import p07_b5_raw_trace_offline_admission as gate

def good_dummy_mailbox():
    w=[0]*64
    w[0]=verifier.B5_MAGIC
    w[1]=1
    w[2]=0x600D600D
    w[63]=0xC0DEF00D
    w[12]=0x464D3442
    w[13]=26
    w[14]=w[15]=702
    w[16]=699
    w[17]=3
    w[18]=31512
    w[19]=1514
    w[20]=w[21]=1489
    w[22]=1
    w[23]=21384
    w[24]=1010
    w[25]=0x4D6E64AD
    w[26]=0xB59CA859
    w[27]=702*438272
    w[28]=0
    w[29]=(702*106496) & 0xFFFFFFFF
    w[30]=(702*106496) >> 32
    w[31]=10000
    w[33]=25
    w[46]=702
    w[47]=0x42354331
    w[48]=w[49]=w[50]=0
    w[51]=26260
    w[52]=210080
    w[53]=0x42000000
    w[54]=0x420CD280
    w[55]=0
    w[56]=1
    return struct.pack("<64I",*w)

def test_distinct_new_B5_raw_256B_mailbox_structural_accounting_valid():
    msg=verifier.verify_b5_mailbox(good_dummy_mailbox(),expected_class=1)
    assert msg["schema"]=="p07-b5-original-raw-a53-26tick-physical-mailbox-v1"
    assert msg["B5_capture_finished"] is True
    assert msg["B5_capture_neurons"]==26260
    assert msg["B5_trace_words"]==210080
    assert msg["all_26_tick_trace_hash"]=="0xB59CA8594D6E64AD"
    assert msg["readout_spike_counts"]==[0,25,0,0,0,0,0,0,0,0]
    assert msg["physical_dispatches"]==702

@pytest.mark.parametrize("word,wrong",[
    (0,0x42344D31), # old V3 mailbox explicitly rejected
    (2,0),          # not PASS
    (63,0),         # not terminal
    (13,25),        # no 26th barrier
    (14,701),       # no 702nd dispatch
    (22,2),         # wrong digit
    (47,0),         # missing new raw recorder magic
    (48,0xFFFFFFFF), # recorder error
    (50,0xFFFFFFFF), # not final
    (51,26259),     # omitted one neuron
    (52,210079),    # raw length wrong
    (53,0x40000000),# physical region not approved candidate
    (54,0x420CD27F),# wrong exclusive end
    (55,1),         # capture fault
    (56,0),         # capture not complete
    (60,0x23),      # failure-only snapshot polluted success
])
def test_b5_mailbox_fails_closed_on_tampering(word,wrong):
    vals=list(struct.unpack("<64I",good_dummy_mailbox()))
    vals[word]=wrong
    with pytest.raises(ValueError):
        verifier.verify_b5_mailbox(struct.pack("<64I",*vals),expected_class=1)

def test_b5_mailbox_refuses_short_or_untrusted_dummy():
    with pytest.raises(ValueError):
        verifier.verify_b5_mailbox(b"\0"*256)
    with pytest.raises(ValueError):
        verifier.verify_b5_mailbox(good_dummy_mailbox()[:-4])
    with pytest.raises(ValueError):
        verifier.verify_b5_mailbox(good_dummy_mailbox(),expected_class=2)

def test_physically_authentic_trace_needs_original_stage_and_cannot_use_random_raw_file(tmp_path):
    fake=tmp_path/"fake_run"
    fake.mkdir()
    (fake/"b5_raw_physical_trace_840320.bin").write_bytes(bytes(840320))
    with pytest.raises(ValueError,match="incomplete or unsuccessful"):
        verifier.verify_session(
            evidence=fake,ordinal=0,frozen=tmp_path/"frozen",
            staged=tmp_path/"stage",routes=tmp_path/"routes",
            build=tmp_path/"build",reports=tmp_path/"reports",
            offline_report=tmp_path/"fake.json",
        )
    (fake/"stage.txt").write_text(verifier.STAGE_SUCCESS+"\n")
    with pytest.raises(ValueError):
        verifier.verify_session(
            evidence=fake,ordinal=0,frozen=tmp_path/"frozen",
            staged=tmp_path/"stage",routes=tmp_path/"routes",
            build=tmp_path/"build",reports=tmp_path/"reports",
            offline_report=tmp_path/"fake.json",
        )

def test_new_13_explicit_consents_required_for_any_board_call(monkeypatch,tmp_path):
    monkeypatch.setattr(runner.physical,"stage_requirements",lambda _:None)
    monkeypatch.setattr(runner.shutil,"which",lambda _: "/usr/bin/fake")
    args=SimpleNamespace(elf=tmp_path/"p07_b5_raw_trace_v1.elf")
    for name in runner.EXTRA_APPROVALS:setattr(args,name,"NO")
    assert len(runner.EXTRA_APPROVALS)==5
    assert len(runner.physical.APPROVALS)==8
    for name in runner.EXTRA_APPROVALS:
        with pytest.raises(runner.RawLaunchNoGo,match="YES required"):
            runner.require_new_risk_approval(args)
        setattr(args,name,"YES")
    runner.require_new_risk_approval(args)
    setattr(args,runner.EXTRA_APPROVALS[-1],"NO")
    with pytest.raises(runner.RawLaunchNoGo):
        runner.require_new_risk_approval(args)

def test_preflight_is_only_PC_and_never_calls_stager(monkeypatch,tmp_path):
    args=[
        "--mode","preflight",
        *[v for k in ("frozen-dir","staged-dir","bindings-dir","routes-dir",
                      "offline-report","reports","b4i-build","build-dir","elf")
          for v in ("--"+k,str(tmp_path/k))],
    ]
    monkeypatch.setattr(sys,"argv",["p07_b5_raw_physical_capture.py",*args])
    monkeypatch.setattr(runner,"require_pc_original_and_new_b5",
                        lambda a: ({},{},{},{}))
    def board_must_not_be_called(*a,**kw):
        raise AssertionError("forbidden board access in PC preflight")
    monkeypatch.setattr(runner.physical,"execute_staging",board_must_not_be_called)
    monkeypatch.setattr(runner,"require_new_risk_approval",board_must_not_be_called)
    output=io.StringIO()
    with contextlib.redirect_stdout(output):
        assert runner.main()==0
    assert "P07_B5_BOARD_CONTACT=0" in output.getvalue()
    assert "P07_B5_NEW_RAW_LAUNCH_AUTHORIZED_BY_PREFLIGHT=0" in output.getvalue()

def test_actual_B5_tcl_guards_new_identity_hash_original_and_exact_physical_capture():
    tcl=(ROOT/"vivado/p07_b5_raw_trace_xsdb_run.tcl").read_text()
    python=(ROOT/"scripts/p07_b5_raw_physical_capture.py").read_text()
    assert runner.ELF_SHA==gate.ELF_SHA if hasattr(gate,"ELF_SHA") else len(runner.ELF_SHA)==64
    assert runner.ELF_SHA in tcl
    assert runner.LAUNCH_TOKEN in tcl
    assert "p07_b4m_diag_v3_26tick.elf" not in tcl
    assert "0x43FF0100" in tcl and "0x42000000" in tcl
    assert "0x420CD280" in tcl
    assert "210080" in tcl and "840320" in tcl
    assert "mrd -bin -file $chunk" in tcl
    assert "P07_B5_RAW_COMPLETE_CAPTURE_RECEIPT_PHYSICAL_PASS=1" not in tcl
    for marker in verifier.MARKERS:
        assert marker in tcl
    assert 'if args.mode=="preflight":' in python
    assert 'physical.execute_staging(' in python
    assert "P07_B5_NEW_LOW_DDR_0_TO_0x107BC0_EXCLUSIVITY_PROVEN=0" in python
    assert "P07_B5_NEW_RAW_840320B_DDR_OWNER_INDEPENDENTLY_PROVEN=0" in python
    assert "actual_DDR_physical_ownership_independently_proven" in python
