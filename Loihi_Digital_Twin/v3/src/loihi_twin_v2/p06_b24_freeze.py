"""P06-B2.4 reproducible, no-overwrite, full trained checkpoint/DDR freeze.

Recreates the user-verified B2.3 three-frame numerical gate from canonical
TRAIN-only archives, then serializes the actual trained source graph, B1.2
mapping, 27 accepted P02 initial 512KiB DDR records and full checkpoint
bytes to a *new* local, hash-indexed directory. Never touches official TEST,
changes the existing B2.2 candidate or runs hardware. Freeze materialization
does not imply user-native B2.4 acceptance or actual physical deployment.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile

from .compiler import NetworkSpec
from .ddr_abi import (
    P02_DDR_CONTEXT_STRIDE_BYTES, build_initial_ddr_context_record,
    ddr_context_offset, parse_ddr_context_header,
)
from .hardware_p08 import export_paged_hardware_image
from .p06_b12_partition import B12Options, B12Result, compile_synapse_aware
from .p06_b22_training import load_candidate
from .p06_b23_trained_audit import audit_candidate, PINNED_B22_WEIGHTS_SHA256, PINNED_B22_INTEGER_SHA256

B24_SCHEMA = "p06-b2.4-trained-27core-static-ddr-freeze-v1"
B24_VALIDATION_ORDINALS = (0, 1, 2)
B24_RECORDS_DIR = "initial_ddr"
B24_MANIFEST_NAME = "frozen_manifest.json"
B24_PROTOCOL_NAME = "predeclared_official_test_protocol.json"

# Captured directly from user-reported, previously accepted B2.3 full 26-tick
# numerical report on the canonical *TRAIN-DERIVED VALIDATION* ordinals.
PINNED_B23_SOURCE_SHA256 = "0a3ec838a9f95a73de118e37f31d596bf38e63cd8cf82e6f5c9d0dd48b22797a"
PINNED_B23_DEPLOYMENT_SHA256 = "02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a"
PINNED_B23_CAPACITY_SHA256 = "82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498"
PINNED_B23_FRAMES = (
    (0, 37384, "5978f00e0f60c14e1ee17ea73f08f071516de8d0eb89b0e7cab1753d53d7fcd3",
     "4bef8f76965d4080a7c4ec2f3feab7c805e636d6397afb80a4a09f07733aea35",
     "4afdce2bdd77e74199727872f882ee271aabdf8560ed11876749b94b612b43aa"),
    (1, 27347, "3e3c39ef3319fb9dc08c3661f3a9a9575d131db7946ab90f95f457d9189429c3",
     "e62d996996d795f2fefe681e928586b066957c746f9ef9ca60692c11ad5c31ca",
     "1cb32f77092862e856bfcd488b7a2239e61675d159e2e655f22a98579acdb214"),
    (2, 20178, "ecba50a209e6d07d7d12d2121a2931330e9085054e63831d38242c10300930c1",
     "9cce27d0d59145b5249acdbec46564af20040bbbccf12f3cab3e5f36e00c707a",
     "9c5766a6ce5302fa357449d78c32d0c9580872314ee7f5605e339a082ba7083b"),
)


class B24FreezeError(ValueError):
    """Missing, tampered, inconsistent, or unsafe frozen source/output."""


def sha256_file(path: Path) -> str:
    d = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            d.update(chunk)
    return d.hexdigest()


def canonical_sha(document: dict) -> str:
    return hashlib.sha256(json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("utf-8")).hexdigest()


def _dump_json(path: Path, document: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, sort_keys=True, indent=2)
        handle.write("\n")


def _asset(path: Path, root: Path) -> dict:
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _safe_asset_path(root: Path, relative: str) -> Path:
    if (not isinstance(relative, str) or not relative
            or str(PurePosixPath(relative)) != relative
            or PurePosixPath(relative).is_absolute()
            or any(part in (".", "..") for part in PurePosixPath(relative).parts)):
        raise B24FreezeError("invalid relative frozen asset path")
    target = root / relative
    for ancestor in (target, *target.parents):
        if ancestor.is_symlink():
            raise B24FreezeError("symlinked frozen assets are prohibited")
    if target.is_symlink():
        raise B24FreezeError("symlinked frozen assets are prohibited")
    return target


def _check_b23_against_user_report(report: dict) -> None:
    if (report.get("weights_file_sha256") != PINNED_B22_WEIGHTS_SHA256
            or report.get("effective_integer_weights_sha256") != PINNED_B22_INTEGER_SHA256
            or report.get("trained_source_network_sha256") != PINNED_B23_SOURCE_SHA256
            or report.get("compiled_deployment_sha256") != PINNED_B23_DEPLOYMENT_SHA256
            or report.get("capacity_audit_sha256") != PINNED_B23_CAPACITY_SHA256
            or report.get("core_count") != 27
            or report.get("initial_ddr_backing_bytes") != 27 * 524288
            or report.get("validation_frame_count") != 3
            or report.get("official_mnist_test_status") != "SEALED_NOT_ACCESSED"):
        raise B24FreezeError("B2.3 checkpoint/deployment/validation evidence changed")
    frames = report["validation_frames"]
    for frame, witness in zip(frames, PINNED_B23_FRAMES, strict=True):
        ordinal, idx, image, mono, partitioned = witness
        if (frame.get("validation_ordinal") != ordinal
                or frame.get("canonical_train_idx") != idx
                or frame.get("image_sha256") != image
                or frame.get("monolithic_trace_sha256") != mono
                or frame.get("partitioned_trace_sha256") != partitioned
                or frame.get("all_26_ticks_full_neuron_parity") is not True):
            raise B24FreezeError(f"B2.3 frozen validation ordinal {ordinal} trace differs")


def predeclared_official_test_protocol() -> dict:
    """Protocol is predeclared and written WITHOUT EVER OPENING TEST."""
    return {
        "schema": "p06-b2.4-sealed-mnist-official-test-protocol-v1",
        "model_identity": {
            "weights_file_sha256": PINNED_B22_WEIGHTS_SHA256,
            "integer_weights_sha256": PINNED_B22_INTEGER_SHA256,
            "trained_network_sha256": PINNED_B23_SOURCE_SHA256,
            "compiled_deployment_sha256": PINNED_B23_DEPLOYMENT_SHA256,
            "capacity_audit_sha256": PINNED_B23_CAPACITY_SHA256,
        },
        "test_population": "canonical MNIST official 10000 TEST images in original IDX order",
        "test_count": 10000,
        "decision_before_unseal": "ALL_10000_OR_EXPLICIT_NEW_PREFROZEN_PROTOCOL",
        "input": "raw 28x28 uint8, no normalization or augmentation",
        "encoder": "p06-uint8-quota-phase17-v1",
        "timestep_contract": "25 external input epochs, one external-free drain; NEXT hidden/readout",
        "reset": "all state, event banks, pending packets and counters zeroed per image",
        "readout": "26-tick 10 class spike counts, argmax first tie, all zero -> class 0",
        "predict": "one recorded prediction per selected TEST image with errors/attempts reported",
        "metrics": ["top1_count_and_denominator", "per_class_recall",
                    "confusion_matrix", "all_silent_rate", "error_count"],
        "no_model_selection_after_unseal": True,
        "first_unseal_conditions": [
            "B2.4 user-native model/checkpoint/DDR freeze accepted",
            "P07-B scaled A53 ingress/page/routing and board-vs-host numeric parity accepted",
            "software/board/measurement IDs, population and score protocol frozen",
            "TEST archives not used in TRAIN/validation/checkpoint selection",
        ],
        "current_unseal_status": "SEALED_NOT_ACCESSED",
        "board_27_core_run": "NOT_TESTED",
        "not_measured_metrics": ["scaled_fpga_latency", "scaled_energy", "scaled_page_engine_bytes"],
    }


def _validate_freeze_manifest_shape(manifest: dict) -> None:
    if (not isinstance(manifest, dict) or manifest.get("schema") != B24_SCHEMA
            or manifest.get("status") != "HOST_FROZEN_CANDIDATE_PENDING_NATIVE_ACCEPTANCE"
            or manifest.get("checkpoint_frozen") is not True
            or manifest.get("user_native_B2_4_accepted") is not False
            or manifest.get("official_mnist_test_status") != "SEALED_NOT_ACCESSED"
            or manifest.get("physical_kv260_execution") != "NOT_TESTED"
            or manifest.get("B2_3_parity_validation_ordinals") != [0, 1, 2]
            or manifest.get("weights_file_sha256") != PINNED_B22_WEIGHTS_SHA256
            or manifest.get("effective_integer_weights_sha256") != PINNED_B22_INTEGER_SHA256
            or manifest.get("source_network_sha256") != PINNED_B23_SOURCE_SHA256
            or manifest.get("deployment_sha256") != PINNED_B23_DEPLOYMENT_SHA256
            or manifest.get("capacity_audit_sha256") != PINNED_B23_CAPACITY_SHA256
            or manifest.get("core_count") != 27
            or manifest.get("backing_bytes") != 27 * P02_DDR_CONTEXT_STRIDE_BYTES):
        raise B24FreezeError("B2.4 identity/status/resource manifest mismatch")


def verify_frozen_directory(
    directory: str | Path, *, deep: bool = False,
) -> dict:
    """Hash every staged file, verify fixed DDR ABI/IDs, optionally rebuild B12.

    deep=True rehydrates checked trained source and serialized deployment from
    preserved JSON, compares source/packed fingerprints and all per-core DDR
    SHA256s to a freshly exported original P02 backing record. This reads
    freeze files only; NEVER reads MNIST TRAIN/TEST datasets.
    """
    root = Path(directory)
    manifest_file = root / B24_MANIFEST_NAME
    if not manifest_file.is_file() or manifest_file.is_symlink():
        raise B24FreezeError("B2.4 frozen manifest missing or symlinked")
    document = json.loads(manifest_file.read_text(encoding="utf-8"))
    checksum = document.get("manifest_sha256")
    unsigned = {k: v for k, v in document.items() if k != "manifest_sha256"}
    if checksum != canonical_sha(unsigned):
        raise B24FreezeError("B2.4 manifest checksum mismatch")
    _validate_freeze_manifest_shape(document)
    assets = document.get("assets")
    if not isinstance(assets, list) or len(assets) != 33:
        # 2 B2.2 candidate files + source graph + compiled deployment +
        # B2.3 numerical report + predeclared protocol + 27 DDR records = 33.
        raise B24FreezeError("B2.4 requires exactly 33 frozen asset digests")
    paths = set()
    for entry in assets:
        relative = entry.get("path")
        f = _safe_asset_path(root, relative)
        if relative in paths or not f.is_file():
            raise B24FreezeError("duplicated/missing frozen asset")
        paths.add(relative)
        if entry.get("bytes") != f.stat().st_size or entry.get("sha256") != sha256_file(f):
            raise B24FreezeError(f"B2.4 frozen file changed: {relative}")
    expected_paths = {
        "checkpoint/weights_state_dict.pt", "checkpoint/candidate_manifest.json",
        "network_source.json", "packed_deployment.json",
        "b23_validation_parity.json", B24_PROTOCOL_NAME,
    } | {f"{B24_RECORDS_DIR}/core_{i:03d}_initial_p02_512k.bin" for i in range(27)}
    if paths != expected_paths:
        raise B24FreezeError("B2.4 frozen path set incomplete or unexpected")
    actual_paths = {f.relative_to(root).as_posix()
                    for f in root.rglob("*") if f.is_file()}
    if actual_paths != expected_paths | {B24_MANIFEST_NAME}:
        raise B24FreezeError("B2.4 frozen directory contains unexpected/unindexed files")
    by_path = {a["path"]: a for a in assets}
    if by_path["checkpoint/weights_state_dict.pt"]["sha256"] != PINNED_B22_WEIGHTS_SHA256:
        raise B24FreezeError("frozen checkpoint bytes differ from B2.2 user acceptance")
    if (document.get("ddr_context_sha256") != [
            by_path[f"{B24_RECORDS_DIR}/core_{i:03d}_initial_p02_512k.bin"]["sha256"]
            for i in range(27)]):
        raise B24FreezeError("B2.4 DDR SHA manifest does not match core files")
    for core in range(27):
        f = root / B24_RECORDS_DIR / f"core_{core:03d}_initial_p02_512k.bin"
        if f.stat().st_size != P02_DDR_CONTEXT_STRIDE_BYTES:
            raise B24FreezeError("B2.4 DDR record stride mismatch")
        header = parse_ddr_context_header(f.read_bytes(), verify_payload=True)
        if (header.logical_core_id != core
                or header.event0_count != 0 or header.event1_count != 0
                or header.packet_count != 0
                or ddr_context_offset(core) != core * P02_DDR_CONTEXT_STRIDE_BYTES):
            raise B24FreezeError("B2.4 DDR initial state or address index invalid")
    protocol = json.loads((root / B24_PROTOCOL_NAME).read_text(encoding="utf-8"))
    if protocol != predeclared_official_test_protocol():
        raise B24FreezeError("frozen official TEST protocol changed")
    b23 = json.loads((root / "b23_validation_parity.json").read_text(encoding="utf-8"))
    _check_b23_against_user_report(b23)
    manifest_candidate = json.loads((root / "checkpoint/candidate_manifest.json").read_text(encoding="utf-8"))
    if (manifest_candidate.get("weights_file_sha256") != PINNED_B22_WEIGHTS_SHA256
            or manifest_candidate.get("effective_integer_weights_sha256") != PINNED_B22_INTEGER_SHA256):
        raise B24FreezeError("B2.4 copied source candidate manifest identity mismatch")
    if deep:
        network = NetworkSpec.from_json((root / "network_source.json").read_text(encoding="utf-8"))
        compiled = B12Result.from_json((root / "packed_deployment.json").read_text(encoding="utf-8"))
        if (network.fingerprint != PINNED_B23_SOURCE_SHA256
                or compiled.compiled.source_fingerprint != network.fingerprint
                or compiled.compiled.fingerprint != PINNED_B23_DEPLOYMENT_SHA256
                or compiled.capacity_audit["audit_sha256"] != PINNED_B23_CAPACITY_SHA256):
            raise B24FreezeError("B2.4 reloaded source/compiler/packed audit mismatch")
        contexts = export_paged_hardware_image(
            compiled.compiled.logical_deployment.core_configs).backing_contexts
        for context in contexts:
            cid = context.logical_core_id
            regenerated = build_initial_ddr_context_record(context)
            if sha256_file(root / B24_RECORDS_DIR / f"core_{cid:03d}_initial_p02_512k.bin") != hashlib.sha256(regenerated).hexdigest():
                raise B24FreezeError(f"core {cid}: recomputed P02 initial record differs")
    return {
        "schema": B24_SCHEMA,
        "status": document["status"],
        "manifest_sha256": checksum,
        "files_checked": len(assets),
        "cores_checked": 27,
        "total_initial_ddr_bytes": 27 * P02_DDR_CONTEXT_STRIDE_BYTES,
        "deep_regeneration": bool(deep),
        "official_mnist_test_status": "SEALED_NOT_ACCESSED",
        "physical_kv260_execution": "NOT_TESTED",
        "user_native_B2_4_accepted": False,
    }


def freeze_trained_candidate(
    candidate_dir: str | Path, data_dir: str | Path,
    output_dir: str | Path,
) -> dict:
    """Write one new complete freeze, fail closed on previously checked B2.3.

    Transaction: write into private sibling staging directory, fully verify,
    then rename into absent final directory. Existing checkpoint remains
    byte-identical. No option to overwrite frozen output or official TEST.
    """
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"refusing overwrite of B2.4 freeze: {output}")
    if not output.parent.is_dir():
        raise FileNotFoundError(f"freeze parent folder missing: {output.parent}")
    # Run complete real trained dense 26-tick validation on prespecified
    # canonical train-derived validation ordinals BEFORE writing freeze.
    b23 = audit_candidate(candidate_dir, data_dir=data_dir,
                          validation_ordinals=B24_VALIDATION_ORDINALS)
    evidence = b23.report()
    _check_b23_against_user_report(evidence)
    model, candidate = load_candidate(candidate_dir)
    network = model.to_network_spec()
    if network.fingerprint != PINNED_B23_SOURCE_SHA256:
        raise B24FreezeError("trained source network changed during freeze")
    packed = compile_synapse_aware(network, B12Options(readout_population="readout"))
    if (packed.compiled.fingerprint != PINNED_B23_DEPLOYMENT_SHA256
            or packed.capacity_audit["audit_sha256"] != PINNED_B23_CAPACITY_SHA256
            or packed.capacity_audit["backing_bytes"] != 27 * P02_DDR_CONTEXT_STRIDE_BYTES):
        raise B24FreezeError("trained B1.2 packed deployment changed during freeze")
    image = export_paged_hardware_image(packed.compiled.logical_deployment.core_configs)
    if (image.logical_core_ids != tuple(range(27))
            or image.physical_engine_count != 1 or image.resident_context_count != 3):
        raise B24FreezeError("P08 page ownership mapping changed")

    tmp = Path(tempfile.mkdtemp(prefix=".p06_b24_freeze_", dir=output.parent))
    try:
        (tmp / "checkpoint").mkdir()
        (tmp / B24_RECORDS_DIR).mkdir()
        for filename in ("weights_state_dict.pt", "candidate_manifest.json"):
            source = Path(candidate_dir) / filename
            if not source.is_file() or source.is_symlink():
                raise B24FreezeError("checkpoint source file absent or symlinked")
            shutil.copyfile(source, tmp / "checkpoint" / filename)
        if sha256_file(tmp / "checkpoint/weights_state_dict.pt") != PINNED_B22_WEIGHTS_SHA256:
            raise B24FreezeError("B2.4 copied checkpoint bytes changed")

        with (tmp / "network_source.json").open("x", encoding="utf-8") as out:
            out.write(network.to_json())
        with (tmp / "packed_deployment.json").open("x", encoding="utf-8") as out:
            out.write(packed.to_json())
        _dump_json(tmp / "b23_validation_parity.json", evidence)
        _dump_json(tmp / B24_PROTOCOL_NAME, predeclared_official_test_protocol())
        rows = {row["core_id"]: row for row in packed.capacity_audit["cores"]}
        if set(rows) != set(range(27)):
            raise B24FreezeError("B2.4 P02 core provenance does not match expected IDs")
        ddr_shas = []
        for context in image.backing_contexts:
            cid = context.logical_core_id
            record = build_initial_ddr_context_record(context)
            hdr = parse_ddr_context_header(record, verify_payload=True)
            digest = hashlib.sha256(record).hexdigest()
            if (len(record) != P02_DDR_CONTEXT_STRIDE_BYTES
                    or hdr.logical_core_id != cid
                    or digest != rows[cid]["initial_ddr_sha256"]
                    or hdr.payload_sha256 != rows[cid]["initial_ddr_payload_sha256"]):
                raise B24FreezeError(f"core {cid}: P02 SHA or header disagrees with B1.1 audit")
            path = tmp / B24_RECORDS_DIR / f"core_{cid:03d}_initial_p02_512k.bin"
            with path.open("xb") as f:
                f.write(record)
            ddr_shas.append(digest)
        files = sorted(path for path in tmp.rglob("*") if path.is_file())
        assets = [_asset(path, tmp) for path in files]
        if len(assets) != 33:
            raise B24FreezeError("B2.4 output unexpected count of frozen files")
        doc = {
            "schema": B24_SCHEMA,
            "status": "HOST_FROZEN_CANDIDATE_PENDING_NATIVE_ACCEPTANCE",
            "checkpoint_frozen": True,
            "user_native_B2_4_accepted": False,
            "official_mnist_test_status": "SEALED_NOT_ACCESSED",
            "physical_kv260_execution": "NOT_TESTED",
            "source_network_sha256": network.fingerprint,
            "deployment_sha256": packed.compiled.fingerprint,
            "capacity_audit_sha256": packed.capacity_audit["audit_sha256"],
            "weights_file_sha256": candidate["weights_file_sha256"],
            "effective_integer_weights_sha256": candidate["effective_integer_weights_sha256"],
            "architecture": [784, 1000, 10],
            "core_count": 27,
            "backing_bytes": 27 * P02_DDR_CONTEXT_STRIDE_BYTES,
            "ddr_context_sha256": ddr_shas,
            "B2_3_parity_validation_ordinals": list(B24_VALIDATION_ORDINALS),
            "validation_provenance": {
                "best_epoch": candidate["best_epoch"],
                "TRAIN_derived_validation_count": candidate["best_validation"]["count"],
                "TRAIN_derived_validation_accuracy": candidate["best_validation"]["accuracy"],
                "all_silent_validation_count": candidate["best_validation"]["all_silent_count"],
            },
            "assets": assets,
            "immutability_claim": "content-hashed-no-overwrite-snapshot-not-OS-WORM-storage",
            "P07_B_scaled_board_execution": "NOT_TESTED",
            "P08_B_measured_scaled_latency_energy": "NOT_MEASURED",
        }
        doc["manifest_sha256"] = canonical_sha(doc)
        _dump_json(tmp / B24_MANIFEST_NAME, doc)
        result = verify_frozen_directory(tmp, deep=False)
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"freeze destination appeared while staging: {output}")
        tmp.rename(output)
        return result
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)
