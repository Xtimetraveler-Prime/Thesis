"""P07-B.3b native event-slice/3-slot LRU integration; synthetic only.

27 logical IDs, actual original P03 event offsets in C; no physical FPGA,
trained B2.4 tensors, official TEST, or protected frozen asset access.
"""
from __future__ import annotations

import ctypes as C
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import zlib

import pytest
from loihi_twin_v2.p06_input_contract import pixel_spikes
from test_p07_b2b_transaction import (IngressBinding, IngressView, PacketBinding,
                                     Route, Event, Tx, Receipt, U8, U16, U32)

ROOT = Path(__file__).resolve().parents[1]
N = 27
SLOTS = 3
DEPTH = 4096
CAP = 8192
N_ROUTES = 784 * 26
SHA_COMPILED = hashlib.sha256(b"P07-B3b synthetic only compiled-route fixture").digest()
SHA_AUDIT = hashlib.sha256(b"P07-B3b synthetic only audit fixture").digest()


class Op(C.Structure):
    _fields_ = [
        ("kind", U32), ("tick", U32), ("ordinal", U32), ("core", U32),
        ("slot", U32), ("victim", U32), ("current_bank", U32),
        ("next_bank", U32), ("bytes", U32), ("backing_address", C.c_uint64),
    ]


class Traffic(C.Structure):
    _fields_ = [("dispatches", U32), ("barriers", U32), ("page_ins", U32),
                ("hits", U32), ("cold_ins", U32), ("replacements", U32),
                ("dirty_evictions", U32), ("runtime_outs", U32),
                ("final_outs", U32), ("read_bytes", C.c_uint64),
                ("write_bytes", C.c_uint64)]


class Pager(C.Structure):
    _fields_ = [
        ("order_mode", U32), ("tick", U32), ("cursor", U32), ("ordinal", U32),
        ("flush_slot", U32), ("resident", C.c_int32 * SLOTS),
        ("dirty", U32 * SLOTS), ("last_use", U32 * SLOTS),
        ("stage", U32), ("selected_slot", U32), ("selected_core", U32),
        ("selected_victim", U32), ("has_pending", U32), ("failed", U32),
        ("first_failure_kind", U32), ("pending", Op), ("counters", Traffic),
    ]


class Bank(C.Structure):
    _fields_ = [("count", U32 * 2), ("axon", (U32 * DEPTH) * 2)]


class Owner(C.Structure):
    _fields_ = [
        ("pager", C.POINTER(Pager)), ("transport", C.POINTER(Tx)),
        ("backing", C.POINTER(Bank)), ("slot", C.POINTER(Bank)),
        ("scratch", C.POINTER(Event)), ("scratch_capacity", C.c_size_t),
        ("tick_started", U32), ("poisoned", U32), ("first_error", U32),
        ("current_expected", U32 * N), ("current_consumed", U32 * N),
        ("dispatched", U8 * N), ("resident_next", U32),
        ("nonresident_next", U32), ("barriers_committed", U32),
    ]


def sha_array(digest):
    return (U8 * 32).from_buffer_copy(digest)


def frame(magic, words, payload):
    assert len(words) == 14 and words[10] == 0 and words[11] == 0
    fields = list(words)
    fields[10] = zlib.crc32(payload)
    hdr = bytearray(struct.pack("<8s14I", magic, *fields)
                    + SHA_COMPILED + SHA_AUDIT)
    struct.pack_into("<I", hdr, 52, zlib.crc32(hdr))
    return bytes(hdr) + payload


def ingress(pixels):
    routes = b"".join(struct.pack("<HHH", pix, core, pix)
                      for pix in range(784) for core in range(26))
    payload = routes + pixels
    raw = frame(b"P06B13I1", (1, 128, len(payload), N_ROUTES, N, 784,
                            25, 26, 6, 784, 0, 0, 0, 0), payload)
    assert len(raw) == 123216
    return raw, routes


def emitted_frame(tick, hidden_sources):
    packets = b"".join(struct.pack("<IHHHH", tick + 1, core, 0, 26, core + 100)
                       for core in hidden_sources)
    return frame(b"P06B13R1", (1, 128, len(packets), len(hidden_sources), N,
                              12, 4096, 0, 0, 0, 0, 0, 0), packets)


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    cc = shutil.which("cc") or shutil.which("gcc")
    assert cc, "A host C11 compiler is required"
    binary = tmp_path_factory.mktemp("p07_b3b") / "libp07_b3b.so"
    subprocess.run([
        cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-shared", "-fPIC",
        "-I", str(ROOT / "software/p07/include"),
        "-I", str(ROOT / "software/p03/include"),
        "-I", str(ROOT / "software/p05/include"),
        *map(str, (
            ROOT / "software/p07/p07_b2_ingress.c",
            ROOT / "software/p07/p07_b2_packet.c",
            ROOT / "software/p07/p07_b2b_transaction.c",
            ROOT / "software/p07/p07_b3_pager.c",
            ROOT / "software/p07/p07_b3b_event_owner.c",
        )), "-o", str(binary)
    ], check=True, capture_output=True, text=True)
    lib = C.CDLL(str(binary))
    lib.p07_b2_decode_ingress.argtypes = [
        C.c_void_p, C.c_size_t, C.POINTER(IngressBinding), C.POINTER(IngressView)]
    lib.p07_b2_decode_ingress.restype = C.c_int
    lib.p07_b2b_transaction_init.argtypes = [
        C.POINTER(Tx), C.POINTER(IngressView), C.POINTER(PacketBinding),
        C.POINTER(Event), C.c_size_t]
    lib.p07_b2b_transaction_init.restype = C.c_int
    lib.p07_b3_init.argtypes = [C.POINTER(Pager), U32]
    lib.p07_b3_init.restype = C.c_int
    lib.p07_b3b_init.argtypes = [
        C.POINTER(Owner), C.POINTER(Pager), C.POINTER(Tx),
        C.POINTER(Bank), C.POINTER(Bank), C.POINTER(Event), C.c_size_t]
    lib.p07_b3b_init.restype = C.c_int
    lib.p07_b3b_next.argtypes = [C.POINTER(Owner), C.POINTER(Op)]
    lib.p07_b3b_next.restype = C.c_int
    lib.p07_b3b_ack.argtypes = [C.POINTER(Owner), C.POINTER(Op), C.c_int]
    lib.p07_b3b_ack.restype = C.c_int
    lib.p07_b3b_barrier.argtypes = [
        C.POINTER(Owner), C.POINTER(Op), C.c_void_p, C.c_size_t,
        C.c_void_p, C.c_size_t, C.POINTER(Receipt)]
    lib.p07_b3b_barrier.restype = C.c_int
    lib.p07_b3b_read.argtypes = [
        C.POINTER(Owner), U32, U32, U32, C.POINTER(U32)]
    lib.p07_b3b_read.restype = C.c_int
    return lib


def contents(obj):
    return C.string_at(C.addressof(obj), C.sizeof(obj))


class Fixture:
    def __init__(self, lib, pixels, mode):
        raw, routes = ingress(pixels)
        self.lib, self.pixels = lib, pixels
        self.raw = C.create_string_buffer(raw)
        self.routes_bytes = C.create_string_buffer(routes)
        self.ingress_binding = IngressBinding(
            N, N_ROUTES, C.addressof(self.routes_bytes), len(routes),
            sha_array(SHA_COMPILED), sha_array(SHA_AUDIT))
        self.ingress_view = IngressView()
        assert lib.p07_b2_decode_ingress(
            self.raw, len(raw), C.byref(self.ingress_binding),
            C.byref(self.ingress_view)) == 0
        self.routes = (Route * 26)(*(
            Route(core, 0, 26, core + 100) for core in range(26)))
        self.compartments = (U16 * N)(*[1] * N)
        self.packet_binding = PacketBinding(
            N, 26, self.routes, self.compartments,
            sha_array(SHA_COMPILED), sha_array(SHA_AUDIT))
        self.pending = (Event * CAP)()
        self.tx = Tx()
        assert lib.p07_b2b_transaction_init(
            C.byref(self.tx), C.byref(self.ingress_view),
            C.byref(self.packet_binding), self.pending, CAP) == 0
        self.pager = Pager()
        assert lib.p07_b3_init(C.byref(self.pager), mode) == 0
        self.backing = (Bank * N)()
        self.slots = (Bank * SLOTS)()
        self.scratch = (Event * CAP)()
        self.owner = Owner()
        assert lib.p07_b3b_init(
            C.byref(self.owner), C.byref(self.pager), C.byref(self.tx),
            self.backing, self.slots, self.scratch, CAP) == 0
        self.receipt = Receipt()

    def next(self):
        op = Op()
        state = self.lib.p07_b3b_next(C.byref(self.owner), C.byref(op))
        return state, op

    def ack(self, op, ok=True):
        return self.lib.p07_b3b_ack(C.byref(self.owner), C.byref(op), int(ok))

    def barrier(self, op, frame_bytes, emitters):
        wire = C.create_string_buffer(frame_bytes)
        packed = (U16 * (max(1, len(emitters)) * 2))()
        for i, core in enumerate(emitters):
            packed[2 * i], packed[2 * i + 1] = core, 0
        return self.lib.p07_b3b_barrier(
            C.byref(self.owner), C.byref(op), wire, len(frame_bytes),
            packed if emitters else None, len(emitters), C.byref(self.receipt))

    def bank_words(self, core, which):
        out = []
        for i in range(4096):
            value = U32()
            status = self.lib.p07_b3b_read(
                C.byref(self.owner), core, which, i, C.byref(value))
            if status != 0:
                break
            out.append(value.value)
        return tuple(out)

    def owners(self):
        return tuple(int(x) for x in self.pager.resident)


@pytest.mark.parametrize("mode", [0, 1])
@pytest.mark.parametrize("pixels", [
    bytes([255] * 784),
    bytes(784),
    bytes((i * 31 + 43) % 256 for i in range(784)),
])
def test_27_core_26_epoch_paging_current_next_and_bank_ownership(native, mode, pixels):
    """Independent epoch arithmetic and materialized core/slot storage checks."""
    f = Fixture(native, pixels, mode)
    emitted_total = external_total = 0
    for tick in range(26):
        fired = tuple(pixel_spikes(pixels, tick))
        previous = tuple(range(100, 126)) if tick > 0 and pixel_spikes(pixels, tick - 1) else ()
        should_emit = tuple(range(26)) if tick < 25 and fired else ()
        expected = {
            core: (fired if core < 26 else previous) for core in range(N)
        }
        seen = set()
        while True:
            status, op = f.next()
            assert status == 0, f"premature end/fault tick {tick}: {status}"
            assert op.tick == tick
            if op.kind == 3:
                core = int(op.core)
                assert core not in seen
                seen.add(core)
                actual = f.bank_words(core, tick % 2)
                assert actual == expected[core], (
                    f"epoch={tick} core={core} expected={expected[core][:8]} actual={actual[:8]}")
                assert f.ack(op) == 0
                assert f.owner.current_consumed[core] == len(actual)
            elif op.kind == 4:
                assert len(seen) == N
                frame_bytes = emitted_frame(tick, should_emit)
                assert f.barrier(op, frame_bytes, should_emit) == 0
                expected_ext = len(fired) * 26
                assert f.receipt.external_events == expected_ext
                assert f.receipt.routed_current == len(previous)
                assert f.receipt.routed_next == len(should_emit)
                assert tuple(f.receipt.current_by_core[:N]) == tuple(
                    len(expected[core]) for core in range(N))
                assert tuple(f.receipt.next_by_core[:N]) == (
                    (0,) * 26 + (len(should_emit),))
                assert f.tx.tick == tick + 1
                assert f.pager.counters.barriers == tick + 1
                assert f.owner.barriers_committed == tick + 1
                assert f.bank_words(26, 1 - tick % 2) == tuple(
                    core + 100 for core in should_emit)
                is_resident = 26 in f.owners()
                if should_emit:
                    assert is_resident == (mode == 0 or tick % 2 == 0)
                assert f.owner.resident_next + f.owner.nonresident_next == (
                    emitted_total + len(should_emit))
                emitted_total += len(should_emit)
                external_total += expected_ext
                break
            else:
                assert op.kind in (1, 2)
                assert f.ack(op) == 0
    assert f.owner.tick_started == 0
    assert f.tx.tick == 26
    while True:
        code, op = f.next()
        if code == 1:
            break
        assert code == 0 and op.kind == 5
        assert f.ack(op) == 0
    assert f.pager.counters.dispatches == 702
    assert f.pager.counters.barriers == 26
    assert f.pager.counters.final_outs == 3
    assert all(v == 0 for v in f.pager.dirty)
    assert (f.pager.counters.page_ins, f.pager.counters.hits) == (
        (702, 0) if mode == 0 else (627, 75))
    assert external_total == sum(len(pixel_spikes(pixels, t)) for t in range(25)) * 26
    assert emitted_total == sum(
        26 for t in range(25) if pixel_spikes(pixels, t))
    # Resident/nonresident classification at the *emission barrier*, not
    # at earlier page-ins or a future destination dispatch.
    assert f.owner.resident_next + f.owner.nonresident_next == emitted_total
    if mode == 0:
        assert f.owner.nonresident_next == 0
    else:
        expected_nonresident = sum(
            26 for t in range(25) if (t & 1) and pixel_spikes(pixels, t))
        assert f.owner.nonresident_next == expected_nonresident


def _go_to_barrier(f):
    while True:
        rc, op = f.next()
        assert rc == 0
        if op.kind == 4:
            return op
        assert f.ack(op) == 0


def test_bad_packet_poison_at_barrier_leaves_banks_transport_and_receipt_intact(native):
    f = Fixture(native, bytes([255] * 784), 0)
    op = _go_to_barrier(f)
    packet = bytearray(emitted_frame(0, tuple(range(26))))
    packet[-1] ^= 1
    before = (contents(f.backing), contents(f.slots), contents(f.tx),
              contents(f.pending), contents(f.receipt))
    assert f.barrier(op, bytes(packet), tuple(range(26))) == -2
    assert before == (contents(f.backing), contents(f.slots), contents(f.tx),
                      contents(f.pending), contents(f.receipt))
    assert f.pager.counters.barriers == 0
    assert f.pager.tick == 0 and f.pager.failed and f.owner.poisoned
    assert f.next()[0] == -2


def test_mismatched_resident_next_bank_rejected_before_next_dispatch(native):
    f = Fixture(native, bytes([255] * 784), 0)
    barrier = _go_to_barrier(f)
    assert f.barrier(barrier, emitted_frame(0, tuple(range(26))),
                     tuple(range(26))) == 0
    # Core26 is resident on slot 2 at the end of ascending tick0.
    idx = f.owners().index(26)
    assert f.slots[idx].count[1] == 26
    f.slots[idx].axon[1][0] ^= 1  # simulated silent URAM corruption
    bank_snapshot = (contents(f.backing), contents(f.slots), contents(f.tx))
    assert f.next()[0] == -2
    assert (contents(f.backing), contents(f.slots), contents(f.tx)) == bank_snapshot
    assert f.owner.poisoned and f.pager.failed


def test_dirty_eviction_failure_preserves_resident_next_event_bank(native):
    f = Fixture(native, bytes([255] * 784), 0)
    barrier = _go_to_barrier(f)
    assert f.barrier(barrier, emitted_frame(0, tuple(range(26))),
                     tuple(range(26))) == 0
    resident_slot = f.owners().index(26)
    assert f.slots[resident_slot].count[1] == 26
    assert f.backing[26].count[1] == 0  # dirty resident, backing deliberately stale
    while True:
        status, op = f.next()
        assert status == 0
        if op.kind == 1 and op.core == 26:
            assert op.slot == resident_slot
            assert f.ack(op, ok=False) == -2
            break
        assert f.ack(op) == 0
    assert f.slots[resident_slot].count[1] == 26
    assert f.backing[26].count[1] == 0
    assert f.owner.poisoned and f.pager.failed
    assert f.next()[0] == -2
