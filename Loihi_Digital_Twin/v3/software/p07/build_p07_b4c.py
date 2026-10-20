#!/usr/bin/env python3
"""P07-B.4c isolated Vitis 2025.2 read-only A53 ELF candidate build.

Reuses the original successful P05/P07-A Vitis Python APIs. Must be invoked
inside a user-owned Vitis installation with pinned XSA, in a fresh workspace.
Never launches a board, installs firmware, touches FPGA or opens B2 TEST.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys
import traceback

APP = "p07_b4c_readonly_probe"
PLATFORM = "p07_b4c_readonly_platform"
DOMAIN = "standalone_psu_cortexa53_0"
SOURCES = (
    "p07_b4c_readonly_board.c",
    "p07_b4b_board_admission.c",
    "p07_b4b_xilinx_platform.c",
    "p03_hw_adapter.c",
    "p03_hw_xilinx_io.c",
)
HEADERS = (
    "p07_b4b_board_admission.h",
    "p07_b4b_xilinx_platform.h",
    "p07_b4a_current_ingress.h",
    "p07_b2_ingress.h",
    "p07_b3_pager.h",
    "p03_hw_adapter.h",
    "p03_hw_xilinx_io.h",
    "p03_runtime.h",
    "p03_mmio.h",
)
# P07 dependencies are header-only for this probe; no inferencing C source.
# A dedicated app must *not* import B4a/B3c pager, event writer, packet
# transport or HLS inference drivers.
EXPECTED = frozenset(SOURCES + HEADERS)


def check_stage(source: Path) -> None:
    if not source.is_dir():
        raise ValueError("missing isolated source staging directory")
    actual = {p.name for p in source.iterdir() if p.is_file()}
    if actual != EXPECTED:
        raise ValueError(f"unapproved/missing staged build files: "
                         f"missing={sorted(EXPECTED-actual)}, "
                         f"extra={sorted(actual-EXPECTED)}")
    for name in SOURCES + HEADERS:
        if not (source/name).is_file() or (source/name).is_symlink():
            raise ValueError(f"not an ordinary staged file: {name}")
    if not (source/"p07_b4c_readonly_board.c").read_text(
        encoding="utf8"
    ).find("P07_B4C_A53_READONLY_FPD128_SHELL_PROBE_V1") >= 0:
        raise ValueError("build identity missing from read-only main")


def build(xsa: Path, workspace: Path, source: Path) -> tuple[Path, Path]:
    xsa=xsa.resolve(strict=True)
    source=source.resolve(strict=True)
    if not xsa.is_file():
        raise ValueError("missing physical XSA")
    check_stage(source)
    if workspace.exists():
        raise ValueError("refusing an already existing Vitis workspace")
    # Import only after all filesystem admission checks. This also allows
    # negative host tests without requiring the actual Vitis installation.
    import vitis
    workspace.mkdir(parents=True, exist_ok=False)
    client=vitis.create_client()
    client.set_workspace(path=str(workspace))
    try:
        client.create_platform_component(
            name=PLATFORM,hw_design=str(xsa),os="standalone",
            cpu="psu_cortexa53_0",domain_name=DOMAIN,no_boot_bsp=True,
        )
        platform=client.get_component(name=PLATFORM)
        platform.build()
        xpfm=(workspace/PLATFORM/"export"/PLATFORM/(PLATFORM+".xpfm"))
        if not xpfm.is_file():
            raise RuntimeError("Vitis did not export the accepted platform XPFM")
        templates=client.get_templates(type="EMBD_APP")
        if "empty_application" not in templates:
            raise RuntimeError("embedded empty_application template absent")
        client.create_app_component(
            name=APP,platform=str(xpfm),domain=DOMAIN,
            template="empty_application",
        )
        app=client.get_component(name=APP)
        app.import_files(
            from_loc=str(source),files=list(SOURCES+HEADERS),
            dest_dir_in_cmp="src",
        )
        imported=workspace/APP/"src"
        actual_c={p.name for p in imported.rglob("*.c")}
        if actual_c!=set(SOURCES):
            raise RuntimeError("read-only application has missing/extra C: "
                               +repr(sorted(actual_c)))
        actual_h={p.name for p in imported.rglob("*.h")}
        if actual_h!=set(HEADERS):
            raise RuntimeError("read-only application has missing/extra H: "
                               +repr(sorted(actual_h)))
        app.build()
        binaries=sorted((workspace/APP).rglob("*.elf"))
        if len(binaries)!=1:
            raise RuntimeError("expected exactly one genuine Vitis A53 ELF")
        elf=workspace/(APP+".elf")
        shutil.copy2(binaries[0],elf)
        # A linker map is mandatory. A default Vitis BSP can be configured
        # to emit no map: that is a NO-GO, never an excuse to invent one.
        maps=sorted(p for p in (workspace/APP).rglob("*.map")
                    if p.is_file() and p.stat().st_size>0)
        if len(maps)!=1:
            raise RuntimeError(
                "expected one generated linker .map (configure Vitis -Wl,-Map; "
                "do not fabricate a map): "+repr([str(p) for p in maps])
            )
        final_map=workspace/(APP+".map")
        shutil.copy2(maps[0],final_map)
        print(f"P07_B4C_XPFM={xpfm}")
        print(f"P07_B4C_CANDIDATE_ELF={elf}")
        print(f"P07_B4C_CANDIDATE_MAP={final_map}")
        print("P07_B4C_ELF_CREATED_NOT_BOARD_RUN=1")
        return elf,final_map
    except Exception:
        print("P07-B.4c Vitis failed; preserve isolated workspace and logs",
              file=sys.stderr)
        for log in sorted(workspace.rglob("*.log"))[-5:]:
            print("--- "+str(log),file=sys.stderr)
            for line in log.read_text(errors="replace").splitlines()[-65:]:
                print(line,file=sys.stderr)
        traceback.print_exc()
        raise


def main() -> int:
    arg=argparse.ArgumentParser()
    arg.add_argument("--xsa",required=True,type=Path)
    arg.add_argument("--workspace",required=True,type=Path)
    arg.add_argument("--source-dir",required=True,type=Path)
    args=arg.parse_args()
    try:
        build(args.xsa,args.workspace,args.source_dir)
    except (ValueError,OSError,RuntimeError):
        return 3
    return 0


if __name__=="__main__":
    raise SystemExit(main())
