"""Host-side transactional trace acceptance for the M05 rolling FPGA candidate.

The HLS kernel streams rows BEFORE its final AXI-Lite return status is known.
A failure at a later tick invalidates EVERY earlier row. This gate receives
rows (which must be drained concurrently with hardware execution) and makes
them visible to the caller ONLY after successful completion and full framing.

This is a CPU-only receiver CONTRACT, not DMA, FPGA AXIS backpressure,
hardware interrupt handling, or a physical board driver. Stage memory is
host memory; a future board adapter needs a real concurrently draining
AXI-stream/DMA interface and final ap_done/status read.

No row in a failed run may be accepted or interpreted as a valid inference.
"""
from __future__ import annotations

from dataclasses import dataclass

MAX_NEURONS = 1024
MAX_TICKS = 64
MAX_PER_TICK = 4096
MAX_TRACE_ROWS = MAX_NEURONS * MAX_TICKS
VALID_HARDWARE_STATUSES = frozenset(range(7))


@dataclass(frozen=True)
class RollingTraceRow:
    tick: int
    neuron_id: int
    voltage: int
    spike: int
    evaluated: int
    delivered_count: int


@dataclass(frozen=True)
class TraceRunResult:
    accepted: bool
    status: int | None
    rows: tuple[RollingTraceRow, ...]
    drained_rows: int
    reason: str | None


class RollingTraceCommitGate:
    """Bounded host staging with fail-closed protocol validation.

    Feed each AXIS transfer into offer_row() as it is drained. The caller
    MUST NOT wait for ap_done to drain AXIS, because a blocked trace port can
    prevent the kernel from reaching ap_done. After ap_done, call complete()
    with the actual AXI-Lite returned status (0..6). A timeout calls abort(),
    but a real hardware recovery/reset sequence is NOT implemented here.

    The gate has no ready/valid or device access; tests use a deterministic
    single-slot FIFO to model consumer stalls separately.
    """

    def __init__(self, neuron_count: int, ticks: int):
        if type(neuron_count) is not int or not 1 <= neuron_count <= MAX_NEURONS:
            raise ValueError("neuron_count outside 1..1024")
        if type(ticks) is not int or not 1 <= ticks <= MAX_TICKS:
            raise ValueError("ticks outside 1..64")
        self.neuron_count = neuron_count
        self.ticks = ticks
        self.expected_rows = neuron_count * ticks
        self._staged: list[RollingTraceRow] = []
        self._count = 0
        self._fault: str | None = None
        self._closed = False
        self._first_delivered_count: int | None = None

    @property
    def received_count(self) -> int:
        return self._count

    @property
    def is_finished(self) -> bool:
        return self._closed

    @property
    def has_uncommitted_rows(self) -> bool:
        return bool(self._staged)

    def offer_row(self, row: RollingTraceRow) -> None:
        """Consume one transfer; record bad data but keep draining.

        Invalid framing poisons the entire run. In particular do NOT raise
        during AXIS draining: stopping the receiving side might deadlock the
        hardware sender. Only a closed/aborted receiver rejects an API call.
        """
        if self._closed:
            raise RuntimeError("trace receiver is closed")
        index = self._count
        self._count += 1
        if self._fault is not None:
            return
        if not isinstance(row, RollingTraceRow):
            self._poison("non-trace row")
            return
        fields = (row.tick, row.neuron_id, row.voltage, row.spike,
                  row.evaluated, row.delivered_count)
        if any(type(v) is not int for v in fields):
            self._poison("non-integer row field")
            return
        if index >= self.expected_rows:
            self._poison("more trace rows than expected")
            return
        tick, neuron_id = divmod(index, self.neuron_count)
        if row.tick != tick or row.neuron_id != neuron_id:
            self._poison("out-of-order/duplicate/missing tick or neuron")
            return
        if not -32768 <= row.voltage <= 32767:
            self._poison("voltage outside signed W16")
            return
        if row.spike not in (0, 1) or row.evaluated not in (0, 1):
            self._poison("spike/evaluated must be binary")
            return
        if row.spike and not row.evaluated:
            self._poison("spike on a skipped neuron")
            return
        if not 0 <= row.delivered_count <= MAX_PER_TICK:
            self._poison("delivery_count exceeds admitted tick capacity")
            return
        if neuron_id == 0:
            self._first_delivered_count = row.delivered_count
        elif row.delivered_count != self._first_delivered_count:
            self._poison("tick delivery_count disagrees across neurons")
            return
        self._staged.append(row)

    def complete(self, final_status: int) -> TraceRunResult:
        """Return accepted rows *only* on zero status and exact framing.

        A nonzero hardware status (including late overflow/invalid-order)
        invalidates the whole staging buffer even if prior ticks were valid.
        """
        if self._closed:
            raise RuntimeError("trace receiver already finalized")
        self._closed = True
        if type(final_status) is not int or final_status not in VALID_HARDWARE_STATUSES:
            self._poison("unknown or non-integer completion status")
        if final_status != 0 and self._fault is None:
            self._poison("hardware returned nonzero status")
        if self._count != self.expected_rows and self._fault is None:
            self._poison("incomplete trace framing")
        if self._fault is not None:
            self._staged.clear()
            return TraceRunResult(False, final_status, (), self._count, self._fault)
        rows = tuple(self._staged)
        self._staged.clear()
        return TraceRunResult(True, 0, rows, self._count, None)

    def abort(self, reason: str = "timeout or transport error") -> TraceRunResult:
        """Discard a run when final status is unavailable; no hardware reset."""
        if self._closed:
            raise RuntimeError("trace receiver already finalized")
        self._closed = True
        self._poison(reason or "aborted without completion status")
        return TraceRunResult(False, None, (), self._count, self._fault)

    def _poison(self, reason: str) -> None:
        if self._fault is None:
            self._fault = reason
            self._staged.clear()
