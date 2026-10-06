#!/usr/bin/env python3
"""Build the P03.2c standalone Cortex-A53 smoke application with Vitis 2025.2."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil

import vitis


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xsa", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    args = parser.parse_args()

    xsa = args.xsa.resolve()
    workspace = args.workspace.resolve()
    source_dir = args.source_dir.resolve()

    for path in (xsa, source_dir):
        if not path.exists():
            raise SystemExit(f"missing P03.2c input: {path}")

    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)

    client = vitis.create_client()
    client.set_workspace(path=str(workspace))

    platform_name = "p03_2c_platform"
    domain_name = "standalone_psu_cortexa53_0"
    app_name = "p03_2c_smoke"

    # P03.2c is loaded over XSDB onto an already initialized ZynqMP, so Vitis
    # boot artifacts (FSBL/PMUFW) are unnecessary.  Keep platform creation to
    # the documented standalone A53 inputs and explicitly suppress boot BSP
    # generation.  This also avoids making platform creation depend on an FSBL
    # component that the smoke never consumes.
    platform = client.create_platform_component(
        name=platform_name,
        hw_design=str(xsa),
        os="standalone",
        cpu="psu_cortexa53_0",
        domain_name=domain_name,
        no_boot_bsp=True,
    )
    platform = client.get_component(name=platform_name)
    platform.build()

    xpfm = (
        workspace
        / platform_name
        / "export"
        / platform_name
        / f"{platform_name}.xpfm"
    )
    if not xpfm.exists():
        raise SystemExit(f"P03.2c platform XPFM was not produced: {xpfm}")

    app = client.create_app_component(
        name=app_name,
        platform=str(xpfm),
        domain=domain_name,
        template="empty",
    )
    app = client.get_component(name=app_name)
    app.import_files(
        from_loc=str(source_dir),
        files=["p03_2c_smoke.c", "p03_mmio.h", "p03_2c_fixture.h"],
        dest_dir_in_cmp="src",
    )
    app.build()

    elf_candidates = sorted((workspace / app_name).rglob("*.elf"))
    if len(elf_candidates) != 1:
        raise SystemExit(
            "P03.2c expected exactly one application ELF, got "
            f"{[str(path) for path in elf_candidates]}"
        )

    elf = elf_candidates[0]
    out = workspace / "p03_2c_smoke.elf"
    shutil.copy2(elf, out)

    print(f"P03_2C_XPFM={xpfm}")
    print(f"P03_2C_ELF={out}")
    print("PASS: P03.2c standalone Cortex-A53 smoke application built")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
