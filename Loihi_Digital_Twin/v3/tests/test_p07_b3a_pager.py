"""P07-B.3a host C pager vs original accepted P06-B1.5 LRU model.

Synthetic schedule geometry only; never reads frozen B2 weights or MNIST TEST.
No KV260 programming, DDR reads/writes, or physical page-traffic claims.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest

from loihi_twin_v2.p06_b15_paging import (
    ResidentLRU, P05_FULL_PAGE_IN_BYTES, P05_MUTABLE_PAGE_OUT_BYTES,
)

ROOT = Path(__file__).resolve().parents[1]
NO = 2**32 - 1
BASE = 0x40000000
RECORD = 0x80000


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    cc = shutil.which("cc") or shutil.which("gcc")
    assert cc, "host C11 compiler required"
    binary = tmp_path_factory.mktemp("p07_b3a") / "p07_b3a_native"
    subprocess.run([
        cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-I", str(ROOT / "software/p07/include"),
        "-I", str(ROOT / "software/p03/include"),
        "-I", str(ROOT / "software/p05/include"),
        str(ROOT / "software/p07/p07_b3_pager.c"),
        str(ROOT / "tests/native/p07_b3a_pager_harness.c"),
        "-o", str(binary),
    ], check=True, capture_output=True, text=True)
    return binary


def _oracle(alternating: bool):
    paging = ResidentLRU(tuple(range(27)))
    actions = []
    ordinal = 0
    for tick in range(26):
        order = range(26, -1, -1) if alternating and tick % 2 else range(27)
        for core in order:
            event = paging.visit(tick, ordinal, core)
            slot, victim = event.slot, event.evicted_core
            if event.mutable_page_out_bytes:
                assert victim is not None
                actions.append((tick, ordinal, 1, victim, slot, NO,
                                tick % 2, 1 - tick % 2,
                                BASE + victim * RECORD,
                                P05_MUTABLE_PAGE_OUT_BYTES))
            if event.page_in_bytes:
                actions.append((tick, ordinal, 2, core, slot,
                                NO if victim is None else victim,
                                tick % 2, 1 - tick % 2,
                                BASE + core * RECORD,
                                P05_FULL_PAGE_IN_BYTES))
            actions.append((tick, ordinal, 3, core, slot, NO,
                            tick % 2, 1 - tick % 2, 0, 0))
            ordinal += 1
        actions.append((tick, ordinal, 4, NO, NO, NO,
                        tick % 2, 1 - tick % 2, 0, 0))
    flushes = paging.flush()
    for flushed in flushes:
        actions.append((26, 702, 5, flushed.core_id, flushed.slot, NO,
                        0, 1, BASE + flushed.core_id * RECORD,
                        P05_MUTABLE_PAGE_OUT_BYTES))
    return actions, paging.report()


@pytest.mark.parametrize("mode", (0, 1))
def test_all_702_actions_and_26_barriers_match_original_B15_LRU(native, mode):
    run = subprocess.run([str(native), str(mode)], capture_output=True,
                         text=True, check=True, timeout=90)
    rows = run.stdout.splitlines()
    actions, oracle = _oracle(alternating=bool(mode))
    got = []
    for line in rows[:-1]:
        pieces = line.split()
        assert pieces[0] == "OP" and len(pieces) == 11
        got.append(tuple(int(field) for field in pieces[1:]))
    assert got == actions  # exact action/core/slot/victim/epoch/DDR address/size/order
    summary = rows[-1].split()
    assert summary[0] == "SUMMARY" and len(summary) == 12
    (dispatches, barriers, ins, hits, cold, replacements, runtime_outs,
     final_outs, dirty, read_bytes, write_bytes) = map(int, summary[1:])
    assert dispatches == 702 and barriers == 26
    assert ins == oracle["full_page_ins"]
    assert hits == oracle["page_hits"]
    assert cold == oracle["initial_empty_slot_page_ins"]
    assert replacements == oracle["replacement_page_ins"]
    assert runtime_outs == dirty == oracle["dirty_evictions"]
    assert final_outs == oracle["final_mutable_page_outs"] == 3
    assert read_bytes == oracle["estimated_page_engine_read_bytes"]
    assert write_bytes == oracle["estimated_page_engine_write_bytes"]
    assert (ins, hits, runtime_outs, final_outs) == (
        (702, 0, 699, 3) if mode == 0 else (627, 75, 624, 3)
    )
    assert read_bytes + write_bytes == (
        382_427_136 if mode == 0 else 341_569_536
    )  # modeled traffic, never a board measurement


def test_ack_failure_is_sticky_before_dirty_overwrite_or_barrier(native):
    run = subprocess.run([str(native), "2"], capture_output=True,
                         text=True, check=True, timeout=90)
    assert run.stdout.strip() == "P07_B3A_NATIVE_FAULT_GATE_PASS=1"
