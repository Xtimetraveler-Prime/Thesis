"""P07-B.1 native planning gates. No BSP/FPGA, MNIST or freeze access."""
import pytest

from loihi_twin_v2.p07_b1_admission import (
    B1AdmissionError, B1OwnerMap, assert_source_contract, ingress_length,
    page_burst_counts,
)


def test_source_contract_and_address_map():
    assert_source_contract()
    owner = B1OwnerMap()
    assert owner.address(0) == 0x40000000
    assert owner.address(26) == 0x40D00000
    assert owner.address(26) + 0x80000 == 0x40D80000
    assert owner.core_count * owner.record_bytes == 14_155_776
    assert B1OwnerMap(core_count=126).address(125) + 0x80000 <= 0x44000000


@pytest.mark.parametrize("kwargs", [
    {"core_count": 0}, {"core_count": 127},
    {"record_bytes": 0x40000}, {"resident_slots": 4},
    {"physical_engines": 2}, {"backing_base": 0x40000001},
    {"backing_bytes": 0x01000000}, {"core_count": True},
])
def test_fail_closed_resource_admission(kwargs):
    with pytest.raises(B1AdmissionError):
        B1OwnerMap(**kwargs).validate()


@pytest.mark.parametrize("core", [-1, 27, 128, True, 0.0])
def test_fail_closed_core_address(core):
    with pytest.raises(B1AdmissionError):
        B1OwnerMap().address(core)


def test_b13_maximum_frame_and_rejections():
    assert ingress_length(0) == 912
    assert ingress_length(784 * 126) == 593_696
    for n in (-1, 784 * 126 + 1, True, 1.5):
        with pytest.raises(B1AdmissionError):
            ingress_length(n)


def test_p05_burst_accounting_only():
    assert page_burst_counts(1, 1) == (1712, 416)
    assert page_burst_counts(80, 80) == (136_960, 33_280)
    assert sum(page_burst_counts(80, 80)) * 256 == 43_581_440
    for args in [(-1, 0), (0, -1), (True, 0), (0, 0x100000000)]:
        with pytest.raises(B1AdmissionError):
            page_burst_counts(*args)
