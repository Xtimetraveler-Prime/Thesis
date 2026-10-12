#!/usr/bin/env python3
"""Safely recheck EXISTING KV260 P05.2e evidence; no JTAG or board rerun.

Original failure should be preserved as verify.log. This performs a
strict new full-DDR comparison against independently derived packet RAM
route order, *without changing* any original P05G records, generated
logical goldens, physical dumps, A53 mailbox, or terminal log. The
only new output on disk is composite_physical_golden/ and a separate
p05_2_packet_layout_ledger.json, recomputed exclusively from model.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
SRC=str(ROOT/"src")
if SRC in sys.path:sys.path.remove(SRC)
sys.path.insert(0,SRC)


def module(name:str,p:Path):
    spec=importlib.util.spec_from_file_location(name,p)
    assert spec and spec.loader
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


CHECK=module("p05_2e_recheck_verify",ROOT/"scripts/p05_2_composite_verify.py")
LAYOUT=module("p05_2e_recheck_layout",ROOT/"scripts/p05_2_packet_layout.py")


def hashfile(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--directory",required=True,type=Path)
    p=arg.parse_args().directory.resolve()
    selected=[
        p/"p05_a53_result.bin",
        p/"p05_artifacts/p05_header.bin",
        p/"p05_artifacts/p05_payload.bin",
        p/"p05_artifacts/p05_manifest.json",
        p/"p05_2_composite_spec.json",
        p/"p05_2_composite_gate.json",
        p/"composite_golden/manifest.json",
        *[p/"composite_golden"/f"core{core}_expected.bin" for core in range(5)],
        *[p/"final_ddr"/f"core{core}_after.bin" for core in range(5)],
    ]
    try:
        if not all(s.is_file() for s in selected):
            raise ValueError("missing original full hardware/model evidence")
        old={str(s):hashfile(s) for s in selected}
        actual=(p/"final_ddr/core3_after.bin").read_bytes()
        normalized=(p/"composite_golden/core3_expected.bin").read_bytes()
        if len(actual)!=0x80000 or len(normalized)!=0x80000:
            raise ValueError("core3 full image missing or truncated")
        print("P05_2E_OLD_PACKET0="+str({
            "physical":f"0x{actual[0x64000]:02X}",
            "old_sorted_logical_reference":f"0x{normalized[0x64000]:02X}",
        }))
        if actual[0x64000]!=4 or normalized[0x64000]!=0:
            raise ValueError("existing evidence does not exhibit specified core3 0x04/0x00 incident")
        proof=LAYOUT.derive(p)
        now={str(s):hashfile(s) for s in selected}
        if now!=old:
            raise ValueError("original evidence mutated during physical packet layout derivation")
        if not CHECK.verify(p/"p05_a53_result.bin",p):
            print("FAIL: P05.2e new packet-order physical DDR recheck still differs; preserve evidence",
                  file=sys.stderr)
            return 1
        again={str(s):hashfile(s) for s in selected}
        if again!=old:
            raise ValueError("original evidence mutated during verifier run")
        print("PASS: P05.2e original A53/FPGA/mailbox/P05G and FIVE physical DDR records unchanged")
        print("PASS: P05.2e original normalized neural Python oracle unchanged; corrected *only* derived physical packet RAM word order")
        print("P05_2E_RECHECK_EXIT=0")
        return 0
    except (OSError,ValueError,KeyError,AssertionError) as e:
        print("FAIL: P05.2e route-order recheck: "+str(e),file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
