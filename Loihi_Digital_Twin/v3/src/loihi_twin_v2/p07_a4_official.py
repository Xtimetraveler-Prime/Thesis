"""P07-A4.3/4 sealed-independent OFFICIAL full10000 persistent evaluation.

Never download/open canonical TEST implicitly; callers must explicitly load
canonical t10k through the existing MD5/IDX-gated loader after separate
physical-fault admission and user --i-accept-unseal. All outputs and labels
stay HOST-side. The KV260 sees only 784-byte images and frozen mapping.
No access to original TRAIN partition or model weights changes.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import json
import struct

from .p07_a4_protocol import OfficialTest, FRAME_COUNT, SCHEMA
from .p07_a4_stream import (
    Stream, make_stream, parse_stream, parse_journal, initial_journal, sha256,
)
from .p07_a2_batch import COMPILED_FINGERPRINT, DDR_SHA256

STAGE_SCHEMA = "p07-a4-3-official-persistent-original10000-v1"
LEDGER_SCHEMA = "p07-a4-3-official-labels-host-only-v1"
TRACE_INDEX = 9999
SCOPE = "OFFICIAL_MNIST_TEST_FULL10000"
STAGE_FILES = {
    "descriptor":"p07_a4_descriptor_256.bin",
    "mapping":"p07_a4_mapping_1568.bin",
    "pixels":"p07_a4_pixels_raw.bin",
    "zero_journal_1m":"p07_a4_journal_initial_1m.bin",
}
LEDGER_FILE = "p07_a4_official_labels_HOST_ONLY.json"
MANIFEST_FILE = "p07_a4_official_stage_manifest.json"


def _check_official(test: OfficialTest) -> None:
    if (not isinstance(test,OfficialTest) or
        test.count!=FRAME_COUNT or len(test.pixels)!=FRAME_COUNT*784 or
        len(test.labels)!=FRAME_COUNT or
        test.manifest.get("schema")!=SCHEMA+"-actual-archive-provenance-v1" or
        test.manifest.get("image_count")!=FRAME_COUNT or
        test.manifest.get("pixel_stream_sha256")!=sha256(test.pixels) or
        test.manifest.get("label_stream_sha256")!=sha256(test.labels) or
        any(label>9 for label in test.labels)):
        raise ValueError("P07-A4 canonical original-order 10000 TEST provenance mismatch")
    archives=test.manifest.get("archives",{})
    if set(archives)!={"images","labels"} or any(
        not isinstance(archives[k].get("compressed_sha256"),str) or
        not isinstance(archives[k].get("decoded_idx_sha256"),str)
        for k in ("images","labels")):
        raise ValueError("P07-A4 official canonical archive SHA256 manifests missing")


def make_official_stage(test: OfficialTest, mapping: tuple[int,...]) -> tuple[
    Stream, dict, dict, dict[str,bytes]
]:
    """Pure host function: CI uses synthetic 10000 images, NOT test files.

    Production callers must only obtain OfficialTest using the original
    canonical loader, which verifies two pinned compressed archive MD5s.
    """
    _check_official(test)
    stream=make_stream(test.pixels,mapping,trace_index=TRACE_INDEX)
    files={
        "descriptor":stream.header,
        "mapping":stream.mapping_bytes,
        "pixels":stream.images,
        "zero_journal_1m":initial_journal(stream),
    }
    rows=[{
        "index":i,
        "truth":test.labels[i],
        "pixels_sha256":sha256(stream.image(i)),
    } for i in range(FRAME_COUNT)]
    ledger={
        "schema":LEDGER_SCHEMA,"scope":SCOPE,
        "official_mnist_test":"UNSEALED_PREPARED_NOT_SCORED",
        "labels_host_only":True,"original_test_indices":[0,FRAME_COUNT-1],
        "count":FRAME_COUNT,
        "source_label_sha256":sha256(test.labels),
        "rows":rows,
    }
    manifest={
        "schema":STAGE_SCHEMA,"scope":SCOPE,
        "official_mnist_test":"UNSEALED_PREPARED_NOT_SCORED",
        "physical_hardware":"NOT_RUN",
        "count":FRAME_COUNT,"trace_index":TRACE_INDEX,
        "full_test_population":"original canonical IDX image index 0..9999",
        "selected_full_compartment_trace_only":TRACE_INDEX,
        "per_image_physical_output_spikes":"26x10 for every image",
        "measurement_policy":"one full 26x42 trace for original test image 9999, all 10000 per-image output spikes/routes",
        "ddr_sha256":DDR_SHA256,
        "compiled_fingerprint":COMPILED_FINGERPRINT,
        "source_manifest":test.manifest,
        "sha256":{key:sha256(value) for key,value in files.items()},
        "labels_host_only_sha256":sha256(
            (json.dumps(ledger,sort_keys=True,indent=2)+"\n").encode()
        ),
    }
    return stream,manifest,ledger,files


def write_official_stage(directory: Path, test: OfficialTest,
                         mapping: tuple[int,...]) -> dict:
    """Exclusive immutable new output directory; NEVER overwrite evidence."""
    stream,manifest,ledger,files=make_official_stage(test,mapping)
    if directory.exists():
        raise FileExistsError("P07-A4 official persistent source already exists: "+str(directory))
    directory.mkdir(parents=True,exist_ok=False)
    for key,name in STAGE_FILES.items():
        (directory/name).write_bytes(files[key])
    (directory/LEDGER_FILE).write_text(
        json.dumps(ledger,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    (directory/MANIFEST_FILE).write_text(
        json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return manifest


def check_official_stage(directory: Path,test: OfficialTest) -> tuple[Stream,dict,dict]:
    """Reload actual canonical test and compare every byte/host-only label."""
    _check_official(test)
    manifest=json.loads((directory/MANIFEST_FILE).read_text(encoding="utf-8"))
    ledger=json.loads((directory/LEDGER_FILE).read_text(encoding="utf-8"))
    raw={k:(directory/name).read_bytes() for k,name in STAGE_FILES.items()}
    for key,data in raw.items():
        if manifest.get("sha256",{}).get(key)!=sha256(data):
            raise ValueError("P07-A4 official staged bytes SHA mismatch: "+key)
    stream=parse_stream(raw["descriptor"],raw["mapping"],raw["pixels"])
    if (manifest.get("schema")!=STAGE_SCHEMA or
        manifest.get("scope")!=SCOPE or
        manifest.get("official_mnist_test")!="UNSEALED_PREPARED_NOT_SCORED" or
        manifest.get("physical_hardware")!="NOT_RUN" or
        manifest.get("count")!=FRAME_COUNT or
        manifest.get("trace_index")!=TRACE_INDEX or
        manifest.get("source_manifest")!=test.manifest or
        manifest.get("ddr_sha256")!=DDR_SHA256 or
        manifest.get("compiled_fingerprint")!=COMPILED_FINGERPRINT or
        manifest.get("measurement_policy")!=
          "one full 26x42 trace for original test image 9999, all 10000 per-image output spikes/routes" or
        stream.image_count!=FRAME_COUNT or stream.trace_index!=TRACE_INDEX or
        stream.images!=test.pixels or
        raw["zero_journal_1m"]!=initial_journal(stream)):
        raise ValueError("P07-A4 canonical full TEST original-order persistent stage mutated")
    ledger_bytes=(directory/LEDGER_FILE).read_bytes()
    if (sha256(ledger_bytes)!=manifest.get("labels_host_only_sha256") or
        ledger.get("schema")!=LEDGER_SCHEMA or
        ledger.get("scope")!=SCOPE or
        ledger.get("official_mnist_test")!="UNSEALED_PREPARED_NOT_SCORED" or
        ledger.get("labels_host_only") is not True or
        ledger.get("original_test_indices")!=[0,9999] or
        ledger.get("count")!=FRAME_COUNT or
        ledger.get("source_label_sha256")!=sha256(test.labels) or
        len(ledger.get("rows",[]))!=FRAME_COUNT):
        raise ValueError("P07-A4 official host-only label ledger changed")
    for i,row in enumerate(ledger["rows"]):
        if (row.get("index")!=i or row.get("truth")!=test.labels[i] or
            row.get("pixels_sha256")!=sha256(stream.image(i))):
            raise ValueError(f"P07-A4 official original-order pixel/label ledger mismatch idx={i}")
    return stream,manifest,ledger


def full_score(records, test: OfficialTest) -> dict:
    """Only caller should invoke AFTER complete independent physical oracle."""
    _check_official(test)
    if len(records)!=FRAME_COUNT:raise ValueError("P07-A4 no partial score denominator")
    cm=[[0]*10 for _ in range(10)]
    silent=0
    out=[]
    for i,r in enumerate(records):
        if r.image_index!=i or not 0<=r.predicted<10:
            raise ValueError("P07-A4 record order mutated during scoring")
        y=test.labels[i]
        cm[y][r.predicted]+=1
        silent+=int(r.all_silent)
        out.append({
            "index":i,"true_label":y,"predicted":r.predicted,
            "spike_counts":list(r.counts),"all_silent":int(r.all_silent),
            "raw_pixel_sha256":sha256(test.pixels[i*784:(i+1)*784]),
        })
    right=sum(cm[i][i] for i in range(10))
    return {
        "schema":"p07-a4-4-full10000-physical-score-v1",
        "source":"canonical MNIST TEST ORIGINAL IDX order indices 0..9999",
        "test_samples":FRAME_COUNT,"correct":right,
        "accuracy_fraction":right/FRAME_COUNT,
        "accuracy_percent":100*right/FRAME_COUNT,
        "incorrect":FRAME_COUNT-right,"all_silent":silent,
        "confusion_matrix_rows_truth_columns_predicted":cm,
        "class_support":[sum(row) for row in cm],
        "class_recall":[cm[i][i]/sum(cm[i]) if sum(cm[i]) else None for i in range(10)],
        "rows":out,
    }
