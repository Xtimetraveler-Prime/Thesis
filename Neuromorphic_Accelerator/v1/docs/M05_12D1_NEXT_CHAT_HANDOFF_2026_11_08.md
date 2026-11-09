> **CURRENT SOURCE/CI VERIFICATION:** **CI VERIFIED at source+documentation commit `e49c8ed18f5206d887175588c6e05d5523459a4b`:** all five GitHub Actions workflows **SUCCESS**. [M05 workflow 42541636739](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42541636739) exercised **267 named M05 methods**: first Python discovery executed 266 PASS and **one Icarus-dependent SKIP** before Icarus was installed; then a mandatory post-install step compiled the exact RTL shell wrapper with Icarus and reran all eight M05.12d.1 tests, including the previously skipped elaboration (**8/8 PASS**). Prior accepted M01–M04 methods **22+28+21+20=91 PASS**. Therefore all **358 distinct named native methods have passed at least once**; none of these CI tests is genuine Vivado IP Integrator connected-net verification, which is still pending local operator evidence. Next accepted action: run OFFLINE `bash scripts/run_m05_12d1_axis_graph.sh` with Vivado 2025.2 sourced and return ORIGINAL `result.txt`, `01_axis_links.txt`, `02_vivado.log`, `03_independent_audit.log`, hashes and commit. Earlier genuine M05.12c K26 config evidence is already accepted, do not redo or edit it.

# CURRENT M05.12d.1 HANDOFF — 2026-11-08 local / 2026-11-09 UTC

**Repo** `Xtimetraveler-Prime/Thesis` · **Branch** `agent/neuromorphic-accelerator-v1-m05-sparse-onchip` · **PR #79 DRAFT, UNMERGED** · **M05 OPEN**. Do not touch `Loihi_Digital_Twin/v4`; do not reopen completed M05.11c neural execution. No physical board JTAG/XSDB, PS DDR, DMA writes or bitstreams authorized. Keep signed32 HLS kernel `hls/m05_rolling/m05_rolling.cpp` and generated RTL unchanged.

**M05.11c genuine generated RTL + transport shell XSim ACCEPTED:** original `neuromorphic_v1_m05_11c_real_hls_20261109T000446Z_keEFQy`, checkout `bf20f33aa07df2b187bfb837ee5ba2a946cb7098`, `exit_status=0`, 24 status0 committed24 and 8 status4 committed0 with valid TLAST/footer, independent frame replay PASS and 148 stalls.

**M05.12a host-only DMA admission/lifecycle:** accepted via native tests. No PS driver. **M05.12b** owner real K26 Vivado AXI DMA 7.1 catalog accepted: `neuromorphic_v1_m05_12_ip_catalog_20261109T001921Z_4ZocHi`.

**M05.12c owner real Vivado CONFIGURATION ACCEPTED:** `~/Thesis_Evidence/neuromorphic_v1_m05_12c_dma_candidate_20261109T003049Z_y5AEce`, source `0ea2178c71023250150609a2983a67bbd6c84ef2`, `exit_status=0`, genuine four unconnected DMA v7.1 K26 MM2S3/S2MM1, 256b AXIS/MM, SG0/direct, length24, addr32, proper interfaces and independent audit PASS. Exactly four `BD 41-737` CRITICAL WARNINGs caused by trying to set read-only async-clock property, despite verified actual=0. Focused source fix removes write, enforces readback0, adds native regression. Preserve original owner folder.

**M05.12d.1 NEW developed, genuine Vivado PENDING:** Four-stream BD **connectivity gate** creates unconnected PS/DDR offline in-memory K26 design with real four configured AXI DMA IPs and a Vivado HDL Module Reference wrapping the exact unchanged M05.11 transport shell. `rtl/m05_12/m05_12d_axis_shell_ref.v` exposes 4 native 256-bit AXIS interfaces with attributes, pass-through mapping all 54 original shell ports. `scripts/m05_12d1_axis_graph.tcl` uses four true Vivado `connect_bd_intf_net` nets and readback of both endpoint interfaces and point-to-point count; `scripts/m05_12d1_axis_graph_audit.py` independently fail-closes any mismatched/duplicated/missing net or DMA config. `scripts/run_m05_12d1_axis_graph.sh` creates new original evidence. 8 new native tests plus 1 read-only clock regression. CI now explicitly mandates Icarus elaboration of wrapper after installing `iverilog` (not just optional Python skip). **No original M05.12d.1 Vivado output yet. Do not mark PASS until user provides exact logs.** [Full new engineering+operator runbook](M05_12D1_OFFLINE_PL_AXIS_GRAPH_2026_11_08.md).

Next operator action, offline Vivado 2025.2, with a clean checkout and real logs:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m05_12*.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -q
bash -n scripts/run_m05_12d1_axis_graph.sh
bash scripts/run_m05_12d1_axis_graph.sh
export AXIS_GRAPH="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d1_axis_graph_* | head -n 1)"
cat "$AXIS_GRAPH/result.txt"
cat "$AXIS_GRAPH/commit.txt"
cat "$AXIS_GRAPH/01_axis_links.txt" 2>/dev/null || true
tail -n 160 "$AXIS_GRAPH/02_vivado.log" 2>/dev/null || true
cat "$AXIS_GRAPH/03_independent_audit.log" 2>/dev/null || true
cat "$AXIS_GRAPH/source_sha256.txt" 2>/dev/null || true
```

**Acceptance:** genuine exit0, Vivado four actual AXIS net PASS, independent Python 4-link audit PASS, all source/checkout/correct IP config. **Scope only connected PL AXIS shell↔DMA;** no HLS, PS-DDR, clock/reset, AXI-Lite controls or full BD implementation yet. If FAIL, preserve the first original evidence and fix RTL interface inference/BD Tcl only where justified, never kernel, never weaken tests. Follow remaining M05.12d.2 PS address/clock/DDR planning only after inspection. M05.13 timing/physical remains separate.
