# M08.4 — first routed paged-neural original, image review and blocked one-shot physical stage

**Date:** 2026-11-20. **Current status:** native bit and all 15 original receipt files exist and verify by the owner; **new-image DRC/timing/clock warning instances have NOT been supplied for independent review; physical programming is BLOCKED.** This is engineering within the single M08.4 gate, not another milestone or PR. Do not merge draft PRs #93/#94.

## Owner-original native provenance

- Original successful post-fix Vivado 2025.2 first routed candidate: `~/Thesis_Evidence/M08/m08_paged_m06_lif_QFKpXlPW`.
- Candidate: `bitstream_candidate/m08_paged_m06_lif_jtag_UNRELEASED.bit`.
- Owner supplied SHA256: `6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494`.
- Owner original `sha256sum -c 99_evidence_sha256.txt` printed **15/15 OK**: Vivado log/journal/exit; source copies of fan XDC, POR, shell, engine, AXIL, host bank; routed DRC, timing, utilization, clocks, native metadata, and original bit. **This does not verify the contents/acceptability of DRC, WNS/WHS, clocks or physical fan conditions.**
- Prior failed original native `m08_paged_m06_lif_gkft3TOX` remains separate and immutable. Previously accepted M32Q native and first physical evidence must never be re-run or overwritten.

### Read-only first-original triage — run now on owner PC

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
RUN="$HOME/Thesis_Evidence/M08/m08_paged_m06_lif_QFKpXlPW"
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt)
python3 scripts/m08_paged_m06_lif_physical_readiness.py --run-dir "$RUN"
```

The tool re-validates the *new* original 15-file/source/bit SHA, requires the exact claimed original bit and successful native exit, and prints original DRC/timing/utilization/clock report digests and selected text lines **without touching JTAG**. The output includes `physical_programming_authorized=false` regardless of read-only success. The operator must supply genuine `reports/20_route_drc.rpt`, `reports/21_route_timing.rpt`, `reports/23_route_clocks.rpt` and `reports/30_native_result.txt` (and utilization if relevant) for inspection. These files may be shared for review, not rewritten. Every new warning, exact pin/hierarchy, setup/hold slack, timing exceptions and PS PL0/fan routing must be addressed. Do not inherit any D3.D.2E warning exception by class name alone.

## Staged physical source — not yet authorized

- `scripts/m08_paged_m06_lif_physical_vectors.py`: creates **input-only** six 256B logical pages (6+6+6+6+6+2 neurons), a separate 256B five-edge setup page, and an independent comparison-only 512-word M02/M03 oracle in a **new** owner evidence directory.
- `scripts/m08_paged_m06_lif_physical_once.tcl`: proposed one-shot K26 JTAG operator using the exact previous physical `xck26_0`, `hw_axi_1`, on-fabric BRAM `0xA0000000` and the **new design's verified** AXI-Lite `0xA0001000` mapping. Stages 64 distinct words, reads and compares all 64 before COMMIT, configures five signed recurrent edges, performs **24** serialized neuron-page LOAD → COMMIT → DISPATCH → 64 full DIRTY readbacks → SAVE → replacement/reload over four barriers, storing **actual JTAG readback** into host backing instead of golden output. Each 32x4 neural slot is compared to the independent oracle.
- **Correct comparison attribution:** 128 original HOST-coalesced external current inputs, 128 FPGA-computed voltages, 128 FPGA-computed spikes and 128 FPGA-computed recurrent currents = 512; the latest image has **no raw-event FIFO and no PS/PL DDR/DMA**.
- `scripts/run_m08_paged_m06_lif_physical_once.sh`: a one-run, no retry, newly isolated SHA-receipted hardware runner; its first-original test and JTAG environment remain blocked **BEFORE any board access** unless `scripts/m08_paged_m06_lif_exact_native_accept.py` exists **and exits 0** for the exact image. That checker is deliberately **not implemented** until owner-original new routed reports are independently reviewed. The runner also requires active cooling, UART/rollback/exclusive JTAG preflight and two explicit user-set opt-ins.
- `scripts/m08_paged_m06_lif_physical_audit.py`: separately rechecks original native source/bit SHA, **13** first physical SHA receipts, actual unmodified executed Tcl/log, exactly one program marker, all 24 per-page saves, four tick barriers and 128 ordered readback observations against independently regenerated M02/M03 values. A source test/audit PASS is never an additional physical run.
- `tests/test_m08_paged_m06_lif_physical_stage.py`: source-only parser and fail-closed regression checks; no Hardware Manager or JTAG. The physical staging assets are intentionally not part of the Vivado offline build.

**DON'T RUN physical runner yet.** The image-specific release gate requires original DRC warning/pin and routed timing/clock examination and separate owner confirmation of cooling, UART logging, **exclusive** single-owner JTAG and stock recovery. The accepted earlier M32Q `.bit` and original evidence must not be reused; no guessed DDR/PS write addresses.

## What comes next within M08.4

1. Obtain/review the original `QFKpXlPW` route DRC/timing/clock metadata and independent read-only triage. If safe and fully specified, create an exact SHA-pinned first-image native acceptance validator with adversarial tests and verify on owner PC.
2. Confirm active independent cooling, UART evidence logging, stock image rollback and only one Hardware Manager/JTAG owner before *any* physical run. Add one-shot image authorization to the owner-local runner only when both native review and preflight pass.
3. Owner runs the *new* original image exactly once, shares first-original 13-file receipts, uses read-only independent physical auditor and explicitly accepts or rejects M08.4 based on 128 HOST input + 384 PL numerical comparisons across all 24 actual physical saves/reloads.
4. Only after first original paged state is accepted proceed to **M08.5** matched physical controls and guarded DDR ownership research; do not claim genuine PS DDR from this JTAG-host-staged state.
