"""P07-A4 precommitted full canonical 10,000-image MNIST TEST protocol.

CRITICAL: Loading/downloading the previously sealed official t10k archives
is allowed only via the explicit, separately gated P07-A4.2 command.
Native unit tests use entirely SYNTHETIC in-memory IDX fixtures.

The accepted on-board A53 ABI remains 16 frames/batch, hence 625
separate physical launches if unchanged. No model retraining or
numerical/DDR ABI changes are permitted.
"""
from __future__ import annotations

from dataclasses import dataclass
import gzip
import hashlib
import json
from pathlib import Path
import struct
from urllib.request import urlopen

from .p07_a1_ingress import encode_ingress
from .p07_a2_batch import (
    COMPILED_FINGERPRINT, DDR_SHA256, RESULT_BYTES,
    create_batch, parse_batch,
)

SCHEMA = "p07-a4-mnist-canonical-full10000-v1"
BATCH_SCHEMA = "p07-a4-mnist-canonical-16-v1"
LABEL_SCHEMA = "p07-a4-mnist-canonical-label-ledger-v1"
BATCH_SIZE = 16
FRAME_COUNT = 10000
BATCH_COUNT = 625
TRACE_FRAME = 0
XSA_SHA256 = "52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f"
MIRROR = "https://ossci-datasets.s3.amazonaws.com/mnist/"
TEST_FILES = {
    "images": ("t10k-images-idx3-ubyte.gz", "9fb629c4189551a2d022fa330f9573f3"),
    "labels": ("t10k-labels-idx1-ubyte.gz", "ec29112dd5afa0611ce80d1b7f02629c"),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode_json(data: dict) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True)+"\n").encode("utf-8")


@dataclass(frozen=True)
class OfficialTest:
    pixels: bytes
    labels: bytes
    manifest: dict

    @property
    def count(self) -> int:
        return len(self.labels)


def _idx_payload(idx: bytes, *, kind: str, count: int) -> bytes:
    """Independent parser usable for small synthetic IDX fixtures in unit tests.

    Real test loading ALWAYS invokes this with count=10000 and exact MD5s.
    """
    if type(count) is not int or count < 1:
        raise ValueError("IDX expected count must be positive integer")
    if kind == "images":
        if len(idx) < 16:
            raise ValueError("official test image IDX truncated")
        magic, n, height, width = struct.unpack_from(">4I", idx)
        header_bytes, stride = 16, 784
        if (magic, n, height, width) != (2051, count, 28, 28):
            raise ValueError("official image IDX shape/count/magic changed")
    elif kind == "labels":
        if len(idx) < 8:
            raise ValueError("official test label IDX truncated")
        magic, n = struct.unpack_from(">2I", idx)
        header_bytes, stride = 8, 1
        if (magic, n) != (2049, count):
            raise ValueError("official label IDX shape/count/magic changed")
    else:
        raise ValueError("unknown IDX kind")
    if len(idx) != header_bytes + count*stride:
        raise ValueError("official IDX truncated or has trailing bytes")
    out = idx[header_bytes:]
    if kind == "labels" and any(x > 9 for x in out):
        raise ValueError("official labels must be uint8 class [0,9]")
    return out


def load_canonical_official_test(directory: Path) -> OfficialTest:
    """Explicit P07-A4.2 TEST UNSEAL ONLY: MD5 + IDX + new measured SHA256."""
    decoded = {}
    provenance = {}
    for kind, (name, expected_md5) in TEST_FILES.items():
        filename = directory/name
        compressed = filename.read_bytes()
        if hashlib.md5(compressed).hexdigest() != expected_md5:
            raise ValueError(f"noncanonical/corrupted official MNIST TEST {kind} archive")
        try:
            raw = gzip.decompress(compressed)
        except (OSError, EOFError) as exc:
            raise ValueError(f"official {kind} not valid gzip") from exc
        decoded[kind] = _idx_payload(raw, kind=kind, count=FRAME_COUNT)
        provenance[kind] = {
            "filename": name, "source_url": MIRROR+name,
            "compressed_bytes": len(compressed), "source_md5": expected_md5,
            "compressed_sha256": sha(compressed), "decoded_idx_sha256": sha(raw),
        }
    if len(decoded["images"]) != FRAME_COUNT*784 or len(decoded["labels"]) != FRAME_COUNT:
        raise ValueError("canonical official dataset dimensions wrong")
    return OfficialTest(decoded["images"], decoded["labels"], {
        "schema": SCHEMA+"-actual-archive-provenance-v1",
        "source": "canonical torchvision MNIST t10k IDX; ORIGINAL order 0..9999",
        "archives": provenance, "image_count": FRAME_COUNT,
        "pixel_format": "row-major 28x28 uint8, no normalization",
        "labels": "uint8 class 0..9, host-only not transferred to A53",
        "selected_indices": "all original 0..9999 in original IDX order",
        "pixel_stream_sha256": sha(decoded["images"]),
        "label_stream_sha256": sha(decoded["labels"]),
    })


def download_canonical_official_test(directory: Path) -> None:
    """Explicitly requested UNSEAL; NEVER called at import/native unit gate."""
    directory.mkdir(parents=True, exist_ok=True)
    for name, expected_md5 in TEST_FILES.values():
        output = directory/name
        if output.exists():
            if hashlib.md5(output.read_bytes()).hexdigest() != expected_md5:
                raise ValueError("existing noncanonical official TEST archive: "+str(output))
            continue
        temp = directory/(name+".part")
        if temp.exists():
            raise FileExistsError("leftover partial official archive; inspect before retry: "+str(temp))
        try:
            with urlopen(MIRROR+name, timeout=120) as response, temp.open("xb") as target:
                size = 0
                while True:
                    part = response.read(1024*1024)
                    if not part:
                        break
                    size += len(part)
                    if size > 100*1024*1024:
                        raise ValueError("unexpectedly large test archive")
                    target.write(part)
            if hashlib.md5(temp.read_bytes()).hexdigest() != expected_md5:
                raise ValueError("downloaded official TEST archive MD5 mismatch: "+name)
            temp.rename(output)
        finally:
            temp.unlink(missing_ok=True)


@dataclass(frozen=True)
class OfficialBatch:
    header: bytes
    payload: bytes
    manifest: dict
    labels: dict


def make_batch(test: OfficialTest, index: int,
               mapping: tuple[int, ...]) -> OfficialBatch:
    """Fixed 16-frame batch in canonical order, labels in separate HOST ledger."""
    if test.count != FRAME_COUNT or len(test.pixels) != FRAME_COUNT*784:
        raise ValueError("P07-A4 batch needs complete canonical 10,000-image TEST")
    if type(index) is not int or not 0 <= index < BATCH_COUNT:
        raise ValueError("P07-A4 physical batch index must be in 0..624")
    if len(mapping) != 784:
        raise ValueError("P07-A4 frozen compiled ingress must map exactly 784 pixels")
    first = index*BATCH_SIZE
    records = []
    rows = []
    for local in range(BATCH_SIZE):
        n = first+local
        pixel = test.pixels[n*784:(n+1)*784]
        label = test.labels[n]
        raw = encode_ingress(pixel, mapping, ddr_sha256=DDR_SHA256,
                             deployment_fingerprint=COMPILED_FINGERPRINT)
        records.append(raw)
        rows.append({
            "frame": local, "test_index": n, "truth": label,
            "pixels_sha256": sha(pixel), "ingress_sha256": sha(raw),
        })
    header, payload = create_batch(tuple(records), trace_frame=TRACE_FRAME)
    if parse_batch(header, payload) != tuple(records):
        raise AssertionError("P07-A4 batch self-validation failed")
    manifest = {
        "schema": BATCH_SCHEMA,
        "scope": "official MNIST TEST physical NOT RUN",
        "batch_index": index, "first_test_index": first,
        "last_test_index": first+BATCH_SIZE-1,
        "frame_count": BATCH_SIZE, "trace_frame": TRACE_FRAME,
        "ddr_sha256": DDR_SHA256,
        "compiled_fingerprint": COMPILED_FINGERPRINT,
        "sha256": {
            "header": sha(header), "payload": sha(payload),
            "mailbox_initial": sha(bytes(RESULT_BYTES)),
            "records": [sha(r) for r in records],
        },
        "official_mnist_test": "UNSEALED_FOR_FROZEN_FULL_10000_PROTOCOL_NOT_YET_SCORED",
    }
    ledger = {
        "schema": LABEL_SCHEMA, "batch_index": index,
        "batch_header_sha256": sha(header),
        "batch_payload_sha256": sha(payload), "rows": rows,
        "labels_host_only": True,
    }
    return OfficialBatch(header, payload, manifest, ledger)


def immutable_plan(test: OfficialTest, mapping: tuple[int, ...]) -> tuple[dict, tuple[OfficialBatch, ...]]:
    """Build 625 complete official batches before writing; no oracle predictions."""
    if test.count != FRAME_COUNT:
        raise ValueError("official full evaluation has denominator 10000")
    batches = tuple(make_batch(test, b, mapping) for b in range(BATCH_COUNT))
    source = test.manifest
    if source.get("image_count") != FRAME_COUNT:
        raise ValueError("P07-A4 canonical official test manifest is incomplete")
    plan = {
        "schema": SCHEMA, "population": "full canonical MNIST TEST, original index order",
        "official_test_count": FRAME_COUNT, "physical_batches": BATCH_COUNT,
        "physical_launch_mode": "manual cold/JTAG bare-metal reboot before each of 625 launches",
        "wire_format": "P07A2B01 16x2480 input records, 64B header, 64KiB result mailbox",
        "predictions_required": FRAME_COUNT,
        "failure_policy": "no skipping, no denominator reduction, preserve earliest error and any retries separately",
        "ddr_sha256": DDR_SHA256, "compiled_fingerprint": COMPILED_FINGERPRINT,
        "xsa_sha256": XSA_SHA256, "encoder": "p06-uint8-quota-phase17-v1",
        "timesteps": 26, "readout": "10 class spike counts, argmax lowest class, silence=0",
        "dataset": source,
        "batches": [
            {"batch_index": i, "batch_name": f"batch_{i:04d}",
             "indices": [i*16, i*16+15],
             "header_sha256": b.manifest["sha256"]["header"],
             "payload_sha256": b.manifest["sha256"]["payload"],
             "labels_sha256": sha(encode_json(b.labels))}
            for i,b in enumerate(batches)
        ],
        "status": "OFFICIAL_DATA_PREPARED / KV260_NOT_YET_RUN / NOT_SCORED",
    }
    return plan, batches


def write_plan(directory: Path, plan: dict,
               batches: tuple[OfficialBatch, ...]) -> None:
    if directory.exists():
        raise FileExistsError("official TEST prepared directory exists; no overwrite")
    if (plan.get("schema") != SCHEMA or
            plan.get("official_test_count") != FRAME_COUNT or
            len(batches) != BATCH_COUNT):
        raise ValueError("P07-A4 cannot write a reduced/mutated official evaluation")
    directory.mkdir(parents=True, exist_ok=False)
    for index, batch in enumerate(batches):
        base = directory/f"batch_{index:04d}"
        base.mkdir(exist_ok=False)
        (base/"p07_a2_header_64.bin").write_bytes(batch.header)
        (base/"p07_a2_ingress_payload.bin").write_bytes(batch.payload)
        (base/"p07_a2_mailbox_zero_64k.bin").write_bytes(bytes(RESULT_BYTES))
        (base/"p07_a2_manifest.json").write_bytes(encode_json(batch.manifest))
        (base/"p07_a4_test_labels_HOST_ONLY.json").write_bytes(encode_json(batch.labels))
    (directory/"p07_a4_full10000_protocol.json").write_bytes(encode_json(plan))


def verify_plan(directory: Path, test: OfficialTest,
                mapping: tuple[int, ...]) -> tuple[dict, tuple[OfficialBatch, ...]]:
    """Fresh canonical test reload ties every label/pixel/record to locked plan."""
    expected, batches = immutable_plan(test, mapping)
    if (directory/"p07_a4_full10000_protocol.json").read_bytes() != encode_json(expected):
        raise ValueError("official 10k precommitted manifest or dataset SHA mismatch")
    for i,b in enumerate(batches):
        folder = directory/f"batch_{i:04d}"
        want = {
            "p07_a2_header_64.bin": b.header,
            "p07_a2_ingress_payload.bin": b.payload,
            "p07_a2_mailbox_zero_64k.bin": bytes(RESULT_BYTES),
            "p07_a2_manifest.json": encode_json(b.manifest),
            "p07_a4_test_labels_HOST_ONLY.json": encode_json(b.labels),
        }
        for name, exact in want.items():
            if (folder/name).read_bytes() != exact:
                raise ValueError(f"official test batch_ {i:04d} / {name} differs from frozen original")
    return expected, batches
