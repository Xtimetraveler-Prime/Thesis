"""Synthetic-only layout / atomic packer gate; no actual B2.4 local snapshot in CI."""
import hashlib
import importlib.util
from pathlib import Path
import struct

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "p07_b4m_frozen_inputs",ROOT/"scripts/p07_b4m_frozen_inputs.py"
)
packer=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(packer)


def fixture():
    rows=[]
    for core in range(27):
        comp=39 if core<24 else 32 if core<26 else 10
        bm=bytearray(512)
        axons=list(range(100,126)) if core==26 else [1]
        for ax in axons:
            bm[ax>>3] |= 1<<(ax&7)
        rows.append({
            "core_id":core,"compartments":comp,
            "axon_count":len(axons),"bitmap_hex":bm.hex()
        })
    ingress=[(i,0,1) for i in range(784)]
    output=[(i,0,26,100+i) for i in range(26)]
    return rows,ingress,output


def test_original_full_27_core_fixed_routing_bin_geometry():
    rows,inp,out=fixture()
    result,ext=packer.pack_tables(rows,inp,out)
    assert len(result)==packer.OUT_BYTES==0x14000
    assert len(ext)==packer.IN_BYTES==0xE0000
    assert result[:8]==b"B4MROUT1"
    assert ext[:8]==b"B4MING01"
    assert struct.unpack_from("<6I",result,8)==(1,0x14000,27,26,8,128)
    assert struct.unpack_from("<6I",ext,8)==(1,0xE0000,27,784,6,128)
    assert result[32:64]==bytes.fromhex(packer.PINNED_SHA)
    assert ext[64:96]==bytes.fromhex(packer.CAP_SHA)
    assert result[96:128]==hashlib.sha256(result[128:]).digest()
    assert ext[96:128]==hashlib.sha256(ext[128:]).digest()
    assert sum(struct.unpack_from("<27H",result,128))==1010
    assert struct.unpack_from("<4H",result,192)==(0,0,26,100)
    assert struct.unpack_from("<4H",result,192+25*8)==(25,0,26,125)
    assert struct.unpack_from("<3H",ext,128)==(0,0,1)
    assert struct.unpack_from("<3H",ext,128+783*6)==(783,0,1)
    assert result[192+26*8:]==bytes(len(result)-192-26*8)
    assert ext[128+784*6:]==bytes(len(ext)-128-784*6)


@pytest.mark.parametrize("mutate",[
    lambda r,i,o:(r[:-1],i,o),
    lambda r,i,o:(r,i[:783],o),
    lambda r,i,o:(r,i[:-1]+[(999,0,1)],o),
    lambda r,i,o:(r,i[:-1]+[(0,0,1)],o),
    lambda r,i,o:(r,i,o+[(0,0,26,100)]),
    lambda r,i,o:(r,i,[(0,0,26,126)]),
    lambda r,i,o:(r,i,[(0,999,26,100)]),
    lambda r,i,o:(r,i,o*386),
])
def test_invalid_frozen_original_topology_fails_closed(mutate):
    r,i,o=fixture()
    with pytest.raises(packer.FrozenRouteError):
        packer.pack_tables(*mutate(r,i,o))


def test_no_physical_permission_or_test_dataset_input():
    src=(ROOT/"scripts/p07_b4m_frozen_inputs.py").read_text()
    assert "load_train_validation(data_dir,strict=True)" in src
    assert "require_pinned_train_validation(split)" in src
    assert "b1.admit_freeze(frozen)" in src
    assert "decode_ingress_frame(wire,b12)" in src
    assert 'FRAME_IDX={0:37384,1:27347,2:20178}' in src
    assert "TEST_IDX" not in src
