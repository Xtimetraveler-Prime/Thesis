"""P07-B.4c host-only isolated Vitis build contract and genuine ELF gate.

Mocked Vitis client and mocked binutils are NOT Vitis build evidence.
Their purpose is to ensure actual build and verification fail closed.
"""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import types
from unittest import mock
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "scripts"
sys.path.insert(0,str(SRC))
from p07_b4c_verify_elf import IDENTITY, verify


def load_builder():
    p=ROOT/"software/p07/build_p07_b4c.py"
    spec=importlib.util.spec_from_file_location("p07_b4c_build",p)
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def stage(tmp,mod):
    base=tmp/"staging"
    base.mkdir()
    for name in mod.SOURCES + mod.HEADERS:
        (base/name).write_text("/* synthetic sealed build source */\n",encoding="utf8")
    (base/"p07_b4c_readonly_board.c").write_text(
        "const char *identity=\"P07_B4C_A53_READONLY_FPD128_SHELL_PROBE_V1\";\n",
        encoding="utf8")
    return base


class MockVitis:
    def __init__(self,omit_map=False):
        self.workspace=None
        self.expected_sources=None
        self.omit_map=omit_map
        self.events=[]
    def set_workspace(self,*,path):
        self.workspace=Path(path)
        self.events.append("workspace")
    def create_platform_component(self,**kwargs):
        assert kwargs=={
            "name":"p07_b4c_readonly_platform",
            "hw_design":str(self.xsa),
            "os":"standalone","cpu":"psu_cortexa53_0",
            "domain_name":"standalone_psu_cortexa53_0",
            "no_boot_bsp":True,
        }
        self.events.append("platform")
        p=self.workspace/"p07_b4c_readonly_platform"/"export"/"p07_b4c_readonly_platform"
        p.mkdir(parents=True)
        (p/"p07_b4c_readonly_platform.xpfm").write_bytes(b"mock platform")
    def get_component(self,*,name):
        return MockComponent(self,name)
    def get_templates(self,*,type):
        assert type=="EMBD_APP"
        return {"empty_application":{}}
    def create_app_component(self,**kwargs):
        assert kwargs["name"]=="p07_b4c_readonly_probe"
        assert kwargs["template"]=="empty_application"
        assert kwargs["domain"]=="standalone_psu_cortexa53_0"
        assert Path(kwargs["platform"]).is_file()
        self.events.append("app")
        (self.workspace/"p07_b4c_readonly_probe"/"src").mkdir(parents=True)


class MockComponent:
    def __init__(self,client,name):
        self.client=client;self.name=name
    def set_app_config(self,*,key,values):
        assert self.name=="p07_b4c_readonly_probe"
        assert key=="USER_LINK_OTHER_FLAGS"
        assert values==[
            f"-Wl,-Map={self.client.workspace}/p07_b4c_readonly_probe.map"
        ]
        self.client.events.append("configure:linker_map")
    def import_files(self,*,from_loc,files,dest_dir_in_cmp):
        assert dest_dir_in_cmp=="src"
        self.client.events.append("import")
        for name in files:
            shutil.copy2(Path(from_loc)/name,
                         self.client.workspace/self.name/dest_dir_in_cmp/name)
    def build(self):
        self.client.events.append("build:"+self.name)
        if self.name=="p07_b4c_readonly_probe":
            folder=self.client.workspace/self.name/"Debug"
            folder.mkdir(parents=True)
            (folder/"probe.elf").write_bytes(b"SIMULATED_ONLY_NOT_AN_ELF")
            if not self.client.omit_map:
                (self.client.workspace/"p07_b4c_readonly_probe.map").write_text(
                    "Linker script and memory map\n"
                    ".text 0x00000000 0x00005000\n"
                    "main\n.bss 0x0000e080 0x000109c0\n",
                    encoding="utf8",
                )


def test_real_project_readonly_manifest_is_exact():
    mod=load_builder()
    manifest=set(mod.SOURCES)
    assert manifest=={
        "p07_b4c_readonly_board.c","p07_b4b_board_admission.c",
        "p07_b4b_xilinx_platform.c","p03_hw_adapter.c",
        "p03_hw_xilinx_io.c",
    }
    assert "p07_b3c3_next_commit.c" not in manifest
    assert "p07_b4a_current_ingress.c" not in manifest
    assert "p07_b3c2_hw_scheduler.c" not in manifest
    for name in mod.SOURCES[:3]:
        assert (ROOT/"software/p07"/name).is_file()
    for name in mod.SOURCES[3:]:
        assert (ROOT/"software/p03"/name).is_file()
    probe=(ROOT/"software/p07/p07_b4c_readonly_board.c").read_text()
    assert "P07_B4C_A53_READONLY_FPD128_SHELL_PROBE_V1" in probe
    assert "p07_b4b_probe" in probe
    assert "p03_hw_page(" not in probe
    assert "p03_hw_dispatch(" not in probe


def test_fake_vitis_contract_imports_only_readonly_sources_and_needs_linker_map(tmp_path):
    mod=load_builder()
    staged=stage(tmp_path,mod)
    xsa=tmp_path/"pinned.xsa"
    xsa.write_bytes(b"FAKE_NO_PHYSICAL_XSA")
    fake=MockVitis()
    fake.xsa=xsa.resolve()
    with mock.patch.dict(sys.modules,{"vitis":types.SimpleNamespace(
        create_client=lambda:fake
    )}):
        elf,mapp=mod.build(xsa,tmp_path/"workspace",staged)
    assert elf.is_file() and mapp.is_file()
    assert fake.events==[
        "workspace","platform","build:p07_b4c_readonly_platform",
        "app","configure:linker_map","import","build:p07_b4c_readonly_probe"]
    # A fake ELF must NEVER pass the real executable checker.
    with pytest.raises(ValueError,match="not a genuine ELF"):
        verify(elf,mapp,"0x300000:0x310000","0x320000:0x330000")
    with pytest.raises(ValueError,match="already existing"):
        mod.build(xsa,tmp_path/"workspace",staged)
    second=MockVitis(omit_map=True)
    second.xsa=xsa.resolve()
    with mock.patch.dict(sys.modules,{"vitis":types.SimpleNamespace(
        create_client=lambda:second
    )}):
        with pytest.raises(RuntimeError,match="linker"):
            mod.build(xsa,tmp_path/"workspace_missing_map",staged)


def test_fake_vitis_rejects_non_linker_generated_map(tmp_path):
    mod=load_builder()
    staged=stage(tmp_path,mod)
    xsa=tmp_path/"pinned.xsa"
    xsa.write_bytes(b"FAKE_NO_PHYSICAL_XSA")
    fake=MockVitis()
    fake.xsa=xsa.resolve()
    old=MockComponent.build
    def forged_map(self):
        old(self)
        if self.name=="p07_b4c_readonly_probe":
            (fake.workspace/"p07_b4c_readonly_probe.map").write_text(
                "STUB .text main .bss",encoding="utf8"
            )
    with mock.patch.object(MockComponent,"build",forged_map):
        with mock.patch.dict(sys.modules,{"vitis":types.SimpleNamespace(
            create_client=lambda:fake
        )}):
            with pytest.raises(RuntimeError,match="GNU linker memory-map"):
                mod.build(xsa,tmp_path/"workspace_forged",staged)


def test_stage_rejects_missing_injected_or_symlinked_source(tmp_path):
    mod=load_builder();staged=stage(tmp_path,mod)
    mod.check_stage(staged)
    (staged/"unsigned_extra.c").write_text("bad")
    with pytest.raises(ValueError,match="unapproved"):
        mod.check_stage(staged)
    (staged/"unsigned_extra.c").unlink()
    (staged/mod.SOURCES[2]).unlink()
    with pytest.raises(ValueError,match="missing"):
        mod.check_stage(staged)


HEADER=("ELF Header:\n  Class: ELF64\n"
        "  Data: 2's complement, little endian\n"
        "  Type: EXEC (Executable file)\n  Machine: AArch64\n")
LOAD=(" LOAD 0x0 0x100000 0x100000 0x100 0x100000 RWE 0x1000\n")
NAMES=("main","p07_b4b_probe","p07_b4b_xilinx_read_phys",
       "p03_hw_init","p03_hw_identify","p03_hw_quiescent","p03_hw_xilinx_io")
NM="".join(f"{0x100000+i*0x20:016x} 00000010 T {s}\n"
           for i,s in enumerate(NAMES))+"0000000000110000 00011000 b hw\n"
MAP=".text main\n.bss hw\n"


def pseudo_elf(tmp):
    elf=tmp/"probe.elf"
    elf.write_bytes(b"\x7fELF\x02"+IDENTITY+b"fake actual linker evidence")
    linker=tmp/"probe.map"
    linker.write_text(MAP)
    return elf,linker


def binutils(command,**kwargs):
    if "-h" in command:return subprocess.CompletedProcess(command,0,HEADER,"")
    if "-l" in command:return subprocess.CompletedProcess(command,0,LOAD,"")
    if "--defined-only" in command:return subprocess.CompletedProcess(command,0,NM,"")
    raise AssertionError(f"unexpected cross binutils: {command}")


def test_mock_binutils_accepts_only_complete_fake_evidence_and_never_approves_board(tmp_path):
    elf,linker=pseudo_elf(tmp_path)
    with mock.patch("p07_b4c_verify_elf.subprocess.run",side_effect=binutils):
        proof=verify(elf,linker,"0x300000:0x310000","0x320000:0x330000",
                     readelf="/mock/aarch64-none-elf-readelf",
                     nm="/mock/aarch64-none-elf-nm")
    assert proof["read_only_firmware_identity_present"]
    assert proof["board_probe_executed"] is False
    assert proof["inference_authorized"] is False
    assert proof["DDR_exclusivity_verified"] is False
    assert proof["elf_sha256"]==hashlib.sha256(elf.read_bytes()).hexdigest()


@pytest.mark.parametrize("defect,why",[
    ("identity","identity"),
    ("magic","genuine ELF"),
    ("symlink","symlinked"),
    ("map","linker map"),
])
def test_bad_elf_identity_or_map_rejected_before_binutils(tmp_path,defect,why):
    elf,linker=pseudo_elf(tmp_path)
    if defect=="identity":elf.write_bytes(b"\x7fELF\x02"+b"missing ID")
    if defect=="magic":elf.write_bytes(b"AN_EXECUTABLE"+IDENTITY)
    if defect=="map":linker.write_text("")
    if defect=="symlink":
        actual=tmp_path/"real.elf"
        elf.rename(actual);elf.symlink_to(actual)
    with pytest.raises(ValueError,match=why):
        verify(elf,linker,"0x300000:0x310000","0x320000:0x330000")


def test_xsa_wrong_hash_or_missing_route_refused_before_vitis(tmp_path):
    script=ROOT/"scripts/build_p07_b4c.sh"
    assert subprocess.run(["bash","-n",str(script)]).returncode==0
    fake=tmp_path/"fake.xsa";fake.write_bytes(b"not accepted")
    report=tmp_path/"route_metrics.txt"
    report.write_text("p03_hpm0_data_width_bits=64\n")
    env={
        "P07_B4C_BUILD_DIR":str(tmp_path/"isolated"),
        "P07_B4C_XSA":str(fake),
        "P07_B4C_XSA_SHA256":"0"*64,
        "P07_B4C_ROUTE_METRICS":str(report),
        "P07_B4C_STACK":"0x300000:0x310000",
        "P07_B4C_HEAP":"0x320000:0x330000",
        "PATH":__import__("os").environ["PATH"],
    }
    run=subprocess.run(["bash",str(script)],env=env,
                       text=True,capture_output=True)
    assert run.returncode!=0
    assert "SHA mismatch" in run.stderr
    assert not (tmp_path/"isolated").exists()
