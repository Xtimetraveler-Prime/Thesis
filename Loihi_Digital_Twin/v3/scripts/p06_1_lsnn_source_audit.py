#!/usr/bin/env python3
"""P06.1 audit immutable PAPER-LINKED LSNN source and trained .npy headers.

No NxSDK import, no MNIST official test evaluation, no training, no
guessing missing weights. All pinned objects are upstream Git blobs.
The separate source manifest is the candidate record, not an accepted
benchmark freeze or a claim that AHP already runs on the KV260.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"docs/P06_1_LSNN_SOURCE_MANIFEST.json"
EXPECTED_COMMIT="3dc53bfcfae1efe8772b8cb5e2c512bb28c872f8"
# ORIGINAL ON-DISK matrices are (source, destination). The author's
# apps/seqmnist/seq_mnist.py loadWeightsAndDelays() returns
# (wIn.T, wRec.T, wOut.T); the runtime expects (destination, source).
# Do not confuse the stored checkpoint with the runtime connectivity arrays.
EXPECTED_SHAPES={
    "w_in.npy":(80,240),
    "w_rec.npy":(240,240),
    "w_out.npy":(240,10),
}
EXPECTED_BYTES={"w_in.npy":76928,"w_rec.npy":230528,"w_out.npy":9728}

def parse_npy_header(blob:bytes)->dict:
    """Parse and validate NumPy .npy v1/v2/v3 header without executing data."""
    if blob[:6]!=b"\x93NUMPY" or len(blob)<12:
        raise ValueError("not a NumPy .npy data file")
    major,minor=blob[6],blob[7]
    if (major,minor) not in ((1,0),(2,0),(3,0)):
        raise ValueError(f"unexpected NumPy array version {major}.{minor}")
    if major==1:
        size=struct.unpack_from("<H",blob,8)[0]
        offset=10
    else:
        size=struct.unpack_from("<I",blob,8)[0]
        offset=12
    if size<10 or offset+size>len(blob):
        raise ValueError("truncated or invalid NumPy header length")
    try:
        header=ast.literal_eval(blob[offset:offset+size].decode(
            "utf-8" if major==3 else "latin1"
        ).strip())
    except (SyntaxError,ValueError,UnicodeDecodeError) as e:
        raise ValueError("bad literal NumPy header") from e
    if type(header) is not dict or set(header)!={"descr","fortran_order","shape"}:
        raise ValueError("unexpected NumPy metadata schema")
    shape=header["shape"]
    if (not isinstance(shape,tuple) or len(shape)!=2 or
        not all(type(n)==int and n>0 for n in shape)):
        raise ValueError("shape must be nonempty two-dimensional matrix")
    if header["fortran_order"] is not False:
        raise ValueError("unexpected Fortran-order matrix; inspect source before mapping")
    dtype=header["descr"]
    # No object, structured, big-endian or variable-length payloads.
    if dtype not in ("<f4","<i4","<u4","=f4","=i4","=u4","|i4","|u4","|f4"):
        raise ValueError(f"unexpected weight dtype {dtype!r}; no coerced assumptions")
    values=shape[0]*shape[1]
    bytes_expected=offset+size+values*4
    if bytes_expected!=len(blob):
        raise ValueError(f"NumPy header/payload byte mismatch {len(blob)} vs {bytes_expected}")
    return {
        "version":f"{major}.{minor}",
        "descr":dtype,"shape":list(shape),
        "fortran_order":False,
        "payload_elements":values,"payload_bytes":values*4,
        "header_bytes":offset+size,
    }

def measure_weight_payload(blob:bytes,header:dict)->dict:
    """Inspect actual original 4-byte coefficients; never guess sparsity.

    This only counts source .npy values, not Loihi compressed synapse
    entries or physical mapped synapse occupancy.
    """
    descr=header["descr"]
    kind=descr[-2]
    fmt={"f":"<f","i":"<i","u":"<I"}.get(kind)
    if fmt is None:
        raise ValueError("unsupported four-byte numeric weight kind")
    data=memoryview(blob)[header["header_bytes"]:]
    positive=negative=zeros=0
    minimum=None
    maximum=None
    for (v,) in struct.iter_unpack(fmt,data):
        if kind=="f" and not math.isfinite(v):
            raise ValueError("NaN or infinite weight in original pretrained matrix")
        if v>0:
            positive+=1
        elif v<0:
            negative+=1
        else:
            zeros+=1
        if minimum is None or v<minimum:
            minimum=v
        if maximum is None or v>maximum:
            maximum=v
    entries=positive+negative+zeros
    if entries!=header["payload_elements"] or entries==0:
        raise ValueError("trained matrix payload element count inconsistent")
    return {
        "entries":entries,"positive_entries":positive,
        "negative_entries":negative,"zero_entries":zeros,
        "nonzero_entries":positive+negative,
        "density_fraction":(positive+negative)/entries,
        "min_value":minimum,"max_value":maximum,
    }


def git_output(folder:Path,*args:str)->str:
    p=subprocess.run(
        ["git","-C",str(folder),*args],text=True,capture_output=True,
        check=False,timeout=15,
    )
    if p.returncode:
        raise ValueError("git source provenance command failed: "+
                         " ".join(args)+" :: "+p.stderr.strip()[:180])
    return p.stdout.strip()

def digest(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def audit(upstream:Path)->dict:
    if not MANIFEST.is_file():
        raise ValueError("P06 source manifest missing")
    man=json.loads(MANIFEST.read_text())
    if (man["schema"]!="p06-lsnn-source-candidate-v1" or
        man["status"]!="CANDIDATE_SOURCE_PIN_ONLY_NOT_FROZEN_OR_REPRODUCED" or
        man["upstream"]["commit"]!=EXPECTED_COMMIT or
        man["freeze_status"]!="PROHIBITED_UNTIL_SOURCE_ASSET_AUDIT_AND_FPGA_CONTRACT_PROVEN_AND_REVIEWED"):
        raise ValueError("candidate source manifest unreviewed mutation")
    upstream=upstream.resolve(strict=True)
    if git_output(upstream,"rev-parse","HEAD")!=EXPECTED_COMMIT:
        raise ValueError("upstream NOT checked out to paper-linked pinned exact commit")
    if git_output(upstream,"status","--porcelain","--untracked-files=no"):
        raise ValueError("upstream tracked files modified; cannot audit source identity")
    assets={}
    if len(man["upstream"]["files"])!=9:
        raise ValueError("all 3 weight files and 6 source files required")
    seen=set()
    for entry in man["upstream"]["files"]:
        rel=entry["path"]
        if rel in seen or rel.startswith("/") or ".." in Path(rel).parts:
            raise ValueError("invalid/duplicate pinned artifact path")
        seen.add(rel)
        p=upstream/rel
        if not p.is_file() or p.is_symlink():
            raise ValueError("required upstream file missing or symlink: "+rel)
        if p.stat().st_size!=entry["size_bytes"]:
            raise ValueError("upstream file byte-size mismatch: "+rel)
        if git_output(upstream,"hash-object",rel)!=entry["git_blob"]:
            raise ValueError("upstream Git SHA blob mismatch: "+rel)
        row={
            "git_blob_sha1":entry["git_blob"],
            "sha256":digest(p),
            "file_bytes":p.stat().st_size,
        }
        if entry["type"]=="WEIGHTS_REQUIRE_LOCAL_DTYPE_HEADER_VERIFICATION":
            raw=p.read_bytes()
            header=parse_npy_header(raw)
            expected=EXPECTED_SHAPES.get(p.name)
            if expected is None or tuple(header["shape"])!=expected:
                raise ValueError("unexpected paper-linked pretrained matrix shape: "+rel)
            if len(raw)!=EXPECTED_BYTES[p.name]:
                raise ValueError("unexpected paper-linked pretrained matrix byte count")
            if header["descr"]!=entry["expected_stored_dtype"]:
                raise ValueError("pinned checkpoint actual stored dtype mismatch: "+rel)
            if tuple(entry["expected_shape"])!=expected:
                raise ValueError("pinned checkpoint stored-shape manifest mismatch: "+rel)
            if tuple(entry.get("expected_runtime_shape_after_author_transpose",[]))!=expected[::-1]:
                raise ValueError("pinned author runtime transpose contract mismatch: "+rel)
            row["numpy_header"]=header
            row["author_runtime_shape_after_transpose"]=[expected[1],expected[0]]
            row["source_coefficients"]=measure_weight_payload(raw,header)
            declared=man["upstream"]["observed_matrix_statistics_from_pinned_blobs"][p.name]
            measured=row["source_coefficients"]
            for key,obs_key in (("entries","entries"),("nonzero","nonzero_entries"),
                                ("zeros","zero_entries"),("positive","positive_entries"),
                                ("negative","negative_entries"),("min","min_value"),
                                ("max","max_value")):
                if declared[key]!=measured[obs_key]:
                    raise ValueError("pinned genuine coefficient statistics mismatch: "+p.name)
        assets[rel]=row
    all_weights=sum(a["numpy_header"]["payload_elements"]
                    for a in assets.values() if "numpy_header" in a)
    if all_weights!=79200:
        raise ValueError("unexpected exact physical candidate matrix position count")
    combined=man["upstream"]["observed_matrix_statistics_from_pinned_blobs"]["total"]
    if combined["entries"]!=all_weights:
        raise ValueError("pinned total coefficient count mismatch")
    physical_coefficients={
        "entries":all_weights,
        "nonzero_entries":sum(a["source_coefficients"]["nonzero_entries"]
                              for a in assets.values()
                              if "source_coefficients" in a),
    }
    physical_coefficients["zero_entries"]=(
        all_weights-physical_coefficients["nonzero_entries"])
    physical_coefficients["density_fraction"]=(
        physical_coefficients["nonzero_entries"]/all_weights)
    if (physical_coefficients["nonzero_entries"]!=combined["nonzero"]
        or physical_coefficients["zero_entries"]!=combined["zeros"]):
        raise ValueError("pinned aggregate weight-sparsity provenance mismatch")
    info={
        "profile":man["schema"],
        "status":"IMMUTABLE_AUTHOR_SOURCE_VERIFIED; NO_FPGA_FREEZE",
        "upstream_repository":man["upstream"]["repository"],
        "upstream_commit":EXPECTED_COMMIT,
        "source_manifest_sha256":digest(MANIFEST),
        "candidate":"Rao et al. 2022 sMNIST Loihi 1 AHP-LSNN",
        "topology":{"input_channels":80,"regular_units":140,
                    "adaptive_units":100,"nonspiking_outputs":10,
                    "source_dense_matrix_positions":79200,
                    "source_weight_occupancy":physical_coefficients},
        "source_files":assets,
        "limitations":"Exact source/header provenance only. No NxSDK reference run, "
                      "paper-specified accuracy association, AHP FPGA support, "
                      "MNIST checksum, or P06 freeze.",
    }
    return info

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--upstream-repo",required=True,type=Path)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    try:
        data=audit(args.upstream_repo)
        if args.out:
            if args.out.exists():raise ValueError("refuse to overwrite source-audit evidence")
            args.out.parent.mkdir(parents=True,exist_ok=True)
            args.out.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    except (OSError,ValueError,KeyError,TypeError,subprocess.TimeoutExpired) as e:
        print("FAIL: P06.1 official source/weights audit: "+str(e),file=sys.stderr)
        print("P06_1_SOURCE_AUDIT_EXIT=1",file=sys.stderr)
        return 1
    print("PASS: P06.1 official paper-linked upstream git commit and all nine immutable author artifacts exact")
    print("PASS: P06.1 all three genuine pretrained source weight files verified, no retraining or fabricated weights")
    print("P06_1_SOURCE_AUDIT_METADATA="+json.dumps({
        "commit":EXPECTED_COMMIT,
        "shape_by_file":{p:a["numpy_header"]["shape"] for p,a in data["source_files"].items()
                         if "numpy_header" in a},
        "dtype_by_file":{p:a["numpy_header"]["descr"] for p,a in data["source_files"].items()
                         if "numpy_header" in a},
        "source_manifest_sha256":data["source_manifest_sha256"],
        "real_trained_coefficients":data["topology"]["source_weight_occupancy"],
    },sort_keys=True))
    print("P06_1_SOURCE_AUDIT_EXIT=0")
    print("P06_1_PAPER_FREEZE=NOT_ACCEPTED_AHP_EXTENSION_AND_BENCHMARK_METRIC_AUDIT_REQUIRED")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
