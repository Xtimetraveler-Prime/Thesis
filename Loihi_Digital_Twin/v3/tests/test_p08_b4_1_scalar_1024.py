"""P08-B4.1 full 1,024 source/oracle admission: strictly PC-only tests.

Synthetic tests NEVER claim physical results, never touch KV260, never
download MNIST official TEST, train, run Vitis or alter accepted B3 files.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b4_1_scalar_shard as shard
import p08_b4_1_merge_scalar_1024 as merge

def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def row(i:int,rawhash:str,wirehash:str)->dict:
    return {
        "ordinal":i,
        "TRAIN_source_index":10000+i,
        "raw_pixels_sha256":rawhash,
        "original_27core_ingress_sha256":wirehash,
        "expected_prediction":i%10,
        "expected_external_current":100+i,
        "expected_source_spikes":200+i,
        "expected_captured_packets":300+i,
        "expected_inserted_next":400+i,
        "expected_dispatches":702,
        "expected_barriers":26,
        "expected_trace_compartments_per_tick":1010,
        "expected_output_spike_counts":[i%7]*10,
        "expected_all_26_ticks_1010_neuron_FNV64":f"0x{i:016X}",
        "expected_per_tick_neuron_FNV64":[f"0x{(i+t):016X}" for t in range(26)],
        "original_scalar_trace_sha256":sha(str(i).encode()),
    }

@pytest.fixture
def admitted_synthetic_1024(tmp_path,monkeypatch):
    """Entire dataset/64 signed-shard structure is synthetic fixture."""
    ingest=tmp_path/"original_ingress";ingest.mkdir()
    shards=tmp_path/"independent_64_shards";shards.mkdir()
    raw=b"".join(bytes([i%256])*784 for i in range(1024))
    (ingest/shard.RAW_FILENAME).write_bytes(raw)
    source=[]
    wire=[]
    frames=[]
    for i in range(1024):
        rsha=sha(raw[i*784:(i+1)*784])
        wsha=sha(b"wire-provenance-"+i.to_bytes(4,"little"))
        source.append({
            "frame":i,"TRAIN_source_index":10000+i,
            "raw_pixels_sha256":rsha,
            "B24_27core_B13_ingress_sha256":wsha,
            "encoded_wire_bytes":123216,
        })
        wire.append(wsha)
        frames.append(row(i,rsha,wsha))
    ledger=("".join(s+"\n" for s in wire)).encode()
    (ingest/shard.HASH_FILENAME).write_bytes(ledger)
    manifest={
        "schema":"p08-b2-1-original27-matched1024-train-only-ingress-v1",
        "count":1024,
        "original_OFFICIAL_MNIST_TEST":"SEALED_NOT_ACCESSED",
        "frames":source,
    }
    mraw=json.dumps(manifest,sort_keys=True).encode()
    (ingest/shard.MANIFEST_FILENAME).write_bytes(mraw)
    original=tmp_path/"first16.json"
    original.write_text(json.dumps({"frames":frames[:16]}))
    monkeypatch.setattr(merge.first16,"ORACLE_SHA",sha(original.read_bytes()))
    monkeypatch.setattr(merge.first16,"source_oracle",
                        lambda _path: {"frames":frames[:16]})
    monkeypatch.setattr(merge.baseline,"RAW_POOL_SHA",sha(raw))
    monkeypatch.setattr(merge.baseline,"B2_MANIFEST_SHA",sha(mraw))
    monkeypatch.setattr(merge.baseline,"B2_INGRESS_LEDGER_SHA",sha(ledger))
    for index in range(64):
        obj={
            "schema":shard.SCHEMA,
            "dataset_count":1024,
            "count":16,
            "original_first16_scalar_sha256":merge.first16.ORACLE_SHA,
            "original_raw1024_sha256":merge.baseline.RAW_POOL_SHA,
            "original_1024_ingress_manifest_sha256":merge.baseline.B2_MANIFEST_SHA,
            "original_1024_wire_SHA_ledger_sha256":merge.baseline.B2_INGRESS_LEDGER_SHA,
            "original_27core_p02_sha256":
                "3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e",
            "original_full1024_A53_ELF_expected_sha256":merge.baseline.B23_ELF_SHA,
            "original_full1024_A53_map_expected_sha256":merge.baseline.B23_MAP_SHA,
            "independent_KV260_physical_execution":False,
            "official_MNIST_TEST":"SEALED_NOT_ACCESSED",
            "shard":index,"start_ordinal":index*16,
            "end_ordinal_exclusive":index*16+16,
            "original_b24_source_sha256":
                "0a3ec838a9f95a73de118e37f31d596bf38e63cd8cf82e6f5c9d0dd48b22797a",
            "original_b24_compiled_sha256":
                "02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a",
            "frames":frames[index*16:(index+1)*16],
        }
        (shards/merge.SHARD_PATTERN.format(index)).write_text(
            json.dumps(obj,sort_keys=True))
    return ingest,shards,original,frames

def test_all_1024_independent_shard_consolidation_pc_only(
        admitted_synthetic_1024,tmp_path):
    ingest,shards,first16,frames=admitted_synthetic_1024
    out=tmp_path/"new_full_original_1024.json"
    result=merge.merge(shards,ingest,first16,out)
    assert out.is_file()
    assert result["count"]==1024
    assert len(result["frames"])==1024
    assert result["frames"][0]==frames[0]
    assert result["frames"][1023]==frames[1023]
    assert len(result["source_shards_sha256"])==64
    assert result["actual_KV260_1024_physical_execution"] is False
    assert result["physical_latency_accepted"] is False
    assert result["official_MNIST_TEST"]=="SEALED_NOT_ACCESSED"
    with pytest.raises(merge.MergeNoGo,match="new external"):
        merge.merge(shards,ingest,first16,out)

@pytest.mark.parametrize("tamper",[
    "missing_shard","extra_shard","duplicated_ordinal","modified_raw_source",
    "modified_ingress_wire","modified_first16",
    "different_model","partial_shard","fake_board",
])
def test_fail_closed_on_1024_source_or_shard_drift(
        admitted_synthetic_1024,tmp_path,tamper):
    ingest,shards,first16,frames=admitted_synthetic_1024
    path=shards/merge.SHARD_PATTERN.format(23)
    obj=json.loads(path.read_text())
    if tamper=="missing_shard":
        path.unlink()
    elif tamper=="extra_shard":
        (shards/"unexpected.json").write_text("{}")
    elif tamper=="duplicated_ordinal":
        obj["frames"][9]["ordinal"]=obj["frames"][8]["ordinal"]
        path.write_text(json.dumps(obj))
    elif tamper=="modified_raw_source":
        pixels=ingest/shard.RAW_FILENAME
        pixels.write_bytes(bytes(pixels.stat().st_size))
    elif tamper=="modified_ingress_wire":
        obj["frames"][0]["original_27core_ingress_sha256"]="0"*64
        path.write_text(json.dumps(obj))
    elif tamper=="modified_first16":
        original=shards/merge.SHARD_PATTERN.format(0)
        old=json.loads(original.read_text())
        old["frames"][1]["expected_prediction"]=9
        original.write_text(json.dumps(old))
    elif tamper=="different_model":
        obj["original_b24_compiled_sha256"]="0"*64
        path.write_text(json.dumps(obj))
    elif tamper=="partial_shard":
        obj["frames"]=obj["frames"][:15]
        path.write_text(json.dumps(obj))
    elif tamper=="fake_board":
        obj["independent_KV260_physical_execution"]=True
        path.write_text(json.dumps(obj))
    with pytest.raises(merge.MergeNoGo):
        merge.merge(shards,ingest,first16,tmp_path/"should_not_exist.json")
    assert not (tmp_path/"should_not_exist.json").exists()

def test_all_1024_oracle_sources_are_readonly_and_board_sealed():
    root=ROOT/"scripts"
    for source in ("p08_b4_1_scalar_shard.py",
                   "p08_b4_1_merge_scalar_1024.py"):
        content=(root/source).read_text()
        assert "xsdb" not in content.lower() or "no xsdb" in content.lower()
        assert "subprocess." not in content
        assert "create_branch" not in content
        assert "TEST" in content
    assert shard.SHARDS==64
    assert shard.SHARD_SIZE==16
    assert merge.SCHEMA.endswith("full1024-independent-scalar-oracle-v1")

def test_strict_1024_frame_structure_admission_rejects_malformed():
    original=row(1023,"a"*64,"b"*64)
    source={"TRAIN_source_index":11023,"raw_pixels_sha256":"a"*64}
    merge.check_frame(original,1023,source,"b"*64)
    altered=dict(original)
    altered["expected_per_tick_neuron_FNV64"]=original[
        "expected_per_tick_neuron_FNV64"][:25]
    with pytest.raises(merge.MergeNoGo):
        merge.check_frame(altered,1023,source,"b"*64)
    altered=dict(original)
    altered["expected_output_spike_counts"]=[0]*9
    with pytest.raises(merge.MergeNoGo):
        merge.check_frame(altered,1023,source,"b"*64)
    altered=dict(original)
    altered["expected_dispatches"]=26
    with pytest.raises(merge.MergeNoGo):
        merge.check_frame(altered,1023,source,"b"*64)
