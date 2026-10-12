#!/usr/bin/env python3
"""P03 final board-local launch fixture: frozen P02.4b golden, 7 or 100 steps.

The ONLY runtime input from the PC is initial DDR records plus an immutable,
versioned 256-byte launch manifest. The A53 itself injects the frozen
P02.4b one-external-event/core/timestep stream at each dispatch.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
# When invoked as "python scripts/p03_finish_*.py", Python puts scripts/
# rather than v3/src on sys.path. Use THIS checkout's golden package,
# not an older similarly-named package in the activated v2 virtualenv.
V3_SRC = str(ROOT / "src")
if V3_SRC in sys.path:
    sys.path.remove(V3_SRC)
sys.path.insert(0, V3_SRC)
ORACLE = ROOT / "scripts/p02_4b_ring_fixture.py"
MAGIC = 0x50334346  # P3CF
VERSION = 1
MANIFEST_WORDS = 64
MAILBOX_BYTES = 256


def expected_residency(timesteps: int) -> dict[str, int]:
    """Exact P03.3a initial-three + RR victim policy, not P02 host pager.

    P02 chose additional paging for routed destination delivery, whereas
    P03.3b sends nonresident traffic directly to DDR. Its logical golden
    remains identical; page/eviction counts may legitimately differ.
    """
    resident = [0, 1, 2]
    dirty = [False] * 3
    next_slot = 0
    page_ins = page_outs = evictions = hits = 0
    for _ in range(timesteps):
        for core in range(5):
            if core in resident:
                slot = resident.index(core)
                hits += 1
            else:
                slot = next_slot
                next_slot = (next_slot + 1) % 3
                if dirty[slot]:
                    page_outs += 1
                evictions += 1
                page_ins += 1
                resident[slot] = core
                dirty[slot] = False
            dirty[slot] = True
    flush_outs = sum(dirty)
    return {
        "expected_initial_page_ins": 3,
        "expected_replacement_page_ins": page_ins,
        "expected_runtime_page_outs": page_outs,
        "expected_evictions": evictions,
        "expected_page_hits": hits,
        "expected_final_flush_page_outs": flush_outs,
        "expected_page_operations": 3 + page_ins + page_outs + flush_outs,
    }


def make(output: Path, timesteps: int) -> dict:
    if timesteps not in (7, 100):
        raise ValueError("P03 physical gate is frozen to 7 or 100 timesteps")
    output.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("p03_frozen_p02_ring", ORACLE)
    assert spec is not None and spec.loader is not None
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    oracle.TIMESTEPS = timesteps  # Same accepted P02 workload, longer run.
    golden = oracle.generate(output)
    assert golden["logical_core_ids"] == [0, 1, 2, 3, 4]
    assert golden["dispatch_count"] == 5 * timesteps
    if timesteps == 7:
        assert golden["expected_packet_count_total"] == 30
        assert golden["trace_fingerprint"] == (
            "9a925277fdeffbcce837954b6d44ce118d88e839f3a6b2d9d6e4956cf32747ac"
        )
    configs = oracle.make_workload()
    backing = oracle.export_paged_hardware_image(configs, resident_context_count=3)
    words = [0] * MANIFEST_WORDS
    words[0:10] = [
        MAGIC, VERSION, timesteps, 5, 3, 10,
        0x40000000, 0x80000, 0x43FF0000, 1,
    ]
    record_crc = []
    for k in range(5):
        img = backing.backing_by_logical_core[k].image
        meta = (
            k | (img.compartment_count << 7) |
            (img.synapse_count << 18) | (img.route_count << 34)
        )
        words[10 + 2*k] = meta & 0xFFFFFFFF
        words[11 + 2*k] = (meta >> 32) & 0xFFFFFFFF
        words[20 + k] = img.config_words[0] & 0xFFFFFFFF
        words[25 + k] = 0  # initial CURRENT/NEXT counts
        words[30 + k] = 10 + k  # one external event before each dispatch
        words[35 + k] = k
        raw = (output / f"core{k}_initial.bin").read_bytes()
        assert len(raw) == 0x80000
        crc = zlib.crc32(raw)
        words[40 + k] = crc
        record_crc.append(f"0x{crc:08X}")
    words[45] = golden["expected_packet_count_total"]
    words[46] = 5 * timesteps
    words[47] = timesteps
    words[48] = timesteps & 1
    words[63] = zlib.crc32(struct.pack("<63I", *words[:63]))
    blob = struct.pack("<64I", *words)
    (output / "p03_run_config.bin").write_bytes(blob)
    (output / "mailbox_zero.bin").write_bytes(bytes(MAILBOX_BYTES))
    manifest = dict(golden)
    manifest["p03_schema"] = "p03-autonomous-p02-ring-launch-v1"
    manifest["p03_timesteps"] = timesteps
    manifest.update(expected_residency(timesteps))
    manifest["p03_record_crc32"] = record_crc
    manifest["p03_run_config_crc32"] = f"0x{words[63]:08X}"
    manifest["p03_launch_sha256"] = hashlib.sha256(blob).hexdigest()
    (output / "p03_run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"PASS: P03 frozen P02.4b golden t={timesteps} "
        f"dispatches={words[46]} packets={words[45]} "
        f"manifest_crc=0x{words[63]:08X}"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--timesteps", required=True, type=int, choices=(7, 100))
    args = parser.parse_args()
    make(args.output_dir, args.timesteps)
