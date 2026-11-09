"""D4.3 SOURCE-ONLY synthetic 256:128 byte-oracle tests, never vendor RTL."""
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m05_12d4_axi_byte_oracle import (
    ProtocolError, check_suite, known_byte, read_check, stability, write_check,
)


def sample_write(beats=3, addr=0x4000, segmented=False, error=False):
    if segmented:
        assert beats == 3
    tx = {
        "case_id": "write3", "op": "WRITE", "burst": "INCR",
        "address": addr, "beats": beats, "id": 13,
        "upstream_w": [], "downstream_w": [],
        "downstream_addresses": [
            {"address": addr, "beats": 2 if segmented else beats*2,
             "size": 4, "id": 8}
        ] + ([{"address": addr+32, "beats": 4, "size": 4, "id": 9}]
             if segmented else []),
        "downstream_b": [{"id": 8, "resp": 0}] +
                        ([{"id": 9, "resp": 2 if error else 0}] if segmented else []),
        "upstream_b": {"id": 13, "resp": 2 if error else 0},
    }
    for i in range(beats):
        b = bytes(((addr+32*i+j)*17+j) & 0xff for j in range(32))
        mask = [0xFFFFFFFF, 0xF000000F, 0xA5A55A5A][i % 3]
        tx["upstream_w"].append({"data": b.hex(), "strb": mask, "last": i == beats-1})
        tx["downstream_w"].extend((
            {"data": b[:16].hex(), "strb": mask & 0xffff,
             "last": (i == 0) if segmented else (i == beats-1 and False)},
            {"data": b[16:].hex(), "strb": mask >> 16,
             "last": (i == beats-1) if segmented else (i == beats-1)},
        ))
    if segmented:
        # segment0 is just the first upstream beat, second covers the other two
        tx["downstream_w"][0]["last"] = False
        tx["downstream_w"][1]["last"] = True
        tx["downstream_w"][2]["last"] = False
        tx["downstream_w"][3]["last"] = False
        tx["downstream_w"][4]["last"] = False
        tx["downstream_w"][5]["last"] = True
    else:
        for row in tx["downstream_w"]:
            row["last"] = False
        tx["downstream_w"][-1]["last"] = True
    return tx


def sample_read(beats=2, addr=0x5000, error=False):
    tx = {
        "case_id": "read2", "op": "READ", "burst": "INCR",
        "address": addr, "beats": beats, "id": 7,
        "downstream_addresses": [{"address": addr, "beats": beats*2,
                                  "size": 4, "id": 98}],
        "downstream_r": [], "upstream_r": [],
    }
    for i in range(beats*2):
        data = bytes(known_byte(addr+i*16+j) for j in range(16))
        tx["downstream_r"].append({
            "data": data.hex(), "id": 98, "resp": (2 if error and i == 1 else 0),
            "last": i == beats*2-1,
        })
    for i in range(beats):
        data = bytes(known_byte(addr+i*32+j) for j in range(32))
        tx["upstream_r"].append({
            "data": data.hex(), "id": 7, "resp": (2 if error and i == 0 else 0),
            "last": i == beats-1,
        })
    return tx


def all_stalls():
    zeros = {ch: {"valid": False, "ready": False, "payload": ""}
             for ch in ("AW", "W", "B", "AR", "R")}
    samples = [{"reset_n": False}]
    for ch in ("AW", "W", "B", "AR", "R"):
        for ready in (False, True):
            signal = copy.deepcopy(zeros)
            signal[ch] = {"valid": True, "ready": ready, "payload": "0xA55A"}
            samples.append({"reset_n": True, "channels": signal})
    return samples


class AXIByteOracleTests(unittest.TestCase):
    def test_256_128_write_active_bytes_lane_masks_last_and_bresp(self):
        result = write_check(sample_write())
        self.assertEqual(result["upstream_bytes"], 96)
        self.assertEqual(result["downstream_bytes"], 96)
        self.assertEqual(result["axi_widths"], [256, 128])
        self.assertEqual(result["segments"], 1)
        self.assertEqual(result["downstream_errors"], 0)

    def test_write_segments_and_error_correlation(self):
        result = write_check(sample_write(segmented=True, error=True))
        self.assertEqual(result["segments"], 2)
        self.assertEqual(result["downstream_errors"], 1)

    def test_read_byte_oracle_2_halves_and_rlast(self):
        result = read_check(sample_read())
        self.assertEqual(result["downstream_bytes"], 64)
        self.assertEqual(result["upstream_bytes"], 64)
        self.assertEqual(result["downstream_errors"], 0)

    def test_read_rresp_error_must_reach_original_256bit_beat(self):
        self.assertEqual(read_check(sample_read(error=True))["downstream_errors"], 1)
        bad = sample_read(error=True)
        bad["upstream_r"][0]["resp"] = 0
        with self.assertRaisesRegex(ProtocolError, "RRESP"):
            read_check(bad)

    def test_high_order_write_data_and_mask_corruption_detected(self):
        original = sample_write()
        high = copy.deepcopy(original)
        high["downstream_w"][1]["data"] = ("00"*16)
        with self.assertRaisesRegex(ProtocolError, "active data byte"):
            write_check(high)
        mask = copy.deepcopy(original)
        mask["downstream_w"][1]["strb"] = 0
        with self.assertRaisesRegex(ProtocolError, "strobe"):
            write_check(mask)
        last = copy.deepcopy(original)
        last["downstream_w"][0]["last"] = True
        with self.assertRaisesRegex(ProtocolError, "WLAST"):
            write_check(last)

    def test_read_high_order_byte_corruption_and_loss_detected(self):
        high = sample_read()
        high["upstream_r"][0]["data"] = high["upstream_r"][0]["data"][:32] + "00"*16
        with self.assertRaisesRegex(ProtocolError, "RDATA"):
            read_check(high)
        lost = sample_read()
        lost["downstream_r"] = lost["downstream_r"][:-1]
        with self.assertRaisesRegex(ProtocolError, "cardinality"):
            read_check(lost)
        bad_id = sample_read()
        bad_id["upstream_r"][0]["id"] += 1
        with self.assertRaisesRegex(ProtocolError, "RID"):
            read_check(bad_id)

    def test_error_bresp_routing_and_segment_id_fail_closed(self):
        good = sample_write()
        bad_b = copy.deepcopy(good)
        bad_b["upstream_b"]["resp"] = 2
        with self.assertRaisesRegex(ProtocolError, "response"):
            write_check(bad_b)
        bad_id = copy.deepcopy(good)
        bad_id["downstream_b"][0]["id"] = 99
        with self.assertRaisesRegex(ProtocolError, "BID"):
            write_check(bad_id)
        missing_b = copy.deepcopy(good)
        missing_b["downstream_b"] = []
        with self.assertRaisesRegex(ProtocolError, "response"):
            write_check(missing_b)

    def test_axi_illegal_burst_crossing_4k_and_unaligned_and_wrong_size_rejected(self):
        wrong = sample_write(beats=2, addr=0xFE0)
        with self.assertRaisesRegex(ProtocolError, "4KiB"):
            write_check(wrong)
        wrong = sample_write(beats=1, addr=0x4010)
        with self.assertRaisesRegex(ProtocolError, "aligned"):
            write_check(wrong)
        wrong = sample_read()
        wrong["downstream_addresses"][0]["size"] = 5
        with self.assertRaisesRegex(ProtocolError, "SIZE"):
            read_check(wrong)
        wrong = sample_read()
        wrong["downstream_addresses"][0]["beats"] = 3
        with self.assertRaisesRegex(ProtocolError, "byte count"):
            read_check(wrong)

    def test_ready_valid_backpressure_stability_reset_and_watchdog(self):
        verified = stability(all_stalls(), require_all_channels=True)
        self.assertTrue(verified["reset_seen"])
        self.assertEqual(len(verified["backpressure_channels"]), 5)
        self.assertEqual(len(verified["handshaken_channels"]), 5)
        changed = all_stalls()
        changed[2]["channels"]["AW"]["payload"] = "different"
        with self.assertRaisesRegex(ProtocolError, "changed while stalled"):
            stability(changed)
        timed_out = all_stalls()
        with self.assertRaisesRegex(ProtocolError, "overflowing"):
            stability(timed_out, watchdog=2)
        with self.assertRaisesRegex(ProtocolError, "coverage"):
            stability(all_stalls()[0:3], require_all_channels=True)

    def test_unproven_host_only_trace_must_never_claim_vendor_success(self):
        suite = {"scope": "M05_D4_AXI256_TO128_TRANSACTION_TRACE_V1",
                 "origin": "SYNTHETIC_HOST_ONLY",
                 "cases": [sample_read(), sample_write(segmented=True, error=True)],
                 "cycles": all_stalls()}
        result = check_suite(suite, enforce_provenance=False)
        self.assertEqual(result["checked_cases"], 2)
        self.assertFalse(result["axi_vendor_adapter_functionally_proven"])
        self.assertFalse(result["provenance_is_externally_authenticated"])
        with self.assertRaisesRegex(ProtocolError, "not vendor verification"):
            check_suite(suite, enforce_provenance=True)
        forged = copy.deepcopy(suite)
        forged["origin"] = "GENUINE_VENDOR_XSIM_CAPTURE"
        with self.assertRaisesRegex(ProtocolError, "provenance"):
            check_suite(forged, enforce_provenance=True)
        duplicate = copy.deepcopy(suite)
        duplicate["cases"][1]["case_id"] = duplicate["cases"][0]["case_id"]
        with self.assertRaisesRegex(ProtocolError, "duplicate"):
            check_suite(duplicate, enforce_provenance=False)

    def test_cli_refuses_unattested_synthetic_trace(self):
        import json
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "unproven.json"
            source.write_text(json.dumps({
                "scope": "M05_D4_AXI256_TO128_TRANSACTION_TRACE_V1",
                "origin": "SYNTHETIC_HOST_ONLY",
                "cases": [sample_write()], "cycles": all_stalls(),
            }))
            dst = root / "new" / "result.json"
            dst.parent.mkdir()
            cmd = subprocess.run([
                sys.executable, str(ROOT / "scripts/m05_12d4_axi_byte_oracle.py"),
                "--trace-json", str(source), "--output", str(dst),
            ], capture_output=True, text=True)
            self.assertEqual(cmd.returncode, 2)
            self.assertFalse(dst.exists())


if __name__ == "__main__":
    unittest.main()
