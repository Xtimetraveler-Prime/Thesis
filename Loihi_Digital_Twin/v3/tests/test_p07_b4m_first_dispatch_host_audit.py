"""Offline original B2.4 first-dispatch source/HLS semantics audit tests."""
from __future__ import annotations
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4m_first_dispatch_host_audit as audit


def original_shape_image(*,bad_axon=False,bad_delay=False,bad_target=False):
    axon=0 if bad_axon else (
        1<<41 # valid
        | 0 # synapse start
        | 1<<15 # one synapse word
    )
    synapse=(
        (3 if bad_target else 0)
        | ((1 if bad_delay else 0)<<34)
    )
    return SimpleNamespace(
        compartment_count=1,
        synapse_words=(synapse,),
        axon_words=(SimpleNamespace(index=14,word=axon),),
        config_words=(0,),state_words=(0,),
        route_descriptor_words=(),
        route_words=(),
    )


def test_original_first_core_event_and_hls_axon_semantics():
    # Pixel0=255 always emits on tick0 and every tick0..24.
    pixel=bytes([255])+bytes(783)
    rows=[(0,0,14),(1,1,15)]
    result=audit.check_first_core_hls_path(pixel,rows,original_shape_image())
    assert result["HLS_first_dispatch_expected_current_events"]==1
    assert result["HLS_first_dispatch_input_semantics_ok"] is True
    assert result["HLS_first_dispatch_input_semantics_violations"]==[]
    assert result["independent_real_PL_dispatch_protocol_or_trace_verified"] is False
    assert result["first_12_expected_current_events"][0]["target_axon"]==14


@pytest.mark.parametrize("flag,expected",[
    ("bad_axon","invalid/reserved axon"),
    ("bad_delay","unsupported HLS delay"),
    ("bad_target","synapse target out of bounds"),
])
def test_hw_fatal_source_conditions_caught_before_any_board_access(flag,expected):
    pixel=bytes([255])+bytes(783)
    result=audit.check_first_core_hls_path(
        pixel,[(0,0,14)],original_shape_image(**{flag:True})
    )
    assert not result["HLS_first_dispatch_input_semantics_ok"]
    assert expected in result["HLS_first_dispatch_input_semantics_violations"][0]


def test_original_event_phase_and_terminal_tick():
    assert audit.fired(255,0,0)
    assert audit.fired(255,0,24)
    assert not audit.fired(255,0,25)
    assert not audit.fired(0,0,0)
    with pytest.raises(audit.DispatchAuditNoGo):
        audit.fired(255,0,26)


def test_diagnostic_never_claims_real_physical_PL_acceptance():
    source=(ROOT/"scripts/p07_b4m_first_dispatch_host_audit.py").read_text()
    assert "official_MNIST_TEST" in source
    assert '"physical_board_access":False' in source
    assert '"original_failure_root_cause_independently_proven":False' in source
    assert "xsdb" not in source
    assert "import p07_b4m_physical_full_inference" not in source
