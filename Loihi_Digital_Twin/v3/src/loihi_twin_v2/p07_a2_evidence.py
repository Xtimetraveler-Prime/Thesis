"""P07-A2 64KiB physical evidence parser and first-divergence comparator.

Physical data must originate from XSDB after one autonomous P07-A2 A53
application run. This module never substitutes a host simulator for FPGA data.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct

from .p06_input_contract import classify_spike_counts, image_event_schedule
from .p07_a2_batch import RESULT_BYTES, parse_batch

MAGIC = b"P07R"
SUCCESS = 0x600D600D
BASE = 256
STRIDE = 128
TRACE_BASE = 4096
TRACE_SIZE = 26 * 42 * 32


@dataclass(frozen=True)
class PhysicalFrame:
    counts: tuple[int, ...]
    predicted: int
    silent: bool
    output_spikes: tuple[tuple[int, ...], ...]
    external_event_count: int
    routed_packets: int
    dropped_packets: int
    timesteps: int
    dispatches: int
    barriers: int
    input_crc32: int


@dataclass(frozen=True)
class PhysicalBatch:
    frames: tuple[PhysicalFrame, ...]
    trace_frame: int
    trace: bytes


def _u32(data: bytes, pos: int) -> int:
    return struct.unpack_from("<I", data, pos)[0]


def parse_evidence(mailbox: bytes, batch_header: bytes, payload: bytes) -> PhysicalBatch:
    records = parse_batch(batch_header, payload)
    if len(mailbox) != RESULT_BYTES:
        raise ValueError("full P07-A2 physical mailbox must be exactly 64 KiB")
    if mailbox[:4] != MAGIC or _u32(mailbox, 4) != 1:
        raise ValueError("unknown physical evidence mailbox magic/version")
    status = _u32(mailbox, 8)
    if status != SUCCESS:
        raise ValueError(
            f"KV260 A53 did not report terminal success: status=0x{status:08X}, "
            f"error={_u32(mailbox,12)}, first_failure_frame={_u32(mailbox,16)}, "
            f"detail={_u32(mailbox,20)}"
        )
    count = _u32(mailbox, 24)
    selected = _u32(mailbox, 28)
    if count != len(records) or not 0 <= selected < count or _u32(mailbox, 32) != count:
        raise ValueError("A53 frame count/completion or trace selection mismatch")
    frames = []
    for n, record in enumerate(records):
        base = BASE + n * STRIDE
        if _u32(mailbox, base) != SUCCESS:
            raise ValueError(f"frame {n}: missing complete A53 execution status")
        counts = tuple(_u32(mailbox, base + (8+cls)*4) for cls in range(10))
        predicted = _u32(mailbox, base + 4)
        silent = _u32(mailbox, base + 8)
        if silent not in (0, 1) or predicted >= 10:
            raise ValueError(f"frame {n}: invalid class/silent marker")
        mask = int.from_bytes(mailbox[base+23*4:base+32*4], "little")
        spikes = tuple(tuple((mask >> (tick*10+cls)) & 1
                             for cls in range(10)) for tick in range(26))
        if any(sum(row[cls] for row in spikes) != counts[cls] for cls in range(10)):
            raise ValueError(f"frame {n}: per-tick output flags disagree with class counts")
        if predicted != classify_spike_counts(counts) or bool(silent) != (sum(counts) == 0):
            raise ValueError(f"frame {n}: invalid readout/tie/silence result")
        if (_u32(mailbox, base+3*4), _u32(mailbox, base+4*4),
                _u32(mailbox, base+5*4)) != (26, 26, 26):
            raise ValueError(f"frame {n}: incomplete 26-barrier execution")
        if _u32(mailbox, base+19*4) != 0:
            raise ValueError(f"frame {n}: P03 runtime fault reported")
        if _u32(mailbox, base+21*4) != _u32(record, 56):
            raise ValueError(f"frame {n}: ingress source CRC identity mismatch")
        schedule = image_event_schedule(record[-784:])
        if _u32(mailbox, base+18*4) != sum(len(t) for t in schedule):
            raise ValueError(f"frame {n}: A53 external input count differs from frozen encoder")
        frames.append(PhysicalFrame(
            counts, predicted, bool(silent), spikes,
            _u32(mailbox, base+18*4),
            _u32(mailbox, base+6*4),
            _u32(mailbox, base+7*4),
            _u32(mailbox, base+3*4),
            _u32(mailbox, base+4*4),
            _u32(mailbox, base+5*4),
            _u32(mailbox, base+21*4),
        ))
    return PhysicalBatch(tuple(frames), selected, mailbox[TRACE_BASE:TRACE_BASE+TRACE_SIZE])


def _state_word(state) -> int:
    return ((state.current & 0xFFFFFF) |
            ((state.voltage & 0xFFFFFF) << 24) |
            ((state.refractory_remaining & 0xFFFF) << 48))


def compare_to_packed_oracle(batch: PhysicalBatch, header: bytes, payload: bytes,
                             packed_image, mapping: tuple[int, ...]) -> None:
    """First-mismatch per-tick comparisons vs frozen independent P03 oracle.

    Does not score images against any labels or official MNIST TEST data.
    """
    from .p06_packed_replay import replay_p03_image

    records = parse_batch(header, payload)
    for n, (frame, raw) in enumerate(zip(batch.frames, records)):
        expected = replay_p03_image(packed_image, mapping, raw[-784:])
        for tick, ideal_tick in enumerate(expected.ticks):
            expected_spikes = tuple(int(32+cls in ideal_tick.fired_compartments)
                                    for cls in range(10))
            if frame.output_spikes[tick] != expected_spikes:
                raise AssertionError(
                    f"first FPGA mismatch frame={n} tick={tick} output spikes "
                    f"hardware={frame.output_spikes[tick]} oracle={expected_spikes}"
                )
        if frame.counts != expected.output_counts or frame.predicted != expected.predicted_class:
            raise AssertionError(
                f"first FPGA mismatch frame={n} complete readout: "
                f"hardware={frame.counts}/{frame.predicted} "
                f"oracle={expected.output_counts}/{expected.predicted_class}"
            )
        expect_routed = sum(len(step.next_packet_axons) for step in expected.ticks[:-1])
        if (frame.routed_packets != expect_routed or
            frame.dropped_packets != len(expected.dropped_boundary_packets)):
            raise AssertionError(f"first FPGA mismatch frame={n}: NEXT routing/drain count")

        if n != batch.trace_frame:
            continue
        for tick, expected_tick in enumerate(expected.ticks):
            for comp in range(42):
                pos = (tick*42+comp)*32
                actual = batch.trace[pos:pos+32]
                if len(actual) != 32:
                    raise ValueError("physical trace truncated")
                before = int.from_bytes(actual[0:8], "little")
                accumulator = int.from_bytes(actual[8:16], "little")
                after = int.from_bytes(actual[16:24], "little")
                spike_and_reserved = int.from_bytes(actual[24:32], "little")
                ideal_before = (packed_image.state_words[comp] if tick == 0 else
                                _state_word(expected.ticks[tick-1].states_after[comp]))
                ideal_after = _state_word(expected_tick.states_after[comp])
                ideal_acc = expected_tick.accumulators[comp] & ((1 << 64) - 1)
                ideal_spike = int(comp in expected_tick.fired_compartments)
                for key, value, wanted in (
                    ("before_state", before, ideal_before),
                    ("synaptic_accumulator", accumulator, ideal_acc),
                    ("after_state", after, ideal_after),
                    ("spike_bit_and_reserved", spike_and_reserved, ideal_spike),
                ):
                    if value != wanted:
                        raise AssertionError(
                            f"first FPGA mismatch frame={n} tick={tick} "
                            f"core=0 compartment={comp} field={key} "
                            f"hardware=0x{value:X} oracle=0x{wanted:X}"
                        )
