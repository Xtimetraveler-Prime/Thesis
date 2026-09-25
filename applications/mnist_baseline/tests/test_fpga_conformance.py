from __future__ import annotations

from types import SimpleNamespace

from mnist_app.fpga_conformance import (
    MnistFpgaConformanceCase,
    compare_physical_to_golden,
    select_single_image_anchor,
    write_systemverilog_include,
)


def test_select_single_image_anchor_uses_first_both_correct():
    corpus = {
        "schema": "neuromorphic-twin-mnist-fpga-corpus-v1",
        "entries": [
            {
                "selection_reason": "profile-divergent",
                "cropped_dense_correct": False,
                "native_sparse_correct": True,
            },
            {
                "selection_reason": "both-correct",
                "cropped_dense_correct": True,
                "native_sparse_correct": True,
                "mnist_test_index": 3,
                "label": 0,
            },
            {
                "selection_reason": "both-correct",
                "cropped_dense_correct": True,
                "native_sparse_correct": True,
                "mnist_test_index": 9,
                "label": 1,
            },
        ],
    }
    anchor = select_single_image_anchor(corpus)
    assert anchor["mnist_test_index"] == 3


def _dummy_case(case_id: int, profile: str, axons: int, synapses: int):
    return MnistFpgaConformanceCase(
        case_id=case_id,
        name=f"case-{case_id}",
        profile=profile,
        mnist_test_index=3,
        label=0,
        expected_prediction=0,
        config_words=(1, 2),
        initial_state_words=(0, 0),
        format_words=(0x0100, 0x0200),
        synapse_words=tuple(range(synapses)),
        weight_rows=tuple(range(axons + 1)),
        route_rows=(0, 0, 0),
        route_targets=(),
        external_schedule=((0,), (1,)),
        golden_trace=None,
    )


def test_systemverilog_include_uses_m12_3_input_contract(tmp_path):
    cases = (
        _dummy_case(0, "cropped-dense", 2, 2),
        _dummy_case(1, "native-sparse", 3, 3),
    )
    output = write_systemverilog_include(cases, tmp_path / "cases.svh")
    text = output.read_text(encoding="utf-8")
    assert "M12_3_CASE_COUNT = 2" in text
    assert "M12_3_MAX_AXONS = 3" in text
    assert "M12_3_MAX_SYNAPSES = 3" in text
    assert "M12_3_ROUTE_COUNTS" in text
    assert "M12_3_EXTERNAL_EVENTS" in text
    assert "M12_3_EXPECTED" not in text
    assert "RECURRENT_SCHEDULE" not in text


def _snapshot(*, after=(0,), spikes=(False,)):
    return SimpleNamespace(
        committed_tick=1,
        neuron_count=len(after),
        external_input_axons=(0,),
        recurrent_input_axons=(),
        synaptic_input=(64,) * len(after),
        state_before_words=(0,) * len(after),
        state_after_words=after,
        spikes=spikes,
        routed_output_axons=(),
    )


def _tick(snapshot):
    return SimpleNamespace(
        snapshot=snapshot,
        core_fault=False,
        core_fault_code=0,
        external_event_count=len(snapshot.external_input_axons),
        consumed_recurrent_count=0,
        routed_recurrent_count=0,
    )


def test_compare_physical_to_golden_accepts_exact_trace():
    golden = SimpleNamespace(
        scenario_id="mnist07",
        ticks=(_tick(_snapshot(after=(1, 2), spikes=(True, False))),),
    )
    physical = SimpleNamespace(
        scenario_id="mnist07",
        transport="jtag-vio",
        ticks=(_tick(_snapshot(after=(1, 2), spikes=(True, False))),),
    )
    report = compare_physical_to_golden(golden, physical, expected_prediction=0)
    assert report["passed"] is True
    assert report["mismatch_count"] == 0
    assert report["physical_prediction"] == 0


def test_compare_physical_to_golden_reports_state_mismatch():
    golden = SimpleNamespace(
        scenario_id="mnist07",
        ticks=(_tick(_snapshot(after=(1, 2), spikes=(True, False))),),
    )
    physical = SimpleNamespace(
        scenario_id="mnist07",
        transport="jtag-vio",
        ticks=(_tick(_snapshot(after=(1, 3), spikes=(True, False))),),
    )
    report = compare_physical_to_golden(golden, physical, expected_prediction=0)
    assert report["passed"] is False
    assert any(
        mismatch["field"] == "snapshot.state_after_words"
        for mismatch in report["mismatches"]
    )
