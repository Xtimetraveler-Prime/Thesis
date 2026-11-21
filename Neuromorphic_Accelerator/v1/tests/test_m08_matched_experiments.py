"""M08.5 exact original-fixture and fail-closed comparator tests (NO BOARD)."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import m08_matched_contract as cli
import m08_paged_m06_lif_fixture as original
from neuromorphic_accelerator_v1.m08_matched_experiments import (
    BIT_D2C, BIT_D2E, BIT_M084, CELLS, ContractError, build_contract,
    check_contract, classify_ddr_observation, compare_structure,
    witness_from_original,
)


def _new() -> dict:
    return cli.make_report()


def _future(cell: str) -> dict:
    """SYNTHETIC metadata only; never a physical or performance evidence row."""
    return dict(
        cell=cell,
        neural_witness_sha256="a"*64,
        ordered_event_stream_sha256="b"*64,
        precision_and_arithmetic="M06_SIGNED16_TRUNC_ZERO_3_4",
        synapse_and_event_work_sha256="c"*64,
        input_ingress="RAW_17_EVENTS_FABRIC_FIFO_TICK_SERVICE",
        event_delivery_order_sha256="d"*64,
        timing_boundary="PL_FIRST_COMMIT_TO_LAST_RESULT_SAME_CLOCK",
        resource_envelope_sha256="e"*64,
        new_owner_raw_evidence_verified=True,
        actual_sparse_neuron_skip_verified=True,
        ddr_ownership_audited=False,
    )


class M085OriginalFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = _new()

    def test_exact_m02_m03_oracle_input_and_six_page_layout(self):
        doc = self.report
        check_contract(doc)
        witness = doc["same_original_m02_m03_neural_oracle"]
        self.assertEqual(witness["state_bits"], 16)
        self.assertEqual((witness["leak_num"], witness["leak_den"]), (3, 4))
        self.assertEqual(witness["logical_neurons_per_page"], [6, 6, 6, 6, 6, 2])
        self.assertEqual(witness["raw_event_count"], 17)
        self.assertEqual(len(witness["host_input_neural_page_sha256"]), 6)
        self.assertEqual(len(original.golden_words()), 512)
        self.assertEqual(len(witness["independent_reference_source_sha256"]), 6)
        self.assertTrue(witness["oracle_words_never_loaded_as_inputs"])
        for i in range(6):
            self.assertTrue(original.audit_page(original.neural_words(i), i, 0))
        with self.assertRaises(original.Reject):
            changed = list(original.neural_words(0))
            changed[0] ^= 1
            original.audit_page(tuple(changed), 0, 0)

    def test_historical_d2c_d2e_m084_not_speedup_measurements(self):
        rows = self.report["rows"]
        self.assertEqual([x["cell"] for x in rows], list(CELLS))
        self.assertEqual([x["original_bitstream_sha256"] for x in rows[:3]],
                         [BIT_D2C, BIT_D2E, BIT_M084])
        self.assertEqual([x["historical_checked_quantities"] for x in rows],
                         [384, 512, 512, 0, 0, 0])
        self.assertEqual(rows[1]["fabric_current_checks"], 128)
        self.assertEqual(rows[2]["host_current_checks"], 128)
        self.assertEqual(rows[2]["fabric_current_checks"], 0)
        self.assertEqual(rows[2]["physical_neural_computations_checked"], 384)
        self.assertEqual(rows[2]["physical_page_dispatches"], 24)
        self.assertEqual(rows[2]["resident_page_banks"], 1)
        self.assertNotEqual(rows[0]["input_ingress"], rows[1]["input_ingress"])
        self.assertEqual(rows[0]["input_ingress"], rows[2]["input_ingress"])
        self.assertTrue(all(r["actual_sparse_neuron_skip_verified"] is False for r in rows))
        self.assertEqual(self.report["full_matched_performance_pairs_available"], 0)
        for row in rows:
            self.assertFalse(row["quantitatively_comparable"])
            self.assertFalse(row["original_owner_evidence_reopened_here"])
            self.assertFalse(row["real_ddr_ownership_verified"])
            for k in ("actual_ps_pl_ddr_read_bytes", "actual_ps_pl_ddr_write_bytes",
                      "actual_ps_pl_ddr_transactions", "measured_end_to_end_ns",
                      "measured_pl_active_cycles", "actual_jtag_host_transferred_bytes"):
                self.assertIsNone(row[k], k)
        self.assertEqual(self.report["ddr_readiness"]["status"], "UNKNOWN")

    def test_source_witness_rejects_wrong_event_count_or_oracle(self):
        _, _, events, _, _, _, _ = original.source()
        pages = tuple(original.neural_words(i) for i in range(6))
        source_hashes = self.report["same_original_m02_m03_neural_oracle"][
            "independent_reference_source_sha256"]
        args = dict(
            neuron_pages=pages, edge_page=original.edge_words(),
            event_records=tuple((e.tick, e.neuron, e.current) for e in events),
            golden_words=original.golden_words(),
            reference_source_sha256=source_hashes,
        )
        for k, bad in (
            ("neuron_pages", pages[:5]),
            ("event_records", args["event_records"][:-1]),
            ("golden_words", args["golden_words"][:-1]),
            ("edge_page", args["edge_page"][:-1]),
            ("reference_source_sha256", {"fake": "a"*64}),
        ):
            changed = dict(args, **{k: bad})
            if k == "reference_source_sha256":
                # The source constructor accepts generic source manifests;
                # the report's stricter independent-reference gate rejects this.
                witness = witness_from_original(**changed)
                with self.assertRaises(ContractError):
                    build_contract(witness)
            else:
                with self.assertRaises(ContractError):
                    witness_from_original(**changed)

    def test_mutated_reference_and_hardware_counts_cannot_pass(self):
        attacks = (
            ("same_original_m02_m03_neural_oracle", "state_bits", 24),
            ("same_original_m02_m03_neural_oracle", "raw_event_count", 16),
            ("same_original_m02_m03_neural_oracle", "ordered_event_stream_sha256", "bad"),
        )
        for section, key, val in attacks:
            broken = deepcopy(self.report)
            broken[section][key] = val
            with self.subTest(key=key), self.assertRaises(ContractError):
                check_contract(broken)
        mutations = (
            (2, "host_current_checks", 0),
            (2, "fabric_voltage_checks", 127),
            (2, "physical_page_dispatches", 23),
            (2, "original_bitstream_sha256", "forged"),
            (2, "measured_end_to_end_ns", 1),
            (2, "real_ddr_ownership_verified", True),
            (1, "actual_sparse_neuron_skip_verified", True),
            (4, "availability", "HISTORICAL_PHYSICAL_NOT_MATCHED"),
            (4, "actual_ps_pl_ddr_read_bytes", 0),
        )
        for index, key, val in mutations:
            broken = deepcopy(self.report)
            broken["rows"][index][key] = val
            with self.subTest(index=index, key=key), self.assertRaises(ContractError):
                check_contract(broken)

    def test_ddr_inventory_never_grants_ownership(self):
        self.assertEqual(classify_ddr_observation()["status"], "UNKNOWN")
        self.assertEqual(classify_ddr_observation(
            {"candidate_dma_heaps_not_ownership": True,
             "physical_dma_ready": False})["status"], "UNKNOWN")
        for misleading in ({"physical_dma_ready": True},
                           {"AVAILABLE_VERIFIED": True},
                           {"owner_verified_path_absent": True}):
            with self.subTest(misleading=misleading), self.assertRaises(ContractError):
                classify_ddr_observation(misleading)
        result = classify_ddr_observation(
            {"owner_verified_path_absent": True, "owner_absence_receipt_sha256": "f"*64})
        self.assertEqual(result["status"], "NOT_AVAILABLE")
        self.assertFalse(result["available_verified"])
        with self.assertRaises(ContractError):
            classify_ddr_observation("device exists")

    def test_original_historical_rows_rejected_as_matched_physical_result(self):
        first, second, paged = self.report["rows"][:3]
        for a, b, axis in (
            (first, second, "execution"),
            (first, paged, "placement"),
            (second, paged, "placement"),
        ):
            with self.subTest(axis=axis), self.assertRaises(ContractError):
                compare_structure(a, b, axis=axis)

    def test_synthetic_future_metadata_structural_positive_and_mutations(self):
        timestep = _future("timestep/onchip")
        event = _future("event/onchip")
        outcome = compare_structure(timestep, event, axis="execution")
        self.assertEqual(outcome["status"], "STRUCTURALLY_MATCHED_ONLY_NO_LATENCY_CLAIM")
        self.assertIsNone(outcome["speedup"])
        self.assertFalse(outcome["performance_comparable"])

        paged = _future("timestep/jtag_host_paged")
        outcome = compare_structure(timestep, paged, axis="placement")
        self.assertEqual(outcome["axis"], "placement")
        for key, bad in (
            ("ordered_event_stream_sha256", "0"*64),
            ("neural_witness_sha256", "1"*64),
            ("precision_and_arithmetic", "signed24"),
            ("synapse_and_event_work_sha256", "2"*64),
            ("input_ingress", "HOST_COALESCED_17_INPUT_CURRENTS"),
            ("event_delivery_order_sha256", "3"*64),
            ("timing_boundary", "HOST_END_TO_END"),
            ("resource_envelope_sha256", "4"*64),
            ("new_owner_raw_evidence_verified", False),
        ):
            altered = dict(paged, **{key: bad})
            with self.subTest(key=key), self.assertRaises(ContractError):
                compare_structure(timestep, altered, axis="placement")
        with self.assertRaises(ContractError):
            compare_structure(timestep, paged, axis="execution")
        with self.assertRaises(ContractError):
            compare_structure(timestep, event, axis="placement")
        with self.assertRaises(ContractError):
            compare_structure(timestep, event, axis="speedup")
        with self.assertRaises(ContractError):
            compare_structure(timestep, dict(event, actual_sparse_neuron_skip_verified=False),
                              axis="execution")
        ddr = _future("timestep/ps_pl_ddr")
        with self.assertRaises(ContractError):
            compare_structure(timestep, ddr, axis="placement")
        self.assertEqual(compare_structure(timestep, dict(ddr, ddr_ownership_audited=True),
                                           axis="placement")["speedup"], None)

    def test_cli_json_source_only_and_exclusive_no_overwrite(self):
        cmd = [sys.executable, str(ROOT / "scripts/m08_matched_contract.py"), "--source-only"]
        out = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        decoded = json.loads(out.stdout)
        check_contract(decoded)
        self.assertFalse(decoded["new_fpga_run_performed"])
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "contract.json"
            a = subprocess.run(cmd + ["--output", str(p)], capture_output=True, text=True)
            self.assertEqual(a.returncode, 0, a.stderr)
            original_bytes = p.read_bytes()
            b = subprocess.run(cmd + ["--output", str(p)], capture_output=True, text=True)
            self.assertNotEqual(b.returncode, 0)
            self.assertEqual(p.read_bytes(), original_bytes)


if __name__ == "__main__":
    unittest.main()
