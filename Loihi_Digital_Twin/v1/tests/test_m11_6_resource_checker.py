from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "rtl" / "core_v1" / "check_m11_6_resources.py"


def _run(tmp_path: Path, *, clb_luts: int = 2000) -> subprocess.CompletedProcess[str]:
    util = tmp_path / "utilization_impl.rpt"
    ram = tmp_path / "ram_utilization_impl.rpt"
    util.write_text(
        "\n".join(
            [
                "| Site Type | Used | Fixed | Prohibited | Available | Util% |",
                f"| CLB LUTs | {clb_luts} | 0 | 0 | 117120 | 1.71 |",
                "| CLB Registers | 1000 | 0 | 0 | 234240 | 0.43 |",
                "| DSPs | 2 | 0 | 0 | 1248 | 0.16 |",
                "| URAM | 0 | 0 | 0 | 64 | 0.00 |",
            ]
        ),
        encoding="utf-8",
    )
    # Deliberately no `Block RAM Tile` row. This freezes the actual M11.6
    # post-implementation format that exposed the original parser bug.
    ram.write_text(
        "\n".join(
            [
                "| RAM Type | Used |",
                "| RAMB36/FIFO* | 25 |",
                "| RAMB18 | 3 |",
            ]
        ),
        encoding="utf-8",
    )
    return subprocess.run(
        [sys.executable, str(CHECKER), str(util), str(ram)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_m11_6_resource_checker_accepts_split_vivado_reports(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "M11.6 implementation resource check passed:" in result.stdout
    assert "BRAM_TILE<=27/144 (RAMB36=25, RAMB18=3)" in result.stdout


def test_m11_6_resource_checker_rejects_k26_overflow(tmp_path: Path) -> None:
    result = _run(tmp_path, clb_luts=117121)
    assert result.returncode != 0
    assert "exceeds K26 physical resource capacity" in result.stderr
