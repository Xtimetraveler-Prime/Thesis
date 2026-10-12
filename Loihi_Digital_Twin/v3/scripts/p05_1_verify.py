#!/usr/bin/env python3
"""P05.1 standalone physical probe verifier: P05R mailbox + P02 DDR oracle.

Independent *post-execution* evidence analysis only. The PC may not use this
module to control any A53 timestep, page replacement, route, or barrier.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
V3_SRC = str(ROOT / "src")
if V3_SRC in sys.path:
    sys.path.remove(V3_SRC)
sys.path.insert(0, V3_SRC)

ORACLE = ROOT / "scripts/p02_4b_ring_fixture.py"
FIELDS = (
    "magic", "version", "result", "error",
    "steps", "completed_steps", "cores", "slots",
    "phase", "fault", "fault_phase",
    "dispatches", "packets", "barriers",
    "initial_ins", "replacement_ins", "runtime_outs",
    "final_outs", "evictions", "hits",
    "pl_dispatch_lo", "pl_dispatch_hi", "pl_page_lo", "pl_page_hi",
    "ps_infer_lo", "ps_infer_hi", "ps_route_lo", "ps_route_hi",
    "ps_barrier_lo", "ps_barrier_hi", "ps_control_lo", "ps_control_hi",
    "cntfrq_hz", "hw_id", "hw_caps", "hw_dispatches",
    "hw_pages", "hw_last_page_bytes", "hw_status", "hw_pending_bytes",
    "hw_read_bursts", "hw_write_bursts",
    "resident_deliveries", "inputs_consumed", "checkpoints_passed",
    "failed_step", "failed_core", "failed_class", "expected_crc",
    "observed_crc", "header_crc", "payload_crc",
    "last_packet_lo", "last_packet_hi", "diagnostic_mode",
    "expected_events", "expected_checks", "expected_dispatches",
    "diag_flags", "last_page_error",
)
assert len(FIELDS) == 60


def verify(mailbox: Path, fixture_dir: Path, artifact_dir: Path,
           dump_dir: Path) -> bool:
    errors: list[str] = []
    try:
        raw = mailbox.read_bytes()
        header = (artifact_dir / "p05_header.bin").read_bytes()
        payload = (artifact_dir / "p05_payload.bin").read_bytes()
        p05 = json.loads((artifact_dir / "p05_manifest.json").read_text())
        golden = json.loads((fixture_dir / "p03_run_manifest.json").read_text())
        if len(raw) != 256 or len(header) != 256:
            raise ValueError("result/header must each be exactly 256 bytes")
        mb = struct.unpack("<64I", raw)
        h = struct.unpack("<64I", header)
        result = dict(zip(FIELDS, mb))
        if p05["schema"] != "p05-regression-deployment-v1":
            raise ValueError("wrong P05 manifest schema")
        if p05["logical_core_ids_in_service_order"] != [0, 1, 2, 3, 4]:
            raise ValueError("frozen ring probe requires five cores in order")
        if h[4] != 7 or h[5] != 5 or h[6] != 3 or h[3] != 1:
            raise ValueError("physical probe requires P05 7-step 5-over-3 diagnostic")
        if p05["timesteps"] != 7 or p05["events"] != 35 or p05["checkpoints"] != 35:
            raise ValueError("expected exactly 35 ring events and 35 checkpoints")
        if golden["p03_timesteps"] != 7 or golden["expected_packet_count_total"] != 30:
            raise ValueError("frozen P02 golden must be 7 steps / 30 packets")
        if p05["header_crc32"] != f"0x{h[23]:08X}" or p05["payload_crc32"] != f"0x{h[22]:08X}":
            raise ValueError("generated deployment manifest checksum mismatch")
        if mb[60:] != (0, 0, 0, 0):
            errors.append("reserved result words 60..63 must be zero")
    except (OSError, ValueError, KeyError, TypeError, struct.error) as err:
        print("FAIL: P05.1 evidence admission: " + str(err), file=sys.stderr)
        return False

    def expect(field: str, wanted: int) -> None:
        actual = result[field]
        if actual != wanted:
            errors.append(f"{field}: actual=0x{actual:X} expected=0x{wanted:X}")

    for name, value in (
        ("magic", 0x52353050), ("version", 1),
        ("result", 0x600D600D), ("error", 0),
        ("steps", 7), ("completed_steps", 7),
        ("cores", 5), ("slots", 3),
        ("phase", 18), ("fault", 0), ("dispatches", 35),
        ("packets", 30), ("barriers", 7),
        ("initial_ins", 3),
        ("replacement_ins", golden["expected_replacement_page_ins"]),
        ("runtime_outs", golden["expected_runtime_page_outs"]),
        ("final_outs", golden["expected_final_flush_page_outs"]),
        ("evictions", golden["expected_evictions"]),
        ("hits", golden["expected_page_hits"]),
        ("hw_id", 0x4C543302), ("hw_caps", 0x0001031F),
        ("hw_dispatches", 35),
        ("hw_pages", golden["expected_page_operations"]),
        ("hw_last_page_bytes", 106496),
        ("hw_status", 0), ("hw_pending_bytes", 0),
        ("inputs_consumed", 35), ("checkpoints_passed", 35),
        ("failed_step", 0), ("failed_core", 0),
        ("failed_class", 0), ("expected_crc", 0),
        ("observed_crc", 0), ("header_crc", h[23]),
        ("payload_crc", h[22]), ("diagnostic_mode", 1),
        ("expected_events", 35), ("expected_checks", 35),
        ("expected_dispatches", 35), ("diag_flags", 0),
        ("last_page_error", 0),
    ):
        expect(name, value)
    if result["resident_deliveries"] > result["packets"]:
        errors.append("resident deliveries exceeds total routed packets")
    for name in ("cntfrq_hz", "hw_read_bursts", "hw_write_bursts"):
        if result[name] == 0:
            errors.append(f"{name} unexpectedly zero")
    for lo, hi in (
        ("pl_dispatch_lo", "pl_dispatch_hi"),
        ("pl_page_lo", "pl_page_hi"),
        ("ps_infer_lo", "ps_infer_hi"),
    ):
        if result[lo] | result[hi] == 0:
            errors.append(f"{lo}/{hi} unexpectedly zero")
    # Useful on any terminal failure, even if mailbox counters are wrong:
    # never discard captured final DDR just because the device failed late.
    ddr_details = None
    ddr_error = None
    try:
        spec = importlib.util.spec_from_file_location("p05_p02_oracle", ORACLE)
        assert spec is not None and spec.loader is not None
        oracle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(oracle)
        ddr_details = oracle.verify(fixture_dir, dump_dir)
    except (OSError, ValueError, AssertionError) as err:
        ddr_error = str(err)

    if errors or ddr_error is not None:
        for e in errors:
            print("FAIL: P05.1 mailbox " + e, file=sys.stderr)
        if result["result"] != 0x600D600D:
            print(
                "P05_FIRST_DIAGNOSTIC=" + json.dumps({
                    key: result[key] for key in (
                        "error", "fault", "fault_phase", "phase",
                        "dispatches", "barriers", "packets",
                        "inputs_consumed", "checkpoints_passed",
                        "failed_step", "failed_core", "failed_class",
                        "expected_crc", "observed_crc", "diag_flags",
                        "last_page_error",
                    )
                }, sort_keys=True), file=sys.stderr,
            )
        if ddr_error is not None:
            print("P05_FINAL_DDR_COMPARISON=FAIL "+ddr_error, file=sys.stderr)
        else:
            print("P05_FINAL_DDR_COMPARISON=PASS (mailbox still failed)", file=sys.stderr)
        return False

    print(
        "PASS: P05.1 independent physical 35-checkpoint ring replay "
        f"steps=7 cores=5 slots=3 dispatches=35 packets=30 "
        f"barriers=7 events=35 checkpoints=35 "
        f"resident_deliveries={result['resident_deliveries']}"
    )
    print("PASS: P05.1 all five final 512KiB DDR records byte-exact to frozen P02 oracle")
    print("P05_RESULT_METADATA="+json.dumps({
        "trace_sha256_reference": golden["trace_fingerprint"],
        "header_crc32": f"0x{h[23]:08X}",
        "payload_crc32": f"0x{h[22]:08X}",
        "resident_deliveries": result["resident_deliveries"],
        "ps_timer_hz": result["cntfrq_hz"],
        "ps_inference_ticks": result["ps_infer_lo"] |
                              (result["ps_infer_hi"] << 32),
        "pl_dispatch_cycles": result["pl_dispatch_lo"] |
                              (result["pl_dispatch_hi"] << 32),
        "pl_page_cycles": result["pl_page_lo"] |
                          (result["pl_page_hi"] << 32),
        "records": ddr_details["records"],
    }, sort_keys=True))
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mailbox", type=Path, required=True)
    parser.add_argument("--fixture-dir", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--dump-dir", type=Path, required=True)
    args = parser.parse_args()
    return 0 if verify(args.mailbox, args.fixture_dir,
                       args.artifact_dir, args.dump_dir) else 1


if __name__ == "__main__":
    raise SystemExit(main())
