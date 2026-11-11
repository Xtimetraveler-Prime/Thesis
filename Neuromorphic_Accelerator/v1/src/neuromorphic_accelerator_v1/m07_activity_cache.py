"""M07.4 causal activity-history residency experiment; SOURCE ONLY.

M06 already evaluates eligible neurons in ascending logical-ID order each
tick, so their block IDs are already ordered. Sorting the very same eligible
list by block would not reduce page switches. The single M07.4 candidate
instead changes only *which full block is evicted*, using a bounded history
of completed neuron evaluations (not future events, oracle voltages or spikes).

The cache reuses the unmodified M06 BlockCache for every read/write, version
check, owner check, dirty writeback, quarantine, and transfer acknowledgment.
Before a capacity miss, it makes the selected victim oldest in M06's ordered
resident map; the accepted M06 transfer machinery then does all work. This
reorders cache metadata only, NEVER neural processing, delivery or output.

History page IDs use additional logical metadata *not charged* to the
on-chip STATE DATA budget; estimates are NOT HDL area/cycles/AXI/DMA.
"""
from __future__ import annotations

from collections import Counter, deque

from .m06_block_residency import BlockCache, ResidencyError, checked_int

DEFAULT_HISTORY_DEPTH = 16


class ActivityHistoryCache(BlockCache):
    """Bounded last-N completed neuron EVALUATIONS, LFU/LRU victim priority.

    On a miss, evict the resident page with the fewest appearances in the
    previous N completed read/write neuron pairs; break ties by M06 LRU age.
    Strict read→write pairing is required to define completed evaluations.
    This policy uses no future stimulus, neural oracle or tick lookahead.
    """

    def __init__(self, store, *, owner: str,
                 history_depth: int = DEFAULT_HISTORY_DEPTH):
        super().__init__(store, owner=owner)
        self.history_depth = checked_int("history_depth", history_depth, 1, 4096)
        self._recent_completed: deque[int] = deque(maxlen=history_depth)
        self._pending_neuron: int | None = None
        self.policy_victim_decisions = 0
        self.policy_victim_candidates_examined = 0
        self.policy_non_lru_choices = 0
        self.peak_history_page_ids = 0

    @property
    def pending_neuron(self) -> int | None:
        return self._pending_neuron

    @property
    def completed_page_history(self) -> tuple[int, ...]:
        return tuple(self._recent_completed)

    def _protocol_error(self, message: str) -> None:
        self._poisoned = True
        raise ResidencyError(message)

    def read(self, neuron: int) -> bytes:
        if self._pending_neuron is not None:
            self._protocol_error("activity policy requires paired write before next read")
        # Geometry validation and owner state must precede any metadata change.
        self._ensure_safe()
        page = self.geometry.page_for_neuron(neuron)
        if page not in self._resident and len(self._resident) >= self.geometry.slots:
            # Only prior *completed* neuron evaluations influence the victim.
            scores = Counter(self._recent_completed)
            current_order = tuple(self._resident)
            victim = min(current_order, key=lambda p: scores[p])
            self.policy_victim_decisions += 1
            self.policy_victim_candidates_examined += len(current_order)
            if victim != current_order[0]:
                self.policy_non_lru_choices += 1
                self._resident.move_to_end(victim, last=False)
        # If the backing transfer faults, M06 poisons and the attempted
        # victim remains resident and dirty if its writeback did not commit.
        data = super().read(neuron)
        self._pending_neuron = neuron
        return data

    def write(self, neuron: int, data: bytes) -> None:
        if self._pending_neuron is None or neuron != self._pending_neuron:
            self._protocol_error("activity policy write must match prior read")
        super().write(neuron, data)
        # Only a successful M06 write, not a speculative read, adds history.
        self._recent_completed.append(self.geometry.page_for_neuron(neuron))
        self.peak_history_page_ids = max(
            self.peak_history_page_ids, len(self._recent_completed))
        self._pending_neuron = None

    def flush(self) -> None:
        if self._pending_neuron is not None:
            self._protocol_error("activity policy cannot flush incomplete evaluation")
        super().flush()

    def policy_observer(self) -> dict:
        """Host bookkeeping, not claimed FPGA area, cycles, or service time."""
        return {
            "policy": "activity_history",
            "history_depth_evaluations": self.history_depth,
            "peak_history_page_ids": self.peak_history_page_ids,
            "logical_page_id_bits": max(1, (self.geometry.pages-1).bit_length()),
            "victim_decisions": self.policy_victim_decisions,
            "victim_candidates_examined": self.policy_victim_candidates_examined,
            "non_lru_victim_choices": self.policy_non_lru_choices,
            "history_ids_within_declared_state_budget": False,
            "hardware_area_lut_ff_bram": None,
            "service_cycles": None,
            "b_before_ar_cycles": None,
            "queue_stalls": None,
            "physical_ddr_bytes": None,
        }
