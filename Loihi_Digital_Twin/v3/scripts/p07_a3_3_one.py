#!/usr/bin/env python3
"""One explicit A3.3 physical run: user reboots KV260 between invocations.

Reuses the accepted guarded A2 physical runner, one A53 batch at a time.
No automatic looping/rewrites/retries and no official MNIST test set.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess

from loihi_twin_v2.p07_a2_batch import parse_batch
from loihi_twin_v2.p07_a3_3_protocol import RUN_IDS, SCHEMA, sha


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--protocol-dir", type=Path, required=True)
    p.add_argument("--evidence-root", type=Path, required=True)
    p.add_argument("--run-id", choices=RUN_IDS, required=True)
    p.add_argument("--execute", action="store_true",
                   help="actually invoke physical XSDB/Vivado after reboot")
    args = p.parse_args()
    protocol = args.protocol_dir.resolve()
    evidence_root = args.evidence_root.resolve()
    if not protocol.is_dir() or not args.evidence_root.is_absolute():
        p.error("provide an existing absolute protocol directory and absolute evidence root")
    plan = json.loads((protocol/"p07_a3_3_protocol.json").read_text())
    if plan.get("schema") != SCHEMA or [r.get("run_id") for r in plan.get("runs", [])] != list(RUN_IDS):
        raise ValueError("P07-A3.3 precommitted run plan changed")
    entry = next(e for e in plan["runs"] if e["run_id"] == args.run_id)
    for prev in plan["runs"][:entry["order"]]:
        folder = evidence_root / prev["run_id"]
        if not (folder / "p07_a2_mailbox.bin").is_file() or not (folder/"verify.log").is_file() or (
            "P07_A2_PHYSICAL_TRACES_EXACT=1" not in (folder/"verify.log").read_text()):
            raise ValueError(
                "P07-A3.3 previous physical run missing or failed; do not skip attempts: "
                +prev["run_id"]
            )
    batch = protocol/entry["batch_name"]
    manifest = json.loads((batch/"p07_a2_manifest.json").read_text())
    header = (batch/"p07_a2_header_64.bin").read_bytes()
    payload = (batch/"p07_a2_ingress_payload.bin").read_bytes()
    rec = parse_batch(header, payload)
    expected = plan["batches"][int(entry["batch_name"][-2:])]
    if (len(rec) != 16 or manifest["frame_count"] != 16 or
            manifest["sha256"]["header"] != sha(header) or
            manifest["sha256"]["payload"] != sha(payload) or
            expected["header_sha256"] != sha(header) or
            expected["payload_sha256"] != sha(payload)):
        raise ValueError("P07-A3.3 physical batch was modified")
    run_dir = evidence_root/args.run_id
    if run_dir.exists():
        raise FileExistsError("P07-A3.3 preserves previous physical run; refuse overwrite: "+str(run_dir))
    print("P07_A3_3_NEXT_RUN="+args.run_id, flush=True)
    print("P07_A3_3_BATCH="+str(batch), flush=True)
    print("P07_A3_3_OUTPUT="+str(run_dir), flush=True)
    if not args.execute:
        print("P07_A3_3_DRY_RUN=1")
        print("Reboot KV260 into JTAG-only/bare-metal state before --execute.")
        return
    if os.environ.get("P07_A2_CONFIRM_KV260_DDR_OVERWRITE") != "YES":
        raise ValueError("reboot and explicitly set P07_A2_CONFIRM_KV260_DDR_OVERWRITE=YES")
    env = os.environ.copy()
    env["P07_A2_BATCH_DIR"] = str(batch)
    env["P07_A2_RUN_DIR"] = str(run_dir)
    shell = Path(__file__).resolve().with_name("run_p07_a2_physical.sh")
    subprocess.run(["bash", str(shell)], env=env, check=True)
    print("P07_A3_3_SINGLE_PHYSICAL_GATE_PASS="+args.run_id)


if __name__ == "__main__":
    main()
