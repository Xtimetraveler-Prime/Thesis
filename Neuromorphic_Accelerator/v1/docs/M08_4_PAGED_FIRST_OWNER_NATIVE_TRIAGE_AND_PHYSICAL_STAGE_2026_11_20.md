# M08.4 — historical first-original native review and one-shot staging runbook

> **HISTORICAL runbook, not the current release status.** M08.4 is **PHYSICALLY ACCEPTED/CLOSED** following the owner's successful read-only independent 13/13 physical evidence audit, 15/15 native evidence, and 512/512 exact neural comparisons on 2026-11-20. This file records **pre-release** original commands and risk decisions; do **not** run its one-shot programming command again. For final results, use [accepted first-original physical evidence](M08_4_FIRST_OWNER_PAGED_NEURAL_PHYSICAL_2026_11_20.md); for active M08.5 use [authoritative roadmap](../roadmap.md) and [new-chat handoff](M08_NEXT_CHAT_HANDOFF_CONSOLIDATED_2026_11_20.md). Older "not programmed" statements below are dated historical observations, not the present state.

**Date:** 2026-11-20. **Current status:** owner-original new-image DRC/timing/clocks/metadata and all 15 original SHA receipts supplied and examined. `scripts/m08_paged_m06_lif_exact_native_accept.py` is now the independent exact owner-new-image release checker, pinning the exact 7,797,842-byte bit, all four original report SHA hashes, seven actual vendor-only DRC warning pins/paths and +0.763 ns WNS/+0.010 ns WHS. The owner explicitly accepts the residual five UNTRACED `LUTAR-1` asynchronous-reset methodology warnings; independent methodology/CDC inspection is OPTIONAL, not a requirement from previous accepted physical tests. **Physical programming has NOT yet occurred**: one bounded JTAG run may be attempted ONLY after local exact native checker exit 0, active cooling/UART/stock recovery/exclusive JTAG preflight, and explicit one-shot consent. This is within M08.4, not a new milestone. Draft PRs #93/#94 remain unmerged.

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
- `scripts/run_m08_paged_m06_lif_physical_once.sh`: a one-run, no retry, newly isolated SHA-receipted hardware runner; its first-original test and JTAG environment remain blocked **BEFORE any board access** unless `scripts/m08_paged_m06_lif_exact_native_accept.py` exists **and exits 0** for the exact image. That checker is **implemented** and pinned to the owner-original supplied reports; its local exit 0 is mandatory before any physical hardware action. The runner also requires active cooling, UART/rollback/exclusive JTAG preflight and two explicit user-set opt-ins.
- `scripts/m08_paged_m06_lif_physical_audit.py`: separately rechecks original native source/bit SHA, **13** first physical SHA receipts, actual unmodified executed Tcl/log, exactly one program marker, all 24 per-page saves, four tick barriers and 128 ordered readback observations against independently regenerated M02/M03 values. A source test/audit PASS is never an additional physical run.
- `tests/test_m08_paged_m06_lif_physical_stage.py`: source-only parser and fail-closed regression checks; no Hardware Manager or JTAG. The physical staging assets are intentionally not part of the Vivado offline build.

**Run the bounded physical runner only AFTER its local exact-image native gate exits 0 and the owner confirms active cooling, UART logging, **exclusive** single-owner JTAG and stock recovery.** The accepted earlier M32Q `.bit` and original evidence must not be reused; no guessed DDR/PS write addresses.


## Owner-uploaded first-new-image report examination (read-only; 2026-11-20)

The owner supplied **original** four Vivado text reports from `QFKpXlPW`; file contents and SHA256 were examined without touching the original owner directory. Report SHA256:

| Report | SHA256 |
| --- | --- |
| `reports/20_route_drc.rpt` | `2fd20b6a84cb803c4935b509b4bb5f32306ffb608067450e068d85a2284e92d4` |
| `reports/21_route_timing.rpt` | `fcb73aca06ced0c7df7d2f9f6657e23375a2504a7a5c64461ec683a969c0e42c` |
| `reports/23_route_clocks.rpt` | `e8330903e1ee569af95ef98fa1f072760b33b067a154fd89f3630244ea0a9ac0` |
| `reports/30_native_result.txt` | `495a6468fd23fa2ab1558b793553025518753dddc0faece8d17c951a1894c88a` |

**Actual route:** `m08_paged_m06_lif_jtag_wrapper`, K26 -2LV, fully routed, Vivado 2025.2. `report_drc` default ruledeck has **exactly seven Warning, zero reported Error/Critical Warning**:
- `PDCN-1569` #1/#2/#3: three LUT pin equation advisories in vendor `dbg_hub/inst/BSCANID.u_xsdbm_id/SWITCH_N_EXT_BSCAN` (`temp_curid[31]_i_1` two and `id_state[0]_i_1` one). Their actual physical pin mappings/equations differ from the older accepted M32Q warning profile; do not inherit old exemptions.
- `REQP-1857` #1 and `REQP-1858` #1/#2: three BRAM `WRITE_FIRST` collision advisories in `m08_paged_m06_lif_jtag_i/jtag_axi/inst/jtag_axi_engine_u/` vendor RX/RD/WR command FIFOs. Must not claim that advisory automatically proves collision-free behavior.
- `RTSTAT-10` #1: 39 nets without routable loads, first 15 of 37 paths printed; sampled nets reside in the debug hub / vendor JTAG AXI FIFO hierarchy, not LIF. Must check exact original net paths, not only warning class counts.

**Actual timing:** WNS **+0.763 ns**, TNS 0, **0 / 26,211 setup failures**, WHS **+0.010 ns**, THS 0, **0 / 26,147 hold failures**, worst pulse-width slack **+4.238 ns**, no failing PW endpoints, and zero `unconstrained_internal_endpoints` or `no_clock`. Explicit `All user specified timing constraints are met.` `clk_pl_0` and `clk_pl_1` each 10.000 ns (100 MHz) from `PS8_i/PLCLK[0/1]`; debug BSCAN `INTERNAL_TCK` nominal 50 ns. **Route constraint timing does not prove PS PL0 survives firmware/boot or that physical fan cooling works.**

**Outstanding native *methodology* finding, not visible in DRC summary details:** `report_timing_summary` includes `LUTAR-1  Warning  LUT drives async reset alert  5`, and explicitly warns the summary uses the last methodology run, which may not be current. The four original reports do **not** contain the affected five LUT sources/async reset endpoint pin paths. The five `LUTAR-1` warning cells remain **untraced** and can involve user fabric reset; the owner has expressly accepted this **bounded first physical-test risk**, not claimed vendor-only classification. The previous accepted D3.D.2E owner physical run did **not** independently run `report_methodology`/`report_cdc`. The exact image-specific checker now exists and discloses these five residual warnings. Its independent local pass, cooling/UART/exclusive JTAG/stock recovery and explicit one-shot owner consent remain mandatory.

### Optional extra offline check: methodology + CDC on ORIGINAL routed checkpoint (NOT required for bounded first run)

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
python3 -m unittest discover -s tests -p 'test_m08_paged_m06_lif_methodology_probe.py' -v
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
RUN="$HOME/Thesis_Evidence/M08/m08_paged_m06_lif_QFKpXlPW"
bash scripts/run_m08_paged_m06_lif_methodology_pc.sh "$RUN"
```

The runner first rechecks original source/bit SHA, then **reopens only the ORIGINAL implementation routed .dcp offline**, emitting `10_new_image_methodology.rpt`, `11_new_image_cdc.rpt`, hash ledger and original Vivado log into a **fresh separate** `~/Thesis_Evidence/M08/m08_paged_m06_lif_methodology_XXXXXXXX` folder. It does **NOT** resynthesize, rewrite the bit, or call Hardware Manager. Owner shares the new original supplementary reports for image-specific reset/CDC warning classification.

**Image-specific release checker is now implemented**, with exact new owner source/report/bit identity checks. The separate reset methodology run failed from a Vivado `-tclargs` command-line ordering bug; that script was fixed and its failed run `~/Thesis_Evidence/M08/m08_paged_m06_lif_methodology_snLCj8aX` is preserved, but no rerun is required. The owner elects to proceed with the remaining documented `LUTAR-1` risk, using the exact-image gate and separate cooling/UART/recovery/JTAG preflight. Do not overwrite any original prior evidence.


### Physical owner VS Code commands (bounded JTAG, exactly one new image)

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
RUN="$HOME/Thesis_Evidence/M08/m08_paged_m06_lif_QFKpXlPW"
python3 -m unittest discover -s tests -p 'test_m08_paged_m06_lif_exact_native_accept.py' -v
python3 -m unittest discover -s tests -p 'test_m08_paged_m06_lif_physical_stage.py' -v
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt)
python3 scripts/m08_paged_m06_lif_exact_native_accept.py --run-dir "$RUN"
```

**STOP if exact image-native acceptance does not print**
`M08_4_EXACT_FIRST_OWNER_NEW_IMAGE_REVIEWED_BOUNDED_JTAG_ALLOWED_WITH_PREFLIGHT`
**and exit 0**. Do NOT edit original receipt hashes, substitute the old M32Q image, waive a changed DRC warning, or bypass the checker.

After *independent* physical preflight: confirm cooling/fan/stock recovery, UART logging and single `hw_server` target `localhost:3121` with Vivado Hardware Manager GUI closed. **Only then**:

```bash
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
M08_4_PROGRAM_ONCE=YES M08_4_PREFLIGHT_CONFIRMED=YES \
  bash scripts/run_m08_paged_m06_lif_physical_once.sh "$RUN"
```

The runner will re-run the exact source/DRC/timing/clock/bit gate before creating **one new** unique `m08_paged_m06_lif_HW_XXXXXXXX` capture, execute **one** `program_hw_devices`, then check the actual 24 page load/compute/dirty-save cycles against 128 host-coalesced current inputs + 384 FPGA computed outputs. Original run/Tcl/log/golden/input/readback/exit/13 SHA receipt rows persist even if the hardware run stops. **No automatic retry**; report the first error and preserve evidence. This is not physical DDR/DMA, raw event FIFO or asynchronous timing proof.

## What comes next within M08.4

1. Owner pulls latest branch and verifies SHA, exact original image gate `python3 scripts/m08_paged_m06_lif_exact_native_accept.py --run-dir "$RUN"` and adversarial regressions. Stop if gate does not exit 0.
2. Owner independently confirms active cooling, UART evidence logging, stock-image rollback and only one JTAG Hardware Manager owner before *any* physical run. `M08_4_PROGRAM_ONCE=YES` and `M08_4_PREFLIGHT_CONFIRMED=YES` must be set ONLY for the one separately consented invocation.
3. Owner runs the *new* original image exactly once, shares first-original 13-file receipts, uses read-only independent physical auditor and explicitly accepts or rejects M08.4 based on 128 HOST input + 384 PL numerical comparisons across all 24 actual physical saves/reloads.
4. Only after first original paged state is accepted proceed to **M08.5** matched physical controls and guarded DDR ownership research; do not claim genuine PS DDR from this JTAG-host-staged state.
