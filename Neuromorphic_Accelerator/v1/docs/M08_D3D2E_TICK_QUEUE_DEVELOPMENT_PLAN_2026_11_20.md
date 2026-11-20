> **D3.D.2E first original KV260 hardware RUN FINISHED; independent audit FALSE-NEGATIVE fixed, owner re-audit PENDING (2026-11-20):** The owner ran the exact accepted M32Q bit `2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc` **once** over JTAG, original physical evidence `m08_d3d2e_queue_HW_4HQkm7rN` (distinct from immutable native `m08_d3d2e_queue_GFz0SbiC`). Real program, BRAM transport, M32Q identity, **17 queue acceptances**, **128 current buckets confirmed zero before SERVICE**, tick 0..3 **5/5/4/3 serviced**, **128 current and 384 neural (=512) independent M06 numerical parity comparisons** all printed PASS. Original 6/6 physical SHA receipts OK. Standalone Python physical auditor then returned exit 2 **ONLY** due to literal `\\n` string bug in matching actual newline-terminated tick markers, not a hardware parity mismatch. Auditor now compares exactly four true log lines in order and rejects missing/duplicate/drift; new synthetic full 6-file receipt tests plus adversarial mutations added. **DO NOT rerun/reprogram hardware; owner must run read-only auditor on the exact first original physical folder and share independent audit exit 0 before final physical ACCEPTED claim**. [First actual physical experiment and audit repair](M08_D3D2E_OWNER_FIRST_PHYSICAL_RUN_AND_AUDIT_REPAIR_2026_11_20.md). Draft PR #93 open, no merge. M08 OPEN, M09 PLANNED.

> **D3.D.2E.3 EXACT NEW OWNER IMAGE REVIEW IMPLEMENTED; HARDWARE STILL NOT RUN — 2026-11-20.** Owner supplied full first-original seven DRC warnings; independently reviewed new XSDB LUT A1/A2/A3 pins/equations, JTAG FIFOs, RTSTAT first 15/37 displayed. Full report SHA pinned; route WNS +1.844ns, WHS +0.010ns, 0 failing, 100MHz PS PL0. Separate `scripts/m08_d3d2e_queue_exact_native_accept.py` pins first 12 owner receipts, source/builder/POR, bit SHA, new warning pins and full DRC/timing/clocks SHAs; source/negative tests staged. D3.D.2E.4 owner physical one-shot Tcl/shell/auditor now implemented but **may run ONLY AFTER the new gate returns 0 on the owner's untouched original image and operator confirms active cooling/UART/stock recovery/exclusive JTAG/one-time consent**. This supersedes earlier historical "no image candidate" / "physical one-shot not staged" sections below. [Owner original exact-image review and physical runbook](M08_D3D2E_OWNER_EXACT_NATIVE_REVIEW_AND_PHYSICAL_RUN_2026_11_20.md). No physical result yet, PR #93 draft.

> **FIRST NATIVE OWNER CANDIDATE UPDATE — 2026-11-20 16:35 LOCAL.** The owner now reports a FIRST ORIGINAL offline D3.D.2E Vivado 2025.2 `M32Q` build with 12/12 SHA receipts and successful bitgen: `~/Thesis_Evidence/M08/m08_d3d2e_queue_GFz0SbiC`; `UNRELEASED.bit` SHA256 `2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc` (7,797,844 bytes). This **supersedes historical “not run” statements below**, but **does NOT establish DRC, routed timing, exact owner-image acceptance or physical operation**. The first native review correctly returns `exit=2`, `image_specific_gate=BLOCKED`; the owner has not shared the full DRC/timing reports. Immutable folder, no rebuild/reprogram. [First native read-only next step](M08_D3D2E_FIRST_OWNER_NATIVE_CANDIDATE_2026_11_20.md).\n\n> **SOURCE VERIFICATION UPDATE — 2026-11-20:** Dedicated new M32Q source CI `44834402258` PASS (3 focused real-Icarus/oracle/mutation tests plus 487 M08 discovery tests (the focused tests are included in discovery)); M07 broad source workflow `44834388613` PASS after explicitly provisioning real Icarus (full 1,373-test discovery, including M32Q actual RTL). The new D3.D.2E.1 / D3.D.2E.2 source contracts are **SIMULATED AND CI-VERIFIED**, not owner-local independently repeated and not physical. D3.D.2E.3 offline native builder/reviewer is staged but **NOT EXECUTED on owner PC**. Original new-image DRC, routed 100 MHz timing, image-SHA and native reviewer-specific acceptance are **PENDING**; first-image native reviewer unconditionally exits 2. No D3.D.2E JTAG scripts are released, no FPGA programming, no D3.D.2D evidence modified, no merges.\n\n# M08 D3.D.2E — M32Q bounded tick-aware queue, staged hardware verification

**Date:** 2026-11-20. **Current status: SOURCE CANDIDATE / CI PENDING; NO NEW VIVADO, NATIVE IMAGE, BOARD OR PHYSICAL ACCEPTANCE.** Built as a NEW branch stacked on draft PR #92; new draft PR #93. Never merge or program without owner authorization.

## Evidence boundary and research question

D3.D.2D was physically accepted with 17 individually delivered input events, 128 live hardware input bucket values and 384 M06 neural values (**512/512** comparisons). Its **original first** 7,797,844-byte image SHA256 is `f50a156342eaf1173a3869b5316e4edc1d59662d9f0d687bcec600f7b0efdeab`. Its source, original owner 12 native evidence files, 6 physical files, exact DRC SHA, and independently accepted evidence **MUST REMAIN UNTOUCHED**. See `M08_D3D2D_OWNER_PHYSICAL_ACCEPTANCE_2026_11_20.md`.

D3.D.2E tests **event acceptance decoupled from tick-aware FPGA service**, not asynchronous arrival. The PS-requested 100 MHz PL0 clock, AXI JTAG transport and 4 KiB module register space remain synchronous. Retain original M06 G3.3 **32 neurons x 4 logical ticks; 5 positive-delay recurrent signed16 weights; 17 signed32 input events; decay 3/4 toward zero**, M02 dense/event vs M03 exact sparse comparison. No original M05 physical HLS, M06 physical DDR/paging, DMA, AXI stream, independently clocked fabric, performance, energy or sparse skipping claims.

## Submilestone boundaries

- **D3.D.2E.1 (new source candidate):** `rtl/m08/m08_d3d2e_tick_queue_lif_axil.v`, M32Q v6 0x4D333251/0x00060000, separate 32-entry FIFO, 64 cumulative accepted event limit, shadow bucket sums to reject signed32 overflow before queue admission; 1 entry serviced per active service clock. Event acceptance does not touch live current buckets. Service is requested *per tick* 0 -> 1 -> 2 -> 3; empty tick must be explicitly completed; ordered tick admission, no late tick, no config writes during service/neural BUSY. Each service marks a completed tick and counts popped entries. LAST tick barrier + equality accepted==serviced are mandatory for START; existing neuron staged recurrence remains unmodified. Hardware source is **unverified until real Icarus and CI pass**.
- **D3.D.2E.2 (tests and oracle):** `rtl/m08/tb_m08_d3d2e_tick_queue_lif_axil.sv`, `scripts/m08_d3d2e_queue_gate.py`, `tests/test_m08_d3d2e_tick_queue.py`. Same original **630-word** M06 independently reconciled raw-event vector fixture, **128 live bucket + 128 voltage + 128 spike + 128 recurrent current** comparisons. Negative simulation covers initial invalid START, malformed neuron/tick, partial strobes, positive/negative overflow, FIFO full depth 32, accepted lifetime 64 after service, stale/reordered event tick, skipped/duplicate service tick, enqueue/clear during SERVICE, under-service START, CLEAR/replay, AXI response backpressure and neural BUSY. Icarus is required: missing simulator must fail the new test (no silent skip).
- **D3.D.2E.3 (offline native candidate only):** `scripts/run_m08_d3d2e_queue_pc.sh` and `scripts/m08_d3d2e_queue_build.tcl`. Fresh **original** folder `~/Thesis_Evidence/M08/m08_d3d2e_queue_XXXXXXXX`, Vivado **2025.2**, K26 `xck26-sfvc784-2LV-c`, 100MHz PS PL0, fabric POR 256 cycles, PS HPM off, JTAG AXI -> SmartConnect -> 4KiB BRAM `0xA0000000` + new M32Q `0xA0001000`, independent powered fan requirement, TTC0 fan route A12. Copy original sources, route, DRC/timing/utilization/clocks, generate unique **UNRELEASED** bitstream, 12-file SHA receipt. New first-image read-only inspector **unconditionally returns exit 2** even if evidence is internally consistent. All image-specific DRC warning pins, timing endpoints, bit SHA, RTL/POR/builder SHA and report bytes need **human review**; previous D3.D.2D DRC exceptions are NOT reusable. No Vivado bitstream or new owner evidence exists in this repository or assistant environment.
- **D3.D.2E.4 (not started):** after **owner** supplies first native Vivado candidate, independently audit full DRC, setup/hold, all 12 SHA receipts and first original `.bit`, create *image-specific* approval gate with mutation tests. Only after exact-image gate returns 0, separate explicit owner authorization/cooling/UART/stock recovery/unique JTAG may create one-shot physical scripts. Maintain six-file physical SHA receipt and independent M02/M03 read-only physical checker; NEVER reuse D3.D.2D accepted evidence. Do not implement an active programming path before this approval boundary.

## New M32Q v6 AXI offset contract (base 0xA0001000)

All offsets are byte offsets; 32-bit aligned full-strobe writes, AXI SLVERR/DECERR on malformed operations, no concurrent SERVICE/compute writes.

| Offset | Operation | Meaning |
| --- | --- | --- |
| `0x000/0x004` | R | M32Q magic / version 6 |
| `0x008` | R | neuron BUSY/DONE, unchanged encoding |
| `0x00C/0x010/0x020` | RW | nonce / decay / signed recurrent edge count |
| `0x014` | W | START=1 only after all four tick barriers + 17 serviced + valid config |
| `0x024/0x028/0x02C` | RW | enqueue mailbox neuron / tick / signed32 current |
| `0x030` | W | PUSH=1, atomic admission into FIFO; count+shadow only; no live sum |
| `0x034` | R | successful lifetime accepted event count (max 64) |
| `0x038` | W | CLEAR=1 resets FIFO/shadows/live sums/service state/counters, not neuron config |
| `0x03C` | R | **serviced** live signed32 sum of currently selected mailbox neuron/tick |
| `0x040` | W | SERVICE=<next expected logical tick> 0..3, sequential and exact |
| `0x044` | R | current queue depth 0..32 |
| `0x048` | R | lifetime high-watermark since CLEAR 0..32 |
| `0x04C` | R | actually serviced event count |
| `0x050` | R | four completed tick bits, LSB=tick0 |
| `0x054` | R | `{28'd0,next_service_tick[2:0],service_busy}` |
| `0x058` | R | per-tick serviced count for selected mailbox tick |
| `0x100..0x4FF` | RW except input current writes | neuron parameters and **read-only** serviced input buckets |
| `0x500..0x57F` | RW | 8 positive-delay recurrent connection config |
| `0x900..0xCFF` | R after DONE | 128 LIF voltage values and 32 masks |
| `0xD00..0xEFF` | R after DONE | 128 recurrent-current values |

**Ordering contract:** the queue preserves the arrival order and enforces nondecreasing tick labels. M06 17-event fixture is already ordered by tick, but arbitrary reordering of tick groups is rejected; events with the *same* tick may coalesce and preserve signed order. `PUSH` cannot append to a completed tick; repeated `SERVICE` for a completed tick is rejected; a full queue is rejected, not silently overwritten. The 128 shadow buckets ensure signed32 prefix safety before acceptance (including an event batch crossing FIFO-service boundaries); live buckets only change during service. An asynchronous clock domain is **not** implemented.

## Source verification on owner's Linux VS Code terminal (NO BOARD)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d2e-tick-event-queue
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d2e-tick-event-queue
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
sudo apt-get install -y iverilog   # only if missing
python3 scripts/m08_d3d2e_queue_gate.py --source-only
python3 -m unittest discover -s tests -p 'test_m08_d3d2e_tick_queue.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2e_native_review.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
bash -n scripts/run_m08_d3d2e_queue_pc.sh
```

**Offline image-generation commands are CONDITIONAL on green source tests and a configured Vivado 2025.2** (NOT hardware programming):
```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /path/to/Vivado/2025.2/settings64.sh   # substitute actual installed path
mkdir -p "$HOME/Thesis_Evidence/M08"
bash scripts/run_m08_d3d2e_queue_pc.sh
# Exit 2 is the EXPECTED FIRST-IMAGE REVIEW BLOCK, not authorization.
# Inspect the printed NEW evidence directory, DO NOT rerun/rewrite it.
```

When a first candidate exists, review the genuine **new** full DRC warnings, timing constraints, source hashes and immutable bit before any gate can be accepted. No command in this document calls `program_hw_devices`; no acceptance or merge has been authorized. **M08 OPEN; M09 PLANNED.**
