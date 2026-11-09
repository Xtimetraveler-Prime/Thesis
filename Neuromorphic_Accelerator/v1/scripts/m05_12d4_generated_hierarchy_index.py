#!/usr/bin/env python3
"""Index HASH-VERIFIED original Vivado .gen output for internal-node hints.

Generated-file text/token presence NEVER proves the SmartConnect wrapper in
which Vivado issued an unqualified /m00_nodes warning, nor safe AXI bit loss.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from m05_12d3_ip_output_audit import check as check_d3_products
from m05_12d4_readonly_bd_audit import PREFIX, verify_original_and_inventory

def token_hints(warnings: list[dict], paths: list[tuple[str, Path, str]]) -> list[dict]:
    """Use only distinct internal instance/pin identifiers, never mere m05 count."""
    # Read each authenticated generated file once, even when dozens of
    # warnings share the same internal adapter names. No writes to .gen.
    source_text = []
    for rel, file, digest in paths:
        try:
            body = file.read_text(encoding="utf-8", errors="replace")
        except OSError as err:
            raise ValueError(f"generated file cannot be inspected: {rel}: {err}") from err
        source_text.append((rel, digest, body))
    out = []
    for warning in warnings:
        if warning["id"] != "BD 41-2384":
            continue
        src = warning["source_pin"]
        dst = warning["destination_pin"]
        tokens = []
        for path in (src, dst):
            if path:
                bits = path.strip("/").split("/")
                # Generic routing instance names alone are not enough.
                if len(bits) >= 3:
                    tokens.append(bits[-2])
                if bits and bits[-1].lower() not in ("s_sc_payld",):
                    tokens.append(bits[-1])
        tokens = sorted(set(tokens))
        witnesses = []
        if tokens:
            for rel, digest, body in source_text:
                found = [token for token in tokens if token in body]
                if not found:
                    continue
                lower = rel.lower()
                owners = [name for name in ("ctrl_sc", "mem_sc") if name in lower]
                witnesses.append({
                    "generated_file": rel, "sha256": digest, "tokens": found,
                    "file_parent_hint": owners[0] if len(owners) == 1 else "UNMAPPED",
                    "level": "TEXTUAL_TOKEN_OCCURRENCE_ONLY",
                })
        out.append({
            "original_log_line": warning["line"],
            "warning_id": warning["id"],
            "source_pin": src, "destination_pin": dst,
            "source_width": warning["source_width"],
            "destination_width": warning["destination_width"],
            "possibly_narrowed_bits": warning["narrowed_bits"],
            "tokens_searched": tokens,
            "candidate_vendor_files": witnesses,
            "generated_parent_attribution": "NOT_ESTABLISHED",
            "packed_axi_payload_fields": "NOT_ESTABLISHED",
        })
    return out


def build(original: Path, previous_d4: Path) -> dict:
    data = verify_original_and_inventory(original, previous_d4)
    root = original.resolve(strict=True)
    status, products = check_d3_products(
        root, (root / "15_ip_output_width_readback.txt").read_text(),
        (root / "03_vivado.log").read_text())
    if status["generated"] != 382 or status["mem_sc"] != 118:
        raise ValueError("original generated-IP file baseline no longer matches D3")
    gen = root / "13_file_backed_project/m05_d3_output_products.gen"
    files = [(rel, root / rel, digest) for rel, digest in products]
    for rel, file, digest in files:
        if file.is_symlink() or not file.resolve(strict=True).is_relative_to(gen):
            raise ValueError("original generated-IP source outside original .gen")
        if hashlib.sha256(file.read_bytes()).hexdigest() != digest:
            raise ValueError("original generated source hash drift")
    return {
        "scope": "READ_ONLY_HASHED_GENERATED_IP_TEXTUAL_INDEX_NOT_LOG_PARENT_PROOF",
        "original_source_commit": data["source_commit"],
        "original_d3": str(root),
        "generated_file_count": len(files),
        "generated_mem_sc_file_count": status["mem_sc"],
        "generated_ctrl_sc_file_count_hinted_by_path": sum(
            "ctrl_sc" in rel.lower() for rel, _, _ in files),
        "warnings": token_hints(data["warnings"], files),
        "original_d3_manifest_sha256": data["original_file_sha256"]["16_ip_output_sha256_manifest.txt"],
        "hierarchy_attribution": "NOT_PROVEN_BY_TOKEN_MATCHES",
        "axi_field_semantics": "BLOCKED",
        "vivado_simulation": "NOT_RUN",
        "physical_board": "NOT_AUTHORIZED",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-d3", required=True, type=Path)
    p.add_argument("--previous-d4", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    try:
        parent = a.output.parent.resolve(strict=True)
        if (not parent.name.startswith(PREFIX) or a.output.name != "05_generated_hierarchy_hints.json"
                or a.output.exists() or parent == a.original_d3.resolve()):
            raise ValueError("generated hierarchy index must be a NEW D4.1b artifact")
        result = build(a.original_d3, a.previous_d4)
        with a.output.open("x", encoding="utf-8") as fp:
            json.dump(result, fp, sort_keys=True, indent=2)
            fp.write("\n")
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"FAIL: D4.1b original generated-IP hierarchy text indexing: {exc}", file=sys.stderr)
        return 2
    print(f"GENERATED TEXT INDEX COMPLETE: {result['generated_file_count']} original hashed "
          "vendor files inspected; zero implied semantic waivers; parent proof BLOCKED")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
