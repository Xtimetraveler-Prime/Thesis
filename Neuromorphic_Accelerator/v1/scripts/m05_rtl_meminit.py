"""Stage *existing* generated RTL memory init assets for direct XSim.

The Vitis 2025.2 generated Verilog may reference e.g. ./m05_rolling_...dat.
Running xsim in a clean ~/Thesis_Evidence cwd requires those file assets in
THAT cwd; otherwise XSim can print warnings and leave memories unknown.

This tool NEVER invents memory contents, never overwrites a prior evidence
file, and never edits a generated RTL/build source. It collects only .dat
filenames explicitly named in generated RTL, locates exact filename matches
inside the original operator HLS evidence work tree, refuses inconsistent
duplicates, then copies them into the fresh simulator evidence directory.

If the original Vitis run did not retain all .dat assets, STOP and report it.
A numerically passing XSim run with missing RAM init warnings is not proof
of initialized device RAM. A later simulation can proceed only once the real
input files have been supplied by the existing tool-generated evidence.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import shutil
import sys


# Generated files reference literal file names, usually through an INIT_FILE
# parameter propagated down to a $readmemh. Do not pretend other formats are
# supported. All matches must be simple base names to prevent path traversal.
INIT_FILENAME = re.compile(r"""["'](?:\./)?([A-Za-z0-9_.-]+\.dat)["']""")
EXPECTED_PREFIX = "m05_rolling_replay_"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def referenced_init_files(rtl_directory: Path) -> set[str]:
    rtl = rtl_directory.resolve(strict=True)
    if not rtl.is_dir():
        raise ValueError("RTL source path must be a directory")
    sources = sorted(list(rtl.glob("*.v")) + list(rtl.glob("*.sv")))
    if not sources:
        raise ValueError("no generated RTL source files")
    names: set[str] = set()
    for source in sources:
        for name in INIT_FILENAME.findall(source.read_text(encoding="utf-8",
                                                          errors="replace")):
            if not name.startswith(EXPECTED_PREFIX) or name in (".", ".."):
                raise ValueError("unexpected RTL init filename: " + name)
            names.add(name)
    # Fail if Vitis exposes no explicit literal init assets, rather than
    # calling the init-warning check PASS without proving anything.
    if not names:
        raise ValueError("no literal .dat init filenames found in generated RTL")
    return names


def stage_meminit(impl_evidence: Path, out: Path) -> list[tuple[str, str, str]]:
    root = impl_evidence.resolve(strict=True)
    work = root / "work"
    rtl = work / "hls/syn/verilog"
    target = out.resolve(strict=True)
    if not root.is_dir() or not work.is_dir():
        raise ValueError("implementation evidence work directory missing")
    if not target.is_dir() or target == root or root in target.parents:
        raise ValueError("output must be a separate existing evidence directory")
    names = referenced_init_files(rtl)
    found: dict[str, list[Path]] = {name: [] for name in names}
    for file in work.rglob("*.dat"):
        if file.name not in found:
            continue
        resolved = file.resolve(strict=True)
        if not resolved.is_relative_to(work.resolve()):
            raise ValueError("init file escapes original evidence work tree")
        if not resolved.is_file():
            raise ValueError("init asset not a file")
        found[file.name].append(resolved)
    missing = sorted(name for name in names if not found[name])
    if missing:
        raise ValueError(
            "missing tool-generated .dat assets in original --impl evidence: "
            + ", ".join(missing)
            + ". Retain the failed audit; inspect work/hls/syn/verilog and "
            "work/hls/sim/verilog, but do not fabricate RAM initialization."
        )
    selected: list[tuple[str, Path, str]] = []
    for name in sorted(names):
        matches = sorted(found[name])
        digests = {_hash(m) for m in matches}
        if len(digests) != 1:
            raise ValueError("conflicting generated RAM init assets: " + name)
        dest = target / name
        if dest.exists():
            raise ValueError("refusing to overwrite preexisting init asset: " + name)
        selected.append((name, matches[0], digests.pop()))
    result = []
    for name, source, expected in selected:
        dest = target / name
        with dest.open("xb") as f:
            f.write(source.read_bytes())
        if _hash(dest) != expected:
            raise ValueError("copied RAM init checksum mismatch: " + name)
        result.append((name, str(source), expected))
    manifest = target / "ram_init_manifest.txt"
    with manifest.open("x", encoding="utf-8") as f:
        for name, source, checksum in result:
            f.write(f"{checksum}  {name}  source={source}\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--impl-evidence", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    try:
        copied = stage_meminit(args.impl_evidence, args.output_directory)
    except (ValueError, OSError) as exc:
        print(f"RAM INIT STAGING FAIL: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    print(f"PASS: staged {len(copied)} exact generated RTL .dat files into "
          f"{args.output_directory}")
    print("PASS: RAM-init SHA256/source manifest ram_init_manifest.txt written")


if __name__ == "__main__":
    main()
