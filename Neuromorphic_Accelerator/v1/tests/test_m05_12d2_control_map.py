"""M05.12d.2b candidate control-map admission tests (NO MMIO/PS/DDR).

All base addresses in these tests are FICTIONAL fixtures and must never be
copied to a board or interpreted as real Vivado assign_bd_address evidence.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m05_12d2_control_map import (
    BANKS, MIN_APERTURE_BYTES, MAX_PS_PHYS_EXCLUSIVE,
    AddressAdmissionError, ProposedAperture, ProposedControlMap,
    propose_control_map,
)


def imaginary_apertures():
    # SYNTHETIC ONLY: never claim these bases are real board addresses.
    return tuple(
        ProposedAperture(bank, 0xB0000000 + index * 0x1000)
        for index, bank in enumerate(BANKS)
    )


class M0512D2ControlMapTests(unittest.TestCase):
    def test_six_independent_apertures_and_directional_dma_offsets(self):
        c = propose_control_map(imaginary_apertures())
        self.assertEqual(len(c.apertures), 6)
        self.assertEqual(c.proposed_register_address("dma_neurons", "LENGTH"),
                         0xB0000028)
        self.assertEqual(c.proposed_register_address("dma_trace", "LENGTH"),
                         0xB0003058)
        self.assertEqual(c.proposed_register_address("shell", "VERSION"),
                         0xB0004038)
        self.assertNotEqual(c.aperture("shell").base, c.aperture("hls").base)

    def test_no_missing_extra_duplicate_or_wrong_bank_admission(self):
        good = imaginary_apertures()
        for bad in (
            good[:-1],
            good + (ProposedAperture("dma_neurons", 0xB0006000),),
            good[:1] + (good[0],) + good[2:],
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(AddressAdmissionError):
                    ProposedControlMap(bad)
        with self.assertRaises(AddressAdmissionError):
            ProposedAperture("dma_unknown", 0xB0000000)
        with self.assertRaises(AddressAdmissionError):
            ProposedControlMap(list(good))

    def test_overlap_and_touching_regions(self):
        good = list(imaginary_apertures())
        bad = good.copy()
        bad[1] = ProposedAperture("dma_synapses", 0xB0000000)
        with self.assertRaises(AddressAdmissionError):
            ProposedControlMap(tuple(bad))
        good[0] = ProposedAperture("dma_neurons", 0xB0000000, 0x2000)
        with self.assertRaises(AddressAdmissionError):
            ProposedControlMap(tuple(good))
        # Distinct non-overlapping 4KiB-aligned touching windows are allowed.
        valid = list(imaginary_apertures())
        valid[0] = ProposedAperture("dma_neurons", 0xB0000000, 0x2000)
        valid[1] = ProposedAperture("dma_synapses", 0xB0002000)
        for i, bank in enumerate(BANKS[2:], 3):
            valid[i-1] = ProposedAperture(bank, 0xB0000000 + i * 0x1000)
        self.assertEqual(len(ProposedControlMap(tuple(valid)).apertures), 6)

    def test_alignment_length_rejection_and_40_bit_bound(self):
        cases = (
            ("dma_trace", 0),
            ("dma_trace", -0x1000),
            ("dma_trace", 0xB0000004),
            ("dma_trace", MAX_PS_PHYS_EXCLUSIVE),
            ("dma_trace", MAX_PS_PHYS_EXCLUSIVE - 0x1000),
        )
        for bank, base in cases:
            with self.subTest(base=base):
                if base == MAX_PS_PHYS_EXCLUSIVE - 0x1000:
                    # Exact exclusive upper bound IS allowed by arithmetic
                    self.assertEqual(
                        ProposedAperture(bank, base).end_exclusive,
                        MAX_PS_PHYS_EXCLUSIVE,
                    )
                else:
                    with self.assertRaises(AddressAdmissionError):
                        ProposedAperture(bank, base)
        for length in (0, 4, 0xFFF, 0x1001, 0x2001, 1 << 22):
            with self.subTest(length=length):
                with self.assertRaises(AddressAdmissionError):
                    ProposedAperture("dma_trace", 0xB0000000, length)

    def test_bools_and_non_ints_cannot_be_accepted_as_addresses(self):
        for value in (True, False, 1.5, "0xB0000000", None):
            with self.subTest(value=value):
                with self.assertRaises(AddressAdmissionError):
                    ProposedAperture("shell", value)
        for value in (True, False, 4096.0, "4096", None):
            with self.subTest(value=value):
                with self.assertRaises(AddressAdmissionError):
                    ProposedAperture("shell", 0xB0000000, value)

    def test_read_only_immutable_and_unknown_register_refusal(self):
        c = ProposedControlMap(imaginary_apertures())
        with self.assertRaises(FrozenInstanceError):
            c.apertures[0].base = 4
        with self.assertRaises(FrozenInstanceError):
            c.apertures = ()
        for bank, register in (
            ("hls", "AP_CTRL"),  # generated HLS address unverified
            ("shell", "HLS_STATUS"),
            ("dma_trace", "SA_LOW"),
            ("dma_neurons", "DA_LOW"),
            ("dma_nope", "LENGTH"),
            ("shell", 0x38),
        ):
            with self.subTest(bank=bank, reg=register):
                with self.assertRaises(AddressAdmissionError):
                    c.proposed_register_address(bank, register)

    def test_no_default_addresses_or_hardware_mmio_backend(self):
        src = (ROOT / "src/neuromorphic_accelerator_v1/m05_12d2_control_map.py").read_text()
        self.assertIn("No default base addresses", src)
        self.assertIn("MAX_PS_PHYS_EXCLUSIVE", src)
        self.assertIn("HLS native regmap", src)
        for disallowed in (
            "import mmap", "import os", "dev/mem", "os.open(",
            "cdma", "read32(", "write32(", "assign_bd_address",
            "CMA_Alloc", "allocate(", "axi.write(", "register_write(",
        ):
            with self.subTest(disallowed=disallowed):
                # Explanation in docstrings may discuss prohibited APIs but
                # no runnable backend calls should appear.
                if disallowed in ("dev/mem", "assign_bd_address"):
                    continue
                self.assertNotIn(disallowed, src)


if __name__ == "__main__":
    unittest.main()
