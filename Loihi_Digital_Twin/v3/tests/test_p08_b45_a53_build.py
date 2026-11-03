"""P08-B4.5 both genuine A53 source stages, native GCC syntax, no KV260."""
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "software" / "p08"))
import build_p08_b45_variant as build


def file_for(name: str) -> Path:
    for p in (
        ROOT / "software" / "p08" / name,
        ROOT / "software" / "p07" / name,
        ROOT / "software" / "p07" / "include" / name,
        ROOT / "software" / "p03" / name,
        ROOT / "software" / "p03" / "include" / name,
        ROOT / "software" / "p05" / "include" / name,
    ):
        if p.is_file():
            return p
    raise AssertionError("source asset absent: " + name)


def prepare(tmp_path: Path, mode: str) -> Path:
    stage = tmp_path / ("stage_" + mode)
    stage.mkdir()
    for name in build.sources(mode) + build.HEADERS:
        if name == "p08_b2_2_original_context_sha256.h":
            data = ("#include <stdint.h>\n"
                    "const uint8_t p08_b2_original_context_sha256[27][32]={{1}};\n")
        else:
            data = file_for(name).read_text()
        if name == "p07_b2_packet.h":
            assert "#define P07_B2_MAX_ROUTE_BINDINGS 8192u" in data
            data = data.replace("#define P07_B2_MAX_ROUTE_BINDINGS 8192u",
                                "#define P07_B2_MAX_ROUTE_BINDINGS 10000u")
        if name == "p07_a2_sha256.c":
            data = data.replace('#include "include/p07_a2_sha256.h"',
                                '#include "p07_a2_sha256.h"')
        (stage / name).write_text(data)
    return stage


@pytest.mark.parametrize("mode", build.MODES)
def test_variant_exact_source_staging(mode, tmp_path, capsys):
    stage = prepare(tmp_path, mode)
    assert build.check_stage(stage, mode) is None
    assert len(build.sources(mode)) == len(set(build.sources(mode)))
    assert len(build.HEADERS) == len(set(build.HEADERS))
    assert set(build.sources(mode)).isdisjoint(build.HEADERS)
    assert build.MAINS[mode] == build.sources(mode)[0]
    assert "p08_b2_context_reset.c" not in build.sources(mode)
    assert "p08_b4_4_profile_reset.c" not in build.sources(mode)
    assert "p08_b2_3_image_only_a53.c" not in build.sources(mode)
    assert "p08_b44_profile_full1024_a53.c" not in build.sources(mode)
    assert build.main(["--mode", mode, "--check-stage-only", str(stage)]) == 0
    output = capsys.readouterr().out
    assert "P08_B45_SHELL_STAGE_EXACT_PASS=1" in output
    assert "P08_B45_VITIS_INVOKED=0" in output


@pytest.mark.parametrize("mode", build.MODES)
def test_a53_strict_gcc_syntax_with_standalone_stubs(mode, tmp_path):
    cc = shutil.which("gcc") or shutil.which("cc")
    if cc is None:
        pytest.skip("native C compiler unavailable")
    stage = prepare(tmp_path, mode)
    (stage / "xil_cache.h").write_text(
        "#ifndef FAKE_CACHE_H\n#define FAKE_CACHE_H\n"
        "#include <stdint.h>\n#include <stddef.h>\n"
        "typedef uintptr_t INTPTR;\n"
        "void Xil_DCacheInvalidateRange(INTPTR,uint32_t);\n"
        "void Xil_DCacheFlushRange(INTPTR,uint32_t);\n#endif\n"
    )
    (stage / "xil_io.h").write_text(
        "#ifndef FAKE_IO_H\n#define FAKE_IO_H\n"
        "#include <stdint.h>\ntypedef uintptr_t UINTPTR;\n"
        "uint32_t Xil_In32(UINTPTR);\n"
        "void Xil_Out32(UINTPTR,uint32_t);\n#endif\n"
    )
    (stage / "xil_printf.h").write_text(
        "#ifndef FAKE_PRINTF_H\n#define FAKE_PRINTF_H\n"
        "int xil_printf(const char *,...);\n#endif\n"
    )
    run = subprocess.run(
        [cc, "-std=c11", "-fsyntax-only", "-Wall", "-Wextra", "-Werror",
         "-pedantic", "-I", str(stage),
         str(stage / build.MAINS[mode]),
         str(stage / "p08_b45_reset_variants.c"),
         str(stage / "p08_b45_a53_backup_guard.c")],
        capture_output=True, text=True, timeout=45,
    )
    assert run.returncode == 0, run.stdout + "\n" + run.stderr


@pytest.mark.parametrize("mode", build.MODES)
@pytest.mark.parametrize("bad", ("missing_main", "wrong_mode_main", "changed_guard",
                                 "fake_guard_enabled", "missing_reset"))
def test_variant_stage_fail_closed(mode, bad, tmp_path):
    stage = prepare(tmp_path, mode)
    main = stage / build.MAINS[mode]
    if bad == "missing_main":
        main.unlink()
    elif bad == "wrong_mode_main":
        main.write_text(file_for(build.MAINS[
            "unchecked" if mode == "once" else "once"]).read_text())
    elif bad == "changed_guard":
        (stage / "p08_b45_a53_backup_guard.c").write_text(
            "int p08_b45_a53_backup_lock(void){ return 0; }\n")
    elif bad == "fake_guard_enabled":
        guard = stage / "p08_b45_a53_backup_guard.h"
        guard.write_text(guard.read_text().replace(
            "P08_B45_A53_GUARD_PROVISIONED 0u",
            "P08_B45_A53_GUARD_PROVISIONED 1u"))
    elif bad == "missing_reset":
        (stage / "p08_b45_reset_variants.c").unlink()
    with pytest.raises(ValueError):
        build.check_stage(stage, mode)


def test_real_shell_stage_inventory_exact_and_no_board():
    script = ROOT / "scripts" / "build_p08_b45_variant.sh"
    text = script.read_text()
    run = subprocess.run(["bash", "-n", str(script)], capture_output=True,
                         text=True, timeout=15)
    assert run.returncode == 0, run.stderr
    for needle in (
        "P08_B45_MODE", "P08_B45_BUILD_DIR", "P08_B45_ORIGINAL_ELF",
        "P07_B4L_REPORTS", "P08_B2_RESET_PINS",
        "p08_b45_elf_admission.py",
        "P08_B45_EXPERIMENTAL_DESTRUCTIVE_JTAG_PERMISSION=NOT_GRANTED",
        "--check-stage-only",
        "0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1",
        "52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f",
    ):
        assert needle in text
    assert text.index("--check-stage-only") < text.index("vitis -s")
    assert "xsdb " not in text.lower()
    assert "vivado -mode batch" not in text.lower()
    stage_loops = re.findall(
        r'for n in ([\s\S]*?); do\n\s*'
        r'cp -- "\$V3/software/(p08|p07|p03)/(include/)?\$n" '
        r'"\$BUILD/source/"',
        text,
    )
    assert len(stage_loops) == 6
    for mode in build.MODES:
        copies = []
        for block, _, _ in stage_loops:
            names = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_]*\.[ch]\b", block)
            if '"$MAIN"' in block:
                names.insert(0, build.MAINS[mode])
            copies.extend(names)
        copies.extend(["p08_b2_2_original_context_sha256.h", "p05_deployment.h"])
        assert len(copies) == len(set(copies))
        assert set(copies) == set(build.sources(mode) + build.HEADERS)
    assert "p08_b2_3_image_only_a53.c" not in text


def test_unprovisioned_guard_static_and_both_mains_fail_closed():
    guard_c = (ROOT / "software/p08/p08_b45_a53_backup_guard.c").read_text()
    guard_h = (ROOT / "software/p08/p08_b45_a53_backup_guard.h").read_text()
    assert guard_c.count("return -1;") == 2
    assert "#define P08_B45_A53_GUARD_PROVISIONED 0u" in guard_h
    assert "Xil_Out32" not in guard_c
    for mode in build.MODES:
        main = file_for(build.MAINS[mode]).read_text()
        assert f'#define B23_ID "{build.IDENTITIES[mode]}"' in main
        assert "P08_B45_A53_GUARD_PROVISIONED" in main
        assert "reset_config.lock_backup=p08_b45_a53_backup_lock;" in main
        assert "reset_config.backup_lock_valid=p08_b45_a53_backup_lock_valid;" in main
        assert "if(bind_result!=P08_B45_RESET_OK" in main
        assert "p07_b4m_full_run(" in main
        assert "p08_b2_meter_start(" in main
        assert "P08_B2_CONTEXT_TOTAL" in main
        assert "p08_b2_reset_image(" not in main
        assert "p08_b44_profile_reset_image(" not in main



def test_shell_pinned_hashes_match_accepted_b23_and_b44_sources():
    """Avoid mistaken drift from hand-copied literals in the build wrapper.

    Compare the real shell checksum gates with independent accepted source
    pins, not only with constants duplicated in B4.5 tests.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    import p08_b2_3_elf_admission as accepted

    b45 = (ROOT / "scripts/build_p08_b45_variant.sh").read_text()
    b44 = (ROOT / "scripts/build_p08_b44_profile_full1024.sh").read_text()
    for source in (b44, b45):
        source_lines = source.splitlines()
        sha_header = [
            line for line in source_lines
            if 'sha256sum "$PIN_HEADER"' in line
        ]
        xsa = [
            line for line in source_lines
            if 'sha256sum "$XSA"' in line
        ]
        original_elf = [
            line for line in source_lines
            if 'sha256sum "$ORIGINAL_ELF"' in line
        ]
        manifest = [
            line for line in source_lines
            if 'sha256sum "$PIN_MANIFEST"' in line
        ]
        assert len(sha_header) == len(xsa) == len(original_elf) == len(manifest) == 1
        assert re.findall(r"[a-f0-9]{64}", sha_header[0]) == [
            accepted.EXPECTED_PINS_SHA
        ]
        assert re.findall(r"[a-f0-9]{64}", xsa[0]) == [
            accepted.EXPECTED_XSA_SHA
        ]
        assert re.findall(r"[a-f0-9]{64}", original_elf[0]) == [
            "0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1"
        ]
        assert re.findall(r"[a-f0-9]{64}", manifest[0]) == [
            "1d915c36eaf42740bac9e62afae58ffe80c94ae51cbf6c6c809d3fd6e626ce34"
        ]
