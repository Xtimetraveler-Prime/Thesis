"""P08-B4.5 native reset-variant regressions; no physical hardware."""
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
P08 = ROOT / "software" / "p08"
P07 = ROOT / "software" / "p07"


def test_native_authenticated_once_and_unchecked_content_variants(tmp_path):
    cc = shutil.which("gcc") or shutil.which("cc")
    if not cc:
        import pytest
        pytest.skip("native C compiler unavailable")

    exe = tmp_path / "p08_b45_reset_variants"
    cmd = [
        cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-I", str(P08), "-I", str(P07 / "include"),
        str(ROOT / "tests" / "native" / "p08_b45_reset_variants_native.c"),
        str(P08 / "p08_b45_reset_variants.c"),
        str(P07 / "p07_a2_sha256.c"),
        "-o", str(exe),
    ]
    built = subprocess.run(cmd, cwd=tmp_path, capture_output=True,
                           text=True, timeout=120)
    assert built.returncode == 0, built.stdout + "\n" + built.stderr

    run = subprocess.run([str(exe)], cwd=tmp_path, capture_output=True,
                         text=True, timeout=180)
    assert run.returncode == 0, run.stdout + "\n" + run.stderr
    expected = (
        "P08_B45_AUTHENTICATED_ONCE_27_SHA_BIND_AND_LIGHTWEIGHT_RESET_PASS=1",
        "P08_B45_AUTHENTICATED_ONCE_NO_PER_IMAGE_SHA_PASS=1",
        "P08_B45_UNCHECKED_CONTENT_NO_SHA_OR_HEADER_VALIDATION_PASS=1",
        "P08_B45_PERSISTENT_BACKUP_LOCK_REQUIRED_AND_ENFORCED_BY_CALLBACK_PASS=1",
        "P08_B45_BODY_MUTATION_AFTER_BIND_IS_NOT_DETECTED_WITHOUT_REAL_LOCK=1",
        "P08_B45_OPERATIONAL_FAILURE_POISONS_SESSION_PASS=1",
        "P08_B45_PHYSICAL_KV260_EXECUTED=0",
    )
    for marker in expected:
        assert run.stdout.splitlines().count(marker) == 1


def test_experiments_do_not_replace_accepted_reset_sources():
    original = (P08 / "p08_b2_context_reset.c").read_text()
    original_header = (P08 / "p08_b2_context_reset.h").read_text()
    profile = (P08 / "p08_b4_4_profile_reset.c").read_text()
    production = (P08 / "p08_b2_3_image_only_a53.c").read_text()
    variants = (P08 / "p08_b45_reset_variants.c").read_text()

    assert "p08_b45_reset_image" not in original
    assert "p08_b45_reset_image" not in original_header
    assert "p08_b45_reset_image" not in profile
    assert "p08_b45_reset_image" not in production
    assert "p08_b2_reset_image" in original
    assert "p08_b2_reset_image" in production
    assert "p07_a2_sha256" in variants
    assert "P08_B45_AUTHENTICATED_ONCE" in variants
    assert "P08_B45_UNCHECKED_CONTENT" in variants
