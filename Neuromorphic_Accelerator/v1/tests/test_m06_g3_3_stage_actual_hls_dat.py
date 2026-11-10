"""G3.3 actual accepted Vitis-HLS .dat staging, positive/negative SOURCE tests."""
from __future__ import annotations
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_g3_3_stage_actual_hls_dat import stage


class G33RealDatStagingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.hls=root/"m06_paged_rolling_hls_cosim_SYNTHETIC"
        self.rtl=self.hls/"work/hls/syn/verilog"
        self.rtl.mkdir(parents=True)
        self.out=root/"new_xsim_output"
        self.out.mkdir()
        self.files=[]
        for i in range(40):
            file=self.rtl/f"original_hls_module_{i}.v"
            file.write_text(f"module fixture_{i}; endmodule\n")
            self.files.append(file)
        self.files[0].write_text(
            "module fixture_0; reg [7:0] mem[0:1]; "
            "initial $readmemh(\"init_0.dat\",mem); endmodule\n"
        )
        self.files[1].write_text(
            "module fixture_1; reg [7:0] mem[0:1]; "
            "initial $readmemb(\"./init_1.dat\",mem); endmodule\n"
        )
        (self.rtl/"init_0.dat").write_text("01\n02\n")
        sim=self.hls/"work/hls/sim/verilog"
        sim.mkdir(parents=True)
        (sim/"init_1.dat").write_text("00000001\n00000010\n")
    def test_genuine_bytes_staged_without_owner_mutation(self):
        before=hashlib.sha256((self.rtl/"init_0.dat").read_bytes()).hexdigest()
        r=stage(self.hls,self.files,self.out)
        self.assertEqual(r["status"],"REAL_HLS_DAT_FILES_STAGED_ORIGINAL_BYTES_UNMODIFIED")
        self.assertEqual(r["init_file_count"],2)
        self.assertEqual((self.out/"init_0.dat").read_bytes(),
                         (self.rtl/"init_0.dat").read_bytes())
        self.assertEqual((self.out/"init_1.dat").read_text(),"00000001\n00000010\n")
        self.assertEqual(before,hashlib.sha256((self.rtl/"init_0.dat").read_bytes()).hexdigest())
        self.assertFalse(r["g3_3_neural_rtl_pass"])
        self.assertFalse(r["fabricated_or_zero_filled"])
    def test_missing_hls_init_data_fails_closed(self):
        (self.rtl/"init_0.dat").unlink()
        with self.assertRaisesRegex(ValueError,"missing original HLS .dat"):
            stage(self.hls,self.files,self.out)
    def test_conflicting_original_source_duplicates_rejected(self):
        sim=self.hls/"work/hls/sim/verilog"
        (sim/"init_0.dat").write_text("THIS IS NOT ORIGINAL\n")
        with self.assertRaisesRegex(ValueError,"conflicting original HLS .dat"):
            stage(self.hls,self.files,self.out)
    def test_unsafe_path_refused_and_nonliteral_meminit_rejected(self):
        self.files[0].write_text(
            "module fixture_0; initial $readmemh(\"../outside.dat\",mem); endmodule\n"
        )
        with self.assertRaisesRegex(ValueError,"untrusted HLS initialization path"):
            stage(self.hls,self.files,self.out)
        self.files[0].write_text(
            "module fixture_0; initial $readmemh(FILE_NAME,mem); endmodule\n"
        )
        with self.assertRaisesRegex(ValueError,"unresolved nonliteral"):
            stage(self.hls,self.files,self.out)
    def test_reject_existing_output_and_immutable_owner_directory(self):
        (self.out/"init_0.dat").write_text("user data\n")
        with self.assertRaisesRegex(ValueError,"refuse to overwrite"):
            stage(self.hls,self.files,self.out)
        with self.assertRaisesRegex(ValueError,"outside immutable"):
            stage(self.hls,self.files,self.rtl)
    def test_real_rtl_g33_generator_has_no_late_hls_declaration(self):
        file=(ROOT/"scripts/m06_g3_3_generate_actual_hls_idle_tb.py").read_text()
        first=file.index('for name,(_,width) in sorted(pins.items()):')
        last=file.index('for ip,sc in ROLE:',first)
        self.assertLess(first,last)
        self.assertIn('lines.append("wire "+_decl(width)+"h_"+name+";")',file)


if __name__=="__main__":
    unittest.main()
