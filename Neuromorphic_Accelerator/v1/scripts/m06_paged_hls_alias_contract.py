#!/usr/bin/env python3
"""Read-only source gate for M06 two-master HLS alias intent.

These source assertions protect the ALIAS declaration from being removed while
performing other changes. They do not replace genuine 2025.2 HLS synthesis,
C/RTL cosim, AXI ordering, or the original AMD SmartConnect simulation.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

TOP = "m06_paged_rolling_replay"
POINTERS = ("canonical_read_words", "canonical_write_words")
EXPECTED = {
    POINTERS[0]: "gmem_read",
    POINTERS[1]: "gmem_write",
}


def inspect(source: str, config: str) -> dict:
    if "syn.top="+TOP not in config.splitlines():
        raise ValueError("wrong HLS top in config")
    for name, bundle in EXPECTED.items():
        p = (r"(?m)^\s*#pragma\s+HLS\s+INTERFACE\s+m_axi\s+port="
             + name + r"\s+offset=slave\s+bundle=" + bundle
             + r"\s+depth=16384\s+max_(?:read|write)_burst_length=16\s*$")
        matches = re.findall(p, source)
        if len(matches) != 1:
            raise ValueError("missing or incompatible separate memory master: " + name)
    if len(re.findall(
        r"(?m)^\s*#pragma\s+HLS\s+ALIAS\s+ports="
        r"canonical_read_words,canonical_write_words\s+distance=0\s*$",
        source
    )) != 1:
        raise ValueError("missing or inconsistent zero-distance shared-memory alias")
    # Fail closed if a second ALIAS might override or make alias metadata ambiguous.
    if len(re.findall(r"(?m)^\s*#pragma\s+HLS\s+ALIAS\b", source)) != 1:
        raise ValueError("multiple conflicting HLS ALIAS pragmas")
    if len(re.findall(r"(?m)^\s*#pragma\s+HLS\s+INTERFACE\s+m_axi\b", source)) != 2:
        raise ValueError("additional or removed memory masters")
    return {
        "schema": "m06-source-only-two-master-alias-contract-v1",
        "status": "SOURCE_ONLY_SHARED_BUFFER_ALIAS_DECLARED_NOT_COSIM_VERIFIED",
        "top": TOP,
        "read_bundle": "gmem_read",
        "write_bundle": "gmem_write",
        "shared_buffer_pointer_distance_words": 0,
        "canonical_max_words": 16384,
        "genuine_csim": "NOT_EXECUTED_BY_THIS_TOOL",
        "genuine_csynth": "NOT_EXECUTED_BY_THIS_TOOL",
        "genuine_cosim": "NOT_EXECUTED_BY_THIS_TOOL",
        "physical_DDR_or_original_IP_connected": False,
        "m06_complete": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.root.resolve(strict=True)
        source = (root/"hls/m06_paged_rolling/m06_paged_rolling.cpp").read_text()
        config = (root/"hls/m06_paged_rolling/m06_paged_rolling_hls_config.cfg").read_text()
        print(json.dumps(inspect(source, config), indent=2, sort_keys=True))
    except (OSError, ValueError) as error:
        print("M06 HLS shared-buffer ALIAS CONTRACT REJECTED: "+str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
