"""P06-A3.1 MNIST TRAIN-only IDX ingestion and reproducible split.

No torchvision dataset loader is used: its convenience download routine
may retrieve the *sealed test* archives. We access only the canonical two
training archives, check their published MD5 checksums and record SHA256
of archive bytes plus the decoded IDX payload. Test labels/bytes are never
opened here. This module has no torch dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
import gzip
import hashlib
import json
from pathlib import Path
import random
import struct
from urllib.request import urlopen

SOURCE = "torchvision MNIST canonical mirror (original Yann LeCun training IDX archives)"
MIRROR = "https://ossci-datasets.s3.amazonaws.com/mnist/"
TRAIN_FILES = {
    "images": ("train-images-idx3-ubyte.gz", "f68b3c2dcbeaaa9fbdd348bbdeb94873"),
    "labels": ("train-labels-idx1-ubyte.gz", "d53e105ee54ea40749a09fcbcd1e9432"),
}
TOTAL_IMAGES = 60000
TRAIN_IMAGES = 50000
VALIDATION_IMAGES = 10000
SPLIT_SEED = 20261013
SPLIT_SCHEMA = "p06-a3-mnist-train50000-val10000-seeded-v1"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def download_training_archives(directory: str | Path) -> tuple[Path, Path]:
    """Explicitly fetch the two canonical TRAIN archives, never t10k files.

    No network access occurs unless this function is explicitly invoked.
    Downloading into .part prevents treating partial files as valid archives.
    """
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, expected_md5 in TRAIN_FILES.values():
        path = folder / name
        if path.is_file() and hashlib.md5(path.read_bytes()).hexdigest() == expected_md5:
            paths.append(path)
            continue
        temp = folder / (name + ".part")
        try:
            with urlopen(MIRROR + name, timeout=120) as response, temp.open("wb") as out:
                size = 0
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    size += len(block)
                    if size > 100 * 1024 * 1024:
                        raise ValueError("unexpectedly large training archive")
                    out.write(block)
            if hashlib.md5(temp.read_bytes()).hexdigest() != expected_md5:
                raise ValueError(f"training archive checksum mismatch: {name}")
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)
        paths.append(path)
    return tuple(paths)


def _unpack_idx(raw: bytes, kind: str) -> tuple[int, bytes]:
    if kind == "images":
        if len(raw) < 16:
            raise ValueError("truncated MNIST image IDX header")
        magic, count, height, width = struct.unpack(">IIII", raw[:16])
        if magic != 2051 or (height, width) != (28, 28):
            raise ValueError("expected 28x28 uint8 MNIST training image IDX")
        offset, record_size = 16, 784
    elif kind == "labels":
        if len(raw) < 8:
            raise ValueError("truncated MNIST label IDX header")
        magic, count = struct.unpack(">II", raw[:8])
        if magic != 2049:
            raise ValueError("expected uint8 MNIST training label IDX")
        offset, record_size = 8, 1
    else:
        raise ValueError("unknown IDX kind")
    if len(raw) != offset + count * record_size:
        raise ValueError(f"truncated or trailing {kind} IDX data")
    if kind == "labels" and any(label > 9 for label in raw[offset:]):
        raise ValueError("MNIST labels must be in [0,9]")
    return count, raw[offset:]


def _hash_indices(indices: tuple[int, ...]) -> str:
    packed = bytearray()
    for index in indices:
        packed.extend(struct.pack("<I", index))
    return _sha256(packed)


@dataclass(frozen=True)
class TrainingSplit:
    """Decoded TRAIN image bytes; test archives cannot enter this container."""
    images: bytes  # 784 bytes per sample in canonical source order
    labels: bytes
    train_indices: tuple[int, ...]
    validation_indices: tuple[int, ...]
    manifest: dict

    @property
    def count(self) -> int:
        return len(self.labels)

    def manifest_json(self) -> str:
        return json.dumps(self.manifest, sort_keys=True, indent=2) + "\n"


def load_train_validation(
    directory: str | Path,
    *,
    seed: int = SPLIT_SEED,
    strict: bool = True,
) -> TrainingSplit:
    """Load the canonical TRAIN archives; fail closed on unexpected sources.

    strict=False is for tiny synthetic IDX test fixtures ONLY, not a valid
    benchmark or a CLI-selectable escape hatch. A real training run always
    requires 60,000 images and both canonical archive checksums.
    """
    if type(seed) is not int:
        raise TypeError("split seed must be an integer")
    folder = Path(directory)
    checksums = {}
    decoded = {}
    counts = {}
    for kind, (filename, expected_md5) in TRAIN_FILES.items():
        file = folder / filename
        if not file.is_file():
            raise FileNotFoundError(
                f"missing {file}; download explicitly with --download-train-only"
            )
        packed = file.read_bytes()
        md5 = hashlib.md5(packed).hexdigest()
        if strict and md5 != expected_md5:
            raise ValueError(f"noncanonical or corrupted MNIST TRAIN {kind} archive")
        try:
            raw = gzip.decompress(packed)
        except (OSError, EOFError) as error:
            raise ValueError(f"invalid compressed {kind} IDX archive") from error
        count, decoded[kind] = _unpack_idx(raw, kind)
        counts[kind] = count
        checksums[kind] = {
            "filename": filename, "source_md5": md5,
            "compressed_sha256": _sha256(packed),
            "decoded_idx_sha256": _sha256(raw),
        }
    if counts["images"] != counts["labels"]:
        raise ValueError("MNIST image/label count mismatch")
    if strict and counts["images"] != TOTAL_IMAGES:
        raise ValueError("MNIST training IDX must have 60,000 examples")
    count = counts["images"]
    if count < 2:
        raise ValueError("training fixture requires at least two examples")
    shuffled = list(range(count))
    random.Random(seed).shuffle(shuffled)
    if strict:
        n_train = TRAIN_IMAGES
    else:
        n_train = max(1, count * 5 // 6)
    train_ids, val_ids = tuple(shuffled[:n_train]), tuple(shuffled[n_train:])
    assert len(train_ids) + len(val_ids) == count
    if len(set(train_ids).intersection(val_ids)):
        raise AssertionError("train/validation split overlap")
    manifest = {
        "schema": SPLIT_SCHEMA if strict else "synthetic-idx-test-not-benchmark",
        "source": SOURCE, "mirror": MIRROR,
        "archives": checksums,
        "image_count": count,
        "shape": [28, 28], "pixel_dtype": "uint8", "labels": "uint8 0..9",
        "normalization": "none; raw 0..255 into p06-uint8-quota-phase17-v1",
        "split_seed": seed, "shuffle": "python random.Random(seed).shuffle(range(n))",
        "train_count": len(train_ids), "validation_count": len(val_ids),
        "train_indices_le32_sha256": _hash_indices(train_ids),
        "validation_indices_le32_sha256": _hash_indices(val_ids),
        "official_test_set": "sealed: no t10k archives opened",
    }
    return TrainingSplit(decoded["images"], decoded["labels"], train_ids, val_ids, manifest)
