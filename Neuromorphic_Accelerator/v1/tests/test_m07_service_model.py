"""M07.5 SOURCE-ONLY service trace and queue contract; no bus timing claims."""
from __future__ import annotations
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from neuromorphic_accelerator_v1.m07_service_model import (
    ServiceAssumptions, ServiceSweepPlan, TraceImage,
    _ingress_model, _service_model, evaluate_service_case, run_service_sweep,
)
from neuromorphic_accelerator_v1.m06_block_residency import Geometry
from neuromorphic_accelerator_v1.m03_workloads import WorkloadSpec,build_workload


def trial(*,seed=17,locality="clustered",events=4):
    w=build_workload(WorkloadSpec(
        neuron_count=16,active_roles=4,fanout_per_active=2,
        external_events_per_tick=events,ticks=4,seed=seed,locality=locality))
    g=Geometry(logical_neurons=16,bytes_per_neuron=16,
               neurons_per_block=4,resident_budget_bytes=64,
               max_model_transfer_bytes=32)
    return w,g


def plan(**changes):
    return replace(ServiceSweepPlan(
        neurons=16,active_roles=4,fanout=2,ticks=4,
        seeds=(17,),batches=(1,2),synapse_record_bytes=(4,8),
        block_neurons=4,resident_slots=1),**changes)


class M07ServiceBoundaryTests(unittest.TestCase):
    def test_real_accepted_m06_trace_bytes_chunks_and_b_order_source_only(self):
        w,g=trial()
        results={}
        for policy in ("direct","lru","activity_history"):
            z=evaluate_service_case(
                w,g,policy=policy,batch_width=2,
                synapse_record_bytes=8,assumptions=ServiceAssumptions())
            results[policy]=z
            self.assertTrue(z["neural_and_final_canonical_parity"])
            self.assertEqual(z["cache_counters"]["accesses"],2*z["evaluations"])
            t=z["transfers"]
            self.assertEqual(t["state_read_bytes"],
                             z["cache_counters"]["read_bytes"])
            self.assertEqual(t["state_write_bytes"],
                             z["cache_counters"]["write_bytes"])
            self.assertEqual(t["read_chunks"],
                             z["cache_counters"]["read_transactions"])
            self.assertEqual(t["write_chunks"],
                             z["cache_counters"]["write_transactions"])
            self.assertEqual(t["completed_software_block_reads"],
                             z["cache_counters"]["misses"])
            self.assertEqual(t["assumed_max_concurrent_software_block_transfer"],1)
            self.assertIsNone(t["actual_axi_b_before_ar_cycles"])
            self.assertIsNone(t["actual_outstanding_axi_requests"])
            self.assertIsNone(t["actual_physical_ddr_bytes"])
            self.assertEqual(z["ingress_queue"]["arrivals"],z["delivered_events"])
            self.assertEqual(z["ingress_queue"]["consumed"],z["delivered_events"])
            self.assertIsNone(z["actual_run_cycles"])
            self.assertIsNone(z["actual_runtime_ns"])
        self.assertEqual(results["direct"]["canonical_trace_sha256"],
                         results["lru"]["canonical_trace_sha256"])
        self.assertEqual(results["activity_history"]["canonical_trace_sha256"],
                         results["lru"]["canonical_trace_sha256"])
        self.assertEqual(results["direct"]["evaluations"],results["lru"]["evaluations"])
        self.assertGreater(results["direct"]["transfers"][
            "source_order_write_then_read_guards"],0)

    def test_batch_and_synapse_format_sweep_do_not_change_neural_state(self):
        r=run_service_sweep(plan(),ServiceAssumptions())
        self.assertEqual(r["number_of_matched_cases"],24)
        self.assertEqual(len(r["rows"]),2)
        self.assertFalse(r["actual_hardware_performance_measured"])
        self.assertFalse(r["physical_ddr_executed"])
        self.assertTrue(r["no_vendor_hls_rtl_executed"])
        self.assertEqual(r["rows"][0]["trace_sha256"],r["rows"][1]["trace_sha256"])
        for row in r["rows"]:
            cases=row["cases"]
            self.assertEqual(len(cases),12)
            for policy in ("direct","lru","activity_history"):
                p=[x for x in cases if x["policy"]==policy]
                self.assertEqual(len({x["canonical_trace_sha256"] for x in p}),1)
                self.assertEqual(len({x["transfers"]["state_read_bytes"]
                                      for x in p}),1)
                self.assertEqual(len({x["transfers"]["state_write_bytes"]
                                      for x in p}),1)
                a=next(x for x in p if x["batch_width"]==1
                       and x["synapse_record_bytes_hypothetical"]==4)
                b=next(x for x in p if x["batch_width"]==1
                       and x["synapse_record_bytes_hypothetical"]==8)
                self.assertEqual(2*a["synapse_ddr_analytical_bytes_not_issued"],
                                 b["synapse_ddr_analytical_bytes_not_issued"])
                self.assertEqual(a["modeled_serialized_complete_run_cycles_assumed"],
                                 b["modeled_serialized_complete_run_cycles_assumed"])
                self.assertIsNone(b["resource_utilization"])

    def test_zero_event_queue_and_narrow_fifo_progress(self):
        cfg=ServiceAssumptions(fifo_depth_events=1,enqueue_batch_setup_cycles=2)
        x=_ingress_model((0,8,0,1),batch_width=8,config=cfg)
        self.assertEqual(x["arrivals"],9)
        self.assertEqual(x["consumed"],9)
        self.assertEqual(x["peak_occupancy_events"],1)
        self.assertGreaterEqual(x["queue_model_cycles"],9)
        self.assertLessEqual(x["peak_occupancy_events"],cfg.fifo_depth_events)
        self.assertEqual(x["ticks_with_events"],2)
        self.assertEqual(_ingress_model((0,0),batch_width=1,config=cfg)[
            "queue_model_cycles"],0)
        w,g=trial(events=0)
        z=evaluate_service_case(w,g,policy="lru",batch_width=1,
                                synapse_record_bytes=4,assumptions=cfg)
        self.assertEqual(z["ingress_queue"]["consumed"],z["delivered_events"])

    def test_validation_rejects_bad_bounds_mismatches_and_fabricated_trace(self):
        w,g=trial()
        with self.assertRaises(ValueError):
            evaluate_service_case(w,g,policy="future",batch_width=1,
                                  synapse_record_bytes=8,assumptions=ServiceAssumptions())
        for bad in (0,True,-2,4097,1.5):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                _ingress_model((1,),batch_width=bad,config=ServiceAssumptions())
        for key,value in (("fifo_depth_events",0),("history_depth",4097),
                          ("write_b_ack_cycles",True),
                          ("read_transfer_chunk_cycles",0)):
            with self.subTest(key=key),self.assertRaises(ValueError):
                ServiceAssumptions(**{key:value}).validate()
        for kwargs in ({"seeds":(17,17)},{"batches":(0,)},
                       {"synapse_record_bytes":(8,4)},
                       {"resident_slots":True}, {"block_neurons":3}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                run_service_sweep(plan(**kwargs),ServiceAssumptions())
        with self.assertRaises(AssertionError):
            _service_model([{"op":"R","page":0,"chunks":1,
                             "bytes":2}],g,ServiceAssumptions())
        with self.assertRaises(AssertionError):
            _service_model([{"op":"R","page":0,"chunks":1,
                             "bytes":64}],g,ServiceAssumptions())
        with self.assertRaises(AssertionError):
            _service_model([{"op":"BOGUS","page":0,"chunks":2,
                             "bytes":64}],g,ServiceAssumptions())

    def test_modeled_cycle_accounting_changes_only_with_assumptions(self):
        w,g=trial()
        a=ServiceAssumptions(read_transfer_chunk_cycles=5,
                             write_transfer_chunk_cycles=7)
        b=replace(a,read_transfer_chunk_cycles=11,
                  write_transfer_chunk_cycles=17)
        x=evaluate_service_case(w,g,policy="lru",batch_width=1,
                                synapse_record_bytes=8,assumptions=a)
        y=evaluate_service_case(w,g,policy="lru",batch_width=1,
                                synapse_record_bytes=8,assumptions=b)
        self.assertEqual(x["transfers"]["state_read_bytes"],
                         y["transfers"]["state_read_bytes"])
        self.assertEqual(x["canonical_trace_sha256"],y["canonical_trace_sha256"])
        expected=(6*x["transfers"]["read_chunks"]
                  +10*x["transfers"]["write_chunks"])
        self.assertEqual(y["modeled_serialized_complete_run_cycles_assumed"]-
                         x["modeled_serialized_complete_run_cycles_assumed"],
                         expected)
        self.assertIsNone(y["actual_run_cycles"])

    def test_cli_repeatable_exclusive_artifact_with_source_hash(self):
        cmd=[sys.executable,str(ROOT/"scripts/m07_service_closeout.py"),
             "--neurons","16","--active-roles","4","--ticks","4",
             "--seeds","17","--batches","1,2","--synapse-record-bytes","4,8"]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);a,b=p/"a.json",p/"b.json"
            first=subprocess.run(cmd+["--output",str(a)],
                    capture_output=True,text=True)
            self.assertEqual(first.returncode,0,first.stderr)
            second=subprocess.run(cmd+["--output",str(b)],
                    capture_output=True,text=True)
            self.assertEqual(second.returncode,0,second.stderr)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            overwritten=subprocess.run(cmd+["--output",str(a)],
                    capture_output=True,text=True)
            self.assertNotEqual(overwritten.returncode,0)
            self.assertEqual(a.read_bytes(),b.read_bytes())
            z=json.loads(a.read_text())
            self.assertEqual(z["number_of_matched_cases"],24)
            self.assertEqual(len(z["source_sha256"]),10)
            self.assertTrue(all(len(v)==64 for v in z["source_sha256"].values()))
            self.assertFalse(z["actual_hardware_performance_measured"])


if __name__=="__main__":
    unittest.main()
