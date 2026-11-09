#!/usr/bin/env python3
"""Stage a metadata-only copy of the original owner-authenticated Vitis HLS top.

The accepted HLS top and its sibling RTL are never written, and NO new neural
logic is generated. A single Verilog port attribute declares the five genuine
clock-associated AXI interfaces for Vivado Module Reference (AMD UG994).
The staging output belongs only to a NEW immutable offline evidence directory.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys

BUSIFS = "neurons:synapses:external_events:trace:s_axi_control"
TOP = re.compile(rb"\bmodule[ \t]+m05_rolling_replay\b")
AP_CLOCK = re.compile(
    rb"(?m)^([ \t]*)input[ \t]+(?:wire[ \t]+)?ap_clk[ \t]*;[ \t]*(?:\r?\n|$)"
)


def annotate(original: bytes, frequency_hz: int) -> tuple[bytes, bytes]:
    if not (isinstance(frequency_hz, int) and 1_000_000 <= frequency_hz <= 500_000_000):
        raise ValueError("explicit offline clock frequency must be 1..500 MHz integer Hz")
    if len(original) > 5_000_000 or len(TOP.findall(original)) != 1:
        raise ValueError("missing, duplicated, or oversized authentic HLS top module")
    matches = list(AP_CLOCK.finditer(original))
    if len(matches) != 1:
        raise ValueError("authentic non-ANSI HLS top needs exactly one scalar input ap_clk declaration")
    if b"ASSOCIATED_BUSIF" in original:
        raise ValueError("original HLS top already includes clock association; do not double-annotate")
    # Insert only an IP Integrator clock annotation before the original input.
    # FREQ_HZ must agree with the actual scratch K26 PS pl_clk0 readback in Tcl.
    indent = matches[0].group(1)
    annotation = (
        indent + b'(* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 ap_clk CLK", '
        + b'X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ap_clk, '
        + b'ASSOCIATED_BUSIF ' + BUSIFS.encode("ascii")
        + b', ASSOCIATED_RESET ap_rst_n, FREQ_HZ '
        + str(frequency_hz).encode("ascii")
        + b', FREQ_TOLERANCE_HZ 0" *)\n'
    )
    output = original[: matches[0].start()] + annotation + original[matches[0].start():]
    if output.replace(annotation, b"", 1) != original:
        raise AssertionError("annotation must not alter any original neural RTL bytes")
    return output, annotation


def stage(source: Path, output: Path, manifest: Path, frequency_hz: int) -> None:
    if source.resolve() == output.resolve() or source.resolve() == manifest.resolve():
        raise ValueError("refusing to overwrite the original signed32 Vitis HLS top")
    if output.exists() or manifest.exists():
        raise ValueError("annotation evidence already exists; use a fresh output directory")
    if output.parent.resolve() != manifest.parent.resolve():
        raise ValueError("annotation and manifest must be in the same new evidence directory")
    if not source.is_file() or source.name != "m05_rolling_replay.v":
        raise ValueError("authentic original HLS top m05_rolling_replay.v required")
    original = source.read_bytes()
    derived, insertion = annotate(original, frequency_hz)
    # No overwrite even on a repeated run. Original is only read.
    with output.open("xb") as target:
        target.write(derived)
    with manifest.open("x", encoding="utf-8") as target:
        target.write("META|scope|OFFLINE_ONLY_ORIGINAL_HLS_TOP_CLOCK_ANNOTATION\n")
        target.write(f"ORIGINAL_SHA256|{hashlib.sha256(original).hexdigest()}\n")
        target.write(f"DERIVED_SHA256|{hashlib.sha256(derived).hexdigest()}\n")
        target.write(f"FREQ_HZ|{frequency_hz}\n")
        target.write(f"ASSOCIATED_BUSIF|{BUSIFS}\n")
        target.write("META|neural_logic|BYTE_IDENTICAL_EXCEPT_ONE_CLOCK_INTERFACE_ATTRIBUTE\n")
        target.write("META|physical_board|NOT_AUTHORIZED\n")
    # Re-check that source remains identical after staging.
    if hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(original).digest():
        raise RuntimeError("authenticated Vitis HLS source unexpectedly changed")
    print("PASS: M05.12d.3 offline authentic HLS top clock annotation staged "
          f"({len(insertion)} attribute bytes only, NO NEURAL RTL CHANGE/BOARD)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-top", type=Path, required=True)
    parser.add_argument("--derived-top", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--frequency-hz", type=int, required=True)
    args = parser.parse_args()
    try:
        stage(args.original_top, args.derived_top, args.manifest, args.frequency_hz)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: M05.12d.3 clock annotation admission: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
