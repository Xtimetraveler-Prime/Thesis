"""M06 real ORIGINAL M05-HLS-step integration with 1..8-slot native pager.

Compiles the UNMODIFIED accepted M05 streaming arithmetic top and M05 rolling
event scheduler in distinct native executables. The paged adapter invokes the
ORIGINAL m05_stream_eval for each admitted neuron and uses only bounded
cache-page records for neural previous voltage. Independent dense M02,
independent M03 exact sparse, and ORIGINAL M05 rolling top all must agree.
This is NATIVE C++ integration, NOT RTL or physical DDR.
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
from neuromorphic_accelerator_v1.m02_types import Network, Neuron, Synapse, InputCurrent
from neuromorphic_accelerator_v1.m03_sparse_reference import evaluate_exact_sparse


class OriginalM05PagedNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cc=shutil.which("g++") or shutil.which("c++")
        if not cc:
            raise RuntimeError("M06 original M05-native adapter tests REQUIRE C++17")
        cls.temp=tempfile.TemporaryDirectory(prefix="m06_m05_paged_")
        folder=Path(cls.temp.name)
        cls.paged=str(folder/"m06_original_m05_paged")
        cls.rolling=str(folder/"m05_original_rolling")
        base=[cc,"-std=c++17","-O2","-Wall","-Wextra","-Werror",
              "-pedantic","-Wno-unknown-pragmas"]
        m04=ROOT/"hls/m04_lif_eval/m04_eval.cpp"
        m05_stream=ROOT/"hls/m05_stream_eval/m05_stream.cpp"
        m05_rolling=ROOT/"hls/m05_rolling/m05_rolling.cpp"
        for sources,output in (
            ([m04,m05_stream,ROOT/"hls/m06_paged_adapter/m06_paged_adapter.cpp",
              ROOT/"hls/m06_paged_adapter/m06_paged_adapter_host_cli.cpp"],
             cls.paged),
            ([m04,m05_rolling,ROOT/"hls/m05_rolling/m05_rolling_host_cli.cpp"],
             cls.rolling),
        ):
            p=subprocess.run(base+[*(str(x) for x in sources),"-o",output],
                             capture_output=True,text=True)
            if p.returncode:
                raise RuntimeError(f"M06 original M05 compilation failed {output}:\n"
                                   +p.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @staticmethod
    def encoded(net,events,ticks,slots=None):
        header=[len(net.neurons),len(net.synapses),len(events),ticks,
                net.decay_num,net.decay_den]
        if slots is not None:
            header.append(slots)
        rows=[" ".join(map(str,header))]
        rows.extend(f"{n.initial_v} {n.bias} {n.threshold} {n.reset_v}"
                    for n in net.neurons)
        rows.extend(f"{e.pre} {e.post} {e.weight} {e.delay}"
                    for e in net.synapses)
        rows.extend(f"{e.tick} {e.neuron} {e.current}" for e in events)
        return "\n".join(rows)+"\n"

    def call(self,binary,data):
        result=subprocess.run([binary],input=data,text=True,
                              capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        rows=result.stdout.splitlines()
        self.assertTrue(rows,result.stderr)
        status,count=(int(x) for x in rows[0].split())
        parsed=tuple(tuple(int(x) for x in row.split())
                     for row in rows[1:1+count])
        self.assertEqual(len(parsed),count)
        return status,parsed,rows[1+count:]

    def check_network(self,net,events,ticks,*,slots):
        dense=evaluate_dense(net,events,ticks=ticks)
        sparse=evaluate_exact_sparse(net,events,ticks=ticks)
        self.assertEqual(dense,sparse.trace)
        ordered=tuple(sorted(events,key=lambda x:x.tick))
        status,actual,rest=self.call(
            self.paged,self.encoded(net,ordered,ticks,slots))
        self.assertEqual(status,0)
        original_status,old,old_tail=self.call(
            self.rolling,self.encoded(net,ordered,ticks))
        self.assertEqual(original_status,0)
        self.assertFalse(old_tail)
        self.assertEqual(actual,old,"paged ORIGINAL M05 stream must match "
                                 "UNCHANGED M05 rolling event engine")
        self.assertEqual(len(actual),len(net.neurons)*ticks)
        n=len(net.neurons)
        for tick in range(ticks):
            rows=actual[tick*n:(tick+1)*n]
            self.assertEqual(tuple(row[2] for row in rows),
                             dense.voltage_rows[tick])
            self.assertEqual(tuple(row[1] for row in rows if row[3]),
                             dense.spike_rows[tick])
            self.assertEqual(tuple(row[1] for row in rows if row[4]),
                             sparse.evaluated_ids_by_tick[tick])
            self.assertTrue(all(row[5]==sparse.deliveries_by_tick[tick]
                                for row in rows))
        self.assertEqual(len(rest),2)
        self.assertTrue(rest[0].startswith("CACHE "))
        c=list(map(int,rest[0].split()[1:]))
        self.assertEqual(len(c),11)
        access,hit,miss,evict,writeback,fill,rd,wr,calls,evals,spikes=c
        self.assertEqual(access,hit+miss)
        self.assertEqual(miss,fill)
        self.assertEqual(rd,256*fill)
        self.assertEqual(wr,256*writeback)
        self.assertEqual(calls,evals)
        self.assertEqual(evals,sum(len(ids) for ids in sparse.evaluated_ids_by_tick))
        self.assertEqual(spikes,sum(map(len,dense.spike_rows)))
        self.assertTrue(rest[1].startswith("STATE "))
        canonical=bytes.fromhex(rest[1][6:])
        self.assertEqual(len(canonical),16*n)
        for i in range(n):
            state=canonical[16*i:16*(i+1)]
            self.assertEqual(int.from_bytes(state[:2],"little",signed=True),
                             dense.voltage_rows[-1][i])
            prior=[t for t,row in enumerate(sparse.evaluated_ids_by_tick)
                   if i in row]
            self.assertEqual(int.from_bytes(state[2:6],"little"),
                             (prior[-1]+1) if prior else 0)
            self.assertEqual(state[6:],bytes(10))
        self.assertLessEqual(fill-writeback,fill)
        return c

    @staticmethod
    def make_net(seed,*,n,ticks):
        rng=random.Random(seed)
        cells=tuple(Neuron(initial_v=rng.randint(-4,4),
                           bias=rng.randint(-2,2),
                           threshold=rng.randint(3,8),
                           reset_v=-2) for _ in range(n))
        edges=tuple(Synapse(pre=rng.randrange(n),post=rng.randrange(n),
                            weight=rng.randint(-7,7),
                            delay=rng.randint(1,8)) for _ in range(n//2))
        events=tuple(sorted((
            InputCurrent(tick=rng.randrange(ticks),neuron=rng.randrange(n),
                         current=rng.randint(-12,12))
            for _ in range(2*n)),key=lambda x:x.tick))
        return Network(cells,edges,state_bits=16,decay_num=3,decay_den=4),events

    def test_one_slot_forces_dirty_evictions_and_matches_both_real_m05_and_m02(self):
        net,ev=self.make_net(77,n=32,ticks=12)
        counter=self.check_network(net,ev,12,slots=1)
        self.assertGreater(counter[3],10)
        self.assertGreater(counter[4],10)

    def test_eight_slot_budget_vs_one_slot_on_sixteen_page_neural_network(self):
        net,ev=self.make_net(414,n=256,ticks=12)
        one=self.check_network(net,ev,12,slots=1)
        eight=self.check_network(net,ev,12,slots=8)
        # A sequential full-network sweep through 16 pages gives a fully
        # associative 8-slot LRU no hits across tick boundaries: all 16
        # distinct pages are touched before any is revisited. This is an
        # important non-local workload, NOT evidence the 8-slot LRU is broken.
        self.assertEqual(one[2],eight[2])
        self.assertGreater(one[3],eight[3])
        # All admitted pages are dirty and must eventually reach canonical
        # memory even if the 8-slot cache postpones their writebacks.
        # Identical completed dirty-writeback counts are thus legal.
        self.assertGreaterEqual(one[4],eight[4])
        self.assertGreater(eight[2],8)
        self.assertGreater(one[3],20)

    def test_max_sixty_four_ticks_delay8_recurrence_and_watermark(self):
        net,ev=self.make_net(21,n=32,ticks=64)
        one=self.check_network(net,ev,64,slots=1)
        self.assertGreater(one[4],20)

    def test_zero_cancellation_saturation_and_recurrent_parallel_edges(self):
        cells=tuple(Neuron(threshold=10000,reset_v=0) for _ in range(32))
        edges=(Synapse(0,16,32767,1), Synapse(0,16,-32768,1),
               Synapse(16,0,4,8),Synapse(0,0,-5,2))
        events=tuple(sorted((
            InputCurrent(0,0,32767),InputCurrent(0,0,32767),
            InputCurrent(1,1,-32768), InputCurrent(2,16,0),
            InputCurrent(7,0,32767),InputCurrent(7,0,-32768),
        ),key=lambda x:x.tick))
        net=Network(cells,edges,state_bits=16,decay_num=1,decay_den=2)
        self.check_network(net,events,16,slots=1)

    def test_invalid_shape_fails_before_paging_or_partial_trace(self):
        net,ev=self.make_net(8,n=32,ticks=4)
        for bad_slots in (0,9):
            status,rows,rest=self.call(self.paged,
                self.encoded(net,ev,4,bad_slots))
            self.assertNotEqual(status,0)
            self.assertEqual(rows,())
            self.assertEqual(rest[0],"CACHE 0 0 0 0 0 0 0 0 0 0 0")
            self.assertEqual(rest[1],"STATE ")

    def test_one_slot_and_eight_slots_produce_same_full_trace(self):
        net,ev=self.make_net(121,n=128,ticks=9)
        one=self.check_network(net,ev,9,slots=1)
        eight=self.check_network(net,ev,9,slots=8)
        self.assertGreater(one[2],eight[2])


if __name__=="__main__":
    unittest.main()
