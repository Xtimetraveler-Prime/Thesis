"""P08-B4.5 full1024 native source and board-safe host progress tests."""
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
import build_p08_b45_perf_full1024 as build
import p08_b45_perf_full1024_monitor as monitor
import p08_b45_perf_full1024_physical_run as runner

def source(name):
    for d in (P08,ROOT/"software"/"p07",ROOT/"software"/"p07"/"include",
              ROOT/"software"/"p03",ROOT/"software"/"p03"/"include",
              ROOT/"software"/"p05"/"include"):
        p=d/name
        if p.is_file():return p.read_text()
    raise AssertionError("missing "+name)

def stage(tmp,mode):
    d=tmp/("stage_"+mode);d.mkdir()
    for n in build.sources(mode)+build.HEADERS:
        data=("#include <stdint.h>\n"
              "const uint8_t p08_b2_original_context_sha256[27][32]={{1}};\n"
              if n=="p08_b2_2_original_context_sha256.h" else source(n))
        if n=="p07_a2_sha256.c":
            data=data.replace('#include "include/p07_a2_sha256.h"',
                              '#include "p07_a2_sha256.h"')
        if n=="p07_b2_packet.h":
            assert "#define P07_B2_MAX_ROUTE_BINDINGS 8192u" in data
            data=data.replace("#define P07_B2_MAX_ROUTE_BINDINGS 8192u",
                              "#define P07_B2_MAX_ROUTE_BINDINGS 10000u")
        (d/n).write_text(data)
    return d

@pytest.mark.parametrize("mode",build.MODES)
def test_distinct_full1024_stages_and_native_gcc(mode,tmp_path,capsys):
    d=stage(tmp_path,mode)
    assert build.check_stage(d,mode) is None
    assert build.main(["--mode",mode,"--check-stage-only",str(d)])==0
    assert "P08_B45_PERF_FULL1024_STAGE_EXACT_PASS=1" in capsys.readouterr().out
    c=(d/build.MAINS[mode]).read_text()
    for expected in ("#define B23_FRAMES 1024u",
                     "#define B23_RAW_POOL_BYTES (1024u*784u)",
                     "B45_PROFILE_BYTES==262144u",
                     "words[19]=0u;","p08_b45_perf_reset_image(",
                     build.IDENTITIES[mode],build.DONE[mode]):
        assert expected in c
    assert "p08_b45_a53_backup_lock" not in c
    if shutil.which("gcc"):
        (d/"xil_cache.h").write_text("#include <stdint.h>\n#include <stddef.h>\n"
            "typedef uintptr_t INTPTR;\nvoid Xil_DCacheInvalidateRange(INTPTR,uint32_t);\n"
            "void Xil_DCacheFlushRange(INTPTR,uint32_t);\n")
        (d/"xil_io.h").write_text("#include <stdint.h>\ntypedef uintptr_t UINTPTR;\n"
            "uint32_t Xil_In32(UINTPTR);\nvoid Xil_Out32(UINTPTR,uint32_t);\n")
        (d/"xil_printf.h").write_text("int xil_printf(const char *,...);\n")
        p=subprocess.run(["gcc","-std=c11","-fsyntax-only","-Wall","-Wextra","-Werror",
                          "-pedantic","-I",str(d),str(d/build.MAINS[mode]),
                          str(d/"p08_b45_perf_reset.c")],
                         capture_output=True,text=True,timeout=70)
        assert p.returncode==0,p.stdout+p.stderr

@pytest.mark.parametrize("mode",build.MODES)
@pytest.mark.parametrize("fault",("changed","pilot16","fake_lock","wrong_api","missing","extra","cross"))
def test_no_tampered_full1024_sources(mode,fault,tmp_path):
    d=stage(tmp_path,mode);f=d/build.MAINS[mode]
    if fault=="changed":f.write_text(f.read_text()+"\n//changed")
    if fault=="pilot16":f.write_text(f.read_text().replace("#define B23_FRAMES 1024u",
                                                              "#define B23_FRAMES 16u"))
    if fault=="fake_lock":f.write_text(f.read_text().replace("words[19]=0u;",
                                                                "words[19]=1u;"))
    if fault=="wrong_api":f.write_text(f.read_text().replace("p08_b45_perf_reset_image(",
                                                                "p08_b45_reset_image("))
    if fault=="missing":(d/"p08_b45_perf_reset.h").unlink()
    if fault=="extra":(d/"fake").write_text("x")
    if fault=="cross":f.write_text(source(build.MAINS["once" if mode=="unchecked" else "unchecked"]))
    with pytest.raises(ValueError):build.check_stage(d,mode)

def test_original_failclosed_and_full_jtag_contract():
    assert (P08/"p08_b45_a53_backup_guard.c").read_text().count("return -1;")==2
    assert (P08/"p08_b45_perf_once_pilot16_a53.c").exists()
    s=(ROOT/"vivado"/"p08_b45_perf_full1024_run_and_capture.tcl").read_text()
    for expected in ("P08_B45_PERF_1024_AFTER_SIX_SIGNED_READBACK_UNPROTECTED_RISK_APPROVED",
                     "argc != 8","exec sha256sum $elf","0x42200000 65536",
                     "0x42300000 65536","0x42400000 65536",
                     "3 1023 4 0 5 1024 63","completed>1024",
                     "for {set attempt 0} {$attempt < 172800}",
                     "last_advance_attempt > 3600",
                     "file rename -force $temporary $final",
                     "CAPTURE_DONE_PENDING_INDEPENDENT",
                     "backup_after_27","mrd -bin -file $target $address 131072"):
        assert expected in s,expected
    assert "mwr " not in s and "0xFD000000" not in s
    assert s.index("P08_B45_PERF1024_EXACT_1024_FRAME_HARDWARE_TERMINAL_OBSERVED=1") < s.index(
        "p08_perf1024_progress $out $mode 1024 BACKUP_READBACK")
    p=(ROOT/"scripts"/"p08_b45_perf_full1024_physical_run.py").read_text()
    for expected in ("import p08_b3_pilot16_physical_run as b3",
                     "import p08_b3_pilot16_stage_host as original_stage",
                     "oracle_merge.merge(","original_profile.ORIGINAL_B44_TIMING_SHA",
                     "b3.readback_original(","neural.verify(","check_post_backup(",
                     "z262144.write_bytes(bytes(262144))",
                     "i<1023","default=\"preflight\""):
        assert expected in p,expected

def test_host_only_progress_and_impossible_terminal_rejected(tmp_path):
    data={"schema":monitor.SCHEMA,"mode":"once","completed":17,
          "total":1024,"state":"POLLING","started_epoch":1000,
          "updated_epoch":1040,"elapsed_seconds":40}
    def encode(d):return "\n".join(str(k)+"="+str(v) for k,v in d.items())+"\n"
    assert monitor.parse_snapshot(encode(data),expected_mode="once")["completed"]==17
    for falsified in ({**data,"state":"CAPTURE_DONE_PENDING_INDEPENDENT"},
                      {**data,"completed":1025},
                      {**data,"total":16}):
        with pytest.raises(monitor.ProgressNoGo):
            monitor.parse_snapshot(encode(falsified),expected_mode="once")
    root=tmp_path/"run";cap=root/"performance1024_capture";cap.mkdir(parents=True)
    (root/"stage.txt").write_text("P03_PROGRAMMED_SIX_DDR_STAGING\n")
    (cap/"progress_state.txt").write_text(encode(data))
    msg,done,failed=monitor.snapshot(root,"once",now=1045)
    assert "17/1024" in msg and not done and not failed
    (cap/"progress_state.txt").write_text(encode(
        {**data,"completed":1024,"state":"CAPTURE_DONE_PENDING_INDEPENDENT"}))
    msg,done,failed=monitor.snapshot(root,"once",now=1045)
    assert done and not failed and "independent" in msg.lower()

def test_postrun_27_original_backups_still_fail_closed(tmp_path,monkeypatch):
    original=bytes([0x17])*14155776
    stage=tmp_path/"stage";stage.mkdir()
    name=runner.original_stage.FILES[0][0]
    (stage/name).write_bytes(original)
    monkeypatch.setitem(runner.original_stage.EXPECTED_SHA,name,hashlib.sha256(original).hexdigest())
    folder=tmp_path/"cap"/"backup_after_27";folder.mkdir(parents=True)
    for i in range(27):
        (folder/("core_%02d.bin"%i)).write_bytes(original[i*524288:(i+1)*524288])
    assert len(runner.check_post_backup(stage,folder.parent))==27
    (folder/"core_13.bin").write_bytes(bytes([0x99])*524288)
    with pytest.raises(runner.PilotNoGo):
        runner.check_post_backup(stage,folder.parent)

def test_build_shell_and_independent_audit_never_use_hardware():
    path=ROOT/"scripts"/"build_p08_b45_perf_full1024.sh"
    p=subprocess.run(["bash","-n",str(path)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    c=path.read_text()
    assert "p08_b45_perf_reset.c" in c
    assert "p08_b45_a53_backup_guard.c" not in c
    assert "xsdb " not in c and "vivado -mode batch" not in c
    verify=(ROOT/"scripts"/"p08_b45_perf_full1024_independent_verify.py").read_text()
    for name in ("neural.verify(","bench.check_post_backup(","bench.admission(args)",
                 "one_unprotected_session_descriptive_only","1023",
                 "paired_AB_BA_AB_six_session_speedup_not_established"):
        assert name in verify
    assert "subprocess" not in verify
