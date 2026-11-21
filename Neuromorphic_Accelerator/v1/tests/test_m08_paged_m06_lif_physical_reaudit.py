"""Adversarial read-only re-audit of a full first-original M08.4 JTAG receipt.

Use independently generated fixture, a synthetic 13-file owner hardware
ledger and intentionally Vivado-ECHOED Tcl command lines. NO live Vivado,
JTAG, bit programming, PS/DDR, or owner evidence mutations.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from unittest import mock
import tempfile
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_paged_m06_lif_fixture as oracle
import m08_paged_m06_lif_physical_audit as audit


class SyntheticFirstPagedHardwareReceipt(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        base=self.home/"Thesis_Evidence"/"M08"
        base.mkdir(parents=True)
        self.native=base/"m08_paged_m06_lif_QFKpXlPW"
        self.native.mkdir()
        self.hw=base/"m08_paged_m06_lif_HW_MOCK1234"
        self.hw.mkdir()
        self.golden=oracle.golden_words()
        self.files={
            "00_executed_source.tcl":
                (ROOT/"scripts/m08_paged_m06_lif_physical_once.tcl").read_bytes(),
            "02_jtag_paged_m06.jou":b"Original synthetic Vivado journal\n",
            "03_exit.txt":b"vivado_physical_exit=0\n",
            "10_edge_config_input.hex":
                self.encode_hex(oracle.edge_words()),
            **{
                f"11_neural_page_{p}_input.hex":
                    self.encode_hex(oracle.neural_words(p))
                for p in range(6)
            },
            "20_independent_512_oracle_ONLY.hex":
                self.encode_hex(self.golden),
        }
        self.files["01_jtag_paged_m06.log"]=self.log_bytes()
        self.files["80_physical_paged_neural_parity.txt"]=self.results_bytes()
        self.write_all()
        self.home_patch=mock.patch.object(Path,"home",return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)
        self.native_patch=mock.patch.object(
            audit.first_image,"inspect",
            return_value={"image_specific_gate":"ACCEPTED",
                          "owner_bit_sha256":audit.EXPECTED_BIT_SHA}
        )
        self.native_patch.start()
        self.addCleanup(self.native_patch.stop)

    @staticmethod
    def encode_hex(words):
        return "".join(f"{w:08X}\n" for w in words).encode("ascii")

    @staticmethod
    def standalone_markers():
        result=[
            "M08_4_ORIGINAL_BIT_SHA|"+audit.EXPECTED_BIT_SHA,
            "M08_4_SEPARATE_6_INPUT_PAGES_AND_512_ONLY_EXTERNAL_GOLDEN_PRECHECK_PASS",
            "M08_4_NEW_IMAGE_PROGRAM_ONCE_START",
            "M08_4_NEW_IMAGE_PROGRAM_ONCE_COMPLETE",
            "M08_4_PHYSICAL_EDGE_PAGE_CONFIGURED_5",
        ]
        for t in range(4):
            for p in range(6):
                result.append(f"M08_4_PHYSICAL_256B_LOAD_COMPUTE_FULL_DIRTY_SAVE|{t}|{p}")
            result.append(f"M08_4_PHYSICAL_ORDERED_TICK_BARRIER|{t}")
        result.append("M08_4_PHYSICAL_128_HOST_CURRENTS_384_FABRIC_COMPUTED_24_PAGES_ONE_BANK_PASS")
        return result

    def log_bytes(self):
        # One Tcl command echoes to Vivado log as '# puts ...' BEFORE
        # the runtime marker prints. The original failed Python used
        # substring search, which counted the echo and runtime as two.
        markers=self.standalone_markers()
        lines=[
            "****** Vivado v2025.2 (64-bit)",
            "# puts \"M08_4_NEW_IMAGE_PROGRAM_ONCE_START\"",
            "# puts \"M08_4_NEW_IMAGE_PROGRAM_ONCE_COMPLETE\"",
            "# puts \"M08_4_PHYSICAL_ORDERED_TICK_BARRIER|$tick\"",
            "# puts \"M08_4_PHYSICAL_256B_LOAD_COMPUTE_FULL_DIRTY_SAVE|$tick|$page\"",
            "# puts \"M08_4_PHYSICAL_128_HOST_CURRENTS_384_FABRIC_COMPUTED_24_PAGES_ONE_BANK_PASS\"",
            "INFO: [Labtoolstcl 44-466] Opening hw_target localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA",
            *markers,
            "INFO: [Labtoolstcl 44-464] Closing hw_target localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA",
        ]
        return ("\n".join(lines)+"\n").encode("utf-8")

    def results_bytes(self):
        lines=[
            "result=ONE_NEW_ORIGINAL_SIGNED16_32X4_ONE_RESIDENT_SIX_PAGE_PHYSICAL_PARITY",
            "owner_bit_sha256="+audit.EXPECTED_BIT_SHA,
            "genuine_kv260_jtag_program_count=1",
            "external_raw_events=17",
            "external_ingress=HOST_COALESCED_NOT_RAW_EVENT_FIFO",
            "independently_checked_host_input_currents=128",
            "independently_checked_fabric_voltages=128",
            "independently_checked_fabric_spike_decisions=128",
            "independently_checked_fabric_recurrent_currents=128",
            "real_page_load_compute_dirty_save_dispatches=24",
            "real_resident_neuron_banks=1",
            "physical_ps_pl_ddr=NO",
        ]
        masks=[0]*32
        for t in range(4):
            for p in range(6):
                for local in range(2 if p==5 else 6):
                    n=p*6+local
                    off=t*128+n*4
                    masks[n] |= (self.golden[off+2]&1)<<t
                    lines.append(
                        f"tick={t} page={p} neuron={n} "
                        f"input={self.golden[off]:08X} "
                        f"voltage={self.golden[off+1]:08X} "
                        f"mask={masks[n]:08X} "
                        f"recurrent={self.golden[off+3]:08X}"
                    )
        return ("\n".join(lines)+"\n").encode("ascii")

    def write_all(self):
        for name,contents in self.files.items():
            (self.hw/name).write_bytes(contents)
        ledger="".join(
            f"{sha256(self.files[name]).hexdigest()}  {name}\n"
            for name in audit.NAMES
        )
        (self.hw/"99_evidence_sha256.txt").write_text(ledger,encoding="ascii")

    def test_echoed_tcl_and_actual_runtime_markers_accept_original(self):
        result=audit.inspect(self.native,self.hw)
        self.assertEqual(result["original_physical_sha_files_checked"],13)
        self.assertEqual(result["physical_256_byte_page_dispatches_saved"],24)
        self.assertEqual(result["total_exact_numerical_comparisons"],512)
        self.assertEqual(result["independent_physical_pl_computed_checks"],384)
        self.assertTrue(result["original_single_JTAG_program_marker"])
        self.assertFalse(result["physical_ddr"])

    def test_missing_runtime_marker_with_echo_only_rejected_even_if_rehashed(self):
        marker="M08_4_NEW_IMAGE_PROGRAM_ONCE_START\n"
        original=self.files["01_jtag_paged_m06.log"].decode()
        self.assertEqual(original.count(marker),2) # echo contains text+newline, plus real line
        self.files["01_jtag_paged_m06.log"]=original.replace(
            "\n"+marker,"\n",1
        ).encode()
        self.write_all()
        with self.assertRaisesRegex(audit.Reject,"missing or duplicate original standalone"):
            audit.inspect(self.native,self.hw)

    def test_duplicate_real_runtime_marker_rehashed_rejected(self):
        marker="M08_4_NEW_IMAGE_PROGRAM_ONCE_START\n"
        original=self.files["01_jtag_paged_m06.log"].decode()
        self.files["01_jtag_paged_m06.log"]=original.replace(
            "\n"+marker,"\n"+marker+marker,1
        ).encode()
        self.write_all()
        with self.assertRaisesRegex(audit.Reject,"missing or duplicate original standalone"):
            audit.inspect(self.native,self.hw)

    def test_out_of_order_page_and_tick_rehashed_rejected(self):
        original=self.files["01_jtag_paged_m06.log"].decode()
        a="M08_4_PHYSICAL_256B_LOAD_COMPUTE_FULL_DIRTY_SAVE|1|0"
        b="M08_4_PHYSICAL_ORDERED_TICK_BARRIER|0"
        mutated=original.replace("\n"+a+"\n","\n~PLACEHOLDER~\n",1).replace(
            "\n"+b+"\n","\n"+a+"\n",1
        ).replace("\n~PLACEHOLDER~\n","\n"+b+"\n",1)
        self.files["01_jtag_paged_m06.log"]=mutated.encode()
        self.write_all()
        with self.assertRaisesRegex(audit.Reject,"out of physical execution order"):
            audit.inspect(self.native,self.hw)

    def test_mutated_neural_output_rehashed_rejected(self):
        original=self.files["80_physical_paged_neural_parity.txt"].decode()
        first="input="+f"{self.golden[0]:08X}"
        mutant="input="+f"{(self.golden[0]^1):08X}"
        self.files["80_physical_paged_neural_parity.txt"]=original.replace(
            first,mutant,1
        ).encode()
        self.write_all()
        with self.assertRaisesRegex(audit.Reject,"independent M02/M03 physical neural parity mismatch"):
            audit.inspect(self.native,self.hw)

    def test_tampered_file_unrehased_ledger_rejected(self):
        path=self.hw/"80_physical_paged_neural_parity.txt"
        path.write_bytes(path.read_bytes()+b"changed\n")
        with self.assertRaisesRegex(audit.Reject,"original physical file was altered"):
            audit.inspect(self.native,self.hw)


if __name__=="__main__":
    unittest.main()
