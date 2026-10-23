"""Native-only admission for real newly built 0x42D40 standalone B3 ELF.

Never contacts KV260. Includes tclsh simulation of REAL XSDB descriptor
stager, ordered complete 14MiB+16KiB physical readback and board mailbox.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4l_b3_physical_epoch as runtime
import p07_b4l_frozen_bindings as bindings
import p07_b4l_physical_model_deploy as model
import p07_b4l1_stage_frozen_27core as b1
import p07_b4l_verify_b3_epoch as verifier


def descriptor_and_index(tmp_path,monkeypatch):
    """Synthetic data only, never a substitute for original B2.4 production."""
    original=tmp_path/"accepted_model_staged"
    original.mkdir()
    rows=[]
    index=[]
    h=hashlib.sha256()
    with (original/b1.BUNDLE_NAME).open("wb") as stream:
        for cid in range(27):
            data=bytes([cid])*b1.STRIDE
            stream.write(data)
            h.update(data)
            index.append({"logical_core_id":cid,"physical_address":f"0x{0x40000000+cid*b1.STRIDE:08X}",
                          "sha256":hashlib.sha256(data).hexdigest()})
            bitmap=bytearray(512)
            bitmap[cid//8]|=1<<(cid%8)
            rows.append({"core_id":cid,"compartments":4,
                         "metadata":cid|(4<<7),"axon_count":1,"bitmap_hex":bitmap.hex()})
    monkeypatch.setattr(model,"ACCEPTED_BUNDLE_SHA",h.hexdigest())
    old=bindings.deploy.ACCEPTED_BUNDLE_SHA
    binddir=tmp_path/"real_binding_staged"
    binddir.mkdir()
    data=bindings.build_payload(rows)
    binary=binddir/bindings.FILENAME
    binary.write_bytes(data)
    receipt=bindings.verify_payload(data,rows)
    (binddir/bindings.INDEXNAME).write_text(json.dumps(receipt))
    return original,binddir,index,receipt


def fixture(tmp_path,monkeypatch):
    staged,binddir,index,receipt=descriptor_and_index(tmp_path,monkeypatch)
    reports=tmp_path/"reports"
    reports.mkdir()
    elf=tmp_path/runtime.ELF_NAME
    elf.write_bytes(runtime.ELF_ID+b"synthetic native fixture")
    elf.with_suffix(".map").write_text("Linker script and memory map\n.text\n.bss\n.heap\n.stack\nmain\n")
    a=SimpleNamespace(
        frozen_dir=tmp_path/"frozen",staged_dir=staged,bindings_dir=binddir,
        reports=reports,b4i_build=tmp_path/"b4i_build",elf=elf,
        evidence=tmp_path/"physical_evidence",
        **{name:"YES" for name in runtime.APPROVALS}
    )
    return a,index,receipt


def test_elf_candidate_exact_user_memory_beyond_previous_envelope(monkeypatch,tmp_path):
    a,idx,desc=fixture(tmp_path,monkeypatch)
    sha=hashlib.sha256(a.elf.read_bytes()).hexdigest()
    monkeypatch.setattr(runtime,"ELF_SHA",sha)
    realreadelf=(
        "ELF Header:\n"
        "  Class:                             ELF64\n"
        "  Data:                              2's complement, little endian\n"
        "  Type:                              EXEC (Executable file)\n"
        "  Machine:                           AArch64\n"
        "  Entry point address:               0x0\n"
        "Section Headers:\n  [ 2] .text\n  [ 4] .bss\n  [ 5] .heap\n  [ 6] .stack\n"
        "Program Headers:\n"
        "  LOAD  0x010000 0x0000000000000000 0x0000000000000000 "
        "0x015054 0x042d40 RWE 0x10000\n"
        "Segment Sections...\n .text .bss .heap .stack\n"
    )
    with patch.object(runtime.shutil,"which",return_value="/fake/readelf"),(
        patch.object(runtime.subprocess,"run",return_value=SimpleNamespace(
            returncode=0,stdout=realreadelf,stderr=""))):
        result=runtime.require_real_b3_elf(a.elf)
        assert result["physical_load_end_exclusive"]=="0x00042D40"
        assert result["elf_initial_file_bytes"]==0x15054
        assert result["elf_runtime_mem_bytes"]==0x42D40
        assert result["expanded_memory_proven_exclusive"] is False
        assert result["physical_execution_authorized_by_preflight"] is False

        for raw in (
            realreadelf.replace("0x042d40","0x029d80"),
            realreadelf.replace("0x015054","0x015055"),
            realreadelf.replace("0x0000000000000000 0x015054",
                                "0x0000000040000000 0x015054"),
            realreadelf.replace("Entry point address:               0x0",
                                "Entry point address:               0x1000"),
        ):
            with patch.object(runtime.subprocess,"run",return_value=SimpleNamespace(
                returncode=0,stdout=raw,stderr="")):
                with pytest.raises(runtime.EpochNoGo,match="NO-GO"):
                    runtime.require_real_b3_elf(a.elf)


@pytest.mark.parametrize("flag",runtime.APPROVALS)
def test_each_explicit_destructive_approval_is_independently_required(tmp_path,monkeypatch,flag):
    a,index,descriptor=fixture(tmp_path,monkeypatch)
    setattr(a,flag,"NO")
    with patch.object(runtime.b4i,"log_call",side_effect=AssertionError("board touched")):
        with pytest.raises(runtime.EpochNoGo,match=flag.replace("_","-")):
            runtime.run_hardware(a,index,descriptor,{"verified_elf_sha256":runtime.ELF_SHA})
    assert not a.evidence.exists()


def proof_fixture():
    w=[0]*64
    w[0]=verifier.RECEIPT_MAGIC
    w[1]=1
    w[2]=verifier.PASS
    w[11]=verifier.ONE_EPOCH_MAGIC
    w[12],w[13],w[14]=27,27,24
    w[15],w[16]=1,0
    w[17],w[18]=0,27
    w[19],w[20]=1,2
    w[24],w[25],w[26]=51,27,0xA00
    w[33],w[34],w[35]=27,1000,1000
    bytecount=27*verifier.READ_PAGE_BYTES+24*verifier.DIRTY_PAGE_BYTES
    w[36]=bytecount&0xFFFFFFFF
    w[37]=bytecount>>32
    w[40],w[41],w[42]=27,24,27
    w[44],w[45]=0xFFFFFFFF,0xFFFFFFFF
    w[63]=verifier.DONE
    return struct.pack("<64I",*w)


def takeover_log():
    return "\n".join((
        "P07_B4I_A53_0_STOP_COMMAND_PASS=1",
        "P07_B4I_A53_1_STOP_COMMAND_PASS=1",
        "P07_B4I_A53_2_POWERED_DOWN_OBSERVED=1",
        "P07_B4I_A53_3_POWERED_DOWN_OBSERVED=1",
        "P03_2C_PS_FPD_AXIFS_RAW=0x00000A00",
        "P03_2C_PS_FPD_HPM0_WIDTH_BITS=128",
        "P03_2C_PS_LPD_AXIFS_RAW=0x00000200",
        "P03_2C_PS_LPD_HPM0_WIDTH_BITS=128",
        "P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1",
    ))+"\n"


def test_integrated_physical_order_checks_descriptor_before_A53(tmp_path,monkeypatch,capsys):
    a,index,descriptor=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(runtime,"ELF_SHA",hashlib.sha256(a.elf.read_bytes()).hexdigest())
    calls=[]
    def fake_hw(argv,logpath):
        calls.append(argv)
        step=len(calls)
        if step==1:
            assert argv[:2]==["xsdb",runtime.b4j.TAKEOVER_TCL]
            logpath.write_text(takeover_log())
        elif step==2:
            assert argv[:2]==["vivado","-mode"]
            logpath.write_text(runtime.b4j.PASS_MARKER+"\n")
        elif step==3:
            assert argv[:2]==["xsdb",model.CORE_TCL]
            for cid in range(27):
                shutil.copyfile(a.evidence/"transfer_inputs"/model.CORE_INPUT.format(cid),
                                a.evidence/"physical_readback"/model.CORE_READBACK.format(cid))
            logpath.write_text("\n".join(
                [f"P07_B4L_CORE_{cid}_512K_PHYSICAL_READBACK_PASS=1" for cid in range(27)]
                +["P07_B4L_ALL_27_DDR_CORE_READBACK_TCL_PASS=1"])+"\n")
        elif step==4:
            assert argv[:2]==["xsdb",runtime.BIND_STAGE_TCL]
            assert (a.evidence/"ddr_verified.json").is_file()
            shutil.copyfile(a.evidence/"binding_input_16k.bin",
                            a.evidence/"binding_readback_16k.bin")
            logpath.write_text(
                "P07_B4L_B3_FROZEN_DESCRIPTOR_16K_PHYSICAL_READBACK_TCL_PASS=1\n")
        elif step==5:
            assert argv[:2]==["xsdb",runtime.A53_RUN_TCL]
            assert (a.evidence/"descriptor_verified.json").is_file()
            (a.evidence/"b3_epoch_mailbox_256.bin").write_bytes(proof_fixture())
            logpath.write_text(
                "P07_B4L_B3_A53_EPOCH_ELF_DOWNLOADED=1\n"
                "P07_B4L_B3_A53_EPOCH_MAILBOX_CAPTURED_256_BYTES=1\n"
                "P07_B4L_B3_A53_EPOCH_CAPTURE_READY_FOR_INDEPENDENT_VERIFIER=1\n")
        else:
            raise AssertionError("unexpected board call")
    with patch.object(runtime.shutil,"which",return_value="/mock/tool"),(
        patch.object(runtime.b4i,"log_call",side_effect=fake_hw)):
        runtime.run_hardware(a,index,descriptor,{"verified_elf_sha256":runtime.ELF_SHA})
    assert len(calls)==5
    assert (a.evidence/"stage.txt").read_text().startswith(
        "REAL_B3_FIRST_EPOCH_27_DISPATCH_BARRIER_PENDING_PASS_REBOOT_REQUIRED")
    assert "P07_B4L_B3_REAL_27_DISPATCH_BAR_PRE_ACK_PHYSICAL_RECEIPT_PASS=1" in capsys.readouterr().out


def test_bad_descriptor_prohibits_any_A53_download(tmp_path,monkeypatch):
    a,index,descriptor=fixture(tmp_path,monkeypatch)
    calls=[]
    def fake_hw(argv,log):
        calls.append(argv)
        if len(calls)==1:log.write_text(takeover_log())
        elif len(calls)==2:log.write_text(runtime.b4j.PASS_MARKER+"\n")
        elif len(calls)==3:
            for cid in range(27):
                shutil.copyfile(a.evidence/"transfer_inputs"/model.CORE_INPUT.format(cid),
                                a.evidence/"physical_readback"/model.CORE_READBACK.format(cid))
            log.write_text("\n".join(
                [f"P07_B4L_CORE_{cid}_512K_PHYSICAL_READBACK_PASS=1" for cid in range(27)]
                +["P07_B4L_ALL_27_DDR_CORE_READBACK_TCL_PASS=1"])+"\n")
        elif len(calls)==4:
            (a.evidence/"binding_readback_16k.bin").write_bytes(bytes(bindings.SIZE))
            log.write_text("P07_B4L_B3_FROZEN_DESCRIPTOR_16K_PHYSICAL_READBACK_TCL_PASS=1\n")
        else:raise AssertionError("NO-GO: no ELF download after corrupted descriptor")
    with patch.object(runtime.shutil,"which",return_value="/fake/tool"),(
        patch.object(runtime.b4i,"log_call",side_effect=fake_hw)):
        with pytest.raises(runtime.EpochNoGo,match="16KiB"):
            runtime.run_hardware(a,index,descriptor,{"verified_elf_sha256":runtime.ELF_SHA})
    assert len(calls)==4
    assert not (a.evidence/"a53_b3_epoch.log").exists()


def test_actual_descriptor_tcl_with_mock_psu_target(tmp_path):
    if not shutil.which("tclsh"):pytest.skip("tclsh not installed")
    infile=tmp_path/"binding.bin"
    infile.write_bytes(bindings.build_payload([
        {"core_id":cid,"compartments":4,"metadata":cid|(4<<7),
         "axon_count":1,"bitmap_hex":(bytes([1])+bytes(511)).hex()}
        for cid in range(27)
    ]))
    outfile=tmp_path/"returned.bin"
    real=ROOT/runtime.BIND_STAGE_TCL
    testscript=tmp_path/"fake_xsdb.tcl"
    testscript.write_text(
        'proc connect {args} {return ok}\n'
        'proc disconnect {} {return ok}\n'
        'proc targets {args} {if {[lindex $args end] ne {name =~ "PSU"}} {error "not PSU"};return ok}\n'
        'proc dow {args} {\n'
        ' if {[lindex $args 0] ne "-data" || [lindex $args 2] ne "0x43FC0000"} {error "bad physical write"}\n'
        ' set ::input [lindex $args 1];return ok\n}\n'
        'proc mrd {args} {\n'
        ' if {[lindex $args 3] ne "0x43FC0000" || [lindex $args 4] ne "4096"} {error "bad readback"}\n'
        ' file copy $::input [lindex $args 2]\n'
        ' return ok\n}\n'
        'set argc 4\n'
        f'set argv [list B4L_FROZEN_BINDING_16K_OVERWRITE_APPROVED {{{infile}}} {{{outfile}}} tcp:127.0.0.1:3121]\n'
        f'source {{{real}}}\n'
    )
    result=subprocess.run(["tclsh",str(testscript)],
                          capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr+result.stdout
    assert "P07_B4L_B3_FROZEN_DESCRIPTOR_16K_PHYSICAL_READBACK_TCL_PASS=1" in result.stdout
    assert outfile.read_bytes()==infile.read_bytes()


def test_actual_descriptor_tcl_rejects_bad_input_without_connection(tmp_path):
    if not shutil.which("tclsh"):pytest.skip("tclsh not installed")
    bad=tmp_path/"truncated.bin"
    bad.write_bytes(bytes(10))
    script=tmp_path/"bad.tcl"
    real=ROOT/runtime.BIND_STAGE_TCL
    script.write_text(
        'proc connect {args} {puts "SHOULD_NOT_CONNECT"}\n'
        'set argc 4\n'
        f'set argv [list B4L_FROZEN_BINDING_16K_OVERWRITE_APPROVED '
        f'{{{bad}}} {{{tmp_path/"out.bin"}}} tcp:127.0.0.1:3121]\n'
        f'source {{{real}}}\n'
    )
    result=subprocess.run(["tclsh",str(script)],
                          capture_output=True,text=True,timeout=20)
    assert result.returncode!=0
    assert "SHOULD_NOT_CONNECT" not in result.stdout


def test_launcher_is_not_old_paging_candidate():
    tcl=(ROOT/runtime.A53_RUN_TCL).read_text()
    assert "P07_B4L_A53_B3_ONE_EPOCH_V1" in tcl
    assert "B4L_B3_FIRST_EPOCH_AFTER_27_DDR_AND_BINDINGS_APPROVED" in tcl
    assert "P07_B4L_B3_A53_EPOCH_MAILBOX_CAPTURED_256_BYTES=1" in tcl
    assert "P07_B4L_A53_27CORE_PAGING_PROBE_V1" not in tcl
    script=(ROOT/"scripts/p07_b4l_b3_physical_epoch.py").read_text()
    assert '--recovery-note' not in script
    assert 'default="preflight"' in script
    assert "official" in script.lower()
