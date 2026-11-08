"""M04.5 HOST-ONLY preflight for a provisional W16 K26 first-engine profile.

This is NOT an HLS ingress guard, event-queue implementation, synthesis result,
physical DDR capacity claim, or a modification to accepted M02 revision 1.
It uses an accepted M02 event trace to screen a *known finite workload*.
Runtime/unseen events still require online no-loss admission/backpressure.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from collections.abc import Iterable

from .m02_types import InputCurrent, Network, ReferenceTrace, validate
from .m02_event_reference import evaluate_events

MAX_U32 = (1 << 32) - 1
MAX_U64 = (1 << 64) - 1
MIN_I64 = -(1 << 63)
MAX_I64 = (1 << 63) - 1
FIRST_STATE_BITS = 16
MAX_ARRIVALS_PER_TICK = 4096

class M04AdmissionError(ValueError):
    """A legal M02 workload is not necessarily admitted by the first FPGA profile."""


@dataclass(frozen=True)
class M04AdmissionReport:
    """Computer-only known-input screening; not a synthesized hardware result."""
    status: str
    max_arrivals_per_tick: int
    max_abs_aggregate: int
    ticks: int
    full_m02_trace: ReferenceTrace


def prove_fixed_width_envelope(bits: int, arrivals: int) -> bool:
    """Exact conservative magnitude proof for an optional compiled width.

    Do not use this as a runtime overflow detector or an event-capacity guard.
    The first *synthesis* profile remains W16, even though the proof holds
    for every accepted M02 width (4..32).
    """
    if type(bits) is not int or type(arrivals) is not int:
        return False
    if not 4 <= bits <= 32 or not 0 <= arrivals <= MAX_ARRIVALS_PER_TICK:
        return False
    lo = -(1 << (bits - 1))
    hi = (1 << (bits - 1)) - 1
    worst_negative_i = arrivals * lo
    worst_positive_i = arrivals * hi
    worst_product_negative = lo * MAX_U32
    worst_product_positive = hi * MAX_U32
    # |decayed voltage| <= |previous voltage| because num <= den.
    worst_raw_negative = worst_negative_i + 2 * lo
    worst_raw_positive = worst_positive_i + 2 * hi
    return (MIN_I64 <= worst_negative_i <= worst_positive_i <= MAX_I64
            and MIN_I64 <= worst_product_negative <= worst_product_positive <= MAX_I64
            and MIN_I64 <= worst_raw_negative <= worst_raw_positive <= MAX_I64)


def preflight_known_m04_workload(
    network: Network, inputs: Iterable[InputCurrent], *, ticks: int
) -> M04AdmissionReport:
    """Screen a FINITE, known-input M02 network against initial K26 assumptions.

    A failure rejects the M04 W16 *hardware profile*, NOT the M02 network.
    The accepted reference is never silently modified, rounded or clipped.
    Do not call this from an online hardware hot path.
    """
    events = validate(network, inputs, ticks)
    if network.state_bits != FIRST_STATE_BITS:
        raise M04AdmissionError("first synthesized image requires state_bits=16")
    if network.decay_den > MAX_U32 or network.decay_num > MAX_U32:
        raise M04AdmissionError("decay ratio outside unsigned 32-bit profile")
    if len(network.neurons) > MAX_U32:
        raise M04AdmissionError("logical neuron IDs exceed unsigned 32-bit")
    if ticks - 1 > MAX_U64:
        raise M04AdmissionError("tick exceeds unsigned 64-bit")
    if not prove_fixed_width_envelope(network.state_bits, MAX_ARRIVALS_PER_TICK):
        raise AssertionError("specified i64 bound proof failed")

    counts = [0] * ticks
    currents: dict[tuple[int, int], int] = defaultdict(int)

    def deliver(t: int, neuron: int, signed_current: int) -> None:
        counts[t] += 1
        if counts[t] > MAX_ARRIVALS_PER_TICK:
            raise M04AdmissionError(
                f"tick {t}: more than {MAX_ARRIVALS_PER_TICK} signed deliveries"
            )
        currents[(t, neuron)] += signed_current
        if not MIN_I64 <= currents[(t, neuron)] <= MAX_I64:
            raise M04AdmissionError("signed aggregate outside i64")

    for e in events:
        deliver(e.tick, e.neuron, e.current)

    # This is a source-side *known-input* replay using accepted M02 semantics.
    trace = evaluate_events(network, events, ticks=ticks)
    outgoing = [[] for _ in network.neurons]
    for edge in network.synapses:
        outgoing[edge.pre].append(edge)
    for t, fires in enumerate(trace.spike_rows):
        for pre in fires:
            for edge in outgoing[pre]:
                arriving_tick = t + edge.delay
                if arriving_tick < ticks:
                    deliver(arriving_tick, edge.post, edge.weight)
    return M04AdmissionReport(
        status="HOST_ONLY_KNOWN_INPUT_ADMITTED_NOT_HARDWARE",
        max_arrivals_per_tick=max(counts),
        max_abs_aggregate=max((abs(x) for x in currents.values()), default=0),
        ticks=ticks,
        full_m02_trace=trace,
    )
