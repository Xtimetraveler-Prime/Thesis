"""M08.3.2 host-paged ownership/control reference, adapted from Loihi P08.

The Loihi v2 P08.4.3a/b routed K26 shell and real VIO physical page
replacement prove a host-vs-compute access protocol, NOT Linux DMA buffer
ownership. This state machine models that proven sequencing for later M08
signed16 integration. It is a Python-only logical backing model: no PS,
AXI, DMA, DDR, VIO, MMIO or neural execution is performed by this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256


class HostOwnershipError(RuntimeError):
    """Host/computation exclusivity or unsafe page lifecycle."""


class HostProtocolPoisoned(HostOwnershipError):
    """An uncertain physical state requires an independently fresh session."""


@dataclass
class _Slot:
    logical_id: int | None = None
    image: bytes | None = None
    pending_load: bool = False
    dirty: bool = False


class HostPagedOwnership:
    """One host lease, N logical backing pages, K resident slots.

    All images are SOFTWARE copies; verify_load() models a host-observed
    readback digest, not a hardware attestation. Page save must precede
    dirty eviction; a loaded image is non-dispatchable until readback proof.
    """

    def __init__(self, images: dict[int, bytes], *, slots: int, owner: str):
        if not isinstance(owner, str) or not owner:
            raise ValueError("nonempty SOFTWARE owner token required")
        if type(slots) is not int or slots < 1:
            raise ValueError("positive resident slot count required")
        if type(images) is not dict or not images or len(images) <= slots:
            raise ValueError("logical backing must exceed resident capacity")
        if any(type(k) is not int or k < 0 or type(v) is not bytes or
               not v for k,v in images.items()):
            raise ValueError("logical keys and nonempty byte images required")
        lengths={len(v) for v in images.values()}
        if len(lengths)!=1:
            raise ValueError("fixed uniform hardware image size required")
        self._backing=dict(images)
        self._slots=[_Slot() for _ in range(slots)]
        self._owner=owner
        self._host=False
        self._compute_slot: int | None=None
        self._poisoned=False
        self._complete:set[int]=set()
        self._epoch=0
        self._page_hits=0
        self._page_loads=0
        self._page_saves=0

    def _guard(self,owner:str)->None:
        if owner!=self._owner:
            raise PermissionError("software host lease mismatch")
        if self._poisoned:
            raise HostProtocolPoisoned("uncertain output or page state: new session required")

    def _index(self,slot:int)->_Slot:
        if type(slot) is not int or not 0<=slot<len(self._slots):
            raise ValueError("resident slot out of range")
        return self._slots[slot]

    def begin_host(self,*,owner:str)->None:
        self._guard(owner)
        if self._host or self._compute_slot is not None:
            raise HostOwnershipError("host access may start only when compute idle")
        self._host=True

    def end_host(self,*,owner:str)->None:
        self._guard(owner)
        if not self._host or any(s.pending_load for s in self._slots):
            raise HostOwnershipError("host access cannot end with unverified load")
        self._host=False

    def save_dirty(self,slot:int,*,observed_image:bytes,owner:str)->None:
        self._guard(owner)
        s=self._index(slot)
        if not self._host or s.pending_load or not s.dirty or s.logical_id is None:
            raise HostOwnershipError("dirty save needs host lease and committed resident state")
        if type(observed_image) is not bytes or observed_image!=s.image:
            self._poisoned=True
            raise HostProtocolPoisoned("dirty page readback mismatch; canonical backing untouched")
        self._backing[s.logical_id]=observed_image
        s.dirty=False
        self._page_saves+=1

    def stage_load(self,logical_id:int,slot:int,*,owner:str)->bytes:
        self._guard(owner)
        s=self._index(slot)
        if not self._host or self._compute_slot is not None:
            raise HostOwnershipError("load needs exclusive host lease")
        if logical_id not in self._backing:
            raise ValueError("unknown logical backing context")
        if s.dirty or s.pending_load:
            raise HostOwnershipError("must commit dirty page and verify prior load before replacement")
        if any(i!=slot and other.logical_id==logical_id
               for i,other in enumerate(self._slots)):
            raise HostOwnershipError("same logical backing context resident in another slot")
        if s.logical_id==logical_id and s.image is not None:
            self._page_hits+=1
            return s.image
        s.logical_id=logical_id
        s.image=self._backing[logical_id]
        s.pending_load=True
        self._page_loads+=1
        return s.image

    def verify_load(self,slot:int,*,observed_sha256:str,owner:str)->None:
        self._guard(owner)
        s=self._index(slot)
        if not self._host or not s.pending_load or s.image is None:
            raise HostOwnershipError("no pending host load to verify")
        if type(observed_sha256) is not str or observed_sha256!=sha256(s.image).hexdigest():
            self._poisoned=True
            raise HostProtocolPoisoned("load readback digest mismatch: dispatch embargoed")
        s.pending_load=False

    def dispatch(self,logical_id:int,slot:int,*,owner:str)->bytes:
        self._guard(owner)
        s=self._index(slot)
        if self._host or self._compute_slot is not None or s.pending_load:
            raise HostOwnershipError("compute and host access mutually exclusive")
        if s.logical_id!=logical_id or s.image is None or logical_id in self._complete:
            raise HostOwnershipError("logical ID not verified resident or already completed")
        self._compute_slot=slot
        # Return the emulated input state only; no real engine is called.
        return s.image

    def finish_compute(self,slot:int,*,observed_image:bytes,
                       packets_drained:bool,owner:str)->None:
        self._guard(owner)
        s=self._index(slot)
        if self._host or self._compute_slot!=slot or s.logical_id is None:
            raise HostOwnershipError("no matching compute dispatch")
        if packets_drained is not True or type(observed_image) is not bytes or s.image is None or len(observed_image)!=len(s.image):
            self._poisoned=True
            raise HostProtocolPoisoned("undrained packets or incomplete state: no commit")
        s.image=observed_image
        s.dirty=True
        self._complete.add(s.logical_id)
        self._compute_slot=None

    def advance_epoch(self,*,owner:str)->None:
        self._guard(owner)
        if self._host or self._compute_slot is not None:
            raise HostOwnershipError("cannot advance barrier while host/compute active")
        if self._complete!=set(self._backing):
            raise HostOwnershipError("all logical contexts must complete before barrier")
        if any(s.dirty or s.pending_load for s in self._slots):
            raise HostOwnershipError("all dirty state must be saved before global barrier")
        self._complete.clear()
        self._epoch+=1

    def mark_uncertain(self,*,owner:str)->None:
        self._guard(owner)
        self._poisoned=True

    def backing_snapshot(self,logical_id:int,*,owner:str)->bytes:
        self._guard(owner)
        if logical_id not in self._backing:
            raise ValueError("unknown logical backing context")
        return self._backing[logical_id]

    def receipt(self,*,owner:str)->dict:
        self._guard(owner)
        return {
            "scope":"M08_SOFTWARE_HOST_PAGED_OWNERSHIP_REFERENCE_NOT_KERNEL_DMA",
            "host_busy":self._host,
            "compute_busy":self._compute_slot is not None,
            "epoch":self._epoch,
            "logical_contexts":len(self._backing),
            "resident_slots":len(self._slots),
            "slot_to_logical":[s.logical_id for s in self._slots],
            "completed_logical_ids":sorted(self._complete),
            "page_hits":self._page_hits,
            "page_loads":self._page_loads,
            "page_saves":self._page_saves,
            "physical_dma_ready":False,
            "kernel_dma_buffer_owned":False,
            "hardware_dispatch_measured":False,
        }
