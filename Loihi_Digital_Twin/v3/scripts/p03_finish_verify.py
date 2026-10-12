#!/usr/bin/env python3
"""P03 7/100-step physical autonomy: strict mailbox plus byte-exact P02 oracle.

This verifier executes ONLY after the A53 has completed and the PC has dumped
all five final DDR records. It makes no algorithmic scheduling decisions.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "scripts/p02_4b_ring_fixture.py"

FIELDS = (
    "magic","version","result","error","steps","last_step","bank",
    "fault","fault_phase","runtime_phase","mmio_id","capabilities",
    "cores","slots","dispatches","packets","barriers","completed_steps",
    "initial_ins","replacement_ins","runtime_outs","flush_outs",
    "evictions","hits","pl_dispatch_lo","pl_dispatch_hi",
    "pl_page_lo","pl_page_hi","route_ticks_lo","route_ticks_hi",
    "barrier_ticks_lo","barrier_ticks_hi","infer_ticks_lo","infer_ticks_hi",
    "control_ticks_lo","control_ticks_hi","cntfrq_hz","resident_routes",
    "page_operations","hw_dispatches","last_page_bytes","global_status",
    "page_pending","read_bursts","write_bursts",
)


def verify(mailbox: Path, fixture_dir: Path, dump_dir: Path) -> bool:
    data = mailbox.read_bytes()
    if len(data) != 256:
        print(f"FAIL: P03 final mailbox size {len(data)} != 256",file=sys.stderr)
        return False
    fields = struct.unpack("<64I",data)
    observed = dict(zip(FIELDS,fields[:45]))
    manifest = json.loads((fixture_dir/"p03_run_manifest.json").read_text())
    errors = []
    def expect(label: str, actual: int, expected: int) -> None:
        if actual != expected:
            errors.append(f"{label}: actual=0x{actual:X} expected=0x{expected:X}")
    steps=manifest["p03_timesteps"]
    checks = {
        "magic":0x50335253,
        "version":1,"result":0x600D600D,"error":0,"steps":steps,
        "last_step":steps,"bank":steps&1,"fault":0,
        "runtime_phase":18, # P03_RT_DONE
        "mmio_id":0x4C543302,"capabilities":0x0001031F,
        "cores":5,"slots":3,"dispatches":5*steps,
        "packets":manifest["expected_packet_count_total"],
        "barriers":steps,"completed_steps":steps,
        "initial_ins":3,
        "replacement_ins":manifest["expected_replacement_page_ins"],
        "runtime_outs":manifest["expected_runtime_page_outs"],
        "flush_outs":manifest["expected_final_flush_page_outs"],
        "evictions":manifest["expected_evictions"],
        "hits":manifest["expected_page_hits"],
        "page_operations":manifest["expected_page_operations"],
        "hw_dispatches":5*steps,"last_page_bytes":106496,
        "global_status":0,"page_pending":0,
    }
    for name, expected in checks.items():
        expect(name,observed[name],expected)
    expect("manifest_crc",fields[60],
           int(manifest["p03_run_config_crc32"],16))
    expect("expected_packets_from_firmware",fields[63],
           manifest["expected_packet_count_total"])
    for core in range(5):
        actual_state=fields[45+2*core] | (fields[46+2*core]<<32)
        golden_state=int(manifest["final_state_words"][str(core)],16)
        expect(f"core{core}.state0",actual_state,golden_state)
        expect(
            f"core{core}.final_next_count",
            fields[55+core],
            len(manifest["final_next_events"][str(core)]),
        )
    if not 0 < observed["resident_routes"] <= observed["packets"]:
        errors.append(
            "resident_routes must be positive and not exceed total "
            "packets (independent physical MMIO resident-delivery coverage)"
        )
    for name in ("cntfrq_hz","read_bursts","write_bursts"):
        if observed[name]==0:
            errors.append(f"{name} cannot be zero in a physical 5-core run")
    for name in ("pl_dispatch_lo","pl_page_lo","infer_ticks_lo"):
        if observed[name]==0:
            errors.append(f"{name} cannot be zero in a physical run")
    if errors:
        for e in errors:
            print("FAIL: P03 "+e,file=sys.stderr)
        print(
            "FAIL: P03 autonomous A53 mailbox "
            f"error={observed['error']} first_fault={observed['fault']} "
            f"fault_phase={observed['fault_phase']} "
            f"result=0x{observed['result']:08X}",
            file=sys.stderr,
        )
        return False

    spec=importlib.util.spec_from_file_location("p03_p02_golden",ORACLE)
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        verification=module.verify(fixture_dir,dump_dir)
    except (OSError,ValueError,AssertionError) as error:
        print("FAIL: P03 DDR normalized golden mismatch: "+str(error),
              file=sys.stderr)
        return False
    print(
        "PASS: P03 autonomous five-over-three P02/v2 normalized golden "
        f"timesteps={steps} dispatches={5*steps} "
        f"packets={observed['packets']} "
        f"resident_deliveries={observed['resident_routes']} "
        f"barriers={observed['barriers']} "
        f"page_ins={3+observed['replacement_ins']} "
        f"page_outs={observed['runtime_outs']+observed['flush_outs']} "
        f"trace_sha256={manifest['trace_fingerprint']} "
        f"manifest_sha256={manifest['p03_launch_sha256']}"
    )
    print(
        "PASS: P03 all five final 512KiB DDR records byte-exact "
        "to frozen Python P02 oracle"
    )
    print(
        "P03_RESULT_METADATA="+json.dumps({
            "timesteps":steps,
            "dispatches":observed["dispatches"],
            "packets":observed["packets"],
            "resident_deliveries":observed["resident_routes"],
            "ps_timer_hz":observed["cntfrq_hz"],
            "inference_ticks":(
                observed["infer_ticks_lo"]+(observed["infer_ticks_hi"]<<32)
            ),
            "pl_dispatch_cycles":(
                observed["pl_dispatch_lo"]+(observed["pl_dispatch_hi"]<<32)
            ),
            "pl_page_cycles":(
                observed["pl_page_lo"]+(observed["pl_page_hi"]<<32)
            ),
            "record_checksums":verification["records"],
        },sort_keys=True)
    )
    return True


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--mailbox",type=Path,required=True)
    ap.add_argument("--fixture-dir",type=Path,required=True)
    ap.add_argument("--dump-dir",type=Path,required=True)
    args=ap.parse_args()
    return 0 if verify(args.mailbox,args.fixture_dir,args.dump_dir) else 1


if __name__=="__main__":
    raise SystemExit(main())
