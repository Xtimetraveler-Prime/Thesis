"""Deterministic P08.5.3 closure candidate for the NxTF MNIST study.

This module does not introduce new measurements or comparison ratios. It binds
accepted P08.1-P08.5.2 evidence into one machine-readable closure record and
keeps final P08 completion pending until the closure gate is independently
reproduced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .comparison_ledger import build_ledger
from .final_comparison import build_report

CLOSURE_SCHEMA = "p08-nxtf-final-closure-v1"
CLOSURE_STATUS = "P08_5_3_CLOSURE_REVIEW_PENDING"
CLOSURE_JSON = "p08_final_closure.json"
CLOSURE_MARKDOWN = "p08_final_closure.md"

ACCEPTED_LEDGER_FINGERPRINT = "574023d0e55cf3d5098cccd1f23e597ee63deb872ac119be30bf41a5f495511d"
ACCEPTED_REPORT_FINGERPRINT = "d3d47e95f928f0de77d2c1b59c2c16f5becdf5dd443f6600c187d3f56e1e68a0"

ACCEPTED_MERGES = {
    "p08_4": "ac40c8239c6b8134f4e6ec74849e7dfafda8335e",
    "p08_5_1": "d45bb5e06aba83a906d170b69a510dfac7bd30d6",
    "p08_5_2": "688ba77477ca9a7d7bd99d00ef497f1589c07393",
}

EXPECTED_RESULTS = {
    "ann_test_accuracy": 0.9874,
    "snn_test_accuracy": 0.9824,
    "ann_to_snn_accuracy_drop": 0.0050,
    "ann_error_gap_pp_vs_nxtf": 0.52,
    "snn_error_gap_pp_vs_nxtf": 0.97,
    "conversion_loss_gap_pp_vs_nxtf": 0.45,
    "neurons": 4218,
    "trainable_parameters": 7006,
    "expanded_connections": 338880,
    "logical_cores": 5,
    "resident_contexts": 3,
    "physical_engines": 1,
    "primary_timesteps": 100,
    "representative_forward_page_loads": 497,
    "representative_internal_packets": 17910,
    "physical_dispatch_cycles": 3865,
    "physical_dispatch_us": 38.65,
    "fpga_clock_mhz": 100.0,
    "fpga_uram": 47,
    "fpga_wns_ns": 0.734,
}

REQUIRED_NONCLAIMS = (
    "exact unpublished NxTF paper topology or checkpoint reproduction",
    "native NxTF/Loihi compiler or storage-packing equivalence",
    "direct FPGA-versus-Loihi energy comparison",
    "direct native-Loihi-versus-K26 sample-latency comparison",
    "shared-weight efficiency ratio",
    "mapped-core efficiency ratio",
    "representative 3,865-cycle dispatch as full-sample inference latency",
    "full 100-timestep representative inference physically replayed end-to-end over JTAG",
    "transistor-level or physically asynchronous Loihi equivalence",
    "post-test model, conversion, threshold, decoder, or timestep tuning",
)


def _fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_closure() -> dict[str, Any]:
    ledger = build_ledger()
    report = build_report()

    closure: dict[str, Any] = {
        "schema": CLOSURE_SCHEMA,
        "status": CLOSURE_STATUS,
        "p08_complete": False,
        "completion_condition": "independent reproduction of P08.5.3 closure gate",
        "accepted_ledger_fingerprint": ledger["ledger_fingerprint"],
        "accepted_report_fingerprint": report["report_fingerprint"],
        "accepted_identities": dict(ledger["accepted_identities"]),
        "accepted_merge_commits": dict(ACCEPTED_MERGES),
        "subphases": {
            "P08.1": "ACCEPTED",
            "P08.2": "ACCEPTED",
            "P08.3": "ACCEPTED",
            "P08.4": "ACCEPTED",
            "P08.5.1": "ACCEPTED",
            "P08.5.2": "ACCEPTED",
            "P08.5.3": "REVIEW_PENDING",
        },
        "results": dict(EXPECTED_RESULTS),
        "evidence_chain": [
            {
                "stage": "P08.1",
                "claim": "source-bounded four-convolution reconstruction frozen before accepted training",
                "evidence": "Loihi_Digital_Twin/v2/docs/P08_NXTF_RECONSTRUCTION.md",
            },
            {
                "stage": "P08.2",
                "claim": "five logical cores execute over three resident K26 contexts with deterministic host paging",
                "evidence": "Loihi_Digital_Twin/v2/docs/P08_2_ACCEPTANCE.md",
            },
            {
                "stage": "P08.3",
                "claim": "ANN training and source-recovered ANN-to-SNN conversion frozen without official-test tuning",
                "evidence": "Loihi_Digital_Twin/v2/docs/P08_3_ACCEPTANCE.md",
            },
            {
                "stage": "P08.4.1",
                "claim": "frozen official-test ANN/SNN accuracy measured on all 10,000 MNIST test examples",
                "evidence": "Loihi_Digital_Twin/v2/docs/P08_4_1_OFFICIAL_TEST_ACCEPTANCE.md",
            },
            {
                "stage": "P08.4.2",
                "claim": "complete 100-timestep compiled paging semantics agree across unpaged/forward/reverse execution",
                "evidence": "Loihi_Digital_Twin/v2/docs/P08_4_2_ACCEPTANCE.md",
            },
            {
                "stage": "P08.4.3",
                "claim": "representative real-MNIST deep-core page replacement and physical K26 dispatch match accepted architectural evidence exactly",
                "evidence": "Loihi_Digital_Twin/v2/docs/P08_4_ACCEPTANCE.md",
            },
            {
                "stage": "P08.5.1",
                "claim": "comparison classes and non-comparability guardrails frozen before final interpretation",
                "evidence": "Loihi_Digital_Twin/v2/docs/P08_5_1_ACCEPTANCE.md",
            },
            {
                "stage": "P08.5.2",
                "claim": "final thesis-facing comparison generated deterministically from accepted ledger",
                "evidence": "Loihi_Digital_Twin/v2/docs/P08_5_2_ACCEPTANCE.md",
            },
        ],
        "strongest_defensible_claims": [
            "The project implements a source-backed architectural Loihi-like digital twin on the K26 rather than a transistor-level or timing-exact Loihi clone.",
            "The accepted reconstructed MNIST workload has 4,218 neurons, 7,006 trainable parameters, 338,880 expanded convolutional connections, and a 100-timestep primary horizon.",
            "The frozen official MNIST test accuracy is 98.74% for the ANN and 98.24% for the converted SNN, with no post-test model or conversion selection.",
            "The exact five-logical-core deployment is invariant across the tested unpaged, forward-paged, and reverse-paged 100-timestep compiled executions.",
            "The routed K26 host-paged shell retains three full resident contexts and one physical HLS engine while preserving the accepted five-logical-core architectural deployment.",
            "A representative real-MNIST logical-core-4 timestep-99 page replacement and K26 dispatch reproduced all 618 checked state/trace entries and the final ten-class evidence exactly.",
            "The project and NxTF benchmark have similar published/reconstructed graph scale, but the exact paper topology, native compiler mapping, storage representation, energy boundary, and latency boundary are not treated as equivalent.",
        ],
        "explicit_nonclaims": list(REQUIRED_NONCLAIMS),
        "guardrails": {
            "claim_exact_paper_topology": False,
            "claim_native_loihi_storage_equivalence": False,
            "claim_direct_energy_comparison": False,
            "claim_direct_sample_latency_comparison": False,
            "claim_shared_weight_efficiency_ratio": False,
            "claim_mapped_core_efficiency_ratio": False,
            "claim_dispatch_is_full_sample_latency": False,
            "claim_full_physical_jtag_inference_replay": False,
            "claim_physical_async_equivalence": False,
            "claim_post_test_tuning": False,
        },
    }
    validate_closure(closure)
    closure["closure_fingerprint"] = _fingerprint(closure)
    return closure


def validate_closure(closure: dict[str, Any]) -> None:
    if closure.get("schema") != CLOSURE_SCHEMA:
        raise ValueError("P08.5.3 closure schema drifted")
    if closure.get("status") != CLOSURE_STATUS:
        raise ValueError("P08.5.3 closure status drifted")
    if closure.get("p08_complete") is not False:
        raise ValueError("P08 must remain incomplete until independent P08.5.3 reproduction")
    if closure.get("accepted_ledger_fingerprint") != ACCEPTED_LEDGER_FINGERPRINT:
        raise ValueError("P08.5.3 is not bound to accepted P08.5.1 ledger")
    if closure.get("accepted_report_fingerprint") != ACCEPTED_REPORT_FINGERPRINT:
        raise ValueError("P08.5.3 is not bound to accepted P08.5.2 report")
    if closure.get("accepted_merge_commits") != ACCEPTED_MERGES:
        raise ValueError("accepted P08 merge-commit binding drifted")
    if closure.get("results") != EXPECTED_RESULTS:
        raise ValueError("accepted P08 result summary drifted")

    expected_subphases = {
        "P08.1": "ACCEPTED",
        "P08.2": "ACCEPTED",
        "P08.3": "ACCEPTED",
        "P08.4": "ACCEPTED",
        "P08.5.1": "ACCEPTED",
        "P08.5.2": "ACCEPTED",
        "P08.5.3": "REVIEW_PENDING",
    }
    if closure.get("subphases") != expected_subphases:
        raise ValueError("P08 subphase status chain drifted")

    evidence_chain = closure.get("evidence_chain")
    if not isinstance(evidence_chain, list) or len(evidence_chain) != 8:
        raise ValueError("P08 evidence chain must contain eight frozen stages")
    if {item.get("stage") for item in evidence_chain} != {
        "P08.1", "P08.2", "P08.3", "P08.4.1", "P08.4.2", "P08.4.3", "P08.5.1", "P08.5.2"
    }:
        raise ValueError("P08 evidence-chain stages drifted")

    claims = closure.get("strongest_defensible_claims")
    if not isinstance(claims, list) or len(claims) < 7:
        raise ValueError("P08 closure requires bounded thesis claims")

    nonclaims = closure.get("explicit_nonclaims")
    if tuple(nonclaims or ()) != REQUIRED_NONCLAIMS:
        raise ValueError("P08 explicit non-claim set drifted")

    guardrails = closure.get("guardrails")
    if not isinstance(guardrails, dict) or any(value is not False for value in guardrails.values()):
        raise ValueError("all P08.5.3 overclaim guardrails must remain false")


def render_markdown(closure: dict[str, Any]) -> str:
    payload = {key: value for key, value in closure.items() if key != "closure_fingerprint"}
    validate_closure(payload)
    r = closure["results"]
    lines = [
        "# P08 Final Closure Candidate",
        "",
        "This deterministic record binds the accepted P08 evidence chain. P08 remains review-pending until this P08.5.3 gate is independently reproduced.",
        "",
        "## Frozen final result",
        "",
        f"- ANN official-test accuracy: **{100*r['ann_test_accuracy']:.2f}%**",
        f"- SNN official-test accuracy: **{100*r['snn_test_accuracy']:.2f}%** at {r['primary_timesteps']} timesteps",
        f"- ANN→SNN accuracy drop: **{100*r['ann_to_snn_accuracy_drop']:.2f} percentage points**",
        f"- Reconstructed graph: **{r['neurons']:,} neurons, {r['trainable_parameters']:,} trainable parameters, {r['expanded_connections']:,} expanded connections**",
        f"- Deployment: **{r['logical_cores']} logical cores / {r['resident_contexts']} resident contexts / {r['physical_engines']} physical engine**",
        "",
        "## Accepted NxTF comparison gaps",
        "",
        f"- ANN error gap: {r['ann_error_gap_pp_vs_nxtf']:.2f} percentage points",
        f"- SNN error gap: {r['snn_error_gap_pp_vs_nxtf']:.2f} percentage points",
        f"- ANN→SNN conversion-loss gap: {r['conversion_loss_gap_pp_vs_nxtf']:.2f} percentage points",
        "",
        "These gaps are reconstruction-bounded comparisons, not exact-reproduction claims.",
        "",
        "## Evidence chain",
        "",
    ]
    for item in closure["evidence_chain"]:
        lines.append(f"- **{item['stage']}** — {item['claim']} (`{item['evidence']}`)")
    lines.extend(["", "## Strongest defensible thesis claims", ""])
    for claim in closure["strongest_defensible_claims"]:
        lines.append(f"- {claim}")
    lines.extend(["", "## Explicit non-claims", ""])
    for nonclaim in closure["explicit_nonclaims"]:
        lines.append(f"- No claim of {nonclaim}.")
    lines.extend(
        [
            "",
            "## Physical measurement boundary",
            "",
            f"The accepted representative K26 deep-core dispatch is {r['physical_dispatch_cycles']:,} cycles at {r['fpga_clock_mhz']:.0f} MHz ({r['physical_dispatch_us']:.2f} us). This is one dispatch, not full-sample latency. Complete {r['primary_timesteps']}-timestep paging is established in compiled software conformance; representative physical dispatch conformance is established separately on the K26.",
            "",
            f"Accepted P08.5.1 ledger fingerprint: `{closure['accepted_ledger_fingerprint']}`",
            "",
            f"Accepted P08.5.2 report fingerprint: `{closure['accepted_report_fingerprint']}`",
            "",
            f"Closure candidate fingerprint: `{closure['closure_fingerprint']}`",
            "",
            "**P08 completion remains pending independent reproduction of this gate.**",
            "",
        ]
    )
    return "\n".join(lines)


def write_closure(output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    closure = build_closure()
    (output / CLOSURE_JSON).write_text(
        json.dumps(closure, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / CLOSURE_MARKDOWN).write_text(render_markdown(closure), encoding="utf-8")
    return closure


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic P08.5.3 final closure candidate")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    closure = write_closure(args.output_dir)
    r = closure["results"]
    print(
        "PASS: P08.5.3 closure "
        f"ledger={closure['accepted_ledger_fingerprint']} "
        f"report={closure['accepted_report_fingerprint']} "
        f"fingerprint={closure['closure_fingerprint']}"
    )
    print(
        "PASS: P08.5.3 final metrics "
        f"ann={r['ann_test_accuracy']:.6f} snn={r['snn_test_accuracy']:.6f} "
        f"delta={r['ann_to_snn_accuracy_drop']:.6f} timesteps={r['primary_timesteps']}"
    )
    print(
        "PASS: P08.5.3 architecture "
        f"neurons={r['neurons']} params={r['trainable_parameters']} expanded={r['expanded_connections']} "
        f"logical_cores={r['logical_cores']} resident_contexts={r['resident_contexts']} physical_engines={r['physical_engines']}"
    )
    print(
        "PASS: P08.5.3 claim boundary "
        "exact_paper_topology=false native_storage_equivalence=false energy_direct=false "
        "latency_direct=false shared_weight_ratio=false mapped_core_ratio=false "
        "dispatch_is_sample_latency=false full_jtag_replay=false physical_async_equivalence=false post_test_tuning=false"
    )
    print("PASS: P08.5.3 completion state p08_complete=false independent_reproduction_required=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
