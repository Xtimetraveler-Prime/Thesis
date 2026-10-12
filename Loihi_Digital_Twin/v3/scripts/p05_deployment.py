#!/usr/bin/env python3
"""P05.1 versioned workload envelope; host builder/validator, NO board runner.

Deliberately separate from accepted P03 fixture/ELF. The fixed P03
architecture oracle remains the source of neural expected results.
Requires an existing real P02/P03-compatible 512KiB DDR record for
each logical core, preventing imaginary configurations from looking
ready for physical execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import zlib

MAGIC = 0x47353050  # byte sequence P05G
VERSION = 1
HEADER_BYTES = 256
PAYLOAD_BASE = 0x43F00000
PAYLOAD_CAPACITY = 0xE0000
HEADER_BASE = 0x43FE0000
MAILBOX_BASE = 0x43FF0000
BACKING_BASE = 0x40000000
RECORD_BYTES = 0x80000
MAX_CORES = 126
MAX_SLOTS = 3
MAX_STEPS = 10000
EVENT_DEPTH = 4096
CLASSES = {"state0": 1, "event0": 2, "event1": 3, "packet0": 4}
SCHEMA = "p05-regression-deployment-v1"


def _uint(value: object, maximum: int, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} cannot be bool")
    if isinstance(value, str):
        try:
            number = int(value, 0)
        except ValueError as exc:
            raise ValueError(f"{field}: invalid integer") from exc
    elif type(value) is int:
        number = value
    else:
        raise ValueError(f"{field}: must be integer or 0x-prefixed string")
    if number < 0 or number > maximum:
        raise ValueError(f"{field}: {number} outside [0, {maximum}]")
    return number


def _as_list(value: object, name: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"{name}: list required")
    return value


def _check_keys(row: object, expected: set[str], name: str) -> dict:
    if not isinstance(row, dict) or set(row) != expected:
        raise ValueError(f"{name}: required keys {sorted(expected)}")
    return row


def _record(path: Path, core_id: int) -> tuple[bytes, int, int]:
    raw = path.read_bytes()
    if len(raw) != RECORD_BYTES:
        raise ValueError(f"core {core_id}: record is not 512KiB")
    if (raw[:8] != bytes.fromhex("4c54563343545831") or
            struct.unpack_from("<I", raw, 8)[0] != 1 or
            struct.unpack_from("<I", raw, 0x10)[0] != RECORD_BYTES or
            struct.unpack_from("<I", raw, 0x14)[0] != core_id):
        raise ValueError(f"core {core_id}: record header/ID/stride invalid")
    return raw, zlib.crc32(raw), struct.unpack_from("<I", raw, 0x1000)[0]


def build(spec_path: Path, output: Path) -> dict:
    spec_path = spec_path.resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    _check_keys(spec, {"schema", "timesteps", "slot_count", "mode",
                       "cores", "events", "checkpoints"}, "spec")
    if spec["schema"] != SCHEMA:
        raise ValueError("unsupported P05 workload schema")
    steps = _uint(spec["timesteps"], MAX_STEPS, "timesteps")
    if not steps:
        raise ValueError("timesteps must be positive")
    core_rows = _as_list(spec["cores"], "cores")
    count = len(core_rows)
    if not 1 <= count <= MAX_CORES:
        raise ValueError(f"core count must be in 1..{MAX_CORES}")
    slots = _uint(spec["slot_count"], MAX_SLOTS, "slot_count")
    if not 1 <= slots <= count:
        raise ValueError("slot_count must be between 1 and min(3, core_count)")
    if spec["mode"] not in ("diagnostic", "fast"):
        raise ValueError("mode must be diagnostic or fast")
    mode = int(spec["mode"] == "diagnostic")

    cores, records = [], {}
    rank, axons = {}, {}
    for n, original in enumerate(core_rows):
        row = _check_keys(original, {"id", "metadata", "input_axon", "record"},
                          f"cores[{n}]")
        cid = _uint(row["id"], MAX_CORES - 1, f"cores[{n}].id")
        if cid in rank:
            raise ValueError(f"duplicate logical core id {cid}")
        metadata = _uint(row["metadata"], (1 << 64) - 1,
                         f"cores[{n}].metadata")
        axon = _uint(row["input_axon"], EVENT_DEPTH - 1,
                     f"cores[{n}].input_axon")
        if (metadata & 127) != cid or not ((metadata >> 7) & 0x7FF) or metadata >> 60:
            raise ValueError(f"core {cid}: invalid hardware dispatch metadata")
        path = (spec_path.parent / str(row["record"])).resolve()
        raw, crc, config0 = _record(path, cid)
        if crc == 0:
            raise ValueError(f"core {cid}: zero record CRC is reserved")
        cores.append(struct.pack("<8I", cid, metadata & 0xFFFFFFFF,
                                 metadata >> 32, config0, crc, axon, 0, 0))
        records[cid] = (path, raw, crc)
        rank[cid] = n
        axons[cid] = axon

    ordered_events = []
    for n, entry in enumerate(_as_list(spec["events"], "events")):
        row = _check_keys(entry, {"timestep", "core", "axon"}, f"events[{n}]")
        step = _uint(row["timestep"], steps - 1, f"events[{n}].timestep")
        cid = _uint(row["core"], MAX_CORES - 1, f"events[{n}].core")
        axon = _uint(row["axon"], EVENT_DEPTH - 1, f"events[{n}].axon")
        if cid not in rank or axon != axons[cid]:
            raise ValueError(f"events[{n}]: unregistered core/axon")
        ordered_events.append((step, rank[cid], cid, axon))
    ordered_events.sort()
    counts: dict[tuple[int, int], int] = {}
    for step, _, cid, _ in ordered_events:
        key = (step, cid)
        counts[key] = counts.get(key, 0) + 1
        if counts[key] > EVENT_DEPTH:
            raise ValueError(f"core {cid} timestep {step}: event overflow")
    events = [struct.pack("<4I", step, cid, axon, 0)
              for step, _, cid, axon in ordered_events]

    checkpoints = []
    if not mode and spec["checkpoints"]:
        raise ValueError("fast mode cannot request diagnostic checkpoints")
    for n, entry in enumerate(_as_list(spec["checkpoints"], "checkpoints")):
        row = _check_keys(entry, {"timestep", "core", "state_class",
                                "expected_crc32"}, f"checkpoints[{n}]")
        step = _uint(row["timestep"], steps - 1, f"checkpoints[{n}].timestep")
        cid = _uint(row["core"], MAX_CORES - 1, f"checkpoints[{n}].core")
        cls = row["state_class"]
        if cid not in rank or cls not in CLASSES:
            raise ValueError(f"checkpoints[{n}]: unknown core/state class")
        crc = _uint(row["expected_crc32"], 0xFFFFFFFF,
                    f"checkpoints[{n}].expected_crc32")
        checkpoints.append((step, rank[cid], CLASSES[cls], cid, crc))
    checkpoints.sort()
    if len({(step, r, cls) for step, r, cls, _, _ in checkpoints}) != len(checkpoints):
        raise ValueError("duplicate checkpoint key")
    checks = [struct.pack("<4I", step, cid, cls, crc)
              for step, _, cls, cid, crc in checkpoints]

    core_blob = b"".join(cores)
    event_blob = b"".join(events)
    check_blob = b"".join(checks)
    payload = core_blob + event_blob + check_blob
    if len(payload) > PAYLOAD_CAPACITY:
        raise ValueError(f"payload {len(payload)} exceeds {PAYLOAD_CAPACITY}")
    words = [0] * 64
    words[:21] = [
        MAGIC, VERSION, HEADER_BYTES, mode, steps, count, slots, 1,
        BACKING_BASE, RECORD_BYTES, PAYLOAD_BASE, PAYLOAD_CAPACITY,
        len(payload), len(events), len(checks), count,
        0, len(core_blob), len(core_blob) + len(event_blob),
        MAILBOX_BASE, steps * count,
    ]
    words[22] = zlib.crc32(payload)
    words[23] = 0
    words[23] = zlib.crc32(struct.pack("<64I", *words))
    header = struct.pack("<64I", *words)
    output.mkdir(parents=True, exist_ok=True)
    (output / "p05_header.bin").write_bytes(header)
    (output / "p05_payload.bin").write_bytes(payload)
    for cid, (_, raw, _) in records.items():
        (output / f"core{cid}_initial.bin").write_bytes(raw)
    manifest = {
        "schema": SCHEMA,
        "status": "HOST_CONTRACT_ONLY_NOT_A53_OR_PHYSICAL_ACCEPTANCE",
        "timesteps": steps,
        "logical_core_ids_in_service_order": list(rank),
        "slot_count": slots,
        "diagnostic_mode": bool(mode),
        "events": len(events),
        "checkpoints": len(checks),
        "dispatches": steps * count,
        "header_crc32": f"0x{words[23]:08X}",
        "payload_crc32": f"0x{words[22]:08X}",
        "header_sha256": hashlib.sha256(header).hexdigest(),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "record_sha256": {
            str(cid): hashlib.sha256(raw).hexdigest()
            for cid, (_, raw, _) in records.items()
        },
        "input_spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
    }
    (output / "p05_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def from_p03_fixture(fixture: Path, output_path: Path) -> None:
    """Build a P05 spec using immutable P03 fixture records/metadata.

    This does NOT independently generate neural golden results and is
    only an ABI smoke profile until the new device runner is accepted.
    """
    fixture = fixture.resolve()
    raw = (fixture / "p03_run_config.bin").read_bytes()
    if len(raw) != 256:
        raise ValueError("P03 launch manifest must be 256B")
    words = struct.unpack("<64I", raw)
    if words[0] != 0x50334346 or words[1] != 1 or words[3] != 5:
        raise ValueError("not the accepted five-core P03 fixture")
    cores = []
    for cid in range(5):
        metadata = words[10 + 2 * cid] | (words[11 + 2 * cid] << 32)
        cores.append({
            "id": cid, "metadata": f"0x{metadata:016X}",
            "input_axon": words[30 + cid],
            "record": str(fixture / f"core{cid}_initial.bin"),
        })
    profile = {
        "schema": SCHEMA, "timesteps": words[2], "slot_count": 3,
        "mode": "diagnostic", "cores": cores,
        "events": [
            {"timestep": t, "core": cid, "axon": words[30 + cid]}
            for t in range(words[2]) for cid in range(5)
        ],
        "checkpoints": [],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(profile, indent=2) + "\n",
                           encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_subparsers(dest="command", required=True)
    gen = command.add_parser("build", help="Create strictly bounded P05 ABI")
    gen.add_argument("--spec", type=Path, required=True)
    gen.add_argument("--output-dir", type=Path, required=True)
    convert = command.add_parser("from-p03", help="Make ABI smoke spec from accepted fixture")
    convert.add_argument("--fixture-dir", type=Path, required=True)
    convert.add_argument("--output-spec", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "build":
            manifest = build(args.spec, args.output_dir)
            print("PASS: P05.1 host-only ABI generated " +
                  json.dumps({k: manifest[k] for k in
                              ("timesteps", "events", "checkpoints", "dispatches",
                               "header_crc32", "payload_crc32")}, sort_keys=True))
        else:
            from_p03_fixture(args.fixture_dir, args.output_spec)
            print(f"PASS: P05.1 P03-compatible contract spec: {args.output_spec}")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, "FAIL: P05.1 deployment: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
