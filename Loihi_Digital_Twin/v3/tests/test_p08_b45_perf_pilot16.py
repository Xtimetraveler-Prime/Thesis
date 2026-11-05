"""PC-only/native tests of B4.5 explicit unprotected pilot16."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
P08=ROOT/"software"/"p08"
sys.path.insert(0,str(P08))
sys.path.insert(0,str(ROOT/"scripts"))
import build_p08_b45_perf_pilot16 as build
import p08_b45_perf_pilot16_physical_run as phys

def source(n):
    for root in (P08,ROOT/"software"/"p07",ROOT/"software"/"p07"/"include",
                 ROOT/"software"/"p03",ROOT/"software"/"p03"/"include",
                 ROOT/"software"/"p05"/"include"):
        if (root/n).is_file():return (root/n).read_text()
    raise AssertionError(n)

def stage(tmp,mode):
    root=tmp/("stage_"+mode);root.mkdir()
    for n in build.sources(mode)+build.HEADERS:
        if n=="p08_b2_2_original_context_sha256.h":
            data="#include <stdint.h>\nconst uint8_t p08_b2_original_context_sha256[27][32]={{1}};\n"
        else:data=source(n)
        if n=="p07_b2_packet.h":
            data=data.replace("#define P07_B2_MAX_ROUTE_BINDINGS 8192u",
                              "#define P07_B2_MAX_ROUTE_BINDINGS 10000u")
        if n=="p07_a2_sha256.c":
            data=data.replace('#include "include/p07_a2_sha256.h"',
                              '#include "p07_a2_sha256.h"')
        (root/n).write_text(data)
    return root

@pytest.mark.parametrize("mode",build.MODES)
def test_stage_and_gcc_syntax(mode,tmp_path,capsys):
    root=stage(tmp_path,mode)
    build.check_stage(root,mode)
    assert build.main(["--mode",mode,"--check-stage-only",str(root)])==0
    assert "P08_B45_PERF_PILOT16_STAGE_EXACT_PASS=1" in capsys.readouterr().out
    m=(root/build.MAINS[mode]).read_text()
    assert "#define B23_FRAMES 16u" in m
    assert "#define B23_RAW_POOL_BYTES (1024u*784u)" in m
    assert "words[19]=0u;" in m
    assert "p08_b45_perf_reset_image(" in m and "p08_b45_a53_backup_lock" not in m
    if shutil.which("gcc"):
        (root/"xil_cache.h").write_text(
            "#include <stdint.h>\n#include <stddef.h>\ntypedef uintptr_t INTPTR;\n"
            "void Xil_DCacheInvalidateRange(INTPTR,uint32_t);\nvoid Xil_DCacheFlushRange(INTPTR,uint32_t);\n")
        (root/"xil_io.h").write_text(
            "#include <stdint.h>\ntypedef uintptr_t UINTPTR;\nuint32_t Xil_In32(UINTPTR);\n"
            "void Xil_Out32(UINTPTR,uint32_t);\n")
        (root/"xil_printf.h").write_text("int xil_printf(const char *,...);\n")
        p=subprocess.run(["gcc","-std=c11","-fsyntax-only","-Wall","-Wextra","-Werror",
                          "-pedantic","-I",str(root),str(root/build.MAINS[mode]),
                          str(root/"p08_b45_perf_reset.c")],
                         capture_output=True,text=True,timeout=70)
        assert p.returncode==0,p.stdout+p.stderr

def test_native_reset_and_corruption(tmp_path):
    if not shutil.which("gcc"):pytest.skip("gcc not installed")
    exe=tmp_path/"native"
    p=subprocess.run(["gcc","-std=c11","-O2","-Wall","-Wextra","-Werror",
                      "-pedantic","-I",str(P08),"-I",str(ROOT/"software"/"p07"/"include"),
                      str(ROOT/"tests"/"native"/"p08_b45_perf_reset_native.c"),
                      str(P08/"p08_b45_perf_reset.c"),str(ROOT/"software"/"p07"/"p07_a2_sha256.c"),
                      "-o",str(exe)],capture_output=True,text=True,timeout=90)
    assert p.returncode==0,p.stdout+p.stderr
    run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=180)
    assert run.returncode==0,run.stdout+run.stderr
    assert "P08_B45_PERF_LOCK_CALLBACKS_NEVER_CALLED_PASS=1" in run.stdout
    assert "P08_B45_PERF_MUTATED_BACKUP_AFTER_BIND_NOT_DETECTED_CONFIRMED=1" in run.stdout
    assert "P08_B45_PERF_AUTH_ONCE_HEADER_FAULT_DETECTED_PASS=1" in run.stdout
    assert "P08_B45_PERF_ERROR_POISONS_SESSION_PASS=1" in run.stdout
    assert "P08_B45_PERF_PHYSICAL_KV260_EXECUTED=0" in run.stdout

@pytest.mark.parametrize("mode",build.MODES)
@pytest.mark.parametrize("change",("changed_main","changed_kernel","fake_guard",
                                   "raw16","bad_reset","missing","extra","cross"))
def test_stage_mutation_is_rejected(mode,change,tmp_path):
    root=stage(tmp_path,mode)
    main=root/build.MAINS[mode]
    if change=="changed_main":main.write_text(main.read_text()+"\n// new")
    if change=="changed_kernel":
        f=root/"p08_b45_perf_reset.c";f.write_text(f.read_text()+"\n// new")
    if change=="fake_guard":
        main.write_text(main.read_text().replace("words[19]=0u;","words[19]=1u;"))
    if change=="raw16":
        main.write_text(main.read_text().replace(
            "#define B23_RAW_POOL_BYTES (1024u*784u)","#define B23_RAW_POOL_BYTES (B23_FRAMES*784u)"))
    if change=="bad_reset":
        main.write_text(main.read_text().replace("p08_b45_perf_reset_image(","p08_b45_reset_image("))
    if change=="missing":(root/"p08_b45_perf_reset.h").unlink()
    if change=="extra":(root/"fake").write_text("fake")
    if change=="cross":
        main.write_text(source(build.MAINS["unchecked" if mode=="once" else "once"]))
    with pytest.raises(ValueError):build.check_stage(root,mode)

def test_original_guard_preserved_and_jtag_readback_gated():
    guard=(P08/"p08_b45_a53_backup_guard.c").read_text()
    assert guard.count("return -1;")==2 and "return 0;" not in guard
    perf=(P08/"p08_b45_perf_reset.c").read_text()
    assert "config->lock_backup(" not in perf
    assert "config->backup_lock_valid(" not in perf
    assert "Xil_Out32(" not in perf
    tcl=(ROOT/"vivado"/"p08_b45_perf_pilot16_run_and_capture.tcl").read_text()
    for needle in ("argc != 8","exec sha256sum $elf","0x42400000 1024",
                   "3 15 4 0 5 16 63","backup_after_27",
                   "mrd -bin -file $target $address 131072"):
        assert needle in tcl,needle
    assert "mwr " not in tcl and "1023 4 0 5 1024" not in tcl
    runner=(ROOT/"scripts"/"p08_b45_perf_pilot16_physical_run.py").read_text()
    for marker in ("b3.original_inputs(","b3.readback_original(","neural.verify(",
                   "sidecar.audit(","require_protection=False",
                   "unprotected_backup_integrity_tradeoff_accepted",
                   "default=\"preflight\""):
        assert marker in runner,marker

def test_host_postrun_backup_all_27_then_reject_mutation(tmp_path,monkeypatch):
    raw=bytes([0x6a])*14155776
    stage=tmp_path/"stage";stage.mkdir()
    name=phys.original_stage.FILES[0][0]
    (stage/name).write_bytes(raw)
    monkeypatch.setitem(phys.original_stage.EXPECTED_SHA,name,hashlib.sha256(raw).hexdigest())
    cap=tmp_path/"cap";folder=cap/"backup_after_27";folder.mkdir(parents=True)
    for i in range(27):(folder/f"core_{i:02d}.bin").write_bytes(raw[i*524288:(i+1)*524288])
    assert len(phys.check_post_backup(stage,cap))==27
    (folder/"core_12.bin").write_bytes(b"X"*524288)
    with pytest.raises(phys.PilotNoGo,match="backup core 12"):
        phys.check_post_backup(stage,cap)

def test_pilot_build_shell_safe_to_parse():
    sh=ROOT/"scripts"/"build_p08_b45_perf_pilot16.sh"
    p=subprocess.run(["bash","-n",str(sh)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    s=sh.read_text()
    assert "p08_b45_a53_backup_guard.c" not in s
    assert "p08_b45_perf_reset.c" in s
    assert "xsdb " not in s and "vivado -mode batch" not in s
