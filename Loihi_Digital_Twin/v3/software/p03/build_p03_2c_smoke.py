#!/usr/bin/env python3
"""Build the P03.2c standalone Cortex-A53 smoke application with Vitis 2025.2."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys
import traceback

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
    try:
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
    except Exception:
        print("ERROR: P03.2c Vitis standalone platform creation/build failed", file=sys.stderr)
        print(f"P03_2C_VITIS_WORKSPACE={workspace}", file=sys.stderr)
        component_dir = workspace / platform_name
        if component_dir.exists():
            print(
                "P03_2C_PARTIAL_PLATFORM_FILES="
                + ",".join(
                    str(path.relative_to(workspace))
                    for path in sorted(component_dir.rglob("*"))
                    if path.is_file()
                ),
                file=sys.stderr,
            )
        logs = sorted(workspace.rglob("*.log"))
        if logs:
            print(
                "P03_2C_VITIS_LOGS="
                + ",".join(str(path.relative_to(workspace)) for path in logs),
                file=sys.stderr,
            )
            for log in logs[-5:]:
                try:
                    lines = log.read_text(
                        encoding="utf-8", errors="replace"
                    ).splitlines()
                except OSError:
                    continue
                print(f"--- tail {log} ---", file=sys.stderr)
                for line in lines[-80:]:
                    print(line, file=sys.stderr)
        traceback.print_exc()
        raise SystemExit(2)

    xpfm = (
        workspace
        / platform_name
        / "export"
        / platform_name
        / f"{platform_name}.xpfm"
    )
    if not xpfm.exists():
        raise SystemExit(f"P03.2c platform XPFM was not produced: {xpfm}")

    # Vitis Embedded 2025.2 on this installation rejects the documented
    # generic "empty" application template because its embedded template
    # package has no src directory.  AMD's embedded examples use the
    # "hello_world" template for standalone application components, so use it
    # only as a recognized scaffold and replace its example source completely.
    try:
        app = client.create_app_component(
            name=app_name,
            platform=str(xpfm),
            domain=domain_name,
            template="hello_world",
        )
        app = client.get_component(name=app_name)

        app_src_dir = workspace / app_name / "src"
        if not app_src_dir.is_dir():
            raise RuntimeError(
                f"P03.2c application src directory was not created: {app_src_dir}"
            )

        removed_scaffold = []
        for template_file in sorted(app_src_dir.rglob("*")):
            if not template_file.is_file():
                continue
            if template_file.suffix.lower() in {
                ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"
            }:
                removed_scaffold.append(
                    str(template_file.relative_to(workspace / app_name))
                )
                template_file.unlink()

        app.import_files(
            from_loc=str(source_dir),
            files=["p03_2c_smoke.c", "p03_mmio.h", "p03_2c_fixture.h"],
            dest_dir_in_cmp="src",
        )

        source_files = sorted(
            path
            for path in app_src_dir.rglob("*")
            if path.is_file()
            and path.suffix.lower() in {".c", ".cc", ".cpp", ".cxx"}
        )
        if source_files != [app_src_dir / "p03_2c_smoke.c"]:
            raise RuntimeError(
                "P03.2c expected exactly its own smoke C source after replacing "
                f"the template scaffold, got {source_files}"
            )

        print(
            "P03_2C_REMOVED_TEMPLATE_SOURCES="
            + ",".join(removed_scaffold)
        )
        print("PASS: P03.2c hello-world scaffold replaced with smoke sources")

        app.build()
    except Exception:
        print(
            "ERROR: P03.2c Vitis application creation/import/build failed",
            file=sys.stderr,
        )
        print(f"P03_2C_VITIS_WORKSPACE={workspace}", file=sys.stderr)
        app_dir = workspace / app_name
        if app_dir.exists():
            print(
                "P03_2C_PARTIAL_APP_FILES="
                + ",".join(
                    str(path.relative_to(workspace))
                    for path in sorted(app_dir.rglob("*"))
                    if path.is_file()
                ),
                file=sys.stderr,
            )
        logs = sorted(workspace.rglob("*.log"))
        if logs:
            print(
                "P03_2C_VITIS_LOGS="
                + ",".join(str(path.relative_to(workspace)) for path in logs),
                file=sys.stderr,
            )
            for log in logs[-5:]:
                try:
                    lines = log.read_text(
                        encoding="utf-8", errors="replace"
                    ).splitlines()
                except OSError:
                    continue
                print(f"--- tail {log} ---", file=sys.stderr)
                for line in lines[-80:]:
                    print(line, file=sys.stderr)
        traceback.print_exc()
        raise SystemExit(3)

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
