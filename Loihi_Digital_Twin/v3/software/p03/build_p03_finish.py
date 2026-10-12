#!/usr/bin/env python3
"""Build the P03 final real standalone A53 adapter probe with Vitis 2025.2."""

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
    parser.add_argument("--source-file", default="p03_finish_run.c")
    parser.add_argument("--app-name", default="p03_finish_run")
    args = parser.parse_args()

    xsa = args.xsa.resolve()
    workspace = args.workspace.resolve()
    source_dir = args.source_dir.resolve()

    for path in (xsa, source_dir):
        if not path.exists():
            raise SystemExit(f"missing P03 final input: {path}")

    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)

    client = vitis.create_client()
    client.set_workspace(path=str(workspace))

    platform_name = "p03_finish_platform"
    domain_name = "standalone_psu_cortexa53_0"
    app_name = args.app_name
    source_name = args.source_file
    if source_name != "p03_finish_run.c" or app_name != "p03_finish_run":
        raise SystemExit("P03 final requires a fixed standalone source/app identity")
    source_set = (
        "p03_finish_run.c",
        "p03_runtime.c",
        "p03_hw_adapter.c",
        "p03_hw_runtime_bridge.c",
        "p03_hw_xilinx_io.c",
    )
    header_set = (
        "p03_mmio.h",
        "p03_runtime.h",
        "p03_hw_adapter.h",
        "p03_hw_runtime_bridge.h",
        "p03_hw_xilinx_io.h",
    )

    # P03 final is loaded over XSDB onto an already initialized ZynqMP, so Vitis
    # boot artifacts (FSBL/PMUFW) are unnecessary.  Keep platform creation to
    # the documented standalone A53 inputs and explicitly suppress boot BSP
    # generation.  This also avoids making platform creation depend on an FSBL
    # component that the autonomous runtime never consumes.
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
        print("ERROR: P03 final Vitis standalone platform creation/build failed", file=sys.stderr)
        print(f"P03_FINISH_VITIS_WORKSPACE={workspace}", file=sys.stderr)
        component_dir = workspace / platform_name
        if component_dir.exists():
            print(
                "P03_FINISH_PARTIAL_PLATFORM_FILES="
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
                "P03_FINISH_VITIS_LOGS="
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
        raise SystemExit(f"P03 final platform XPFM was not produced: {xpfm}")

    # Embedded Vitis uses embedded-application template names, which differ
    # from the generic accelerated-application API.  Query the embedded
    # template repository and require the source-free standalone template.
    embedded_templates = client.get_templates(type="EMBD_APP")
    print(
        "P03_FINISH_EMBEDDED_TEMPLATES="
        + ",".join(sorted(str(template) for template in embedded_templates))
    )
    if "empty_application" not in embedded_templates:
        raise SystemExit(
            "P03 final Vitis embedded template repository does not expose "
            "empty_application"
        )

    try:
        app = client.create_app_component(
            name=app_name,
            platform=str(xpfm),
            domain=domain_name,
            template="empty_application",
        )
        app = client.get_component(name=app_name)

        app.import_files(
            from_loc=str(source_dir),
            files=[*source_set, *header_set],
            dest_dir_in_cmp="src",
        )

        app_src_dir = workspace / app_name / "src"
        source_files = sorted(
            path
            for path in app_src_dir.rglob("*")
            if path.is_file()
            and path.suffix.lower() in {".c", ".cc", ".cpp", ".cxx"}
        )
        expected_sources = sorted(app_src_dir / name for name in source_set)
        if source_files != expected_sources:
            raise RuntimeError(
                "P03 final missing/extra C sources in empty application: "
                f"actual={source_files}, expected={expected_sources}"
            )

        print("PASS: P03 final embedded empty-application created and autonomous runtime sources imported")
        app.build()
    except Exception:
        print(
            "ERROR: P03 final Vitis application creation/import/build failed",
            file=sys.stderr,
        )
        print(f"P03_FINISH_VITIS_WORKSPACE={workspace}", file=sys.stderr)
        app_dir = workspace / app_name
        if app_dir.exists():
            print(
                "P03_FINISH_PARTIAL_APP_FILES="
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
                "P03_FINISH_VITIS_LOGS="
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
            "P03 final expected exactly one application ELF, got "
            f"{[str(path) for path in elf_candidates]}"
        )

    elf = elf_candidates[0]
    out = workspace / f"{app_name}.elf"
    shutil.copy2(elf, out)

    print(f"P03_FINISH_XPFM={xpfm}")
    print(f"P03_FINISH_ELF={out}")
    print("PASS: P03 final standalone A53 runtime-adapter probe built")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
