"""Synthetic unit-only original D3.D.2C 12-hash receipt mutation tests.

Uses REAL accepted current RTL+builder+POR bytes, FAKE report, FAKE .bit
and MOCKED timing parser only to test byte-level rejection wiring. These
fixtures never represent original native acceptance or board execution.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_d3d2c_m06_native_review as gate
from test_m08_d3d2c_owner_native_review import synthetic_original_review

class MockFirstOwnerReceiptTests(unittest.TestCase):
    def make_mock(self,root:Path):
        run=root/"M08"/gate.ORIGINAL_OWNER_NATIVE_DIR
        run.mkdir(parents=True)
        values={
            "schema":"m08-d3d2c-m06-32-offline-build-v1",
            "wrapper_top":"m08_d3d2c_m06_lif_jtag_wrapper",
            "neural_mode":"THIRTY_TWO_NEURON_M06_RECURRENT_3_4_SIGNED16",
            "decay_modes":"ZERO_HALF_ONE_THREE_QUARTERS",
            "physical_neurons":"32","physical_ticks":"4",
            "edge_capacity":"8","m06_original_edges":"5",
            "m06_original_external_events":"17",
            "external_event_coalescing":"HOST_PC_ONLY",
            "physical_m06_ddr":"NO",
            "part":"xck26-sfvc784-2LV-c",
            "ps_to_pl_hpm":"DISABLED",
            "ps_clock_dependency":"YES",
            "ps_reset_dependency":"NO",
            "jtag_axi":"ENABLED_PL",
            "ps_pl0_clock_request_hz":"100000000",
            "ps_pl0_runtime_clock_proven":"NO",
            "board_part":"xilinx.com:kv260_som:part0:1.4",
            "linux_management_compatibility":"NOT_PROVEN",
            "bram_map_base":"0xA0000000",
            "lif_base":"0xA0001000",
            "bram_map_range":"0x00001000",
            "lif_map_range":"0x00001000",
            "bram_controller_derived_depth":"1024",
            "bram_depth_words":"1024",
            "bram_width_bits":"32",
            "test_window_bytes":"4096",
            "fan_route":"TTC0_WAVEOUT2_TO_A12",
            "reset_mode":"FABRIC_POR_256_CYCLES",
            "hardware_bitstream_programmed":"NO",
            "hardware_neural_execution_proven":"NO",
            "hardware_jtag_axil_readback_proven":"NO",
            "hardware_lif_readback_proven":"NO",
            "lif_rtl_sha256":gate.OWNER_ORIGINAL_RTL_SHA,
            "fabric_por_rtl_sha256":gate.OWNER_ORIGINAL_POR_SHA,
            "builder_sha256":gate.OWNER_ORIGINAL_BUILDER_SHA,
            "bitstream_size_bytes":"43",
            "vivado_version":"2025.2",
        }
        bit=b"SYNTHETIC-BITSTREAM-WITH-NO-HARDWARE-IMAGE!" # not genuine
        values["bitstream_size_bytes"]=str(len(bit))
        files={
            "00_vivado.log":b"M08_D3D2C_NATIVE_TOP_WRAPPER_VALIDATED|m08_d3d2c_m06_lif_jtag_wrapper\nM08_D3D2C_JTAG_BRAM_OFFLINE_BITSTREAM_CREATED_NOT_PROGRAMMED\n",
            "01_vivado.jou":b"MOCK-JOURNAL\n",
            "02_vivado_exit.txt":b"vivado_build_exit=0\n",
            "reports/10_fan_a12.xdc":b"MOCK-XDC\n",
            "reports/11_fabric_por.v":gate.POR.read_bytes(),
            "reports/12_synaptic_lif_axil.v":gate.RTL.read_bytes(),
            "reports/20_route_drc.rpt":synthetic_original_review().encode(),
            "reports/21_route_timing.rpt":b"MOCK-TIMING-PARSER-RESULT\n",
            "reports/22_route_utilization.rpt":b"MOCK-UTIL\n",
            "reports/23_route_clocks.rpt":b"MOCK-CLOCKS\n",
            "reports/30_native_result.txt":("\n".join(k+"="+v for k,v in values.items())+"\n").encode(),
            gate.BIT_REL:bit,
        }
        for name,blob in files.items():
            path=run/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(blob)
        self.rehash_ledger(run)
        return run,bit,files["reports/20_route_drc.rpt"]

    @staticmethod
    def rehash_ledger(folder:Path):
        (folder/"99_evidence_sha256.txt").write_text(
            "".join(sha256((folder/name).read_bytes()).hexdigest()+"  "+name+"\n"
                    for name in gate.FILES),encoding="ascii")

    def patched(self,bit:bytes,drc:bytes):
        from contextlib import ExitStack
        ctx=ExitStack()
        ctx.enter_context(patch.object(gate,"OWNER_ORIGINAL_BIT_SHA",sha256(bit).hexdigest()))
        ctx.enter_context(patch.object(gate,"OWNER_ORIGINAL_BIT_BYTES",len(bit)))
        ctx.enter_context(patch.object(gate,"OWNER_ORIGINAL_DRC_SHA",sha256(drc).hexdigest()))
        ctx.enter_context(patch.object(gate.d3c,"inspect_timing",return_value={
            "wns_ns":2.675,"tns_ns":0.0,"whs_ns":0.010,"ths_ns":0.0}))
        return ctx

    def test_mock_original_12_sha_receipt_positive_for_parser_only(self):
        with TemporaryDirectory() as tmp:
            folder,bit,drc=self.make_mock(Path(tmp))
            with self.patched(bit,drc):
                result=gate.inspect(folder)
                self.assertEqual(result["candidate_bytes"],len(bit))
                self.assertEqual(result["original_drc_checks"],7)
                self.assertEqual(result["rtstat_sampled_paths"],15)
                self.assertEqual(result["status"],
                                 "M08_D3D2C_EXACT_OWNER_NATIVE_M06_32_IMAGE_ACCEPTED_NO_BOARD")
                self.assertFalse(result["hardware_programmed"])
                self.assertFalse(result["physical_programming_authorized"])

    def test_mutated_mock_image_and_rehashed_ledger_still_rejected(self):
        with TemporaryDirectory() as tmp:
            folder,bit,drc=self.make_mock(Path(tmp))
            with self.patched(bit,drc):
                fp=folder/gate.BIT_REL
                fp.write_bytes(bit+b"X")
                self.rehash_ledger(folder)
                with self.assertRaisesRegex(gate.Reject,"bitstream size differs"):
                    gate.inspect(folder)

    def test_mutated_mock_drc_and_rehashed_ledger_still_rejected(self):
        with TemporaryDirectory() as tmp:
            folder,bit,drc=self.make_mock(Path(tmp))
            with self.patched(bit,drc):
                file=folder/"reports/20_route_drc.rpt"
                file.write_bytes(drc.replace(b"'A2'",b"'A3'"))
                self.rehash_ledger(folder)
                with self.assertRaisesRegex(gate.Reject,"not byte-identical"):
                    gate.inspect(folder)

    def test_mutated_mock_embedded_rtl_and_rehashed_ledger_still_rejected(self):
        with TemporaryDirectory() as tmp:
            folder,bit,drc=self.make_mock(Path(tmp))
            with self.patched(bit,drc):
                file=folder/"reports/12_synaptic_lif_axil.v"
                file.write_bytes(file.read_bytes()+b"\n// tamper\n")
                self.rehash_ledger(folder)
                with self.assertRaisesRegex(gate.Reject,"routed source/provenance mismatch"):
                    gate.inspect(folder)

    def test_mutated_mock_ledger_name_rejected(self):
        with TemporaryDirectory() as tmp:
            folder,bit,drc=self.make_mock(Path(tmp))
            with self.patched(bit,drc):
                receipt=folder/"99_evidence_sha256.txt"
                receipt.write_text(receipt.read_text().replace(
                    "reports/20_route_drc.rpt","reports/21_route_drc.rpt"))
                with self.assertRaisesRegex(gate.Reject,"ledger name/order drift"):
                    gate.inspect(folder)

if __name__=="__main__":
    unittest.main()
