# M08 D3.D.2D — 32-neuron FPGA raw external-event ingress (first source/PC candidate)

**Date:** 2026-11-20. **Stage:** Source-only / Icarus and owner offline Vivado first new candidate. **DO NOT PROGRAM THE KV260** using the D3.D.2D candidate. Native image-specific DRC, timing and SHA approval are pending; no new D3.D.2D physical result exists.

## Where this comes from — original physical D3.D.2C

Owner's first 32-neuron actual FPGA test has just **PASSED**: genuine JTAG folder `~/Thesis_Evidence/M08/m08_d3d2c_m06_HW_BsHcfs4j`, 6/6 original physical SHA entries OK, full 32×4 readback and independent audit `M08_D3D2C_PHYSICAL_M06_32X4_REAL_RECURRENT_M02_PARITY_ACCEPTED`; 128 voltages, 128 spike decisions and 128 on-FPGA delayed recurrent-current values matched original M06 M02 dense/event + M03 sparse. The original D3.D.2C bitstream SHA `244d304a44af6b1eda1943c18e7b5a3bed302cae2308c28a11944ede7eadf932` is immutable. **Only the 17 external M06 events were coalesced on the host** before being sent to fabric. [Exact owner physical acceptance](M08_D3D2C_OWNER_PHYSICAL_ACCEPTANCE_2026_11_20.md).

## Scientific question and controlled physical increment

**Question:** Can the FPGA itself accept the **17 original individually encoded signed external events** and reconstruct the 128 neuron/timestep input buckets while retaining the exact original 32-neuron / 4-tick / five-positive-delay-synapse LIF traces?

The **single** deliberately changed architectural variable is external-event accumulation: PC-side aggregation (D3.D.2C) is replaced by **one event per AXI-Lite mailbox PUSH**, with signed33 overflow checking and 128 on-chip signed32 buckets. The 32-neuron M06 network, 3/4 truncate-toward-zero decay, 5 recurrent signed16 edges (capacity 8), 4 logical timesteps, pulse-based spike output and five-stage pipelined neuron evaluation are otherwise retained.

**Do not misinterpret this test:** Host-to-FPGA **JTAG AXI-Lite control-plane transactions are still serialized and synchronous**, not hardware asynchronous routing, AXI-Stream, DMA, automatic temporal queue, or the originally synthesized M05 event engine. D3.D.2D adds an actual fabric-side external-event **adder**, not a true independent event scheduler or physical DDR paging. The M06 fixture's 17 events may include opposite-sign contributions to the same neuron/tick bucket. Hardware must accept individual signed32 values, correctly accumulate them, and reject signed32 overflow without modifying a bucket or accepted-event counter. Do not claim performance, event-rate capacity, PS DDR, sparse skipping or energy measurements.

## Distinct source and immutable build boundary

New stacked branch `agent/neuromorphic-accelerator-v1-m08-d3d2d-raw-event-ingress`; draft PR #92 stacked on D3.D.2C PR #91 (unmerged). A **new** `M32E` v5 peripheral and new image are required; D3.D.2C's reviewed seven-warning DRC allowlist and bitstream MUST NOT be reused. The prior physically accepted RTL is checked by SHA in source gate; its original files/evidence remain untouched.

### New peripheral AXI byte-address map (`0xA0001000` base)

| Offset | Purpose / access / bounds |
| --- | --- |
| `0x000` | `M32E` magic `0x4D333245` (RO) |
| `0x004` | ABI version `0x00050000` (RO) |
| `0x008` | DONE/BUSY, `0x00C` nonce, `0x010` decay mode, `0x014` START, `0x018` result nonce, `0x01C` completed run count, `0x020` active recurrent edge count |
| `0x024` | EVENT_NEURON RW, integer `0..31` |
| `0x028` | EVENT_TICK RW, integer `0..3` |
| `0x02C` | EVENT_CURRENT RW, signed32, no host aggregation |
| `0x030` | EVENT_PUSH, write-only with value `1`. **Fabric** conditionally does `currents[4*neuron+tick] += signed_current` with signed33 intermediate, overflow check and atomic reject. Full AXI WSTRB required. Each successful PUSH increments counter. Limit 64 accepted events per CLEAR. |
| `0x034` | EVENT_COUNT RO, current successful PUSH count `0..64` |
| `0x038` | EVENT_CLEAR write-only value `1`, zeros all 128 current buckets and resets event mailbox/count, only when IDLE. This permits an independently tested fresh event replay, without changing neuron parameter registers. |
| `0x03C` | Selected accumulated bucket (RO) for currently selected neuron/tick |
| `0x100..0x4FF` | Original 32 neuron param/control banks. External-current words exist for **readback**, but the D3.D.2D physical protocol must write **zero**, not the host-coalesced expected values. |
| `0x500..0x57F` | Eight possible weighted positive-delay recurrent edges (original M06 uses five) |
| `0x900..0xCFF` | 128 voltage results / 32 per-neuron four-bit spike masks, only after DONE |
| `0xD00..0xEFF` | 128 on-device delivered recurrent currents, only after DONE |

Malformed event neuron/tick, signed32 overflow, >64 PUSHes, partial writes, a PUSH during BUSY, invalid CLEAR, writes to RO registers and an unconfigured START must fail closed. Input bucket writes do not affect previous D3.D.2C physical result.

## PC source and numerical acceptance

New files:
- `rtl/m08/m08_d3d2d_raw_event_lif_axil.v`: separate M32E v5 event ingress + exact inherited pipelined recurrent neural RTL (NOT prior accepted D3.D.2C module).
- `scripts/m08_d3d2d_event_vectors.py`: original M06 independent M02/M03 579-word neural oracle **plus 17 raw triples = 630 words**. It computes expected bucket sums only for verification; those sums are **not** written to hardware.
- `rtl/m08/tb_m08_d3d2d_raw_event_lif_axil.sv`: actual Icarus clocked AXI protocol, hardware pushes 17 distinct events, reads all 128 accumulated buckets, checks all 128 voltages + 128 spike decisions + 128 delivered currents, performs three runs (including CLEAR/reingestion), and tests atomic overflow and BUSY/invalid-access rejections. A no-Icarus `SKIP` is not an RTL PASS.
- `scripts/m08_d3d2d_event_gate.py` and `tests/test_m08_d3d2d_raw_events_source.py`: fail-closed predecessor source SHA, new pipeline/API source and real Icarus acceptance.
- `scripts/m08_d3d2d_event_build.tcl` and `scripts/run_m08_d3d2d_event_pc.sh`: only **offline** Vivado 2025.2 K26 implementation. Preserves independent PL reset/PS-clock-dependency, JTAG AXI + BRAM separate base `0xA0000000`, new `M32E` 4KiB base `0xA0001000`, PS HPM disabled, PL fan pin A12, first original 12-file evidence SHA receipt. No hw_manager, no programming.
- `scripts/m08_d3d2d_event_native_review.py`: new first native image source/build/receipt/timing/DRC identity triage that **ALWAYS exits 2** pending independent owner DRC/profile/SHA review, even if bitgen succeeds. This is an intentional safety gate, not a bitgen failure.
- `tests/test_m08_d3d2d_event_native_boundary.py`: source and fake-native fail-closed negative checks, no physical execution.

## Owner local source verification — no Vivado/board needed yet

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d2d-raw-event-ingress
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d2d-raw-event-ingress
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_d3d2d_raw_events_source.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2d_event_native_boundary.py' -v
python3 scripts/m08_d3d2d_event_gate.py --source-only
bash -n scripts/run_m08_d3d2d_event_pc.sh
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
```

**STOP on failure.** None of these commands can program the board.

## Next owner-PC Vivado native candidate (after the above and CI pass)

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
bash scripts/run_m08_d3d2d_event_pc.sh
RC=$?
echo "M08_D3D2D_OFFLINE_BUILD_EXIT=$RC"
```

New folder: `~/Thesis_Evidence/M08/m08_d3d2d_event_XXXXXXXX`. If route/bitgen succeeds, original `bitstream_candidate/m08_d3d2d_event_lif_jtag_UNRELEASED.bit`, new DRC/timing/utilization/clock reports and original 12-entry SHA manifest are preserved. The first-image reviewer will **still exit 2** with `M08_D3D2D_FIRST_NEW_NATIVE_DRC_REVIEW_REQUIRED_NO_BOARD`. If Vivado exits nonzero, preserve the first failed evidence, no automatic retries. Do not replace old D3.D.2C or D3.D.2D folders. Do not attempt the new JTAG test until the owner supplies original report/bit SHA and the image-specific gate has been independently coded and accepted; a separate explicit one-shot hardware release and independent 128 bucket + 384 neural output audit will follow.

**M08 remains OPEN, M09 remains PLANNED, PR #91/92 remain draft and unmerged.**
