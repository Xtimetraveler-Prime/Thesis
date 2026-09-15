from __future__ import annotations

from pathlib import Path

from mnist_app.fpga_corpus import (
    MnistFpgaCorpusCase,
    PROFILE_ID,
    PROFILE_ORDER,
    validate_corpus_case_contract,
    write_corpus_systemverilog_include,
)
from mnist_app.fpga_corpus_reporting import format_suite_summary
from mnist_app.fpga_corpus_shell import (
    patch_capture_controller_text,
    patch_capture_tcl_text,
)


def _cases() -> tuple[MnistFpgaCorpusCase, ...]:
    result: list[MnistFpgaCorpusCase] = []
    reasons = ("both-correct", "profile-divergent", "both-wrong")
    for source_ordinal in range(30):
        for profile in PROFILE_ORDER:
            profile_id = PROFILE_ID[profile]
            base = 100 + profile_id * 100
            result.append(
                MnistFpgaCorpusCase(
                    case_id=len(result),
                    name=f"case-{source_ordinal}-{profile}",
                    profile=profile,
                    profile_id=profile_id,
                    source_ordinal=source_ordinal,
                    selection_reason=reasons[source_ordinal % 3],
                    mnist_test_index=1000 + source_ordinal,
                    label=source_ordinal // 3,
                    expected_prediction=source_ordinal // 3,
                    config_words=(base + 1, base + 2),
                    initial_state_words=(0, 0),
                    format_words=(base + 3,),
                    synapse_words=(base + 4, base + 5),
                    weight_rows=(0, 1, 2),
                    route_rows=(0, 0, 0),
                    route_targets=(),
                    external_schedule=((0,), (1, 1), (), (0,)),
                    golden_trace=object(),
                )
            )
    return tuple(result)


def test_corpus_contract_requires_sixty_paired_cases() -> None:
    cases = _cases()
    validate_corpus_case_contract(cases)
    assert len(cases) == 60
    assert {case.profile for case in cases[:2]} == set(PROFILE_ORDER)


def test_corpus_include_stores_static_images_once_and_banks_events(tmp_path: Path) -> None:
    cases = _cases()
    output = write_corpus_systemverilog_include(cases, tmp_path / "corpus.svh")
    text = output.read_text(encoding="utf-8")

    assert "localparam int M12_3_CASE_COUNT = 60;" in text
    assert "localparam int M12_3_PROFILE_COUNT = 2;" in text
    assert "M12_3_CASE_PROFILE_IDS" in text
    assert "M12_3_EXTERNAL_ROWS" in text

    assert "localparam logic [31:0] M12_3_SYNAPSE_WORDS [0:3]" in text
    assert "localparam logic [15:0] M12_3_EXTERNAL_EVENTS_PROFILE0 [0:119]" in text
    assert "localparam logic [15:0] M12_3_EXTERNAL_EVENTS_PROFILE1 [0:119]" in text
    assert "M12_3_EXTERNAL_EVENTS [" not in text


def test_capture_controller_patch_uses_profile_static_image_and_event_bank() -> None:
    text = """    capture_state_t state;
    logic [7:0] active_case_id;
active_case_id * M12_3_MAX_NEURONS
active_case_id * M12_3_MAX_NEURONS
active_case_id * M12_3_MAX_FORMATS
active_case_id * M12_3_MAX_SYNAPSES
active_case_id * (M12_3_MAX_AXONS + 1)
active_case_id * (M12_3_MAX_NEURONS + 1)
active_case_id * M12_3_MAX_ROUTES
M12_3_EXTERNAL_EVENTS[
                    (((active_case_id * M12_3_MAX_TICKS) + tick_index) *
                     M12_3_MAX_EXTERNAL_EVENTS) + load_index
                ]
"""
    patched = patch_capture_controller_text(text)
    assert "static_image_id = M12_3_CASE_PROFILE_IDS[active_case_id]" in patched
    assert "static_image_id * M12_3_MAX_SYNAPSES" in patched
    assert "M12_3_EXTERNAL_ROWS[" in patched
    assert "M12_3_EXTERNAL_EVENTS_PROFILE0[" in patched
    assert "M12_3_EXTERNAL_EVENTS_PROFILE1[" in patched
    assert "active_case_id * M12_3_MAX_SYNAPSES" not in patched


def test_capture_tcl_patch_accepts_case_ids_above_fifteen() -> None:
    text = """    if {$selected_case != $case_id} {
        error \"M12.3 case-select witness mismatch: requested=$case_id observed=$selected_case phase=$phase\"
    }
"""
    patched = patch_capture_tcl_text(text)
    assert "set expected_case_nibble [expr {$case_id & 0xF}]" in patched
    assert "$selected_case != $expected_case_nibble" in patched


def test_suite_summary_uses_validator_schema_keys() -> None:
    suite = {
        "passed": True,
        "case_count": 60,
        "tick_count": 960,
        "mismatch_count": 0,
        "profiles": {
            "cropped-dense": {"cases": 30, "passed": 30, "mismatches": 0},
            "native-sparse": {"cases": 30, "passed": 30, "mismatches": 0},
        },
        "selection_reasons": {
            "both-correct": {"cases": 20, "passed": 20, "mismatches": 0},
            "profile-divergent": {"cases": 20, "passed": 20, "mismatches": 0},
            "both-wrong": {"cases": 20, "passed": 20, "mismatches": 0},
        },
    }
    lines = format_suite_summary(suite)
    assert lines[0] == "MNIST-08 suite: passed=True cases=60 ticks=960 mismatches=0"
    assert "profile=cropped-dense cases=30 passed=30 mismatches=0" in lines
    assert "reason=both-wrong cases=20 passed=20 mismatches=0" in lines
