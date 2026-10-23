"""P07-B.4g/h fake XSDB + offline shell transcript boundary tests.

tclsh tests stub connect/targets/mrd/disconnect; no hardware access.
Fake ELF/XSA/BIT fixtures and logs never prove physical provenance.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import textwrap

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4h_review_shell_capture as review

TCL=ROOT/"vivado/p07_b4g_readonly_shell.tcl"
VALUES={
    "0xFD615000":"0x00000A00",
    "0xA4000000":"0x4C543302",
    "0xA4000004":"0x00010000",
    "0xA4000008":"0x0001031F",
    "0xA400000C":"0x00000000",
    "0xA4000054":"0x00000000",
}


def fake_tcl(tmp:Path, *,corrupt=None,missing=None,ack=True,invalid_url=False):
    if not shutil.which("tclsh"):
        pytest.skip("Tcl interpreter not installed; CI must provide tclsh")
    values=VALUES.copy()
    if corrupt:
        values.update(corrupt)
    if missing:
        del values[missing]
    lookup=" ".join(f"{addr} {value}" for addr,value in values.items())
    cmd=textwrap.dedent("""
        set argc 1
        set argv [list READ_ONLY_OPERATOR_APPROVED]
        set argv0 fake_tcl
        set calls 0
        proc connect {args} {puts "FAKE_XSDB_CONNECTED=1"}
        proc targets {args} {return "FAKE_PSU"}
        proc disconnect {} {puts "FAKE_XSDB_DISCONNECTED=1"}
        proc stop {args} {error "FORBIDDEN STOP"}
        proc rst {args} {error "FORBIDDEN RST"}
        proc mwr {args} {error "FORBIDDEN MWR"}
        proc dow {args} {error "FORBIDDEN DOWNLOAD"}
        proc con {args} {error "FORBIDDEN CON"}
        proc fpga {args} {error "FORBIDDEN FPGA"}
    """)
    cmd+=f"set fake_values [dict create {lookup}]\n"
    cmd+=textwrap.dedent("""
        proc mrd {args} {
            global fake_values calls
            incr calls
            if {[lrange $args 0 3] ne {-force -value -size w}} {
                error "unexpected or unsafe XSDB read options: $args"
            }
            if {[lindex $args end] ne "1"} {
                error "must read one word only"
            }
            set address [lindex $args end-1]
            if {![dict exists $fake_values $address]} {
                error "FAKE_XSDB_READ_ERROR"
            }
            return [list [dict get $fake_values $address]]
        }
    """)
    if not ack:cmd+="set argv [list WRONG_ACK]\n"
    if invalid_url:cmd+="set argc 2\nset argv [list READ_ONLY_OPERATOR_APPROVED tcp:10.0.0.5:3121]\n"
    cmd+=f"source {{{TCL}}}\n"
    p=tmp/"fakeXSDB.tcl";p.write_text(cmd)
    return subprocess.run(["tclsh",str(p)],text=True,capture_output=True,timeout=12)


def test_b4g_tcl_fake_xsdb_six_reads_pass_and_never_cpu_write(tmp_path):
    result=fake_tcl(tmp_path)
    assert result.returncode==0,result.stderr
    assert result.stdout.count("P07_B4G_PHYSICAL_TARGET=PSU")==1
    assert result.stdout.count("P07_B4G_READONLY_PS_PL_SNAPSHOT_PASS=1")==1
    assert "P07_B4G_INFERENCE_AUTHORIZED=0" in result.stdout
    assert "P07_B4G_A53_ELF_DOWNLOAD_AUTHORIZED=0" in result.stdout
    assert result.stdout.count("FAKE_XSDB_DISCONNECTED=1")==1
    assert len(re.findall(r"(?m)^P07_B4G_.*=0x",result.stdout))==6


@pytest.mark.parametrize("delta,error",[
    ({"0xFD615000":"0x00000100"},"FPD width"),
    ({"0xA4000000":"0x11111111"},"shell ID"),
    ({"0xA400000C":"0x00000001"},"not quiescent"),
    ({"0xA4000054":"0x00000001"},"not quiescent"),
    ({"0xA4000008":"ABCD_BAD"},"malformed"),
])
def test_b4g_tcl_fails_closed_with_disconnect(tmp_path,delta,error):
    result=fake_tcl(tmp_path,corrupt=delta)
    assert result.returncode!=0
    assert error in result.stderr
    assert "P07_B4G_READONLY_PS_PL_SNAPSHOT_FAIL=1" in result.stdout
    assert "P07_B4G_INFERENCE_AUTHORIZED=0" in result.stdout
    assert "P07_B4G_READONLY_PS_PL_SNAPSHOT_PASS=1" not in result.stdout
    assert result.stdout.count("FAKE_XSDB_DISCONNECTED=1")==1


def test_tcl_read_fail_cleanup_and_explicit_opt_in(tmp_path):
    bad=fake_tcl(tmp_path,missing="0xA4000004")
    assert bad.returncode!=0
    assert "FAKE_XSDB_READ_ERROR" in bad.stderr
    assert "FAKE_XSDB_DISCONNECTED=1" in bad.stdout
    ack=fake_tcl(tmp_path,ack=False)
    assert ack.returncode!=0
    assert "acknowledgment is mandatory" in ack.stderr
    assert "FAKE_XSDB_CONNECTED" not in ack.stdout
    remote=fake_tcl(tmp_path,invalid_url=True)
    assert remote.returncode!=0
    assert "local XSDB server" in remote.stderr
    assert "FAKE_XSDB_CONNECTED" not in remote.stdout


def test_b4g_tcl_ast_allowlist_hard_stop():
    s=TCL.read_text()
    assert "mrd -force -value -size w" in s
    assert "READ_ONLY_OPERATOR_APPROVED" in s
    assert s.count("p07_b4g_read32 ")==7  # 1 proc + exactly six reads
    for bad in ("mwr","dow","rst","stop","con","fpga"):
        assert not re.search(r"(?m)^\s*"+bad+r"\s+",s),bad


def fixture(tmp_path):
    folder=tmp_path/"artifact"
    folder.mkdir(parents=True)
    artifacts={}
    for name in ("elf","linker_map","xsa","bit"):
        path=folder/name
        path.write_bytes(("SYNTHETIC_NON_REAL_"+name).encode())
        artifacts[name]=path
    audit={
        "schema":review.IDENTITY,
        "board_ELF_download_authorized":False,
        "physical_inference_authorized":False,
        "board_programming_authorized":False,
        "read_only_source_and_accepted_XSA_inputs_checked":True,
        "user_local_real_elf_and_map_hash_matched":True,
        "bit_fingerprint_provenance":"observed",
        "sha256":{name:review.sha256(path) for name,path in artifacts.items()},
    }
    audit_path=folder/"b4f_audit.json"
    audit_path.write_text(json.dumps(audit,indent=2))
    raw="P07_B4G_PHYSICAL_TARGET=PSU\n"
    raw+="".join(f"P07_B4G_{key}={val}\n" for key,val in {
        "FPD_RAW":"0x00000A00","P03_ID":"0x4C543302",
        "P03_VERSION":"0x00010000","P03_CAPABILITIES":"0x0001031F",
        "P03_GLOBAL_STATUS":"0x00000000","P03_PAGE_PENDING":"0x00000000",
    }.items())
    raw+="".join(f"{k}={v}\n" for k,v in review.MARKERS.items())
    log=folder/"fake_xsdb.log"
    log.write_text(raw)
    return dict(
        audit=audit_path,transcript=log,
        elf=artifacts["elf"],linker_map=artifacts["linker_map"],
        xsa=artifacts["xsa"],bit=artifacts["bit"],
        board_state="unknown",bit_provenance="observed",
    )


def test_b4h_synthetic_log_and_pinned_file_review_stays_no_go(tmp_path):
    kw=fixture(tmp_path)
    report=review.evaluate(**kw)
    assert report["XSDB_log_format_checks_passed"] is True
    assert report["XSDB_log_origin_authenticated"] is False
    assert report["live_BIT_SHA_independently_verified"] is False
    assert report["A53_ELF_download_authorized"] is False
    assert report["physical_inference_authorized"] is False
    assert report["official_B2_MNIST_TEST"]=="SEALED"
    assert report["board_state_operator_reported"]=="unknown"


@pytest.mark.parametrize("damage,expect",[
    ("duplicate","duplicated"),
    ("missing","missing"),
    ("fpd","FPD width"),
    ("busy","mismatch"),
    ("status","unexpected"),
    ("fail","failure"),
    ("badhex","32-bit"),
])
def test_b4h_rejects_fake_or_torn_or_conflicting_logs(tmp_path,damage,expect):
    kw=fixture(tmp_path)
    log=kw["transcript"]
    contents=log.read_text()
    if damage=="duplicate":contents+="P07_B4G_PHYSICAL_TARGET=PSU\n"
    elif damage=="missing":contents=contents.replace("P07_B4G_P03_ID=0x4C543302\n","")
    elif damage=="fpd":contents=contents.replace("0x00000A00","0x00000100")
    elif damage=="busy":contents=contents.replace("P07_B4G_P03_GLOBAL_STATUS=0x00000000","P07_B4G_P03_GLOBAL_STATUS=0x00000001")
    elif damage=="status":contents=contents.replace("P07_B4G_A53_ELF_DOWNLOAD_AUTHORIZED=0","P07_B4G_A53_ELF_DOWNLOAD_AUTHORIZED=1")
    elif damage=="fail":contents+="P07_B4G_READONLY_PS_PL_SNAPSHOT_FAIL=1\n"
    else:contents=contents.replace("0x00000A00","0xNONHEX")
    log.write_text(contents)
    with pytest.raises(ValueError,match=expect):
        review.evaluate(**kw)


def test_b4h_refuses_drifting_real_bytes_or_unsafe_b4f_claim(tmp_path):
    kw=fixture(tmp_path)
    kw["elf"].write_bytes(b"now altered")
    with pytest.raises(ValueError,match="changed"):
        review.evaluate(**kw)
    kw=fixture(tmp_path/"other")
    raw=json.loads(kw["audit"].read_text())
    raw["board_ELF_download_authorized"]=True
    kw["audit"].write_text(json.dumps(raw))
    with pytest.raises(ValueError,match="unsafe"):
        review.evaluate(**kw)
    kw=fixture(tmp_path/"third")
    kw["bit_provenance"]="independently_accepted"
    with pytest.raises(ValueError,match="provenance"):
        review.evaluate(**kw)
