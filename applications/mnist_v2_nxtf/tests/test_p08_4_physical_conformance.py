from __future__ import annotations

from mnist_v2_nxtf.physical_conformance import (
    EXPECTED_FINAL_EVIDENCE,
    EXPECTED_PREDICTION,
    INGRESS_CORE_ID,
    INGRESS_NAME,
    OUTPUT_CORE_ID,
    OUTPUT_NAME,
    PHYSICAL_SEQUENCE,
    PHYSICAL_SLOT,
    PHYSICAL_TIMESTEP,
    _hex,
    _trace_word,
)


def test_p08_4_3b_fixed_selection_contract() -> None:
    assert PHYSICAL_TIMESTEP == 99
    assert PHYSICAL_SLOT == 2
    assert INGRESS_CORE_ID == 0
    assert OUTPUT_CORE_ID == 4
    assert PHYSICAL_SEQUENCE == (INGRESS_NAME, OUTPUT_NAME, INGRESS_NAME)
    assert EXPECTED_PREDICTION == 7
    assert EXPECTED_FINAL_EVIDENCE == (
        -284,
        -1203,
        104,
        109,
        -2253,
        -599,
        -2659,
        1446,
        -436,
        -63,
    )


def test_p08_4_3b_hex_twos_complement_and_trace_layout() -> None:
    assert _hex(-1, 24) == "0xFFFFFF"
    assert _hex(-2, 64) == "0xFFFFFFFFFFFFFFFE"

    before = 0x0123456789ABCDEF
    synaptic = -3
    after = 0x0FEDCBA987654321
    word = _trace_word(before, synaptic, after, True)
    assert word & ((1 << 64) - 1) == before
    assert (word >> 64) & ((1 << 64) - 1) == (synaptic & ((1 << 64) - 1))
    assert (word >> 128) & ((1 << 64) - 1) == after
    assert (word >> 192) & 1 == 1
