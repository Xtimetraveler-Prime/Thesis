#!/usr/bin/env python3
"""M06 independent 32-bit AXI to 256-bit byte-lane reference (NO RTL).

Models EXPECTED byte address preservation across a FUTURE verified AMD
Data Width Converter: 4-byte HLS words must map into the right one of eight
4-byte lanes in a 32-byte SmartConnect word. This is an abstract scoreboard,
NOT a claim about the converter's emitted AWLEN/AWSIZE, beat packing, timing,
IDs or write-error atomicity. A real AMD converter must be simulated.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib


class AXIWidthError(ValueError):
    pass


def exact_int(value: object, name: str, lo: int, hi: int) -> int:
    if type(value) is not int or not lo <= value <= hi:
        raise AXIWidthError(f"{name} outside [{lo},{hi}] or not a plain integer")
    return value


@dataclass(frozen=True)
class WordWrite:
    data: int
    strobe: int = 0xF


class AXI32CanonicalImage:
    """Single-ID sequential transaction oracle, 64KiB byte-addressed image.

    A pending write must reach successful B response before issuing any new
    read from the other master. This is a conservative required contract,
    NOT a statement that real HLS synthesizes such a fence.
    """
    BYTES = 65536
    WORD_BYTES = 4
    WIDE_BYTES = 32
    MAX_BURST_WORDS = 16

    def __init__(self, *, fill: int = 0xA5):
        exact_int(fill, "fill byte", 0, 255)
        self.memory = bytearray([fill] * self.BYTES)
        self.pending: tuple[int, int, list[WordWrite]] | None = None
        self.poisoned = False
        self.written_word_count = 0

    @staticmethod
    def _validate(address: object, words: object, ident: object,
                  size: object, burst: object) -> tuple[int,int,int]:
        address=exact_int(address,"address",0,2**64-1)
        count=exact_int(words,"AXI beats",1,16)
        ident=exact_int(ident,"AXI ID",0,65535)
        if size != 2 or burst != "INCR":
            raise AXIWidthError("only HLS 32-bit SIZE=2 INCR supported")
        if address % 4:
            raise AXIWidthError("unaligned 32-bit word")
        if address + count * 4 > 65536:
            raise AXIWidthError("out of 64KiB canonical address region")
        if (address // 4096) != ((address + count * 4 - 1) // 4096):
            raise AXIWidthError("AXI burst crosses forbidden 4KiB boundary")
        return address,count,ident

    @staticmethod
    def lane(address: int, data: int, strobe: int) -> dict:
        exact_int(address,"byte address",0,65535)
        if address % 4:
            raise AXIWidthError("unaligned 32-bit word")
        exact_int(data,"WDATA",0,2**32-1)
        exact_int(strobe,"WSTRB",0,15)
        offset = address % 32
        return {
            "wide_base_byte_address": address - offset,
            "lane_index": offset//4,
            "byte_mask_32": strobe << offset,
            "shifted_data_256": data << (offset*8),
        }

    def issue_write(self, address: int, words: list[WordWrite],
                    *, ident: int=0, size: int=2, burst: str="INCR") -> list[dict]:
        if self.poisoned:
            raise AXIWidthError("canonical image quarantined after AXI failure")
        if self.pending is not None:
            raise AXIWidthError("prior write B response outstanding")
        if not isinstance(words,list):
            raise AXIWidthError("ordered WDATA/WSTRB words required")
        address,count,ident=self._validate(address,len(words),ident,size,burst)
        plan=[]
        for i,word in enumerate(words):
            if not isinstance(word,WordWrite):
                raise AXIWidthError("missing 32-bit word or strobe")
            plan.append(self.lane(address+i*4,word.data,word.strobe))
        self.pending=(address,ident,list(words))
        return plan

    def complete_write(self, *, ident: int=0, bresp: int=0) -> None:
        if self.pending is None:
            raise AXIWidthError("unsolicited B response")
        address,expected_id,words=self.pending
        if exact_int(ident,"BID",0,65535) != expected_id:
            self.poisoned=True
            self.pending=None
            raise AXIWidthError("BID mismatch: canonical epoch poisoned")
        code=exact_int(bresp,"BRESP",0,3)
        self.pending=None
        if code != 0:
            self.poisoned=True
            raise AXIWidthError("BRESP failure: canonical image is now UNKNOWN")
        for i,word in enumerate(words):
            for byte in range(4):
                if word.strobe & (1 << byte):
                    self.memory[address+i*4+byte] = (word.data>>(8*byte)) & 0xFF
        self.written_word_count+=len(words)

    def read(self,address:int,*,beats:int=1,ident:int=0,
             size:int=2,burst:str="INCR",rresp:int=0) -> list[int]:
        if self.poisoned:
            raise AXIWidthError("canonical image quarantined after AXI failure")
        if self.pending is not None:
            raise AXIWidthError("read of shared memory before write B response")
        address,count,_=self._validate(address,beats,ident,size,burst)
        if exact_int(rresp,"RRESP",0,3)!=0:
            self.poisoned=True
            raise AXIWidthError("RRESP failure: canonical image must be quarantined")
        return [int.from_bytes(self.memory[address+4*i:address+4*i+4],
                               "little") for i in range(count)]

    def digest(self) -> str:
        if self.poisoned or self.pending is not None:
            raise AXIWidthError("cannot attest incomplete/poisoned canonical image")
        return hashlib.sha256(self.memory).hexdigest()
