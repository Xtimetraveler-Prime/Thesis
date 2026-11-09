#!/usr/bin/env python3
"""M05 D4.3 SOURCE-ONLY independent AXI-MM 256-to-128 byte-lane oracle.

A test passing THIS oracle never proves actual vendor-generated SmartConnect.
It can validate a future captured REAL vendor AXI handshake/transaction trace
only when separately source-/model-hash-attested by a genuine XSim runner.

Supported envelope: legal, 32-byte-aligned AXI4 INCR 256-bit upstream
beats (AWSIZE/ARSIZE=5); 16-byte-aligned downstream 128-bit beats (SIZE=4),
non-reordering within each single-ID transaction. NO support is claimed for
WRAP/FIXED/narrow/unaligned bursts, concurrent ID remapping or vendor clocks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


class ProtocolError(ValueError):
    """Bad transport trace or unsupported AXI request, fail closed."""


def require_int(value: object, name: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ProtocolError(f"{name} must be integer in [{low}, {high}]")
    return value


def exact_bytes(value: object, size: int, name: str) -> bytes:
    if not isinstance(value, str) or len(value) != size * 2:
        raise ProtocolError(f"{name} needs exactly {size} bytes of hex, little-endian lane order")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise ProtocolError(f"{name} not hexadecimal") from exc


def known_byte(address: int, seed: int = 0x31) -> int:
    """Position-addressed test-memory initialization, independent of DUT."""
    return hashlib.sha256(f"m05-d4-axi-v1:{seed}:{address}".encode()).digest()[0]


def original_header(tx: dict, op: str) -> tuple[int, int, int]:
    if not isinstance(tx, dict) or tx.get("op") != op or tx.get("burst") != "INCR":
        raise ProtocolError("only explicit AXI4 INCR READ/WRITE envelope supported")
    addr = require_int(tx.get("address"), "upstream address", 0, 2**32 - 1)
    beats = require_int(tx.get("beats"), "upstream beat count", 1, 256)
    ident = require_int(tx.get("id"), "upstream ID", 0, 65535)
    if addr % 32:
        raise ProtocolError("256-bit upstream address not 32-byte aligned")
    if (addr // 4096) != ((addr + 32*beats - 1) // 4096):
        raise ProtocolError("AXI4 upstream INCR cannot cross 4KiB boundary")
    if addr + beats*32 > 2**32:
        raise ProtocolError("upstream transaction exceeds 32-bit DMA address")
    return addr, beats, ident


def segments(tx: dict, addr: int, total_beat_count: int) -> tuple[list[dict], list[int]]:
    segs = tx.get("downstream_addresses")
    if not isinstance(segs, list) or not segs:
        raise ProtocolError("no downstream 128-bit address segments")
    offset = 0
    indices = []
    for idx, seg in enumerate(segs):
        if not isinstance(seg, dict):
            raise ProtocolError("malformed downstream AXI address segment")
        a = require_int(seg.get("address"), f"segment {idx} address", 0, 2**32 - 1)
        n = require_int(seg.get("beats"), f"segment {idx} beats", 1, 256)
        size = require_int(seg.get("size"), f"segment {idx} AXI size", 0, 7)
        require_int(seg.get("id"), f"segment {idx} ID", 0, 65535)
        if size != 4 or a != addr + offset*16 or a % 16:
            raise ProtocolError("downstream SIZE/address changed or byte sequence lost")
        if a // 4096 != (a + 16*n - 1) // 4096:
            raise ProtocolError("downstream AXI burst crosses 4KiB boundary")
        indices.extend([idx] * n)
        offset += n
    if offset != total_beat_count * 2:
        raise ProtocolError("downstream total byte count wrong; high/low beats lost or duplicated")
    return segs, indices


def write_check(tx: dict) -> dict:
    addr, beats, ident = original_header(tx, "WRITE")
    original = tx.get("upstream_w")
    downstream = tx.get("downstream_w")
    down_b = tx.get("downstream_b")
    if (not isinstance(original, list) or len(original) != beats
            or not isinstance(downstream, list) or len(downstream) != beats*2
            or not isinstance(down_b, list)):
        raise ProtocolError("incorrect upstream/downstream W/B cardinality")
    expected: list[tuple[bytes, int]] = []
    for i, row in enumerate(original):
        if not isinstance(row, dict):
            raise ProtocolError("invalid upstream W row")
        data = exact_bytes(row.get("data"), 32, "upstream WDATA")
        mask = require_int(row.get("strb"), "upstream WSTRB", 0, 2**32 - 1)
        if row.get("last") is not (i == beats-1):
            raise ProtocolError("incorrect upstream WLAST")
        expected += [(data[:16], mask & 0xffff), (data[16:], mask >> 16)]
    segs, indices = segments(tx, addr, beats)
    offset = 0
    for idx, (data, mask) in enumerate(expected):
        row = downstream[idx]
        if not isinstance(row, dict):
            raise ProtocolError("malformed downstream W row")
        emitted = exact_bytes(row.get("data"), 16, "downstream WDATA")
        emitted_mask = require_int(row.get("strb"), "downstream WSTRB", 0, 65535)
        if emitted_mask != mask:
            raise ProtocolError(f"byte-strobe truncation or lane shift on downstream beat {idx}")
        for k in range(16):
            if mask & (1 << k) and emitted[k] != data[k]:
                raise ProtocolError(f"active data byte mismatch at downstream beat {idx} byte {k}")
        is_last = idx+1 == len(indices) or indices[idx] != indices[idx+1]
        if row.get("last") is not is_last:
            raise ProtocolError(f"incorrect downstream WLAST segment boundary {idx}")
    if len(down_b) != len(segs):
        raise ProtocolError("missing or duplicated B response for downstream segments")
    errors = 0
    for idx, (response, segment) in enumerate(zip(down_b, segs)):
        if not isinstance(response, dict):
            raise ProtocolError("malformed downstream B response")
        if require_int(response.get("id"), "downstream BID", 0, 65535) != segment["id"]:
            raise ProtocolError("downstream BID does not correlate with AW segment")
        code = require_int(response.get("resp"), "downstream BRESP", 0, 3)
        if code: errors += 1
    b = tx.get("upstream_b")
    if not isinstance(b, dict):
        raise ProtocolError("missing upstream B response")
    if require_int(b.get("id"), "upstream BID", 0, 65535) != ident:
        raise ProtocolError("original upstream BID lost by conversion")
    bcode = require_int(b.get("resp"), "upstream BRESP", 0, 3)
    if bool(bcode) != bool(errors):
        raise ProtocolError("write error response was hidden or fabricated")
    return {"op": "WRITE", "upstream_bytes": beats*32, "downstream_bytes": len(expected)*16,
            "write_active_bytes": sum(mask.bit_count() for _, mask in expected),
            "segments": len(segs), "downstream_errors": errors,
            "axi_widths": [256, 128]}


def read_check(tx: dict) -> dict:
    addr, beats, ident = original_header(tx, "READ")
    upstream = tx.get("upstream_r")
    down = tx.get("downstream_r")
    if (not isinstance(upstream, list) or len(upstream) != beats
            or not isinstance(down, list) or len(down) != beats*2):
        raise ProtocolError("incorrect upstream/downstream R cardinality")
    segs, indices = segments(tx, addr, beats)
    errors: list[bool] = []
    for idx, row in enumerate(down):
        if not isinstance(row, dict):
            raise ProtocolError("invalid downstream R row")
        data = exact_bytes(row.get("data"), 16, "downstream RDATA")
        for j, value in enumerate(data):
            if value != known_byte(addr+idx*16+j):
                raise ProtocolError(f"downstream RDATA differs from known original test-memory byte {idx}:{j}")
        if require_int(row.get("id"), "downstream RID", 0, 65535) != segs[indices[idx]]["id"]:
            raise ProtocolError("downstream RID mismatch")
        code = require_int(row.get("resp"), "downstream RRESP", 0, 3)
        is_last = idx+1 == len(indices) or indices[idx] != indices[idx+1]
        if row.get("last") is not is_last:
            raise ProtocolError("downstream RLAST segmentation error")
        errors.append(bool(code))
    for idx, row in enumerate(upstream):
        if not isinstance(row, dict):
            raise ProtocolError("invalid upstream R row")
        data = exact_bytes(row.get("data"), 32, "upstream RDATA")
        for j, value in enumerate(data):
            if value != known_byte(addr+idx*32+j):
                raise ProtocolError(f"upstream 256-bit RDATA wrong/lost/duplicated byte {idx}:{j}")
        if require_int(row.get("id"), "upstream RID", 0, 65535) != ident:
            raise ProtocolError("original upstream RID not restored")
        if row.get("last") is not (idx == beats-1):
            raise ProtocolError("upstream RLAST wrong")
        code = require_int(row.get("resp"), "upstream RRESP", 0, 3)
        if bool(code) != (errors[2*idx] or errors[2*idx+1]):
            raise ProtocolError("RRESP error hidden or fabricated on 256-bit read beat")
    return {"op": "READ", "upstream_bytes": beats*32, "downstream_bytes": len(down)*16,
            "segments": len(segs), "downstream_errors": sum(errors),
            "axi_widths": [256, 128]}


def stability(cycles: list, require_all_channels: bool = False, watchdog: int = 5000) -> dict:
    """Independent multi-channel VALID/READY stability and coverage detector.

    Only samples given cycles, so passing source-only samples does not prove
    vendor behavior. A genuine DUT capture must independently guarantee
    cycle completeness and originate from signed model/testbench.
    """
    if not isinstance(cycles, list) or not cycles or len(cycles) > watchdog:
        raise ProtocolError("missing/overflowing AXI VALID/READY sampled cycles")
    prev: dict[str, str] = {}
    stalled: set[str] = set()
    seen_handshake: set[str] = set()
    reset_seen = False
    for i, sample in enumerate(cycles):
        if not isinstance(sample, dict) or type(sample.get("reset_n")) is not bool:
            raise ProtocolError(f"malformed reset cycle {i}")
        if not sample["reset_n"]:
            prev.clear()
            reset_seen = True
            continue
        ports = sample.get("channels")
        if not isinstance(ports, dict):
            raise ProtocolError(f"missing signal channels cycle {i}")
        next_stall = {}
        for ch in ("AW", "W", "B", "AR", "R"):
            sig = ports.get(ch)
            if not isinstance(sig, dict):
                raise ProtocolError(f"missing AXI channel {ch} at cycle {i}")
            v, ready = sig.get("valid"), sig.get("ready")
            payload = sig.get("payload")
            if type(v) is not bool or type(ready) is not bool or not isinstance(payload, str):
                raise ProtocolError(f"invalid valid/ready/payload {ch} cycle {i}")
            if ch in prev and (not v or payload != prev[ch]):
                raise ProtocolError(f"{ch} VALID/payload changed while stalled at cycle {i}")
            if v and ready:
                seen_handshake.add(ch)
            elif v:
                stalled.add(ch)
                next_stall[ch] = payload
        prev = next_stall
    if require_all_channels and (set(("AW","W","B","AR","R")) - stalled or
                                 set(("AW","W","B","AR","R")) - seen_handshake or
                                 not reset_seen):
        raise ProtocolError("coverage incomplete: require all five stalls/handshakes and reset")
    if prev:
        raise ProtocolError("trace ended with an unresolved AXI VALID/READY stall")
    return {"backpressure_channels": sorted(stalled), "handshaken_channels": sorted(seen_handshake),
            "reset_seen": reset_seen, "cycles": len(cycles)}


def check_suite(document: dict, enforce_provenance: bool = True) -> dict:
    if not isinstance(document, dict) or document.get("scope") != "M05_D4_AXI256_TO128_TRANSACTION_TRACE_V1":
        raise ProtocolError("wrong 256-to-128 trace schema/scope")
    if enforce_provenance:
        if document.get("origin") != "GENUINE_VENDOR_XSIM_CAPTURE":
            raise ProtocolError("source-only or synthetic transaction records are not vendor verification")
        proof = document.get("provenance")
        if not isinstance(proof, dict) or not all(
            isinstance(proof.get(k), str) and len(proof[k]) == 64
            and all(c in "0123456789abcdef" for c in proof[k])
            for k in ("testbench_sha256", "generated_mem_sc_manifest_sha256",
                      "xsim_log_sha256", "source_commit_sha256")
        ):
            raise ProtocolError("missing genuine vendor model/testbench/run SHA provenance")
    cases = document.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ProtocolError("missing transaction cases")
    seen_ids = set()
    results = []
    for tx in cases:
        if not isinstance(tx, dict) or not isinstance(tx.get("case_id"), str):
            raise ProtocolError("transaction case lacks identifier")
        ident = tx["case_id"]
        if not ident or ident in seen_ids:
            raise ProtocolError("duplicate or blank case ID")
        seen_ids.add(ident)
        if tx.get("op") == "WRITE":
            result = write_check(tx)
        elif tx.get("op") == "READ":
            result = read_check(tx)
        else:
            raise ProtocolError("unsupported AXI operation")
        result["case_id"] = ident
        results.append(result)
    ticks = stability(document.get("cycles"), require_all_channels=enforce_provenance)
    return {
        "scope": "SOURCE_OR_CAPTURED_VENDOR_AXIMM_BYTE_LANE_SCOREBOARD",
        "origin": document.get("origin"),
        "checked_cases": len(results),
        "results": results,
        "handshakes": ticks,
        "supports_only_aligned_32B_INCR": True,
        "provenance_is_externally_authenticated": False,
        "axi_vendor_adapter_functionally_proven": False,
        "physical_board": "NOT_AUTHORIZED",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trace-json", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    try:
        if a.output.exists() or a.output.parent.resolve() == a.trace_json.parent.resolve():
            raise ProtocolError("write NEW independent checker output separately from input")
        result = check_suite(json.loads(a.trace_json.read_text()), enforce_provenance=True)
        with a.output.open("x", encoding="utf-8") as fp:
            json.dump(result, fp, indent=2, sort_keys=True)
            fp.write("\n")
    except (OSError, ValueError, KeyError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"FAIL: M05 D4.3 genuine AXI trace checker: {exc}", file=sys.stderr)
        return 2
    print("AXI byte/response/strobe/last/ID/stall oracle PASS for supplied trace shape; "
          "separate XSim tool/RTL source authentication still required; no vendor PASS")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
