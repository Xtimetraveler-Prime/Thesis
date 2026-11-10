"""Synthetic original-AMD G3.2 ZIP evidence audit tests; NEVER vendor simulation."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from m06_g3_2_connected_evidence_audit import verify_zip, STAGES, SOURCE_COMMIT, PASS
READS=[0,0xffc,0x1000,0xfffc,0xfffc,0xfff8,0x1000,0xffc,0xff00,0xfffc]
WRITES=[0xfffc,0x1000,0xff00]

def fixture() -> dict[str,bytes]:
    events=[]
    def add(stage,kind,addr=None,strb=None):
        row={"kind":kind,"stage":stage,"t":str(1000+len(events)*10)}
        if addr is not None:
            row.update(addr=f"{addr:08x}",len="0",size="2",burst="01")
        if kind in ("R_OBS","R_HS","B_OBS","B_HS"):
            row["resp"]="00"
        if kind=="R_OBS" and stage=="SC_M00_RAM128":
            row["ram_bad"]="0"
        if strb is not None:
            row["strb"]=strb
        events.append("M06_G3_AXI_TRACE "+" ".join(k+"="+v for k,v in row.items()))
    for addr in READS:
        for stage in ("RD_SI32","RD_MI256_SC_S00","SC_M00_RAM128"):
            for kind in ("AR","R_OBS","R_HS"):
                add(stage,kind,addr=addr if kind=="AR" else None)
    for addr,strobe in zip(WRITES,("5000","000f","000f")):
        for stage in ("WR_SI32","WR_MI256_SC_S03","SC_M00_RAM128"):
            for kind in ("AW","W","B_OBS","B_HS"):
                add(stage,kind,addr=addr if kind=="AW" else None,
                    strb=strobe if (stage=="SC_M00_RAM128" and kind=="W") else ("f" if kind=="W" else None))
    assert len(events)==126
    counts=Counter()
    for line in events:
        row=dict(term.split("=",1) for term in line.split()[1:])
        counts[(row["stage"],row["kind"])]+=1
    stages={stage:{kind:counts[(stage,kind)] for kind in ("AR","R_HS","R_OBS","AW","W","B_OBS","B_HS")} for stage in STAGES}
    source="".join("0"*64+f"  src{i}.py\n" for i in range(5)).encode()
    vendor="".join("1"*64+f"  vendor{i}.v\n" for i in range(67)).encode()
    tb=b"// SYNTHETIC testbench fixture, NOT genuine AMD.\n"
    summary=json.dumps(dict(event_count=126,first_decerr=None,trace_truncated_or_incomplete=False,counter_summary={"first_decerr":"0"},by_stage_kind=stages)).encode()
    return {
        "result.txt":b"exit_status=0\n","commit.txt":(SOURCE_COMMIT+"\n").encode(),
        "07_xsim.log":("xsim v2025.2\n"+PASS+" write=3 read=10 m00_w=3 m00_r=10 high_byte=65535 shared_64k=1 NO_HLS_NO_BOARD_NO_DDR\n").encode(),
        "08_axi_handshake_trace.log":("\n".join(events)+"\n").encode(),
        "09_axi_probe_summary.json":summary,
        "generated_bfm_sha256.txt":(hashlib.sha256(tb).hexdigest()+"  tb.sv\n").encode(),
        "tb_m06_g3_real_dwc_original_sc.sv":tb,
        "04_xvhdl.log":b"xvhdl completed\n","05_xvlog.log":b"xvlog completed\n",
        "06_xelab.log":b"xelab completed\n",
        "source_before_sha256.txt":source,"source_after_sha256.txt":source,
        "vendor_sha_before.txt":vendor,"vendor_sha_after.txt":vendor,
        "original_xci_after_sha_check.txt":b"/tmp/m06_g3_read_dwc.xci: OK\n/tmp/m06_g3_write_dwc.xci: OK\n",
        "03_connected_vendor_compile_plan.json":b"{}\n",
    }

class M06G32EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"synthetic.zip"
    def check(self,files):
        with ZipFile(self.path,"w",ZIP_DEFLATED) as z:
            for k,v in files.items(): z.writestr(k,v)
        return verify_zip(self.path)
    def test_positive_synthetic_bfm_only_counts(self):
        r=self.check(fixture())
        self.assertEqual(r["status"],"PASS_G3_2_BFM_ONLY_ORIGINAL_AMD_XSIM_2025_2")
        self.assertEqual(r["handshake_trace_events"],126)
        self.assertFalse(r["generated_hls_neural_rtl_connected"])
        self.assertFalse(r["m06_complete"])
    def test_negative_runner_or_commit_rejected(self):
        f=fixture();f["result.txt"]=b"exit_status=1\n"
        with self.assertRaisesRegex(ValueError,"runner"):self.check(f)
        f=fixture();f["commit.txt"]=b"0"*40
        with self.assertRaisesRegex(ValueError,"corrected source"):self.check(f)
    def test_negative_vendor_hash_or_xci_rejected(self):
        f=fixture();f["vendor_sha_after.txt"]+=b"changed"
        with self.assertRaisesRegex(ValueError,"SHA manifest"):self.check(f)
        f=fixture();f["original_xci_after_sha_check.txt"]=b"/tmp/m06_g3_read_dwc.xci: OK\n"
        with self.assertRaisesRegex(ValueError,"both original AMD"):self.check(f)
    def test_negative_handshake_loss_or_decerr_rejected(self):
        f=fixture();f["08_axi_handshake_trace.log"]=f["08_axi_handshake_trace.log"].replace(b"R_HS",b"R_ERR",1)
        with self.assertRaisesRegex(ValueError,"wrong accepted|incomplete"):self.check(f)
        f=fixture();f["08_axi_handshake_trace.log"]=f["08_axi_handshake_trace.log"].replace(b"resp=00",b"resp=11",1)
        with self.assertRaisesRegex(ValueError,"response"):self.check(f)
    def test_negative_bfm_sha_or_strobe_lane_rejected(self):
        f=fixture();f["generated_bfm_sha256.txt"]=b"f"*64+b" tb.sv"
        with self.assertRaisesRegex(ValueError,"hash mismatch"):self.check(f)
        f=fixture();f["08_axi_handshake_trace.log"]=f["08_axi_handshake_trace.log"].replace(b"strb=5000",b"strb=0005")
        with self.assertRaisesRegex(ValueError,"byte lanes"):self.check(f)
    def test_negative_fatal_xsim_or_duplicate_member_rejected(self):
        f=fixture();f["07_xsim.log"]+=b"Fatal: synthetic error\n"
        with self.assertRaisesRegex(ValueError,"genuine XSim"):self.check(f)
        f=fixture()
        with ZipFile(self.path,"w") as z:
            for k,v in f.items():z.writestr(k,v)
            z.writestr("result.txt",b"exit_status=0")
        with self.assertRaisesRegex(ValueError,"duplicated"):verify_zip(self.path)

if __name__=="__main__":
    unittest.main()
