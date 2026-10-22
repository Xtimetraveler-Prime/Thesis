#!/usr/bin/env python3
"""Isolated Vitis 2025.2 B4l paging probe build; no FPGA, JTAG or Linux actions.
Uses the proven B4c Vitis API sequence; new distinct app/source identity.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import traceback
import sys

APP="p07_b4l_paging_probe"
PLATFORM="p07_b4l_paging_platform"
DOMAIN="standalone_psu_cortexa53_0"
SOURCES=(
    "p07_b4l_paging_probe_board.c",
    "p07_b4l_page_probe.c",
    "p03_hw_adapter.c",
    "p03_hw_xilinx_io.c",
)
HEADERS=(
    "p07_b4l_page_probe.h",
    "p03_hw_adapter.h",
    "p03_hw_xilinx_io.h",
    "p03_runtime.h",
    "p03_mmio.h",
)
IDENTITY="P07_B4L_A53_27CORE_PAGING_PROBE_V1"

def check_stage(source:Path)->None:
    required=set(SOURCES+HEADERS)
    if not source.is_dir():
        raise ValueError("missing independent B4l staging directory")
    actual={p.name for p in source.iterdir() if p.is_file()}
    if required!=actual:
        raise ValueError(f"staged B4l source mismatch: missing={required-actual}, extra={actual-required}")
    for file in required:
        if (source/file).is_symlink() or not (source/file).is_file():
            raise ValueError("invalid staged input "+file)
    if IDENTITY not in (source/SOURCES[0]).read_text():
        raise ValueError("missing distinct B4l application identity")

def build(xsa:Path,workspace:Path,source:Path)->None:
    xsa=xsa.resolve(strict=True)
    source=source.resolve(strict=True)
    if workspace.exists() or not xsa.is_file():
        raise ValueError("new workspace and valid XSA required")
    check_stage(source)
    import vitis
    workspace.mkdir(parents=True,exist_ok=False)
    client=vitis.create_client()
    client.set_workspace(path=str(workspace))
    try:
        client.create_platform_component(
            name=PLATFORM,hw_design=str(xsa),os="standalone",
            cpu="psu_cortexa53_0",domain_name=DOMAIN,no_boot_bsp=True)
        platform=client.get_component(name=PLATFORM)
        platform.build()
        xpfm=workspace/PLATFORM/"export"/PLATFORM/(PLATFORM+".xpfm")
        if not xpfm.is_file():
            raise RuntimeError("Vitis did not produce B4l XPFM")
        if "empty_application" not in client.get_templates(type="EMBD_APP"):
            raise RuntimeError("missing Vitis empty application template")
        client.create_app_component(
            name=APP,platform=str(xpfm),domain=DOMAIN,template="empty_application")
        app=client.get_component(name=APP)
        link_map=workspace/(APP+".map")
        app.set_app_config(key="USER_LINK_OTHER_FLAGS",
                           values=[f"-Wl,-Map={link_map}"])
        app.import_files(from_loc=str(source),files=list(SOURCES+HEADERS),
                         dest_dir_in_cmp="src")
        imported=workspace/APP/"src"
        if {p.name for p in imported.rglob("*.c")}!=set(SOURCES) or (
            {p.name for p in imported.rglob("*.h")}!=set(HEADERS)
        ):
            raise RuntimeError("Vitis B4l source import is incomplete or polluted")
        app.build()
        candidates=sorted((workspace/APP).rglob("*.elf"))
        if len(candidates)!=1:
            raise RuntimeError("require exactly one linked B4l ELF")
        elf=workspace/(APP+".elf")
        shutil.copy2(candidates[0],elf)
        if not link_map.is_file() or not link_map.stat().st_size:
            raise RuntimeError("missing REAL linker-emitted B4l GNU map")
        m=link_map.read_text(errors="replace")
        if "Linker script and memory map" not in m or (
            ".text" not in m or ".bss" not in m or "main" not in m
        ):
            raise RuntimeError("not a real/complete B4l GNU map")
        if IDENTITY.encode() not in elf.read_bytes():
            raise RuntimeError("B4l ELF missing unique entry identity")
        print(f"P07_B4L_ELF={elf}")
        print(f"P07_B4L_REAL_MAP={link_map}")
        print("P07_B4L_LINKED_NOT_BOARD_RUN=1")
    finally:
        client.close() if hasattr(client,"close") else None

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--xsa",type=Path,required=True)
    p.add_argument("--workspace",type=Path,required=True)
    p.add_argument("--source-dir",type=Path,required=True)
    a=p.parse_args()
    try:
        build(a.xsa,a.workspace,a.source_dir)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return 3
    return 0

if __name__=="__main__":
    raise SystemExit(main())
