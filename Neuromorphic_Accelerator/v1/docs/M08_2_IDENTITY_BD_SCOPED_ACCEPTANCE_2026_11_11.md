# M08.2 — scoped genuine KV260 PS→PL identity BD offline acceptance

**Acceptance date:** 2026-11-11 (America/Denver). **Disposition:** **ACCEPTED — IDENTITY-ONLY OFFLINE BLOCK-DESIGN VALIDATION**, not full M08.2 routed physical accelerator construction. Milestone gate remains separate from Linux DMA ownership, signed16 paged neural accelerator, bitstream, PS DDR, board execution and performance.

## 1. Owner-original evidence

**Seventh fresh original run directory (source-consistent independent audit):**
`/home/dna/Thesis_Evidence/M08/m08_2_identity_bd_20261111T074810Z_XlzGwf`.

Owner uploaded these three seventh-run **original** files to the review:
- `result.txt` = `exit_status=0`.
- `04_m08_identity_independent_audit.json` (SHA256 **`27bd4689fbcab91a92ece3c0467ff1f66c3e3e2b4c6aef580b51c51934099d04`**) with exact status `ORIGINAL_OWNER_VIVADO_BD_VALIDATION_EVIDENCE_CONSISTENT`.
- `05_evidence_sha256.txt` listing four original local vendor artifacts and hashes:
  - original `01_vivado_identity_bd.log`: `e84093b5bc2d67f46375a0da072046da48b679027d05b45fcd8025f66c1196f7`
  - original `02_vivado_identity_bd_readback.txt`: `0dc0068bd28ec284fd2cafed81507c6af73951345083b9941e125e4b1657e812`
  - original `03_identity_bd_export.tcl`: `d4c4f2d7e10573a484429610784fcd3ab466dcacf325dd1a975198895e77f303`
  - original `04_m08_identity_independent_audit.json`: `27bd4689fbcab91a92ece3c0467ff1f66c3e3e2b4c6aef580b51c51934099d04`

The review independently hashed the uploaded seventh-run audit bytes and matched their digest to the fourth row of the uploaded `05` receipt. The `02` readback and `03` export SHA match the **original sixth-run** files previously independently reviewed, establishing continuity of those output artifacts, though not a substitute for rehashing the seventh originals.

The auditor reported:
- `requested_clock_hz=100000000`; `actual_clock_hz=99999001`; `actual_clock_deviation_hz=999`.
- `ps_axi_addr_observed_in_bd=true`, `ps_axi_aperture_offset=0xa0000000`, `ps_axi_aperture_range=0x1000`.
- `routed_implementation=false`, `bitstream_programmed=false`, `physical_ddr=false`, `physical_mmio_performed=false`, `neural_inference_verified=false`.
- `source_sha256_manifest=d3b96cd3efb5e8f22f6e4ff7b16f3ba51a7b55d6885de0975039da8c62b4999d`.
- `report_sha256=0dc0068bd28ec284fd2cafed81507c6af73951345083b9941e125e4b1657e812`.
- `vivado_log_sha256=e84093b5bc2d67f46375a0da072046da48b679027d05b45fcd8025f66c1196f7`.
- `vivado_bd_export_sha256=d4c4f2d7e10573a484429610784fcd3ab466dcacf325dd1a975198895e77f303`.

**Evidence limitation:** the seventh-run original raw log, raw readback/export, four-file source SHA manifests and final wrapper console were **not reuploaded in this review**. Their hashes/statuses are original auditor assertions, not independent rehashes of the seventh-run bytes. The previous sixth run *did* supply genuine original complete Vivado log, readback/export and source manifests; it passed `validate_bd_design` in genuine Vivado 2025.2 with no ERROR/CRITICAL WARNING. The corrected source auditor's exact-output-line marker regression and eight M01–M08 CI flows passed on development HEAD `c07fdee4d2910c4c580de08fa8a9cc459b455c1c` before the seventh run. The seventh audit reports that the same-run four-file SHA manifest was consistent with the source it executed against; no source change to the validated RTL/BD was made after sixth native PASS.

## 2. Accepted limited deliverables

1. Genuine Vivado 2025.2 K26 `xck26-sfvc784-2LV-c` with installed `xilinx.com:kv260_som:part0:1.4` PS preset and FPD HPM0 PS master only (no unused LPD/HPM1 clocks).
2. One first-party, side-effect-free, 32-bit read-only AXI4-Lite identity slave through one AMD SmartConnect; validated reset/clock connectivity and 4 KiB original Vivado-assigned PS aperture.
3. Requested 100 MHz / generated 99,999,001 Hz, bounded deviation and post-validation consistent PS / identity / SmartConnect frequency metadata.
4. Original vendor `validate_bd_design -force` and source-only Icarus protocol checks, preserved first five failed original trials, then sixth real vendor PASS and seventh same-branch independent audit-consistent receipt.
5. Independent auditor and SHA receipt keep all original files outside source control in uniquely timestamped owner-owned folders.

**Acceptance is bounded to OFFLINE BD VALIDATION.** It is *not* a routed, timing-closed or physically deployed K26 accelerator. The full M08 engineering plan originally used “M08.2” more broadly to include complete M05/M06 physical shell, route and bitstream. **That broader portion remains OPEN**, tracked as **M08.2b future full-system implementation** in the phased hardware plan, with no reinterpretation of the original full-system gate. Do not claim that M08 as a whole is complete.

## 3. Scientific and engineering stop conditions

- `0xa0000000` is **only** the observed offline BD address candidate. Not authenticated Linux MMIO, not permission for `/dev/mem` or direct PL writes.
- No verified Linux kernel DMA owner, bound DMA device, cache coherence, DMA mask, IOMMU mapping, buffer lifecycle or quiesce/reset. No physical DDR ownership or transactions.
- No original M05 signed32 or M06 signed16 hardware bitstream, place/route timing, physical neural trace, resource-matched four-way accelerator results or energy measurement.
- The independent DMA ownership gate (M08.3) can proceed with **read-only discovery** in parallel with full-system BD planning, but must fail closed for real buffer allocation and device access pending owner physical evidence.
- Keep original source+Vivado evidence immutable and PR #83 draft/open/unmerged until the owner approves broader acceptance/merge.

**Next:** Begin `M08.3.1` — read-only Linux DMA/driver binding readiness inventory and independently audited evidence, followed by owner-provided board facts and a device-specific kernel DMA allocator design. The plan is not authorization to access physical DDR before ownership is demonstrated.

**Related:** [six original runs and root causes](M08_2_VIVADO_FAILURE_LEDGER_2026_11_11.md), [sixth genuine Vivado original log and exported BD review](M08_2_FIRST_GENUINE_BD_VALIDATION_REVIEW_2026_11_11.md), [physical gate plan](M08_PHASED_HARDWARE_PLAN.md).
