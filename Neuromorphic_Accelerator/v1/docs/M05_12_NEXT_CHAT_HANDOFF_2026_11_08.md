> **LATEST CURRENT CI STATUS:** **Native CI independently VERIFIED at M05.12c implementation commit `c5fa13f433c9b0746892a71b029dc3ef9889eccb`:** [M05 workflow 42540072916](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42540072916) original job log explicitly records all seven new M05.12c tests `ok`, **258 M05 methods PASS**. The four previous workflows M01–M04 all PASS (20+21+28+22=91), giving **349/349 named native methods PASS**. These are host-side regression/synthetic report tests and prior standalone RTL smoke, **not Vivado evidence for the new four-IP customization**. Real M05.12c Vivado readback remains PENDING user. Next step remains the offline operator Vivado four-IP probe and inspecting `result.txt`, `01_candidate.txt`, `02_vivado.log`, `03_independent_audit.log` and fingerprints before further BD decisions. M05 open; no hardware authorization.

# CURRENT ACCELERATOR v1 M05.12 HANDOFF — 2026-11-08 local / 2026-11-09 UTC

**Repository:** Xtimetraveler-Prime/Thesis, exact branch `agent/neuromorphic-accelerator-v1-m05-sparse-onchip`; draft PR #79 **DO NOT MERGE**. M01–M04 complete. M05 open. No board, JTAG, XSDB, PS DDR, physical DMA, bitstream or physical evidence is authorized. Do not touch previously verified signed32 `hls/m05_rolling/m05_rolling.cpp`, generated RTL or evidence. Official MNIST test remains sealed.

**M05.11c accepted previously:** Original Vitis signed32 HLS Verilog + custom AXI-Lite/stream shell genuine operator-run Vivado 2025.2 XSim and independent raw-word 256b trace replay both PASS, `exit_status=0`, source checkout `bf20f33aa07df2b187bfb837ee5ba2a946cb7098`, evidence `neuromorphic_v1_m05_11c_real_hls_20261109T000446Z_keEFQy`. 24/24 status0 accepted then 8 provisional status4 committed0, both TLAST footers and 148 stalls. First earlier failed parser proof retained unmodified.

**M05.12a accepted native only:** DMA buffers/length-width, receive-first lifecycle, session/error quarantine and synthetic evidence checks; 15 native tests PASS. Real PS/DDR/cache/DMA driver not built.

**M05.12b now genuine offline Vivado catalog PASS:** owner `~/Thesis_Evidence/neuromorphic_v1_m05_12_ip_catalog_20261109T001921Z_4ZocHi`, checkout `1dc439c9e06e8580008857db52ccba63d25965ca`, `exit_status=0`, exact K26 part and `xilinx.com:ip:axi_dma:7.1`. Catalog default SG1, 32-bit stream and MM, length14, addr32, both directions, micro0/DRE0/async0. **This was not four configured 256b DMAs.** Preserve evidence folder.

**M05.12c now developed:** new `scripts/m05_12_dma_candidate.tcl`, `scripts/run_m05_12_dma_candidate.sh`, `scripts/m05_12_dma_candidate_audit.py`, `tests/test_m05_12_dma_candidate.py`; attempt 3 MM2S-only +1 S2MM-only **unconnected** 256-bit direct-SG0 length24 AXI DMA v7.1 instances in an in-memory K26 Vivado BD, check true CONFIG and interface presence, then independently validate raw report. Seven new **synthetic native** tests. **Next genuine operator step is running OFFLINE Vivado candidate config, no physical hardware.** Read [M05.12c engineering/runbook](M05_12C_FOUR_DMA_IP_CONFIGURATION_2026_11_08.md) for exact commands and raw-log collection. No genuine M05.12c Vivado PASS yet.

**Operator next commands (Vivado 2025.2 sourced):**
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
bash -n scripts/run_m05_12_dma_candidate.sh
bash scripts/run_m05_12_dma_candidate.sh
export DMA_CANDIDATE="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12c_dma_candidate_* | head -n 1)"
cat "$DMA_CANDIDATE/result.txt"
cat "$DMA_CANDIDATE/commit.txt"
cat "$DMA_CANDIDATE/01_candidate.txt" 2>/dev/null || true
tail -n 150 "$DMA_CANDIDATE/02_vivado.log" 2>/dev/null || true
cat "$DMA_CANDIDATE/03_independent_audit.log" 2>/dev/null || true
cat "$DMA_CANDIDATE/source_sha256.txt"
```

**Evidence policy:** Only after `exit_status=0`, genuine Vivado four-IP PASS and independent audit PASS may M05.12c be accepted. If Tcl/property/pin fails, preserve original logs and diagnose before any changes. Even passing M05.12c is **unconnected IP compatibility**, NOT functional DMA, PS/PL BD, DDR ownership or system timing. Next M05.12d needs individually reviewed connected BD, address partitions, clock/reset/CDC, cache/LINUX memory allocations, interrupts, error recovery and offline RTL/VIP tests. Physical hardware separately gated. Keep tests explained, roadmap, docs and handoff in sync. Never merge M05 without explicit user approval.
