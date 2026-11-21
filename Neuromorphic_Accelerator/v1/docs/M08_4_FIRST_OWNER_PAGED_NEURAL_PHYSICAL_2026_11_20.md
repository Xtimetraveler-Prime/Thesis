# M08.4 — PHYSICALLY ACCEPTED: first original KV260 paged signed16 LIF with independently audited evidence

**Run date:** Friday, 2026-11-20, first original Vivado 2025.2 hardware run **18:40:35–18:41:37 America/Denver**. **Final owner audit:** after the source-only echo-marker parser correction, the owner reran the independent auditor **read-only against the exact original hardware directory** and supplied the complete successful console output. **Acceptance status: M08.4 PHYSICALLY ACCEPTED (owner-reviewed 2026-11-20); M08.5 becomes ACTIVE.** All original native, bitstream, hardware log, source and SHA evidence remain immutable. This acceptance is explicitly scoped to **one 256B resident bank, six host-backed logical pages, 32 signed16 neurons, 4 synchronous ticks, 5 recurrent edges, and 512 compared values**; it is not true DDR/DMA or independently asynchronous event service.

## Exact evidence identities (NEVER rewrite, replay, rehash, or overwrite original paths)

| Item | First owner evidence identity |
| --- | --- |
| Post-fix native owner source/route | `~/Thesis_Evidence/M08/m08_paged_m06_lif_QFKpXlPW` |
| Original K26 first paged-neural .bit | `bitstream_candidate/m08_paged_m06_lif_jtag_UNRELEASED.bit` |
| Exact first original bit SHA256 | `6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494` |
| Native report/bit receipt | Original 15/15 SHA entries `OK`; exact-image new native checker independently returned `image_specific_gate=ACCEPTED` and `M08_4_EXACT_FIRST_OWNER_NEW_IMAGE_REVIEWED_BOUNDED_JTAG_ALLOWED_WITH_PREFLIGHT` |
| **First physical owner folder (immutable)** | `~/Thesis_Evidence/M08/m08_paged_m06_lif_HW_zhUx7lLJ` |
| Physical SHA ledger | **13/13** original file rows `OK` on owner CLI, including executed Tcl, original Vivado log/journal, process-exit receipt, independent golden, seven host input-only page hexes (six neuron and one edge config), and the complete physical 128-neuron/tick trace. |
| Historical other runs | Previous failed offline `m08_paged_m06_lif_gkft3TOX`, previous failed optional methodology `m08_paged_m06_lif_methodology_snLCj8aX`, and earlier physically accepted M32Q D3.D.2E originals remain **unchanged**. |

## Observed first-original physical functional result

- Genuine Vivado 2025.2 opened the previously known single JTAG target `localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA`; `program_hw_devices` executed **exactly once** in first original Tcl and its runtime markers `M08_4_NEW_IMAGE_PROGRAM_ONCE_START` and `...COMPLETE` appear in the owner log. Postprogram Vivado confirmed **one real JTAG AXI core**; no automatic replay.
- On-fabric JTAG AXI BRAM write/read matched `55AA22DD`. Neural register `0xA0001000` returned magic `4D303850`, version `00020002` and capability `00000001`. No PS memory access, DDR/DMA, Linux `/dev/mem`, flash or SD writes were attempted by the bounded neural experiment.
- The first 256-byte **five-edge configuration page** was host-loaded, entirely read back and committed, then dispatched on the actual fabric, producing `M08_4_PHYSICAL_EDGE_PAGE_CONFIGURED_5`.
- **All 24** original `M08_4_PHYSICAL_256B_LOAD_COMPUTE_FULL_DIRTY_SAVE|tick|page` physical markers appeared, six each for ordered ticks 0, 1, 2, 3; all four separate `M08_4_PHYSICAL_ORDERED_TICK_BARRIER|tick` markers appeared. Each page's complete 64-word host load/readback, COMMIT, actual compute DISPATCH, complete DIRTY readback against oracle, SAVE, eviction and later host-reload were exercised. The host stores actual FPGA readbacks as next-tick backing, **not** oracle expected outputs.
- Original physical Tcl checked **128 host-coalesced input-current buckets, 128 PL membrane values, 128 PL spike decisions, 128 PL recurrent delivered signed currents**, total **512** exact comparisons with the independent M02/M03 M06 32-neuron × 4-tick reference. This is **384 truly PL-computed** comparisons, not 512 PL-computed values. It printed `M08_4_PHYSICAL_128_HOST_CURRENTS_384_FABRIC_COMPUTED_24_PAGES_ONE_BANK_PASS`.
- First original physical process ended with Vivado `INFO: [Common 17-206] Exiting Vivado` and 13 SHA entries `OK`, confirming the underlying run reached its native post-JTAG and SHA stages with no detected fabric numerical mismatch. This is a user-supplied console result, not direct independent access to the private owner hardware evidence bytes.

## First independent Python audit false negative: root cause and corrected software ONLY

The first original hardware runner's final **read-only** receipt auditor printed:

```text
M08_4_FIRST_HW_RECEIPT_REJECTED: missing or duplicate original physical JTAG marker M08_4_NEW_IMAGE_PROGRAM_ONCE_START
```

This was **not** a physical JTAG rejection. Vivado batch logs echo Tcl source commands as comments, for example `# puts "M08_4_NEW_IMAGE_PROGRAM_ONCE_START"`, **and** separately print the exact runtime event line. The original Python audit counted `sum(marker in line for line in lines)`, inadvertently interpreting the echoed source comment and actual execution as two events. Its additional `"PROGRAM_ONCE_START" in line` check had the same defect, and the page/tick checks could similarly double count. The bug occurred **after** completed original physical run and after all 13 SHA checks returned `OK`.

**Software-only fix** in `scripts/m08_paged_m06_lif_physical_audit.py`: require **whole, standalone original runtime lines equal to each exact marker**, not substring hits in echoed Tcl or arbitrary diagnostic text; require **correct global event ordering** over bit identity, preprogram input check, one programming start/complete pair, edge setup, all 24 page SAVEs, four ordered tick barriers, final numerical success marker. No original hardware bytes were touched or re-created. Auditor continues to validate 13 original SHA rows, exact executed Tcl, native image-specific first-review/15 original SHA/source identity, recomputed host-only input fixture, separate 512-value independent golden, and all **128** actual captured per-neuron/tick 4-field rows against M02/M03, including accumulated spike masks. It cannot infer physical DDR, sparse event ingress, original M06 HLS, autonomous asynchronous execution, throughput/latency, or power.

**New directed software negative regression:** `tests/test_m08_paged_m06_lif_physical_reaudit.py` creates a **synthetic fully matched 13-file original-shaped record**, with *both* Vivado Tcl echoes and runtime markers. It now accepts correctly; rejects rehashed missing or duplicate runtime marker, rehashed reordered page/tick, rehashed neural-current alteration, and non-rehashed file alteration. Real CI on commit `1b16fe10cea6593f49aacca9696d0077f1a738a4` ([workflow run 44851903415](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/44851903415)) passed **548 M08 tests**, including six new adversarial re-audit tests and real Icarus vvp workload. This is **source/synthetic auditor** verification, not a second physical run.

## Completed final acceptance: owner original read-only re-audit (NO Vivado / NO JTAG)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership

cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
RUN="$HOME/Thesis_Evidence/M08/m08_paged_m06_lif_QFKpXlPW"
HW="$HOME/Thesis_Evidence/M08/m08_paged_m06_lif_HW_zhUx7lLJ"

python3 -m unittest discover -s tests -p 'test_m08_paged_m06_lif_physical_reaudit.py' -v
(cd "$HW" && sha256sum -c 99_evidence_sha256.txt)
python3 scripts/m08_paged_m06_lif_physical_audit.py --native-dir "$RUN" --hw-dir "$HW"
```

**ACTUAL OWNER RESULTS — PASS, not merely an expectation.** The owner pasted **13/13** `sha256sum -c` lines ending in `: OK`, followed by the fixed independent auditor's JSON success output. The auditor verified the original **15/15 native SHA files**, original **13/13 hardware SHA files**, exact image `6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494`, exact original Tcl, standalone single-program runtime marker, all four barriers, every one of the **24** full physical page dispatch/save markers, the **128** ordered actual neuron/tick readback records, the independent M02/M03 golden, **128 host input checks**, **384 on-fabric neural-computed checks**, and therefore **512 exact comparisons**. The Python success path emits JSON and returns zero; the user did not paste a separate `echo $?` shell line. No hardware rerun was performed for the auditor fix.

Exact original auditor JSON, as posted by the owner (including its intentionally conservative pre-owner-review status label):

```json
{
  "independent_host_coalesced_input_checks": 128,
  "independent_physical_pl_computed_checks": 384,
  "native_original_bit_sha256": "6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494",
  "new_image_hardware_owner_release_already_required": true,
  "ordered_tick_barriers": 4,
  "original_native_15_SHA_files_checked": true,
  "original_physical_sha_files_checked": 13,
  "original_single_JTAG_program_marker": true,
  "owner_final_M08_4_acceptance_review_pending": true,
  "physical_256_byte_page_dispatches_saved": 24,
  "physical_ddr": false,
  "status": "M08_4_FIRST_ORIGINAL_PHYSICAL_ONE_RESIDENT_6PAGES_128HOST_384PL_NUMERICAL_PASS_REVIEW_REQUIRED",
  "total_exact_numerical_comparisons": 512
}
```

**Interpretation of `owner_final_M08_4_acceptance_review_pending=true` and `...REVIEW_REQUIRED`:** these are **unchanged conservative labels emitted by the reusable read-only Python auditor before a human owner signs off**; they are not failed checks. The auditor's full evidence checks succeeded, and the owner subsequently reviewed the successful result and explicitly instructed documenting completion and proceeding to the next milestone. This document and `roadmap.md` record the human **M08.4 PHYSICALLY ACCEPTED** decision; the original auditor JSON and original evidence are deliberately **not rewritten**. Do not confuse a parser-return status string with a new physical run or a measured throughput result.

### Final M08.4 acceptance decision and boundaries

**ACCEPTED:** original KV260 2025.2 first-paged-LIF execution, 32×4 signed16 5-edge real recurrent dynamics, **6 logical neuron pages × 256B; 1 physically resident 256B state bank; 24 compute-and-save replacements**, independent parity **128 host current + 384 on-fabric neural computations = 512/512**. Native 15/15 and physical 13/13 original SHA receipts and independent read-only observation audit are both accepted. Preserve all evidence; there is no reason to program or rebuild this image again for acceptance.

**NOT established:** physical PS/PL DDR or DMA/cache-coherent paging, source-identical raw 17-event on-fabric FIFO in the new paged image, autonomous asynchrony, physical latency/throughput, energy/power, or original M06 HLS implementation. The five first-image `LUTAR-1` methodology advisories remain untraced; the owner accepted that explicitly bounded risk for the already-successful first JTAG experiment. These constraints carry forward to **M08.5**.


## M08.5 ACTIVE: matched placement/execution strategies (new physical experiments NOT automatically authorized)

At matched original signed16 numerical semantics, network, external event timing, actual N/K residency and physical measurement boundary, compare on-chip timestep vs on-chip event strategies and actual host-page/DDR strategies where ownership is proven. Report page locality, physically observed transfer counts/stalls, checksummed owner-original results, and accurate PS/JTAG versus PL measurement boundaries. Do not treat these JTAG transfers as true DDR, and do not use guessed PS/PL physical buffer addresses. An independent verified kernel-owned DMA/DDR buffer and cache-coherency/quiesce/recovery plan is required before any genuine memory-backed physical experiment. Preserve original PRs #93/#94 draft/unmerged.
