"""Source-only M06 AMD original compile-plan regression, NEVER genuine XSim."""
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_vendor_compile_plan import EXPECTED_D3, MEM_SC, REQUIRED_INCLUDE, plan


def synthetic_sources(directory: Path):
    original=directory/EXPECTED_D3
    original.mkdir()
    folder=original/"13_file_backed_project/m05_d3_output_products.gen/ipshared"
    subset=[]
    def add(rel: str):
        path=folder/rel
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text("// SYNTHETIC CI FIXTURE ONLY\n")
        subset.append(path)
        return path
    header=add("ec67/hdl/axi_infrastructure_v1_1_0.vh")
    infrastructure=add("ec67/hdl/axi_infrastructure_v1_1_vl_rfs.v")
    add("bc4b/hdl/axi_register_slice_v2_1_vl_rfs.v")
    extra_header=add("f0b6/hdl/verilog/sc_util_v1_0_4_constants.vh")
    add("f0b6/hdl/sc_util_v1_0_vl_rfs.sv")
    add(f"mem/{MEM_SC}/sim/{MEM_SC}.sv")
    add(f"mem/{MEM_SC}/bd_0/sim/bd_13bd.v")
    for idx in range(44):
        add(f"sub{idx}/hdl/sc_synthetic_{idx}.sv")
    irrelevant=[f"/outside-original-compile-order/unrelated_{n}.v"
                for n in range(186-len(subset))]
    rows=[f"SIM_SOURCE|{x}" for x in map(str,subset)]
    rows += [f"SIM_SOURCE|{x}" for x in irrelevant]
    assert len(rows)==186
    return original,"\n".join(rows)+"\n",header,infrastructure,extra_header


class M06OriginalVendorCompilePlanTests(unittest.TestCase):
    def test_vivado_header_dir_from_all_original_186_not_shortlisted_rtl(self):
        with tempfile.TemporaryDirectory() as d:
            orig,report,header,infrastructure,other=synthetic_sources(Path(d))
            value=plan(orig,report)
            self.assertEqual(value["vivado_original_source_count"],186)
            self.assertGreaterEqual(value["selected_vendor_compilation_source_count"],45)
            self.assertEqual(value["axi_infrastructure_header"],str(header))
            self.assertIn(str(header.parent),value["include_directories"])
            self.assertIn(str(other.parent),value["include_directories"])
            self.assertNotIn(str(header),value["verilog_files"])
            self.assertIn(str(infrastructure),value["verilog_files"])
            self.assertEqual(value["vendor_XSim_executed"],False)

    def test_missing_or_renamed_header_fails_before_xvlog(self):
        with tempfile.TemporaryDirectory() as d:
            orig,report,header,infrastructure,other=synthetic_sources(Path(d))
            header.unlink()
            with self.assertRaisesRegex(ValueError,"missing or escaped"):
                plan(orig,report)
            # Even if missing entry avoids missing-file rule, exact name is
            # mandatory, preventing an invented substitute header.
            fake=header.parent/"not_axi_infrastructure_v1_1_0.vh"
            fake.write_text("synthetic")
            altered=report.replace(str(header),str(fake))
            with self.assertRaisesRegex(ValueError,"must appear exactly once"):
                plan(orig,altered)

    def test_wrong_original_source_manifest_cardinality_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            orig,report,header,infrastructure,other=synthetic_sources(Path(d))
            with self.assertRaisesRegex(ValueError,"186 unique"):
                plan(orig, "\n".join(report.splitlines()[:-1]))
            bad=report.replace(str(header),str(other))
            with self.assertRaisesRegex(ValueError,"unique"):
                plan(orig,bad)

    def test_unrelated_missing_original_project_file_not_required_for_isolated_mem_sc(self):
        with tempfile.TemporaryDirectory() as d:
            orig, report, header, infrastructure, other = synthetic_sources(Path(d))
            original_unrelated = orig / "13_file_backed_project/unrelated_neural_HLS.v"
            # The old runner incorrectly required *every* full-project
            # source to exist even when not used by isolated vendor mem_sc.
            amended = report.replace(
                "/outside-original-compile-order/unrelated_0.v",
                str(original_unrelated))
            result = plan(orig, amended)
            self.assertEqual(result["vivado_original_source_count"], 186)
            self.assertNotIn(str(original_unrelated), result["verilog_files"])

    def test_selected_dependencies_are_original_only(self):
        with tempfile.TemporaryDirectory() as d:
            orig,report,header,infrastructure,other=synthetic_sources(Path(d))
            value=plan(orig,report)
            for source in value["verilog_files"]:
                self.assertTrue(Path(source).is_relative_to(orig))
            for folder in value["include_directories"]:
                self.assertTrue(Path(folder).is_relative_to(orig))
            self.assertEqual(value["physical_board"],"NOT_AUTHORIZED")


if __name__=="__main__":
    unittest.main()
