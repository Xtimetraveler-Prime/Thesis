"""B.4e REAL XSA/BIT prebuild admission — synthetic offline negative tests.

A ZIP containing an HWH test fixture is NOT an accepted XSA; these tests
exercise only the gate's refusal/integrity behavior, not Vitis or KV260.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import io
import os
import subprocess
import sys
import zipfile

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4e_vitis_inputs as gate


def bundle(tmp:Path):
    reports=tmp/"accepted_report_dir"
    reports.mkdir()
    xsa=reports/"p03_2_ps_mmio.xsa"
    with zipfile.ZipFile(xsa,"w",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("design/system.hwh","<HWH>synthetic NOT original</HWH>")
        z.writestr("design/notes.txt","fake archive")
    bit=reports/"p03_2_ps_mmio.bit"
    bit.write_bytes(b"FAKE_NOT_PHYSICAL_BITSTREAM")
    (reports/"p03_2_ps_mmio.ltx").write_text("<synthetic ltx>")
    (reports/"p03_2_post_route_metrics.txt").write_text(
        "\n".join(sorted(gate.METRICS))+"\n")
    return {
        "reports":reports,"expected_xsa":gate.digest(xsa),
        "expected_bit":gate.digest(bit),"build_dir":tmp/"fresh_real_vitis"
    }


def check(params,**kwargs):
    return gate.evaluate(**(params|kwargs))


def test_synthetic_pinned_hwh_archive_and_readonly_sources_gate(tmp_path):
    params=bundle(tmp_path)
    proof=check(params)
    assert proof["hardware_archive"]["contains_hardware_handoff"] is True
    assert proof["hardware_archive"]["archive_crc_integrity"]=="PASS"
    assert proof["vitis_toolchain_detected"] in (True,False)
    assert len(proof["approved_readonly_build_sources_sha256"])==14
    assert proof["read_only_imported_c_count"]==5
    assert proof["actual_ELF_built"] is False
    assert proof["inference_authorized"] is False
    assert proof["physical_acceptance"] is False
    assert not params["build_dir"].exists()


@pytest.mark.parametrize("change,pattern",[
    ("xsa_hash","XSA pinned SHA256 mismatch"),
    ("bit_hash","BIT pinned SHA256 mismatch"),
    ("xsa_not_zip","not a valid Vivado"),
    ("no_hwh","does not contain"),
    ("route_64","route metrics missing"),
    ("empty_ltx","missing, empty"),
    ("missing_bit","missing, empty"),
    ("existing_build","must be fresh"),
    ("wrong_pin","64-hex"),
])
def test_fail_closed_real_input_mismatch(tmp_path,change,pattern):
    kw=bundle(tmp_path)
    rep=kw["reports"]
    if change=="xsa_hash":kw["expected_xsa"]="a"*64
    if change=="bit_hash":kw["expected_bit"]="b"*64
    if change=="xsa_not_zip":
        f=rep/"p03_2_ps_mmio.xsa"
        f.write_bytes(b"FAKE XSA EXTENSION NOT A ZIP")
        kw["expected_xsa"]=gate.digest(f)
    if change=="no_hwh":
        f=rep/"p03_2_ps_mmio.xsa"
        with zipfile.ZipFile(f,"w") as z:z.writestr("fake/notes.txt","no hardware")
        kw["expected_xsa"]=gate.digest(f)
    if change=="route_64":
        (rep/"p03_2_post_route_metrics.txt").write_text(
            "p03_hpm0_data_width_bits=64\n")
    if change=="empty_ltx":
        (rep/"p03_2_ps_mmio.ltx").write_bytes(b"")
    if change=="missing_bit":(rep/"p03_2_ps_mmio.bit").unlink()
    if change=="existing_build":kw["build_dir"].mkdir()
    if change=="wrong_pin":kw["expected_xsa"]="1234"
    with pytest.raises(ValueError,match=pattern):
        check(kw)


def test_zip_path_traversal_refused_even_with_correct_digest(tmp_path):
    kw=bundle(tmp_path)
    f=kw["reports"]/"p03_2_ps_mmio.xsa"
    with zipfile.ZipFile(f,"w") as z:
        z.writestr("valid.hwh","acceptable")
        z.writestr("../malicious.txt","unsafe")
    kw["expected_xsa"]=gate.digest(f)
    with pytest.raises(ValueError,match="unsafe XSA"):
        check(kw)


def test_required_actual_tools_fail_before_any_build(tmp_path,monkeypatch):
    kw=bundle(tmp_path)
    monkeypatch.setattr(gate.shutil,"which",lambda executable:None)
    with pytest.raises(ValueError,match="missing real Vitis"):
        check(kw,require_tools=True)
    assert not kw["build_dir"].exists()


def test_no_source_manifest_mutation_and_no_repo_build(tmp_path,monkeypatch):
    kw=bundle(tmp_path)
    canonical=gate.exact_source_hashes()
    assert set(canonical)==gate.MANIFEST
    built=ROOT.parent.parent/"temporary_user_must_not_build_here"
    with pytest.raises(ValueError,match="outside Thesis"):
        check(kw,build_dir=built)
    assert not built.exists()
    with pytest.raises(ValueError,match="absolute"):
        check(kw,build_dir=Path("relative/new"))
    source=ROOT/"software/p03/p03_hw_adapter.c"
    assert canonical[source.name]==hashlib.sha256(source.read_bytes()).hexdigest()


def test_operator_script_syntax_and_invalid_pin_never_launches_vitis(tmp_path):
    script=ROOT/"scripts/run_p07_b4e_real_vitis_build.sh"
    assert subprocess.run(["bash","-n",str(script)]).returncode==0
    kw=bundle(tmp_path)
    env=os.environ.copy()
    env.update({
        "P07_B4E_ACCEPTED_REPORTS":str(kw["reports"]),
        "P07_B4E_ACCEPTED_XSA_SHA256":"f"*64, # bad SHA
        "P07_B4E_ACCEPTED_BIT_SHA256":kw["expected_bit"],
        "P07_B4E_PREFLIGHT_DIR":str(tmp_path/"preflight_folder"),
        "P07_B4C_BUILD_DIR":str(kw["build_dir"]),
    })
    run=subprocess.run(["bash",str(script)],env=env,
                       capture_output=True,text=True,timeout=20)
    assert run.returncode!=0
    assert "preflight failed" in run.stderr
    assert not (tmp_path/"preflight_folder").exists()
    assert not kw["build_dir"].exists()
