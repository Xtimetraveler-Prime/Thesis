"""Real M06 signed16 config-to-host-bank 3 logical page integration, no board.

This source test packs the ACCEPTED independent M02/M03 M06 input parameters
into 15+15+2 distinct logical pages with one 256B RTL resident slot. Icarus
exercises all three page loads/readback/dispatch/dirty saves and overwrites;
the compute port is a checksum probe ONLY, not a simulated LIF network.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import m08_m06_parameter_pages as params

RTL=ROOT/"rtl/m08"
FILES=tuple(RTL/name for name in (
    "m08_page_compute_probe_shell.v",
    "m08_page_compute_probe.v",
    "m08_axil_page_control.sv",
    "m08_host_staged_page_bank.sv",
    "tb_m08_m06_parameter_pages.sv",
))
STATUS=("M08_M06_32_SIGNED16_CONFIGS_THREE_LOGICAL_PAGES_ONE_REAL_RTL_SLOT_PASS",
        "M08_M06_HOST_PAGED_NEURAL_PARAMETERS_NOT_NEURAL_EXECUTION_NO_DDR_PASS")

class M06ParameterPageSourceTests(unittest.TestCase):
    def test_all_32_original_signed16_m06_neurons_unaltered_and_only_inputs(self):
        oracle=params.oracle()
        self.assertEqual([params.valid_neurons(i) for i in range(3)],[15,15,2])
        found=[]
        for page in range(3):
            raw=params.image(page)
            self.assertEqual(len(raw),256)
            words=struct.unpack("<64I",raw)
            self.assertEqual(words[60:64],
                             (params.MAGIC,page,params.valid_neurons(page),0))
            for n in range(params.valid_neurons(page)):
                logical_neuron=page*15+n
                wanted=oracle[3+logical_neuron*8:3+logical_neuron*8+4]
                self.assertEqual(words[4*n:4*n+4],wanted)
                found.append(logical_neuron)
            self.assertEqual(
                words[4*params.valid_neurons(page):params.FIRST_METADATA_WORD],
                (0,)*(params.FIRST_METADATA_WORD-4*params.valid_neurons(page)))
            result=params.audit(raw,page)
            self.assertEqual(result["valid_neurons"],params.valid_neurons(page))
            self.assertFalse(result["actual_neural_results_computed"])
            self.assertFalse(result["hardware_page_programmed"])
        self.assertEqual(found,list(range(32)))

    def test_wrong_page_id_wrong_state_overflow_and_provisional_checksum_rejected(self):
        for page in range(3):
            raw=params.image(page)
            for other in range(3):
                if other!=page:
                    with self.assertRaisesRegex(params.Reject,"configuration, logical ID"):
                        params.audit(raw,other)
            for word in (0,4,59,60,61,62,63):
                mutation=bytearray(raw)
                mutation[word*4]^=1
                with self.subTest(page=page,word=word):
                    with self.assertRaises(params.Reject):
                        params.audit(bytes(mutation),page)
            for payload in (raw[:-4],raw+b"\0"*4,bytearray(raw)):
                with self.assertRaises(params.Reject):
                    params.audit(payload,page)
            expected=list(params.parameter_words(page))
            expected[63]=params.expected_probe_result(tuple(expected))
            actual=struct.pack("<64I",*expected)
            out=params.audit(actual,page,post_compute=True)
            self.assertTrue(out["post_compute_probe_only"])
            if expected[63]!=0:
                with self.assertRaises(params.Reject):
                    params.audit(raw,page,post_compute=True)
        for illegal in (-1,3,True,"1",None):
            with self.assertRaises(params.Reject):
                params.image(illegal)

    def test_exact_original_ref_hashes_and_metadata_are_deterministic(self):
        digests=[sha256(params.image(i)).hexdigest() for i in range(3)]
        self.assertEqual(len(set(digests)),3)
        self.assertEqual(params.MAGIC,0x4D365047)
        self.assertEqual(params.WORDS,64)
        self.assertEqual(params.NEURONS,32)
        self.assertEqual(params.PAGE_NEURONS,15)
        self.assertEqual(params.FIRST_METADATA_WORD,60)
        self.assertEqual(params.PROBE_RESULT_WORD,63)
        code=(ROOT/"scripts/m08_m06_parameter_pages.py").read_text()
        for disallowed in ("program_hw_devices","open_hw_manager",
                           "run_hw_axi","/dev/mem","dma_alloc","mmap.mmap"):
            self.assertNotIn(disallowed,code)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "genuine installed Icarus required, no fake simulation PASS")
    def test_real_iverilog_three_page_m06_host_compute_ownership(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            file_args=[]
            for page in range(3):
                words=params.parameter_words(page)
                fixture=folder/f"m06_input_page_{page}.hex"
                fixture.write_text("".join(f"{w:08X}\n" for w in words),
                                   encoding="ascii")
                file_args.append(f"+page{page}={fixture}")
            output=folder/"m06_three_page.vvp"
            build=subprocess.run(
                ["iverilog","-g2012","-s","tb_m08_m06_parameter_pages",
                 "-o",str(output),*[str(p) for p in FILES]],
                capture_output=True,text=True,timeout=90)
            self.assertEqual(build.returncode,0,
                             build.stdout+"\n"+build.stderr)
            self.assertFalse(build.stderr.strip(),
                             "unreviewed true RTL compilation warning")
            run=subprocess.run(["vvp",str(output),*file_args],
                               capture_output=True,text=True,timeout=90)
            self.assertEqual(run.returncode,0,
                             run.stdout+"\n"+run.stderr)
            self.assertEqual(run.stderr.strip(),"",
                             "unexpected true runtime sim warning")
            for marker in STATUS:
                self.assertEqual(run.stdout.count(marker),1,run.stdout)
            for page in range(3):
                marker=f"M08_M06_256B_REAL_RTL_PAGE_REPLACE_AND_PROBE_PASS|{page}|"
                self.assertEqual(run.stdout.count(marker),1,run.stdout)
            self.assertNotIn("FATAL:",run.stdout)

if __name__=="__main__":
    unittest.main()
