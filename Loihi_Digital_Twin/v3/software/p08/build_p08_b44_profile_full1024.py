#!/usr/bin/env python3
"""P08-B4.4.2 NEW 1024-image A53 image-only Vitis 2025.2 build, PC ONLY.

Build only; no XSDB, bitstream download, physical session or JTAG.
Exactly original B4m P07 C11 engine plus NEW P08 reset/ingress/meter main.
Staging shell authenticates source, original frozen SHA header, XSA and metrics.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import traceback
import sys

APP="p08_b44_reset_profile_1024"
PLATFORM="p08_b44_reset_profile_platform"
DOMAIN="standalone_psu_cortexa53_0"
IDENTITY="P08_B44_ORIGINAL_27CORE_RESET_PROFILE_1024_A53_V1"
SOURCES=(
    "p08_b44_profile_full1024_a53.c",
    "p08_b4_4_profile_reset.c",
    "p08_b2_ingress.c",
    "p08_b2_context_reset.c",
    "p08_b2_service_meter.c",
    "p07_b4m_dispatch_metadata.c",
    "p07_b4l_b3_bindings.c",
    "p07_b4m_frozen_routes.c",
    "p07_b4m_spike_trace.c",
    "p07_b4m_epoch_bridge.c",
    "p07_b4m_full_inference.c",
    "p07_b4a_current_ingress.c",
    "p07_b2_ingress.c",
    "p07_b3c2_hw_scheduler.c",
    "p07_b3_pager.c",
    "p07_b2_packet.c",
    "p07_b3c_packet_bridge.c",
    "p07_b3c3_next_commit.c",
    "p03_hw_adapter.c",
    "p03_hw_xilinx_io.c",
    "p07_a2_sha256.c",
)
HEADERS=(
    "p08_b2_ingress.h","p08_b2_context_reset.h",
    "p08_b4_4_profile_reset.h",
    "p08_b2_service_meter.h","p08_b2_2_original_context_sha256.h",
    "p07_b4l_b3_bindings.h","p07_b4m_dispatch_metadata.h",
    "p07_b4m_frozen_routes.h","p07_b4m_spike_trace.h",
    "p07_b4m_epoch_bridge.h","p07_b4m_full_inference.h",
    "p07_b4a_current_ingress.h","p07_b2_ingress.h",
    "p07_b3c2_hw_scheduler.h","p07_b3_pager.h",
    "p07_b2_packet.h","p07_b3c_packet_bridge.h",
    "p07_b3c3_next_commit.h","p07_a2_sha256.h",
    "p03_hw_adapter.h","p03_hw_xilinx_io.h",
    "p03_runtime.h","p03_mmio.h","p05_deployment.h",
)

def check_stage(source:Path)->None:
    required=set(SOURCES+HEADERS)
    if not source.is_dir() or source.is_symlink():
        raise ValueError("new isolated source stage directory required")
    actual={p.name for p in source.iterdir() if p.is_file()}
    if required!=actual:
        raise ValueError(f"new Vitis source stage incomplete/extra: missing={required-actual}, extra={actual-required}")
    for file in required:
        if (source/file).is_symlink() or not (source/file).is_file():
            raise ValueError("source stage symlink or missing file: "+file)
    if IDENTITY not in (source/SOURCES[0]).read_text():
        raise ValueError("P08-B4.4.2 fresh firmware identity not present")
    if "p08_b2_original_context_sha256[27][32]" not in (
        source/"p08_b2_2_original_context_sha256.h").read_text():
        raise ValueError("authentic P08-B2.2 27 per-core SHA pin header missing")
    if "#define P07_B2_MAX_ROUTE_BINDINGS 10000u" not in (
        source/"p07_b2_packet.h").read_text():
        raise ValueError("P08 B4m original frozen output route ceiling not selected")

def build(xsa:Path,workspace:Path,source:Path)->None:
    xsa=xsa.resolve(strict=True)
    source=source.resolve(strict=True)
    if workspace.exists() or not xsa.is_file():
        raise ValueError("new workspace and exact XSA required")
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
            raise RuntimeError("new P08-B4.4.2 platform failed to produce XPFM")
        if "empty_application" not in client.get_templates(type="EMBD_APP"):
            raise RuntimeError("Vitis 2025.2 empty application template unavailable")
        client.create_app_component(
            name=APP,platform=str(xpfm),domain=DOMAIN,template="empty_application")
        app=client.get_component(name=APP)
        link_map=workspace/(APP+".map")
        app.set_app_config(key="USER_LINK_OTHER_FLAGS",
                           values=[f"-Wl,-Map={link_map}"])
        app.import_files(from_loc=str(source),files=list(SOURCES+HEADERS),
                         dest_dir_in_cmp="src")
        imported=workspace/APP/"src"
        if ({p.name for p in imported.rglob("*.c")}!=set(SOURCES) or
            {p.name for p in imported.rglob("*.h")}!=set(HEADERS)):
            raise RuntimeError("P08-B4.4.2 Vitis imported wrong C/header source set")
        app.build()
        candidates=sorted((workspace/APP).rglob("*.elf"))
        if len(candidates)!=1:
            raise RuntimeError("require exactly one genuine linked P08 A53 ELF")
        elf=workspace/(APP+".elf")
        shutil.copy2(candidates[0],elf)
        if not link_map.is_file() or not link_map.stat().st_size:
            raise RuntimeError("genuine new P08 linker map absent")
        m=link_map.read_text(errors="replace")
        if ("Linker script and memory map" not in m or
            ".text" not in m or ".bss" not in m or "main" not in m):
            raise RuntimeError("P08 genuine ELF linker map identity incomplete")
        if IDENTITY.encode() not in elf.read_bytes():
            raise RuntimeError("new original B2.4 A53 image-only ELF identity not linked")
        print(f"P08_B44_NEW_RESET_PROFILE_ELF={elf}")
        print(f"P08_B44_NEW_RESET_PROFILE_MAP={link_map}")
        print("P08_B44_NEW_PROFILE_ELF_LINKED_BUT_JTAG_AUTHORIZED=0")
    finally:
        client.close() if hasattr(client,"close") else None

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("xsa","workspace","source-dir"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    try:
        build(a.xsa,a.workspace,a.source_dir)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return 3
    return 0

if __name__=="__main__":
    raise SystemExit(main())
