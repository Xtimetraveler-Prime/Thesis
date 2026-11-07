#!/usr/bin/env python3
"""P08-B2.2 PC-only original 27-core SHA pins for a future A53 reset driver.

Independently re-verifies all 33 accepted original B2.4 frozen artifacts;
rebuilds original 27x512KiB aggregate SHA in canonical order; generates
an immutable new outside-repo header with 27 expected SHA256 digests.
Does not regenerate, overwrite, deploy, or change original model. NO JTAG.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import p07_b4l1_stage_frozen_27core as b4l1
import p07_b4l_physical_model_deploy as accepted

HEADER_FILE="p08_b2_2_original_context_sha256.h"
MANIFEST_FILE="p08_b2_2_original_context_reset_pins.json"

class ResetPinsNoGo(ValueError):
    pass


def generate_header(rows:list[dict]) -> str:
    if (len(rows)!=27 or
        [r.get("logical_core_id") for r in rows]!=list(range(27))):
        raise ResetPinsNoGo("original 27 core IDs must be sequential and complete")
    lines=[
        "#ifndef P08_B2_2_GENERATED_ORIGINAL_CONTEXT_SHA256_H",
        "#define P08_B2_2_GENERATED_ORIGINAL_CONTEXT_SHA256_H",
        "/* Exact original B2.4 frozen 27x512KiB P02 SHA256, PC-only stage.",
        " * Generated from immutable 33-file freeze; board use needs NEW admission. */",
        "#include <stdint.h>",
        "static const uint8_t p08_b2_original_context_sha256[27][32] = {",
    ]
    for core,row in enumerate(rows):
        digest=row.get("sha256")
        if (not isinstance(digest,str) or len(digest)!=64 or
            not all(c in "0123456789abcdef" for c in digest) or
            digest=="00"*32):
            raise ResetPinsNoGo(f"invalid original context sha at {core}")
        chunks=",".join(f"0x{int(digest[i:i+2],16):02x}" for i in range(0,64,2))
        lines.append(f"  {{{chunks}}}, /* original logical core {core:02d} */")
    lines.extend(["};","#endif",""])
    return "\n".join(lines)


def stage(frozen:Path,out:Path)->dict:
    root=Path(__file__).resolve().parents[3]  # Thesis git root
    if (not out.is_absolute() or out.is_symlink() or out.exists() or
        not out.parent.is_dir() or out.resolve().is_relative_to(root)):
        raise ResetPinsNoGo("require NEW external absolute stage directory")
    frozen_manifest=b4l1.admit_freeze(frozen)
    rows=b4l1.source_index(frozen,frozen_manifest)
    h=hashlib.sha256()
    for row in rows:
        source=frozen/row["source_relative_path"]
        block=source.read_bytes()
        if len(block)!=b4l1.STRIDE or hashlib.sha256(block).hexdigest()!=row["sha256"]:
            raise ResetPinsNoGo("original P02 changed during read: "+str(source))
        h.update(block)
    if h.hexdigest()!=accepted.ACCEPTED_BUNDLE_SHA:
        raise ResetPinsNoGo("original aggregate 27-context SHA mismatch")
    header=generate_header(rows)
    result={
        "schema":"p08-b2-2-original-27-context-sha256-pins-v1",
        "original_27_p02_bundle_sha256":h.hexdigest(),
        "original_frozen_manifest_sha256":b4l1.FROZEN_SHA,
        "original_27_core_count":27,
        "record_bytes":b4l1.STRIDE,
        "total_mutable_context_bytes":b4l1.TOTAL_BYTES,
        "original_source_base":"0x40000000",
        "original_source_end_exclusive":"0x40D80000",
        "proposed_new_mutation_free_backup_base":"0x43000000",
        "proposed_new_backup_end_exclusive":"0x43D80000",
        "generated_header_sha256":hashlib.sha256(header.encode()).hexdigest(),
        "original_per_core_sha256":[row["sha256"] for row in rows],
        "source_assets_changed":False,
        "physical_27_context_backup_readback":False,
        "physical_ddr_exclusivity_proven":False,
        "new_A53_ELF_built":False,
        "original_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "board_contact":False,
    }
    out.mkdir(mode=0o700)
    (out/HEADER_FILE).write_text(header,encoding="ascii")
    (out/MANIFEST_FILE).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",
                                  encoding="utf-8")
    return result


def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--frozen-dir",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    try:
        row=stage(a.frozen_dir,a.out)
        print("P08_B2_2_FROZEN_27_RESET_PINS_PASS=1")
        print("P08_B2_2_ORIGINAL_P02_BUNDLE_SHA256="+row["original_27_p02_bundle_sha256"])
        print("P08_B2_2_GENERATED_HEADER_SHA256="+row["generated_header_sha256"])
        print("P08_B2_2_PHYSICAL_BACKUP_READBACK=NOT_RUN")
        print("P08_B2_2_A53_FIRMWARE=NOT_BUILT")
        print("P08_B2_2_PIN_STAGE="+str(a.out))
    except (ResetPinsNoGo,ValueError,OSError,TypeError,KeyError) as exc:
        print("P08_B2_2_RESET_PINS_NO_GO="+str(exc),file=sys.stderr)
        return 3
    return 0


if __name__=="__main__":
    raise SystemExit(main())
