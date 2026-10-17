#!/usr/bin/env python3
"""Dedicated Vitis 2025.2 standalone A53 build, separate from accepted P05.

Use with scripts/build_p07_a2.sh after selecting a verified physical XSA.
Never reuse an existing Vitis workspace or overwrite golden firmware.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys
import traceback

import vitis

SOURCES = (
    "p07_a4_board.c", "p07_a4_stream.c", "p07_a4_supervisor.c",
    "p07_a2_runtime.c", "p07_a1_ingress.c", "p07_a2_sha256.c",
    "p03_runtime.c", "p03_hw_adapter.c",
    "p03_hw_runtime_bridge.c", "p03_hw_xilinx_io.c",
)
HEADERS = (
    "p07_a1_ingress.h", "p07_a2_runtime.h",
    "p07_a2_batch.h", "p07_a2_sha256.h", "p07_a4_stream.h",
    "p07_a4_supervisor.h",
    "p03_mmio.h", "p03_runtime.h", "p03_hw_adapter.h",
    "p03_hw_runtime_bridge.h", "p03_hw_xilinx_io.h",
)
P07_HEADERS = HEADERS[:6]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xsa", type=Path, required=True)
    ap.add_argument("--workspace", type=Path, required=True)
    ap.add_argument("--source-dir", type=Path, required=True)
    args = ap.parse_args()
    xsa, workspace, source = (
        args.xsa.resolve(), args.workspace.resolve(), args.source_dir.resolve()
    )
    if workspace.exists():
        raise SystemExit("P07-A4.2b refuses to overwrite an existing Vitis workspace")
    if not xsa.is_file() or not source.is_dir():
        raise SystemExit("P07-A4.2b missing routed XSA or staging source directory")
    for name in SOURCES + HEADERS:
        if not (source / name).is_file():
            raise SystemExit("P07-A4.2b missing source/header: " + name)
    for name in P07_HEADERS:
        if not (source / "include" / name).is_file():
            raise SystemExit("P07-A4.2b missing matching nested header: " + name)

    workspace.mkdir(parents=True, exist_ok=False)
    client = vitis.create_client()
    client.set_workspace(path=str(workspace))
    platform_name = "p07_a4_platform"
    domain_name = "standalone_psu_cortexa53_0"
    app_name = "p07_a4_board"
    try:
        client.create_platform_component(
            name=platform_name, hw_design=str(xsa), os="standalone",
            cpu="psu_cortexa53_0", domain_name=domain_name,
            no_boot_bsp=True,
        )
        platform = client.get_component(name=platform_name)
        platform.build()
        xpfm = workspace / platform_name / "export" / platform_name / (
            platform_name + ".xpfm"
        )
        if not xpfm.is_file():
            raise RuntimeError("standalone platform .xpfm not produced")
        templates = client.get_templates(type="EMBD_APP")
        if "empty_application" not in templates:
            raise RuntimeError("Vitis lacks empty_application embedded template")
        client.create_app_component(
            name=app_name, platform=str(xpfm), domain=domain_name,
            template="empty_application",
        )
        app = client.get_component(name=app_name)
        app.import_files(
            from_loc=str(source),
            files=[*SOURCES, *HEADERS],
            dest_dir_in_cmp="src",
        )
        app_src = workspace / app_name / "src"
        nested = app_src / "include"
        if nested.exists():
            raise RuntimeError("unexpected preexisting nested include folder")
        nested.mkdir()
        for name in P07_HEADERS:
            shutil.copy2(source / "include" / name, nested / name)
        actual_c = sorted(p.name for p in app_src.rglob("*.c"))
        if actual_c != sorted(SOURCES):
            raise RuntimeError(
                "P07-A4.2b empty app has wrong C sources: " + repr(actual_c)
            )
        app.build()
        candidates = sorted((workspace / app_name).rglob("*.elf"))
        if len(candidates) != 1:
            raise RuntimeError("expected exactly one P07-A4.2b A53 ELF")
        target = workspace / "p07_a4_board.elf"
        shutil.copy2(candidates[0], target)
        print("P07_A4_XPFM=" + str(xpfm))
        print("P07_A4_ELF=" + str(target))
        print("P07_A4_A53_VITIS_BUILD_PASS=1")
        print("P07_A4_BOARD_STATUS=NOT_RUN")
    except Exception:
        print("P07-A4.2b Vitis standalone build failed; inspect workspace logs",
              file=sys.stderr)
        logs = sorted(workspace.rglob("*.log"))
        for log in logs[-4:]:
            print("--- " + str(log) + " ---", file=sys.stderr)
            try:
                for line in log.read_text(errors="replace").splitlines()[-55:]:
                    print(line, file=sys.stderr)
            except OSError:
                pass
        traceback.print_exc()
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
