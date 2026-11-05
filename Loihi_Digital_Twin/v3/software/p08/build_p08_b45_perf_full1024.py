#!/usr/bin/env python3
"""P08-B4.5: isolated UNPROTECTED performance-only full1024 A53 build, PC ONLY.

Vitis 2025.2 standalone build based on the accepted B4.4 image-only flow.
Imports the exact frozen P07/P03 source plus the selected experimental
reset application. No XSDB, Vivado hardware manager, JTAG, DDR or PL action.
Explicitly opt-out-of-immutability reset kernel; NO lock claims. No board.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import sys
import traceback

V3 = Path(__file__).resolve().parents[2]
DOMAIN = "standalone_psu_cortexa53_0"
MODES = ("once", "unchecked")
MAINS = {
    "once": "p08_b45_perf_once_full1024_a53.c",
    "unchecked": "p08_b45_perf_unchecked_full1024_a53.c",
}
IDENTITIES = {
    "once": "P08_B45_PERF_AUTH_ONCE_ORIGINAL_27CORE_1024_A53_V1",
    "unchecked": "P08_B45_PERF_UNCHECKED_ORIGINAL_27CORE_1024_A53_V1",
}
DONE = {
    "once": "P08_B45_PERF_AUTH_ONCE_1024_TERMINAL_DONE=1",
    "unchecked": "P08_B45_PERF_UNCHECKED_1024_TERMINAL_DONE=1",
}
APPS = {
    "once": "p08_b45_perf_once_full1024",
    "unchecked": "p08_b45_perf_unchecked_full1024",
}
SHARED_SOURCES = (
    "p08_b45_perf_reset.c",
    "p08_b2_ingress.c",
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
HEADERS = (
    "p08_b2_ingress.h", "p08_b2_context_reset.h",
    "p08_b45_reset_variants.h", "p08_b45_perf_reset.h",
    "p08_b2_service_meter.h", "p08_b2_2_original_context_sha256.h",
    "p07_b4l_b3_bindings.h", "p07_b4m_dispatch_metadata.h",
    "p07_b4m_frozen_routes.h", "p07_b4m_spike_trace.h",
    "p07_b4m_epoch_bridge.h", "p07_b4m_full_inference.h",
    "p07_b4a_current_ingress.h", "p07_b2_ingress.h",
    "p07_b3c2_hw_scheduler.h", "p07_b3_pager.h",
    "p07_b2_packet.h", "p07_b3c_packet_bridge.h",
    "p07_b3c3_next_commit.h", "p07_a2_sha256.h",
    "p03_hw_adapter.h", "p03_hw_xilinx_io.h",
    "p03_runtime.h", "p03_mmio.h", "p05_deployment.h",
)

def sources(mode: str) -> tuple[str, ...]:
    if mode not in MODES:
        raise ValueError("P08-B4.5 unknown experiment mode")
    return (MAINS[mode],) + SHARED_SOURCES

def check_stage(source: Path, mode: str) -> None:
    expected = set(sources(mode) + HEADERS)
    if not source.is_dir() or source.is_symlink():
        raise ValueError("isolated, existing, non-symlink source stage required")
    actual = {p.name for p in source.iterdir() if p.is_file()}
    if actual != expected or len(expected) != len(sources(mode) + HEADERS):
        raise ValueError(
            f"source stage incomplete/extra for {mode}: "
            f"missing={expected - actual}, extra={actual - expected}"
        )
    if any((source / n).is_symlink() for n in expected):
        raise ValueError("no symlink permitted in source stage")
    chosen = (source / MAINS[mode]).read_text()
    if IDENTITIES[mode] not in chosen or DONE[mode] not in chosen:
        raise ValueError("chosen unique A53 main identity/terminal absent")
    if "p08_b45_perf_reset_bind(" not in chosen or "p08_b45_perf_reset_image(" not in chosen:
        raise ValueError("A53 main does not use the new reset variant")
    if ("#define B23_FRAMES 1024u" not in chosen or
            "#define B23_RAW_POOL_BYTES (1024u*784u)" not in chosen or
            "words[19]=0u;" not in chosen or
            "reset_config.lock_backup=" in chosen or
            "p08_b45_a53_backup_lock" in chosen):
        raise ValueError("full1024 experiment must run exactly 1024 original raw frames and never fake backup protection")
    for n in (MAINS[mode], "p08_b45_perf_reset.c", "p08_b45_perf_reset.h"):
        original = V3 / "software" / "p08" / n
        if hashlib.sha256((source / n).read_bytes()).digest() != hashlib.sha256(
            original.read_bytes()
        ).digest():
            raise ValueError("unreviewed separate performance-only source drift: " + n)
    clone=(source / "p08_b45_perf_reset.c").read_text()
    if ("int p08_b45_perf_reset_bind(" not in clone or
        "int p08_b45_perf_reset_image(" not in clone or
        "config->lock_backup(" in clone or
        "config->backup_lock_valid(" in clone or
        "Xil_Out32" in clone):
        raise ValueError("performance kernel contains false security callback or MMIO writes")
    if any("p08_b45_a53_backup_guard" in p.name for p in source.iterdir()):
        raise ValueError("protected/guarded source may not enter performance experiment")


def build(xsa: Path, workspace: Path, source: Path, mode: str) -> None:
    xsa = xsa.resolve(strict=True)
    source = source.resolve(strict=True)
    if workspace.exists() or not xsa.is_file():
        raise ValueError("fresh workspace and existing original XSA required")
    check_stage(source, mode)

    import vitis

    workspace.mkdir(parents=True, exist_ok=False)
    platform_name = "p08_b45_perf_" + mode + "_platform"
    app_name = APPS[mode]
    client = vitis.create_client()
    client.set_workspace(path=str(workspace))
    try:
        client.create_platform_component(
            name=platform_name,
            hw_design=str(xsa),
            os="standalone",
            cpu="psu_cortexa53_0",
            domain_name=DOMAIN,
            no_boot_bsp=True,
        )
        platform = client.get_component(name=platform_name)
        platform.build()
        xpfm = (
            workspace / platform_name / "export" /
            platform_name / (platform_name + ".xpfm")
        )
        if not xpfm.is_file():
            raise RuntimeError("new B4.5 platform failed to produce XPFM")
        if "empty_application" not in client.get_templates(type="EMBD_APP"):
            raise RuntimeError("Vitis empty application template unavailable")
        client.create_app_component(
            name=app_name,
            platform=str(xpfm),
            domain=DOMAIN,
            template="empty_application",
        )
        app = client.get_component(name=app_name)
        link_map = workspace / (app_name + ".map")
        app.set_app_config(
            key="USER_LINK_OTHER_FLAGS", values=[f"-Wl,-Map={link_map}"]
        )
        app.import_files(
            from_loc=str(source),
            files=list(sources(mode) + HEADERS),
            dest_dir_in_cmp="src",
        )
        imported = workspace / app_name / "src"
        if (
            {p.name for p in imported.rglob("*.c")} != set(sources(mode))
            or {p.name for p in imported.rglob("*.h")} != set(HEADERS)
        ):
            raise RuntimeError("B4.5 imported unexpected sources")
        app.build()
        candidates = sorted((workspace / app_name).rglob("*.elf"))
        if len(candidates) != 1:
            raise RuntimeError("require exactly one genuine linked A53 ELF")
        elf = workspace / (app_name + ".elf")
        shutil.copy2(candidates[0], elf)
        if not link_map.is_file() or not link_map.stat().st_size:
            raise RuntimeError("genuine A53 linker map absent")
        linker = link_map.read_text(errors="replace")
        if any(marker not in linker for marker in (
            "Linker script and memory map", ".text", ".bss",
            "main", "p08_b45_perf_reset_bind", "p08_b45_perf_reset_image",
            "p07_b4m_full_run", "p08_b2_meter_start",
        )):
            raise RuntimeError("new B4.5 linker map missing required symbols")
        binary = elf.read_bytes()
        if (IDENTITIES[mode].encode() not in binary or
                DONE[mode].encode() not in binary or
                any(IDENTITIES[m].encode() in binary for m in MODES if m != mode)):
            raise RuntimeError("A53 ELF identity/terminal mismatch")
        print("P08_B45_PERF_FULL1024_ELF=" + str(elf))
        print("P08_B45_PERF_FULL1024_MAP=" + str(link_map))
        print("P08_B45_PERF_HARDWARE_BACKUP_PROTECTED=0")
        print("P08_B45_PERF_JTAG_AUTHORIZED_BY_BUILD=0")
    finally:
        client.close() if hasattr(client, "close") else None

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=MODES, required=True)
    for n in ("xsa", "workspace", "source-dir"):
        p.add_argument("--" + n, type=Path)
    p.add_argument("--check-stage-only", type=Path)
    a = p.parse_args(argv)
    try:
        if a.check_stage_only is not None:
            if any(x is not None for x in (a.xsa, a.workspace, a.source_dir)):
                raise ValueError("stage-only is incompatible with Vitis build")
            check_stage(a.check_stage_only, a.mode)
            print("P08_B45_PERF_FULL1024_STAGE_EXACT_PASS=1")
            print("P08_B45_PERF_VITIS_INVOKED=0")
            return 0
        if any(x is None for x in (a.xsa, a.workspace, a.source_dir)):
            raise ValueError("Vitis build needs --xsa --workspace --source-dir")
        build(a.xsa, a.workspace, a.source_dir, a.mode)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return 3
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
