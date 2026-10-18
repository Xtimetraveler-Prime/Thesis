"""Physical trace parser/first-difference tests with clearly synthetic mailbox.

These are NOT physical FPGA results and do not touch official MNIST TEST.
"""
from __future__ import annotations

from types import SimpleNamespace
import struct

import pytest

from loihi_twin_v2.p06_integer_oracle import LIFState
from loihi_twin_v2.p07_a1_ingress import encode_ingress
from loihi_twin_v2.p07_a2_batch import COMPILED_FINGERPRINT, DDR_SHA256, create_batch
from loihi_twin_v2.p07_a2_evidence import compare_to_packed_oracle, parse_evidence

MAP = tuple((i * 73+17) % 4096 for i in range(784))
STATUS = 0x600D600D


def _fixtures():
    records = tuple(encode_ingress(bytes(784), MAP, ddr_sha256=DDR_SHA256,
                                   deployment_fingerprint=COMPILED_FINGERPRINT)
                    for _ in range(2))
    header, payload = create_batch(records, trace_frame=0)
    box = bytearray(65536)
    box[:4] = b"P07R"
    struct.pack_into("<I", box, 4, 1)
    struct.pack_into("<I", box, 8, STATUS)
    struct.pack_into("<I", box, 24, 2)
    struct.pack_into("<I", box, 28, 0)
    struct.pack_into("<I", box, 32, 2)
    for index, raw in enumerate(records):
        offset = 256 + 128 * index
        for word, value in (
            (0, STATUS), (1, 0), (2, 1),
            (3, 26), (4, 26), (5, 26),
            (21, struct.unpack_from("<I", raw, 56)[0]),
        ):
            struct.pack_into("<I", box, offset+word*4, value)
    return header, payload, box


def _toy_oracle():
    states = tuple(LIFState() for _ in range(42))
    tick = SimpleNamespace(
        output_counts=(0,)*10,
        accumulators=(0,)*42,
        states_after=states, fired_compartments=(),
        next_packet_axons=(),
    )
    inference = SimpleNamespace(
        ticks=(tick,)*26, output_counts=(0,)*10,
        predicted_class=0, dropped_boundary_packets=(),
    )
    image = SimpleNamespace(state_words=(0,)*42)
    return image, inference


def test_valid_synthetic_mailbox_and_first_difference(monkeypatch):
    head, data, box = _fixtures()
    decoded = parse_evidence(bytes(box), head, data)
    assert len(decoded.frames) == 2
    assert decoded.trace_frame == 0
    assert len(decoded.trace) == 34944
    assert all(frame.silent and frame.predicted == 0 for frame in decoded.frames)
    image, oracle = _toy_oracle()
    monkeypatch.setattr("loihi_twin_v2.p06_packed_replay.replay_p03_image",
                        lambda *_args: oracle)
    compare_to_packed_oracle(decoded, head, data, image, MAP)
    bad = bytearray(box)
    # Inject a *trace* synaptic accumulator discrepancy after six exact ticks.
    offset = 4096 + (7*42 + 12)*32 + 8
    bad[offset] = 1
    with pytest.raises(AssertionError, match="frame=0 tick=7 core=0 compartment=12 field=synaptic_accumulator"):
        compare_to_packed_oracle(parse_evidence(bytes(bad), head, data),
                                 head, data, image, MAP)


@pytest.mark.parametrize("field,value", [
    (0, 0), (1, 99), (2, 0), (3, 25), (4, 25),
    (5, 25), (19, 1), (21, 0),
])
def test_fail_closed_frame_mutations(field, value):
    head, data, box = _fixtures()
    struct.pack_into("<I", box, 256 + field*4, value)
    with pytest.raises(ValueError):
        parse_evidence(bytes(box), head, data)


def test_bad_mailbox_status_version_and_size_rejected():
    head, data, box = _fixtures()
    for corrupted in (bytes(box)[:-1], bytes([box[0]^1])+bytes(box)[1:]):
        with pytest.raises(ValueError):
            parse_evidence(corrupted, head, data)
    for offset, value in ((4,2), (8,0xDEAD0001), (24,17), (28,3), (32,0)):
        bad = bytearray(box)
        struct.pack_into("<I", bad, offset, value)
        with pytest.raises(ValueError):
            parse_evidence(bytes(bad), head, data)


def test_readout_flags_counts_and_ties_must_agree():
    head, data, box = _fixtures()
    bad = bytearray(box)
    struct.pack_into("<I", bad, 256 + 8*4, 1)
    with pytest.raises(ValueError, match="per-tick"):
        parse_evidence(bytes(bad), head, data)
    bad = bytearray(box)
    struct.pack_into("<I", bad, 256 + 2*4, 0)
    with pytest.raises(ValueError, match="readout"):
        parse_evidence(bytes(bad), head, data)
