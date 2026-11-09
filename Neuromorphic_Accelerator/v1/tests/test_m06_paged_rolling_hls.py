"""New autonomous HLS m_axi paged M05 rolling kernel: native exact parity.

Compiles the actual NEW m06_paged_rolling HLS synthesis source and original
UNCHANGED M04 lif arithmetic. Independently runs original UNCHANGED M05
rolling HLS source in separate binary, and M02 dense / M03 sparse Python.
This is C++ functional execution, NOT Vitis synthesis or generated RTL XSim.
"""
from __future__ import annotations
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m03_sparse_reference import evaluate_exact_sparse
from neuromorphic_accelerator_v1.m02_types import Network,Neuron,Synapse,InputCurrent


class M06PagedHLSNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler=shutil.which("g++") or shutil.which("c++")
        if not compiler:
            raise RuntimeError("M06 native new HLS paging tests REQUIRE C++17")
        cls.temp=tempfile.TemporaryDirectory(prefix="m06_paged_hls_")
        folder=Path(cls.temp.name)
        cls.new=str(folder/"m06_paged_rolling")
        cls.original=str(folder/"m05_accepted_rolling")
        cls.csim=str(folder/"m06_hls_native_csim")
        flags=[compiler,"-std=c++17","-O2","-Wall","-Wextra","-Werror",
               "-pedantic","-Wno-unknown-pragmas"]
        base=ROOT/"hls/m04_lif_eval/m04_eval.cpp"
        runs=(
            ([base,ROOT/"hls/m06_paged_rolling/m06_paged_rolling.cpp",
              ROOT/"hls/m06_paged_rolling/m06_paged_rolling_host_cli.cpp"],cls.new),
            ([base,ROOT/"hls/m05_rolling/m05_rolling.cpp",
              ROOT/"hls/m05_rolling/m05_rolling_host_cli.cpp"],cls.original),
            ([base,ROOT/"hls/m06_paged_rolling/m06_paged_rolling.cpp",
              ROOT/"hls/m06_paged_rolling/m06_paged_rolling_csim_tb.cpp"],
             cls.csim),
        )
        for sources,target in runs:
            p=subprocess.run(flags+[*(str(x) for x in sources),"-o",target],
                             capture_output=True,text=True)
            if p.returncode:
                raise RuntimeError("M06 new paged kernel native compilation failed:\n"+
                                   p.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @staticmethod
    def fixture(seed,n,ticks):
        rng=random.Random(seed)
        neurons=tuple(Neuron(initial_v=rng.randint(-8,8),
                             bias=rng.randint(-2,2),
                             threshold=rng.randint(4,13),
                             reset_v=-2) for _ in range(n))
        synapses=tuple(Synapse(pre=rng.randrange(n),post=rng.randrange(n),
                               weight=rng.randint(-15,15),
                               delay=rng.randint(1,8)) for _ in range(n//2))
        events=tuple(sorted((
            InputCurrent(tick=rng.randrange(ticks),
                         neuron=rng.randrange(n),
                         current=rng.randint(-20,20))
            for _ in range(n)),key=lambda e:e.tick))
        return Network(neurons,synapses,state_bits=16,
                       decay_num=3,decay_den=4),events

    @staticmethod
    def source(net,events,ticks,*,slots=None,base=0):
        head=[len(net.neurons),len(net.synapses),len(events),
              ticks,net.decay_num,net.decay_den]
        if slots is not None:
            head.extend((slots,base))
        rows=[" ".join(map(str,head))]
        rows.extend(f"{n.initial_v} {n.bias} {n.threshold} {n.reset_v}"
                    for n in net.neurons)
        rows.extend(f"{s.pre} {s.post} {s.weight} {s.delay}"
                    for s in net.synapses)
        rows.extend(f"{x.tick} {x.neuron} {x.current}" for x in events)
        return "\n".join(rows)+"\n"

    def call(self,exe,data):
        res=subprocess.run([exe],input=data,text=True,capture_output=True,
                           timeout=60)
        self.assertEqual(res.returncode,0,res.stderr+res.stdout[-300:])
        lines=res.stdout.splitlines()
        self.assertTrue(lines)
        status,count=map(int,lines[0].split())
        trace=tuple(tuple(map(int,row.split()))
                    for row in lines[1:1+count])
        self.assertEqual(len(trace),count)
        return status,trace,lines[1+count:]

    def compare_case(self,net,events,ticks,slots,base=0):
        dense=evaluate_dense(net,events,ticks=ticks)
        sparse=evaluate_exact_sparse(net,events,ticks=ticks)
        self.assertEqual(dense,sparse.trace)
        old_status,old_trace,old_tail=self.call(
            self.original,self.source(net,events,ticks))
        self.assertEqual(old_status,0)
        self.assertEqual(old_tail,[])
        status,actual,tail=self.call(
            self.new,self.source(net,events,ticks,slots=slots,base=base))
        self.assertEqual(status,0)
        self.assertEqual(actual,old_trace,"NEW paged m_axi HLS top changed "
                                        "accepted M05 rolling semantics")
        n=len(net.neurons)
        self.assertEqual(len(actual),n*ticks)
        for t in range(ticks):
            rows=actual[t*n:(t+1)*n]
            self.assertEqual(tuple(x[2] for x in rows),dense.voltage_rows[t])
            self.assertEqual(tuple(x[1] for x in rows if x[3]),dense.spike_rows[t])
            self.assertEqual(tuple(x[1] for x in rows if x[4]),
                             sparse.evaluated_ids_by_tick[t])
            self.assertTrue(all(x[5]==sparse.deliveries_by_tick[t] for x in rows))
        self.assertEqual(len(tail),3)
        self.assertEqual(tail[2],"GUARD PASS",
                         "no neighboring 4096 logical state rows may be modified")
        self.assertTrue(tail[0].startswith("CACHE "))
        numbers=list(map(int,tail[0].split()[1:]))
        self.assertEqual(len(numbers),8)
        access,hits,miss,evict,dirty,fill,evals,spikes=numbers
        self.assertEqual(access,hits+miss)
        self.assertEqual(miss,fill)
        self.assertGreaterEqual(fill, (n+15)//16)
        self.assertGreaterEqual(dirty,1)
        self.assertEqual(evals,sum(map(len,sparse.evaluated_ids_by_tick)))
        self.assertEqual(spikes,sum(map(len,dense.spike_rows)))
        self.assertTrue(tail[1].startswith("STATE "))
        final=bytes.fromhex(tail[1][6:])
        self.assertEqual(len(final),16*n)
        for i in range(n):
            row=final[16*i:16*(i+1)]
            self.assertEqual(int.from_bytes(row[:2],"little",signed=True),
                             dense.voltage_rows[-1][i])
            latest=[t for t,ids in enumerate(sparse.evaluated_ids_by_tick)
                    if i in ids]
            self.assertEqual(int.from_bytes(row[4:8],"little"),latest[-1]+1
                             if latest else 0)
            self.assertEqual(row[2:4],b"\x00\x00")
            self.assertEqual(row[8:],bytes(8))
        return numbers

    def test_same_source_native_vitis_hls_csim_testbench(self):
        p=subprocess.run([self.csim],capture_output=True,text=True,timeout=60)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("M06_PAGED_ROLLING_HLS_CSIM_PASS",p.stdout)

    def test_two_page_single_slot_parity_and_state(self):
        net,ev=self.fixture(101,32,16)
        x=self.compare_case(net,ev,16,slots=1)
        self.assertGreater(x[3],10)

    def test_eight_slot_large_capacity_pressure(self):
        net,ev=self.fixture(454,256,12)
        one=self.compare_case(net,ev,12,slots=1)
        eight=self.compare_case(net,ev,12,slots=8)
        self.assertGreater(one[3],eight[3])
        self.assertEqual(one[6],eight[6])

    def test_sixty_four_tick_recurrence_across_eight_wheel_wraps(self):
        net,ev=self.fixture(21,32,64)
        self.compare_case(net,ev,64,slots=1)

    def test_last_1024_neurons_of_full_4096_canonical_space(self):
        net,ev=self.fixture(99,1024,3)
        x=self.compare_case(net,ev,3,slots=8,base=3072)
        self.assertGreater(x[2],16)

    def test_high_address_small_tile_with_unmodified_neighbor_guard(self):
        net,ev=self.fixture(34,32,16)
        self.compare_case(net,ev,16,slots=1,base=4048)
        self.compare_case(net,ev,16,slots=8,base=2048)

    def test_zero_and_canceling_deliveries_exact(self):
        neurons=tuple(Neuron(threshold=30000) for _ in range(32))
        edges=(Synapse(0,16,32767,1),Synapse(0,16,-32768,1),
               Synapse(16,0,6,8))
        events=tuple(sorted((
            InputCurrent(0,0,32767),InputCurrent(0,0,32767),
            InputCurrent(1,1,-32768),InputCurrent(1,1,32767),
            InputCurrent(2,16,0),
        ),key=lambda e:e.tick))
        net=Network(neurons,edges,decay_num=1,decay_den=2,state_bits=16)
        self.compare_case(net,events,20,slots=1,base=3072)

    def test_out_of_range_address_and_slot_counts_fail_before_state_write(self):
        net,ev=self.fixture(77,32,4)
        for slots,base in ((0,0),(9,0),(1,4080),(1,1),(1,4096)):
            with self.subTest(slots=slots,base=base):
                status,rows,tail=self.call(
                    self.new,self.source(net,ev,4,slots=slots,base=base))
                self.assertNotEqual(status,0)
                self.assertEqual(rows,())
                self.assertEqual(tail,["GUARD PASS"])


if __name__=="__main__":
    unittest.main()
