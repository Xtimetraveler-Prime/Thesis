"""Create a PER-RUN M06 paged-rolling Vitis HLS 2025.2 config.

Vitis may chdir to --work_dir's PARENT before interpreting the INI. Plain
`syn.file=hls/...` and `tb.file=hls/...` then fail to resolve, even when
the caller started in the source root. See M05 actual 2026-11-08 CSim logs.

This utility has zero external dependencies, never invokes hardware or tools,
and exclusively creates an evidence-local config; no checked-in files change.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shlex


FILES = {"syn.file", "tb.file"}
INCLUDE_FIELDS = {"syn.cflags", "syn.csimflags", "tb.cflags"}
ALLOWED_TOPS = {"m06_paged_rolling_replay"}
EXPECTED_PART = "xck26-sfvc784-2LV-c"


def prepare(source_root: Path, template: Path, output: Path, top: str) -> dict:
    root = source_root.resolve(strict=True)
    cfg = template.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("source root must be a directory")
    if not cfg.is_relative_to(root):
        raise ValueError("HLS config must live inside source root")
    if top not in ALLOWED_TOPS:
        raise ValueError("unknown HLS top")
    if output.exists():
        raise FileExistsError("refusing to replace an existing HLS config")

    section = None
    rewritten = []
    source_paths = []
    include_paths = []
    keys = {}

    for raw in cfg.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].lower()
            rewritten.append(raw)
            continue
        if not line or line.startswith("#"):
            rewritten.append(raw)
            continue
        if "=" not in raw:
            raise ValueError(f"malformed HLS config line: {raw!r}")
        key, val = (part.strip() for part in raw.split("=", 1))
        full_key = (section, key)
        keys.setdefault(full_key, []).append(val)

        if key in FILES and section == "hls":
            dest = ((root / val) if not Path(val).is_absolute() else Path(val))
            dest = dest.resolve(strict=True)
            if not dest.is_relative_to(root) or not dest.is_file():
                raise ValueError(f"HLS source is outside project or not a file: {dest}")
            source_paths.append(dest)
            val = str(dest)
        elif key in INCLUDE_FIELDS and section == "hls":
            flags = shlex.split(val)
            converted = []
            for flag in flags:
                if not flag.startswith("-I") or len(flag) < 3:
                    raise ValueError(f"unsupported HLS compiler flag: {flag!r}")
                path = Path(flag[2:])
                included = (path if path.is_absolute() else root / path).resolve(
                    strict=True
                )
                if not included.is_relative_to(root) or not included.is_dir():
                    raise ValueError(f"include directory outside project: {included}")
                include_paths.append(included)
                converted.append("-I" + str(included))
            val = " ".join(converted)
        elif key == "relative_roots" and section == "hls":
            val = str(root)
        elif key == "syn.output.format" and section == "hls":
            raise ValueError("deprecated 2025.2 key syn.output.format")
        rewritten.append(f"{key}={val}")

    if keys.get((None, "part")) != [EXPECTED_PART]:
        raise ValueError("incorrect target part in HLS config")
    if keys.get(("hls", "syn.top")) != [top]:
        raise ValueError("HLS top mismatches requested kernel")
    if keys.get(("hls", "package.output.format")) != ["rtl"]:
        raise ValueError("HLS output must use current package.output.format=rtl")
    if keys.get(("hls", "clock")) != ["10ns"]:
        raise ValueError("unexpected HLS clock")
    if len(keys.get(("hls", "syn.file"), [])) < 1:
        raise ValueError("no HLS synthesis source files")
    if len(keys.get(("hls", "tb.file"), [])) != 1:
        raise ValueError("HLS requires exactly one testbench source")
    if len(keys.get(("hls", "relative_roots"), [])) != 1:
        raise ValueError("HLS requires a single explicit relative_roots")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as target:
        target.write(
            "# GENERATED for a unique M06 offline evidence directory.\n"
            "# Source references are absolute to survive Vitis --work_dir chdir.\n"
        )
        target.write("\n".join(rewritten) + "\n")
    return {
        "top": top,
        "config": str(output),
        "sources": [str(x) for x in source_paths],
        "include_dirs": [str(x) for x in sorted(set(include_paths))],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--top", required=True, choices=sorted(ALLOWED_TOPS))
    args = parser.parse_args()
    meta = prepare(args.root, args.template, args.output, args.top)
    print(
        f"PASS: generated effective {meta['top']} HLS config: {meta['config']}; "
        f"{len(meta['sources'])} absolute source/testbench files, "
        f"{len(meta['include_dirs'])} include directories verified"
    )


if __name__ == "__main__":
    main()
