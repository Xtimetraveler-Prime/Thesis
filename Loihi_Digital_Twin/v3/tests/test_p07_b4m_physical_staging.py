"""P07-B.4m physical staging-only experiment, entirely native/mock-tested.

Never connects to real FPGA. Tests real TCL via fake XSDB commands;
test gates forbid any low-DDR ELF download, A53 resume, and inference.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4m_physical_staging as stage

FRAME_BYTES=128+20384*6+784

def three_signed_shapes(tmp_path):
    files={
        stage.frozen.OUT_FILENAME: b"B4MROUT1"+bytes(81920-8),
        stage.frozen.IN_FILENAME: b"B4MING01"+bytes(917504-8),
        "p07_b4m_original_TRAIN_validation_0_ingress.bin":
            b"P06B13I1"+bytes(FRAME_BYTES-8),
    }
    folder=tmp_path/"source"
    folder.mkdir()
    for filename,data in files.items():
        (folder/filename).write_bytes(data)
    return folder,files


def make_args(tmp_path):
    evidence=tmp_path/"stage_evidence"
    return SimpleNamespace(
        frozen_dir=tmp_path/"frozen",staged_dir=tmp_path/"staged",
        bindings_dir=tmp_path/"bindings",routes_dir=tmp_path/"source",
        offline_report=tmp_path/"pc_admission.json",
        reports=tmp_path/"reports",b4i_build=tmp_path/"b4i",
        elf=tmp_path/"p07_b4m_full_26tick.elf",evidence=evidence,
        validation_ordinal=0,
        **{name:"YES" for name in stage.APPROVALS},
    )


def test_host_gnu_binutils_fallback_is_selected_without_target_named_tools(monkeypatch):
    seen=[]
    available={"readelf":"/usr/bin/readelf","nm":"/usr/bin/nm"}
    monkeypatch.setattr(stage.shutil,"which",lambda name:
                        seen.append(name) or available.get(name))
    assert stage.resolve_elf_inspection_tools()==(
        "/usr/bin/readelf","/usr/bin/nm",
    )
    assert seen==[
        "aarch64-none-elf-readelf",
        "aarch64-linux-gnu-readelf",
        "readelf",
        "aarch64-none-elf-nm",
        "aarch64-linux-gnu-nm",
        "nm",
    ]


def test_target_binutils_preferred_over_host_if_installed(monkeypatch):
    available={
        "aarch64-none-elf-readelf":"/amd/gnu/aarch64-none-elf-readelf",
        "aarch64-none-elf-nm":"/amd/gnu/aarch64-none-elf-nm",
        "readelf":"/usr/bin/readelf",
        "nm":"/usr/bin/nm",
    }
    monkeypatch.setattr(stage.shutil,"which",lambda name: available.get(name))
    assert stage.resolve_elf_inspection_tools()==(
        "/amd/gnu/aarch64-none-elf-readelf",
        "/amd/gnu/aarch64-none-elf-nm",
    )


@pytest.mark.parametrize("available,missing",[
    ({"nm":"/usr/bin/nm"},"readelf"),
    ({"readelf":"/usr/bin/readelf"},"nm"),
])
def test_missing_all_compatible_inspectors_fails_without_board(
    monkeypatch,available,missing
):
    monkeypatch.setattr(stage.shutil,"which",lambda name: available.get(name))
    with pytest.raises(stage.StageNoGo,match="missing GNU "+missing):
        stage.resolve_elf_inspection_tools()


def test_gnu_host_inspectors_are_passed_to_original_b4i_gate(
    tmp_path,monkeypatch
):
    a=make_args(tmp_path)
    a.offline_report=tmp_path/"p07_b4m_admission_synthetic_offline_only.json"
    staging={
        "input_routes":20384,
        "output_routes":1000,
        "registered_axons":21384,
        "staged_files_sha256":dict(stage.EXPECTED_STAGE_SHA),
    }
    elf={
        "new_elf_sha256":stage.EXPECTED_ELF_SHA,
        "new_linker_map_sha256":stage.EXPECTED_MAP_SHA,
        "pt_load_end_exclusive":"0x00106B00",
        "pt_load_filesz":106580,
        "pt_load_memsz":1075968,
    }
    a.offline_report.write_text(json.dumps({
        "schema":"p07-b4m-full-26tick-offline-elf-and-stage-gate-v1",
        "staging":staging,"elf":elf,
        "destructive_launch_authorized":False,
        "real_KV260_inference_executed":False,
        "full_numerical_parity_verified":False,
        "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
    }))
    monkeypatch.setattr(stage.shutil,"which",lambda name:{
        "readelf":"/usr/bin/readelf",
        "nm":"/usr/bin/nm",
    }.get(name))
    called=[]
    def old_b4i_gate(build,reports,*,readelf,nm):
        called.append((build,reports,readelf,nm))
        return {}
    with patch.object(stage.model,"prepare_verified_contexts",
                      return_value={"records":[]}),(
         patch.object(stage.old,"require_real_bindings",
                      return_value={"binary_sha256":"mock"})),(
         patch.object(stage.old.b4i,"preflight",side_effect=old_b4i_gate)),(
         patch.object(stage.admission,"require_routes",return_value=staging)),(
         patch.object(stage.admission,"require_elf",return_value=elf)),(
         patch.object(stage.old.b4i,"log_call",
                      side_effect=AssertionError("board unexpectedly touched"))):
        index,desc,got_staging,got_elf=stage.require_original(a)
    assert called==[(a.b4i_build,a.reports,"/usr/bin/readelf","/usr/bin/nm")]
    assert got_staging==staging and got_elf==elf
    assert not a.evidence.exists()


@pytest.mark.parametrize("flag",stage.APPROVALS)
def test_each_operator_approval_independently_blocks_board(tmp_path,flag):
    args=make_args(tmp_path)
    setattr(args,flag,"NO")
    with pytest.raises(stage.StageNoGo,match=flag.replace("_","-")):
        stage.stage_requirements(args)
    assert not args.evidence.exists()


def test_stage_requires_new_absolute_external_directory(tmp_path):
    args=make_args(tmp_path)
    args.evidence=Path("relative")
    with pytest.raises(stage.StageNoGo,match="external absolute"):
        stage.stage_requirements(args)


def test_stage_original_board_bytes_are_read_back_independently(tmp_path):
    source,files=three_signed_shapes(tmp_path)
    outputs=tmp_path/"readbacks"
    outputs.mkdir()
    staged={
        "output_routes_80k_physical.bin":source/stage.frozen.OUT_FILENAME,
        "input_routes_896k_physical.bin":source/stage.frozen.IN_FILENAME,
        "original_TRAIN_ingress_physical.bin":
            source/"p07_b4m_original_TRAIN_validation_0_ingress.bin",
    }
    for name,origin in staged.items():
        shutil.copyfile(origin,outputs/name)
    r=stage.compare_readback(outputs,staged)
    assert len(r)==3
    assert all(row["byte_exact_vs_signed_host_input"] for row in r.values())
    with (outputs/"original_TRAIN_ingress_physical.bin").open("r+b") as f:
        f.seek(4000)
        f.write(b"X")
    with pytest.raises(stage.StageNoGo,match="byte mismatch"):
        stage.compare_readback(outputs,staged)


@pytest.mark.skipif(shutil.which("tclsh") is None,reason="tclsh not installed")
def test_actual_tcl_separate_signed_3_ddr_stages_with_fake_psu(tmp_path):
    source,_=three_signed_shapes(tmp_path)
    outputs=tmp_path/"physical_readback"
    outputs.mkdir()
    tcl=ROOT/stage.STAGE_TCL
    fixture=tmp_path/"fake_xsdb.tcl"
    fixture.write_text(
        'proc connect {args} {puts "MOCK_CONNECT";return ok}\n'
        'proc disconnect {} {puts "MOCK_DISCONNECT";return ok}\n'
        'proc targets {args} {\n'
        '  if {[string first "PSU" [lindex $args end]]<0} {error "no CPU target"}\n'
        '  return ok\n'
        '}\n'
        'array set ::staged {}\n'
        'proc dow {args} {\n'
        '  if {[lindex $args 0] ne "-data"} {error "unexpected dow format"}\n'
        '  set addr [lindex $args 2]\n'
        '  if {$addr ni {0x43FC4000 0x41000000 0x41100000}} {error "unowned DDR"}\n'
        '  set ::staged($addr) [lindex $args 1]\n'
        '  return ok\n'
        '}\n'
        'proc mrd {args} {\n'
        '  set addr [lindex $args 3]\n'
        '  if {![info exists ::staged($addr)]} {error "no earlier original stage"}\n'
        '  if {[file size $::staged($addr)] != [lindex $args 4]*4} {error "word count bad"}\n'
        '  file copy $::staged($addr) [lindex $args 2]\n'
        '  return ok\n'
        '}\n'
        'set argc 6\n'
        f'set argv [list {stage.STAGE_APPROVAL} '
        f'{{{source/stage.frozen.OUT_FILENAME}}} '
        f'{{{source/stage.frozen.IN_FILENAME}}} '
        f'{{{source/"p07_b4m_original_TRAIN_validation_0_ingress.bin"}}} '
        f'{{{outputs}}} tcp:127.0.0.1:3121]\n'
        f'source {{{tcl}}}\n'
    )
    result=subprocess.run(["tclsh",str(fixture)],capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stderr+result.stdout
    assert "P07_B4M_PHYSICAL_DDR_TARGET=PSU" in result.stdout
    assert result.stdout.count("_BYTE_EXACT_PASS=1")==3
    assert stage.PASS_STAGE in result.stdout
    assert "P07_B4M_PHYSICAL_STAGING_PASS_REBOOT_REQUIRED=1" in result.stdout
    expect={
        "output_routes_80k_physical.bin":source/stage.frozen.OUT_FILENAME,
        "input_routes_896k_physical.bin":source/stage.frozen.IN_FILENAME,
        "original_TRAIN_ingress_physical.bin":
            source/"p07_b4m_original_TRAIN_validation_0_ingress.bin",
    }
    assert len(stage.compare_readback(outputs,expect))==3


@pytest.mark.skipif(shutil.which("tclsh") is None,reason="tclsh not installed")
def test_invalid_source_rejected_before_connect(tmp_path):
    source,_=three_signed_shapes(tmp_path)
    bad=source/"p07_b4m_original_TRAIN_validation_0_ingress.bin"
    bad.write_bytes(b"P06B13I1")
    out=tmp_path/"out"
    out.mkdir()
    wrapper=tmp_path/"reject.tcl"
    wrapper.write_text(
        'proc connect {args} {puts "ERROR_BOARD_CONTACT"}\n'
        'set argc 6\n'
        f'set argv [list {stage.STAGE_APPROVAL} '
        f'{{{source/stage.frozen.OUT_FILENAME}}} '
        f'{{{source/stage.frozen.IN_FILENAME}}} {{{bad}}} '
        f'{{{out}}} tcp:127.0.0.1:3121]\n'
        f'source {{{ROOT/stage.STAGE_TCL}}}\n'
    )
    done=subprocess.run(["tclsh",str(wrapper)],capture_output=True,text=True,timeout=20)
    assert done.returncode!=0
    assert "ERROR_BOARD_CONTACT" not in done.stdout


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


def test_integrated_stage_no_elf_download_and_fail_closed(tmp_path,monkeypatch):
    source,files=three_signed_shapes(tmp_path)
    args=make_args(tmp_path)
    args.routes_dir=source
    args.bindings_dir.mkdir()
    desc_data=b"B4BIND01"+bytes(stage.binds.SIZE-8)
    (args.bindings_dir/stage.binds.FILENAME).write_bytes(desc_data)
    desc_sha=hashlib.sha256(desc_data).hexdigest()
    monkeypatch.setattr(stage.old,"ACCEPTED_DESCRIPTOR_SHA",desc_sha)
    monkeypatch.setattr(stage,"EXPECTED_STAGE_SHA",{
        name:hashlib.sha256(payload).hexdigest() for name,payload in files.items()
    })
    expected_index={"records":[{"logical_core_id":i} for i in range(27)]}
    calls=[]
    def mock_hardware(argv,logpath):
        calls.append(argv)
        n=len(calls)
        if n==1:
            assert argv[:2]==["xsdb",stage.old.b4j.TAKEOVER_TCL]
            logpath.write_text(takeover_log())
        elif n==2:
            assert argv[:4]==["vivado","-mode","batch","-source"]
            logpath.write_text(stage.old.b4j.PASS_MARKER+"\n")
        elif n==3:
            assert argv[:2]==["xsdb",stage.model.CORE_TCL]
            logpath.write_text("\n".join(
                [f"P07_B4L_CORE_{i}_512K_PHYSICAL_READBACK_PASS=1" for i in range(27)]
                +["P07_B4L_ALL_27_DDR_CORE_READBACK_TCL_PASS=1"]
            )+"\n")
        elif n==4:
            assert argv[:2]==["xsdb",stage.old.BIND_STAGE_TCL]
            shutil.copyfile(
                args.evidence/"binding_input_16k.bin",
                args.evidence/"binding_readback_16k.bin",
            )
            logpath.write_text(
                "P07_B4L_B3_FROZEN_DESCRIPTOR_16K_PHYSICAL_READBACK_TCL_PASS=1\n"
            )
        elif n==5:
            assert argv[:2]==["xsdb",stage.STAGE_TCL]
            reader=args.evidence/"b4m_physical_route_readback"
            for label,src in (
                ("output_routes_80k_physical.bin",source/stage.frozen.OUT_FILENAME),
                ("input_routes_896k_physical.bin",source/stage.frozen.IN_FILENAME),
                ("original_TRAIN_ingress_physical.bin",
                 source/"p07_b4m_original_TRAIN_validation_0_ingress.bin"),
            ):
                shutil.copyfile(src,reader/label)
            logpath.write_text("\n".join(
                [f"P07_B4M_DDR_STAGE_{i}_BYTE_EXACT_PASS=1" for i in range(3)]
                +[stage.PASS_STAGE]
            )+"\n")
        else:
            raise AssertionError("NO-GO: unexpected A53 ELF download after stage!")
    def fake_prep(staged,out,index):
        out.mkdir()
    with patch.object(stage,"stage_requirements",return_value=None),(
        patch.object(stage.old.b4i,"log_call",side_effect=mock_hardware)),(
        patch.object(stage.model,"prep_transfer_files",side_effect=fake_prep)),(
        patch.object(stage.model,"verify_physical_readback",return_value={
            "physical_readback_sha256":"synthetic-fake-not-real"
        })),(
        patch.object(stage.old.b4i,"verify_takeover_log",return_value={})
    ):
        stage.execute_staging(args,expected_index,{"binary_sha256":desc_sha},
                              {"staged_files_sha256":stage.EXPECTED_STAGE_SHA}, {
            "new_elf_sha256":stage.EXPECTED_ELF_SHA,
            "pt_load_end_exclusive":"0x00106B00",
        })
    assert len(calls)==5
    assert (args.evidence/"stage.txt").read_text().strip()==stage.STAGING_SUCCESS
    record=json.loads((args.evidence/"independent_staging_receipt.json").read_text())
    assert record["real_elf_downloaded"] is False
    assert record["inference_executed"] is False
    assert record["original_B2_4_routes_and_train_physical_sha256"]


def test_no_unsafe_old_first_epoch_reuse():
    script=(ROOT/"scripts/p07_b4m_physical_staging.py").read_text()
    assert "p07_b4l_b3_xsdb_first_epoch_run.tcl" not in script
    assert "P07_B4M_STAGING_NO_A53_ELF_DOWNLOAD=1" in script
    assert 'default="preflight"' in script
    assert "if args.mode==\"preflight\":" in script
    assert "STAGE_TCL" in script
    assert "P07_B4M_A53_FULL_26TICK_LAUNCH_AUTHORIZED=0" in script
