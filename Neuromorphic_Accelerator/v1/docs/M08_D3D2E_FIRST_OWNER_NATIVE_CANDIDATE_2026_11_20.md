> **UPDATE — FIRST OWNER POSTROUTE SUMMARY + PHYSICAL SCRIPT STAGING.** Owner now supplied full-routed summary for the first exact candidate: `reports/20_route_drc.rpt` SHA **`3c4c1d8bd304dc71eb4f21bddee7a9c35cbf2053857a805c097bc2e96f0157c6`**, `reports/21_route_timing.rpt` SHA **`cdeaf520fbbb944de4148cecca290651125c3009a2375966ee2b5d17f584c59f`**, `reports/23_route_clocks.rpt` SHA **`836479b2faf87c71df2f50b9b19128d4b6ba7e9ac6dd72a41a6f42383ae43820`**. Fully Routed; seven DRC warnings (PDCN-1569×3, REQP-1857×1, REQP-1858×2, RTSTAT-10×1); **WNS +1.844 ns, WHS +0.010 ns**, setup and hold 0 failing endpoints, pulse width +4.238 ns. PL0 and PL1 reported 10 ns periods, debug TCK 50 ns. Exact *full DRC warning details (pins, equations, three BRAM paths, RTSTAT names)* were **NOT INCLUDED** in the user's abbreviated grep; original full DRC/timing report contents still must be reviewed. The new **STAGED-ONLY** `scripts/m08_d3d2e_queue_readback_once.tcl`, `scripts/run_m08_d3d2e_queue_physical_once.sh`, and `scripts/m08_d3d2e_queue_physical_audit.py` have queue acceptance/service and 512-value physical parity plan. **DO NOT RUN the physical shell**; the original first-image inspector still unconditionally exits 2 before opening JTAG. These staged files and their static mock tests are not hardware evidence. The first owner image remains UNRELEASED.\n\n# M08 D3.D.2E M32Q — first owner-native candidate; exact-image review PENDING

**Owner-reported 2026-11-20 at 16:35 local.** This records an **original first offline Vivado 2025.2 candidate**, NOT a reviewed/released physical image and NOT a physical KV260 result. It supplements the D3.D.2E development plan and supersedes its historical "no image built" status. M08 OPEN, M09 PLANNED; draft PR #93 remains stacked on D3.D.2D PR #92. No merge or new board programming authorized.

## Owner first-original facts reported to the project

- **Original native folder:** `/home/dna/Thesis_Evidence/M08/m08_d3d2e_queue_GFz0SbiC`
- **Original UNRELEASED bit:** `bitstream_candidate/m08_d3d2e_queue_lif_jtag_UNRELEASED.bit`
- **New bitstream SHA256:** `2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc`
- **Bitstream size:** `7,797,844` bytes.
- The user pasted genuine owner-terminal output `Bitgen Completed Successfully`, `vivado_build_exit=0`, and **12/12 original native SHA receipt checks marked OK**, including Vivado log/journal, RTL and fabric POR copies, full routed DRC, timing, utilization and clocks reports, metadata and new original bit. The first-read-only `m08_d3d2e_queue_native_review.py` **inspected 12 receipts and source hashes**, then (by design) returned **exit 2**, `drc_allowlist=NONE_NEW_IMAGE_PENDING_HUMAN_REVIEW`, `timing_acceptance=NOT_REVIEWED`, `image_specific_gate=BLOCKED`, `physical_programming=NOT_AUTHORIZED`.
- **Not supplied** in this handoff: full first original `20_route_drc.rpt`, `21_route_timing.rpt`, `23_route_clocks.rpt`, or detailed original `30_native_result.txt` contents. Therefore the original new-image DRC *counts/instances/pins/equations*, routed WNS/TNS/WHS/THS, endpoint violations, unconstrained paths, full exact report hashes and hardware clock constraints are **unknown**, and no new exact-image acceptance gate can truthfully pass. The zero-warning Bitgen Tcl command summary is **not equivalent** to a full routed DRC report.
- The assistant has not accessed the owner's private M08 original directory. No live hardware work performed or authorized. The original D3.D.2D accepted bitstream SHA `f50a156342eaf1173a3869b5316e4edc1d59662d9f0d687bcec600f7b0efdeab` and all its original evidence must remain unchanged.

## Mandatory next step: read-only first-original review (NO JTAG, NO REBUILD)

Owner should run these **read-only** commands on the first original M32Q candidate from Linux VS Code (do not edit the owner files). The local native gate intentionally exits **2** until the image-specific review exists.

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d2e-tick-event-queue
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d2e-tick-event-queue
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
RUN="$HOME/Thesis_Evidence/M08/m08_d3d2e_queue_GFz0SbiC"
BIT="$RUN/bitstream_candidate/m08_d3d2e_queue_lif_jtag_UNRELEASED.bit"
test -d "$RUN" && test ! -L "$RUN"
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt)
test "$(sha256sum "$BIT" | awk '{print $1}')" = "2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc"
test "$(stat -c %s "$BIT")" -eq 7797844
python3 scripts/m08_d3d2e_queue_native_review.py --run-dir "$RUN"
# EXPECTED EXIT 2 (FIRST IMAGE REVIEW REQUIRED); no programming.
```

After confirming the intentional exit 2, copy/paste the following **read-only report summary** into the conversation, and preferably upload **unchanged copies** of the complete original `20_route_drc.rpt`, `21_route_timing.rpt`, `23_route_clocks.rpt`, `30_native_result.txt` and `99_evidence_sha256.txt` for complete independent review. **Do not edit the originals, and do not regenerate any receipt ledger**.

```bash
RUN="$HOME/Thesis_Evidence/M08/m08_d3d2e_queue_GFz0SbiC"
sha256sum "$RUN/reports/20_route_drc.rpt" "$RUN/reports/21_route_timing.rpt" "$RUN/reports/23_route_clocks.rpt" "$RUN/reports/30_native_result.txt"
grep -nEi 'Checks found|PDCN-1569|REQP-1857|REQP-1858|RTSTAT-10|Warning|Critical Warning|Error|Design State' "$RUN/reports/20_route_drc.rpt"
grep -nEi 'WNS|TNS|WHS|THS|Failing Endpoints|Unconstrained|No clocks|Pulse Width|Clock Summary' "$RUN/reports/21_route_timing.rpt"
cat "$RUN/reports/23_route_clocks.rpt"
cat "$RUN/reports/30_native_result.txt"
```

**Never run a new Vivado build merely to clear the review exit 2.** Review exact new warnings including all printed vendor XSDB LUT pins/equations, JTAG FIFO paths and RTSTAT sample, and all timing requirements; do **not** transplant D3.D.2D exception profiles. Only after reviewing the *actual* original reports may a new image-bound exact native gate with mutation-negative tests be implemented. This gate must independently return exit 0 on the untouched original candidate **before** any owner-authorized one-shot shell/Tcl/programming path is staged/released. Physical activity subsequently needs cooling, UART recording, stock recovery, exclusive exact K26 JTAG, new physical SHA receipts and independent 512-value M06 readback/auditor. Nothing in this record authorizes any board operation.
