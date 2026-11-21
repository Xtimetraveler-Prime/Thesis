> **AUTHORITATIVE M08 FUTURE GATES CONSOLIDATED — 2026-11-20:** User requested an end to D3.D.* sub-milestone sprawl. The D3.D.2A–E divisions were justified for first-image safety and are now immutable accepted history, but separate future D3.D.3A/B/C/D releases were **unnecessary**. Three remaining **M08 acceptance gates**, not micro-milestones, are: **(1) M08.4 compute-bearing signed16 host-paged 32-neuron physical conformance with N>K and freshly reviewed Vivado image + original physical audit; (2) M08.5 authentic on-chip-vs-memory-backed matched benchmark with real DDR only after kernel-owned/PS-safe memory/address/coherency proof; (3) M08.6–7 combined repeated physical timing/resource evidence, controls, owner acceptance and M09 handoff.** D3.D.3A is a historical source task within M08.4, not a new release gate; no PR for every handshaking/decoy/readback task. **Current M08.4 work:** proposed 4KiB source reference, 3:2 software ownership, real synthesizable **256B AXI4-Lite host bank + 63-read/1-write compute-port probe** and real Icarus negative tests, and original M06 32-neuron signed16 parameter pages divided **15+15+2 across three logical pages and one physical RTL slot**; the probe does **not** do neural math. Do not equate either source fixture with accepted 32-neuron physically paged neural computation. D3.D.2E original physical **512/512** and six SHA receipts remain accepted and untouched. [Authoritative consolidated M08 plan](M08_REMAINING_PHYSICAL_EXECUTION_PLAN_2026_11_20.md). M08 OPEN/M09 PLANNED. PR #94 draft stacked on #93, neither merged, **no new physical programming**.

# M08 D3.D.3A — safe host-paged state ownership, source-only first increment

**Started:** 2026-11-20. **Branch:** `agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership`, stacked on the **physically accepted, draft and UNMERGED** D3.D.2E source branch. This is a **NEW M08 substage**, not M09 and not a D3.D.2E physical rerun. M08 remains **OPEN**. No new FPGA programming, no Vivado route, no DDR transaction or Linux DMA API address is authorized or claimed. The original D3.D.2E owner native and physical evidence **must never change**.

## Why D3.D.3 instead of M09

**Physically accepted D3.D.2E:** true KV260 signed32 17-event on-fabric queue, four clocked tick service barriers 5/5/4/3, all 128 external current buckets and 384 neural values (**512/512** independent M06 parity), six original owner physical SHA entries and independent physical auditor accepted. See [first owner physical acceptance](M08_D3D2E_OWNER_PHYSICAL_ACCEPTANCE_2026_11_20.md).

**Still missing for core research hypothesis:** physically paging signed16 neuron/recurrent state across more logical neurons than resident on-fabric state; independent host-vs-compute ownership; PS-managed/DDR transactions (only after kernel/driver/safety review); genuine matched hardware timing. These are **M08**, not something M09 analysis should invent after the fact. Source-only M06 and Loihi v2 P08.4.3a/b showed bounded host-paged arbitration separately; neither proves M08 DDR or M32Q page-backed hardware. D3.D.3A starts with the smallest verifiable M06-specific page geometry and a fail-closed host-paging logical control stage.

## New deliverable D3.D.3A.1 — explicit 4 KiB *software-only* M06 page image

`scripts/m08_d3d3a_page_stage.py` derives its **630 original independent M06 words** using unchanged `m08_d3d2d_event_vectors.words()` (M02 dense/event vs M03 sparse reference). It deterministically packs a **proposed**, not implemented-on-FPGA, 1024-word little-endian image:

| Word range | Meaning | Original M06 source index |
| --- | --- | --- |
| 0–7 | M3PG software magic, v1, logical context ID, epoch, nonce, decay mode, 5 edge count, 17 event count | header + software tags |
| 8–135 | 32 neurons ×4 signed16 configured fields, sign-extended to 32 | `3 + neuron*8 + [0..3]` |
| 136–263 | 32 neurons ×4 signed32 fabric-current expected values, **reference only** | `3 + neuron*8 + [4..7]` |
| 264–295 | 8 edge slots ×4 fields; 5 active, 3 zero inactive | `259..290` |
| 296–423 | 32 neurons ×4 signed16 reference voltage words | `291 + neuron*9 + [0..3]` |
| 424–455 | 32 4-tick spike masks | `291 + neuron*9 + 4` |
| 456–583 | 32 neurons ×4 signed32 delivered recurrent-current references | `291 + neuron*9 + [5..8]` |
| 584–634 | 17 original uncoalesced signed32 external event tuples | `579..629` |
| 635–1023 | Reserved all ZERO | source-stage layout only |

This **is not** the D3.D.2E AXI register map and is not an implemented PL page-buffer protocol. The image represents the *known reference fixture*, including expected output traces; it is **not computed physically** by the paging stage. The next hardware design must explicitly separate parameter/state data from expected trace metadata before creating any compute-facing memory interface. That prevents mistakenly treating reference outputs as physical state.

`audit_page()` requires the exact 4 KiB image and checks every field against original M02/M03-derived golden words; rejects wrong context ID, epoch, corrupt signed values, changed raw events, unexpected nonzero reserved words and altered payload geometry. `with_epoch()` deliberately modifies **only the software page epoch header**, with no neural execution claim.

## New deliverable D3.D.3A.2 — three logical pages / two resident slots, source-only host lease

Reuses the already-reviewed `m08_host_page_ownership.HostPagedOwnership` *software* control model, not Loihi signed24 hardware or a new Linux allocator. Three cloned source fixtures are tagged as **distinct logical contexts** with one shared numerical workload; two modeled resident slots. The demonstration requires:

1. Exclusive host lease for page staging, pending-load status and matching software-observed SHA digest before dispatch.
2. No compute while host lease held; no host mutation during compute.
3. A **modeled epoch tag only** for completion after explicit `packets_drained=True`, followed by dirty-save to canonical host backing **before** eviction.
4. Replacement of logical page0 by page2 in slot0 after successful dirty save; independently verified logical identity, epoch and all 4 KiB bytes of all three final backing pages.
5. No global epoch barrier until all three logical contexts have completed and all pages are clean; corrupt readback, uncertain completion and incorrect identity must fail closed.

Expected source-only status: `M08_D3D3A_SOURCE_ONLY_M06_PAGE_GEOMETRY_AND_HOST_LEASE_PASS`, 3 modeled loads, 3 modeled saves, epoch1, 3 logical /2 resident; **no physical neural execution, no PL page replacement and no PS-owned DDR/DMA**.

## Tests / acceptance of THIS FIRST SOURCE INCREMENT

`tests/test_m08_d3d3a_page_stage.py` covers complete 1024-word mapping against original independent fixture; exact 32×4 input, neuron, spike/recurrent and raw tuple byte layout; correct 3-page logical identity separation; 4KiB and little-endian header; negative mutations to every data region and reserved words; invalid IDs/epochs, truncated images, source fixture tick drift; 3:2 software eviction replay and software readback poison; and forbidden device access operations. CI runs no board, Vivado or emulator stub presented as physical success.

**D3.D.3A.1/.2 source acceptance requires:** direct owner local eight test cases PASS, the source CLI prints the **software-only** status, and matching new GitHub CI run PASS. This closes *only* the source page geometry/ownership candidate, not the physical M08 D3.D.3 milestone.

## Required future work before actual new hardware

- **D3.D.3B:** Design an M08-specific *real* host-page memory/compute bridge or HLS-mapped state port. Separate input state from known expected trace metadata, select true page size/endianness/signed16 state fields, implement host/compute mutex, full readback and reset/quarantine; real Icarus RTL and owner native 2025.2 timing/DRC review on a new image and **separate** new original evidence. Preserve D3.D.2E fixed queue and M06 original reference.
- **D3.D.3C:** Independent native K26 board bitstream, exact new DRC instance review, owner-local original source/image/timing SHA acceptance, physical cooling/UART/exclusive JTAG/stock recovery and one-shot *new* physical page decoy→overwrite→dispatch→readback. No inherited D3.D.2E physical signoff.
- **D3.D.3D:** Actual kernel-owned physical DDR/DMA only after real bound PL master/PS-paged contract, mapped DMA mask, IOMMU/cache coherence, kernel allocator ownership, quiescence/reset, and complete independently checked transactions. Read-only M08.3.1 OS inventory is a dependency **not** authorization. No guessed addresses or `/dev/mem` user writes.
- **Later M08.5/M08.6:** Matched on-chip/event/timestep vs DDR physical workloads and real latency/transfer/resource observations, with original per-run SHA evidence. **M09** plots/interpretation only after measurements are accepted.

## Owner VS Code source-only verification

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1

python3 -m unittest discover -s tests -p 'test_m08_d3d3a_page_stage.py' -v
python3 scripts/m08_d3d3a_page_stage.py --source-only
python3 -m unittest discover -s tests -p 'test_m08_host_page_ownership.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d2e_physical_reaudit.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
```

**No `vivado`, JTAG, DDR, SD/QSPI, PS Linux writes, or physical M32Q bitstream operation is needed.** The original accepted D3.D.2E physical test must **NOT** be rerun.
