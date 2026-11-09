# M05.12 — PS/PL DMA preparation: admission, lifecycle and IP-catalog gates

**2026-11-08 local / 2026-11-09 UTC · SAME active M05 branch, draft PR #79 · No board.**

## Verified prerequisite: M05.11c closed

The operator's genuine Vivado 2025.2 integrated original Vitis signed32 HLS Verilog + existing AXI4-Lite/AXIS transport shell XSim run on `bf20f33aa07df2b187bfb837ee5ba2a946cb7098` generated original evidence `~/Thesis_Evidence/neuromorphic_v1_m05_11c_real_hls_20261109T000446Z_keEFQy`. The operator supplied the true `result.txt` status **exit_status=0**, `04_xsim.log` with real XSim PASS, and `05_dma_frame_replay.log` with separate raw 256-bit accepted-word replay PASS. Both same-instance runs were correct: **24 status0 committed24**, **8 provisional status4 committed0**, with 2 correct footer/TLAST words, **148 DMA sink stalls and 148 genuine HLS output stalls**. The earlier failed postcheck folder from 2026-11-08 remains untouched and still says exit_status=1. We did not re-run Vivado in the assistant environment or access the original operator-local folder directly; acceptance is based on the operator-supplied original results and the provenance-checking runner already in the repository. This proves simulated integrated RTL and semantics, NOT physical DMA/DDR/cache/PS operation.

## 1. M05.12 scope and current boundaries

**M05.12a — implemented, native-verified:** `src/neuromorphic_accelerator_v1/m05_12_dma_contract.py` produces an immutable, hardware-agnostic DMA transfer admission plan from the existing accepted `RunPlan` and `build_mm2s_buffers`. It enforces:
- 256-bit (32-byte) transport on all proposed ports; neurons 16B+16B pad, synapses 24B+8B pad, events 16B+16B pad.
- One MM2S transfer per **nonempty** stream, with TLAST only at the final beat; **no zero-byte descriptor and no automatic descriptor splitting**. If a physical engine cannot support full length in one packet, the design needs separately verified SG/packet framing rather than pretending to be equivalent.
- S2MM **maximum successful** capacity = `32 * (neuron_count * ticks + 1)` (last beat is terminal footer). Real late-failure output can be shorter, but programmed S2MM length MUST be large enough for the maximum successful packet and independent actual-byte count must be checked after completion.
- An explicit `DMALimits(length_width=...)` from the *eventually reviewed* Vivado IP settings. It rejects the common insufficient small length width, wrong streaming width, unverified SG/micro configurations, oversize buffers, and invalid session IDs. **The limits object is an assumption, not evidence from actual instantiated IP.**
- Receive-first lifecycle `PREPARED -> RECEIVE_ARMED -> ACTIVE -> FINALIZING -> VERIFIED or FAULT`; host-only synthetic MM2S completion and S2MM evidence require exact actual bytes, final TLAST, device ownership, cache clean/invalidated proof, no outstanding DDR writes, full transport quiescence, independently latched HLS status, and exact atomic `accept_dma_frame` output. Nonzero HLS status returns zero committed rows and sticky FAULT; no automatic recovery. A real adapter must separately establish bridge COMPLETE/ACK before publishing success.

**M05.12b — offline catalog probe implemented, genuine Vivado execution PENDING:** `scripts/run_m05_12_ip_catalog.sh` plus `scripts/m05_12_ip_catalog.tcl`. A sourced Vivado 2025.2 can create an **in-memory scratch K26 project**, enumerate its actual AXI DMA IP VLNV and available length/width/channel/mode parameters and record the defaults in a *new immutable evidence directory*. There is no connected block design, hardware system, address assignment, synth, bitstream, JTAG or device. The probe does not change any existing project. Source-only tests exercise bash syntax, --help and prohibited hardware actions, **not** real Vivado functionality. Do not call the IP catalogue executed until the operator provides its logs.

**M05.12 full PS/PL integration remains NOT IMPLEMENTED:** no chosen real AXI DMA instance count, no validated K26 BD/PS bus connectivity, no actual two AXI-Lite physical base addresses, no reserved DDR buffers/ownership, no Linux kernel DMA driver, no cache-coherence proof, no source or sink interrupts, no actual command ordering across independent PS/PL channels, no real timeout/reset/quiescence fence, no real DMA transfer, no end-to-end PS/PL routed timing. These are next engineering gates, not inferred from native tests.

## 2. AMD AXI DMA v7.1 PG021 design checks (candidate, NOT implementation)

Official source documentation (v7.1, 2025-06-24):
- https://docs.amd.com/r/en-US/pg021_axi_dma/User-Parameters : `c_sg_length_width` default 14, configurable 8..26 bits; 256-bit stream widths are supported, but actual IP customization must be checked in Vivado.
- https://docs.amd.com/r/en-US/pg021_axi_dma/MM2S_LENGTH-MM2S-DMA-Transfer-Length-Register-Offset-28h : direct-mode length writing starts MM2S; nonzero byte count is required.
- https://docs.amd.com/r/en-US/pg021_axi_dma/S2MM_LENGTH-S2MM-DMA-Buffer-Length-Register-Offset-58h : programmed S2MM_LENGTH specifies available RX buffer and must be >= largest packet; after completion register reports actual transferred length. Too-small RX length has **undefined behavior** per PG021.
- https://docs.amd.com/r/en-US/pg021_axi_dma/Field-Descriptions : scatter-gather, micro DMA, DRE and async clock modes have separate constraints and must NOT be silently assumed interchangeable.

Concrete worst-case (currently admitted `RunPlan`): **1024 neurons ×64 ticks =65536 trace rows; 65537 ×32 =2,097,184 S2MM bytes**. Worst-case external data can reach `64 ×4096 ×32 =8,388,608` bytes. A *candidate* common direct-mode length field width of **at least 24 bits** covers these unfragmented byte counts; do NOT commit to this setting until the actual Vivado 2025.2 K26 IP customization is inspected. Standard default 14 bits is not enough for the large examples. DMA buffer allocation and Linux constraints may impose lower per-transaction bounds even if the length register permits them.

## 3. Hardware architecture yet to verify

Candidate external connectivity (not instantiated): a 256-bit stream-capable MM2S engine for each of the three existing ingress shims; one independent S2MM streaming receiver for the trace packetizer; two **separately mapped** AXI4-Lite slave regions (original HLS and custom shell), plus independent DMA control registers. Vivado design decisions remain open: single vs multiple AXI DMA cores/SG, actual 256-bit customization and AXIS TLAST semantics, PS AXI master/control port, HP/HPC DDR data path, address/ID mapping, clock/reset synchronization, interrupts, and allowed DDR ownership. Avoid hidden CDC; M05.11c is single-clock. 

Minimum receive-first host sequence for a future **verified** adapter: admit immutable RunPlan -> reserve separate nonoverlapping DMA-capable buffers and establish ownership -> flush MM2S CPU writes for noncoherent DMA -> prepare S2MM reception and device ownership -> arm S2MM **before** shell START -> configure/verify independent AXI-Lite banks -> arm source channels for nonzero input lengths, service concurrently -> latch actual HLS ap_done and ap_return -> request shell FINISH -> wait for terminal TLAST/S2MM completion, actual transferred bytes and input completion (success case), invalidate RX cache only once DMA writes are drained -> independently verify footer/session/count and no outstanding writes -> verify shell COMPLETE and acknowledge success -> publish complete committed frame. On **any** fault/timeout/stale ID/corrupt TLAST: do not publish, isolate and quiesce all DMA paths, verify independent reset/flush, require explicit new session. This is a specification, **not an implemented Linux/PS algorithm**.

The first true hardware step is a controlled block-diagram/IP design and external memory-ownership review; physical FPGA, JTAG and board DDR must await explicit user authorization. M05.13 full routed timing and physical measurements are separate.

## 4. Native and offline operator verification

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m05_12*.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -q
python3 -m unittest discover -s tests -p 'test_m04*.py' -q
python3 -m unittest discover -s tests -p 'test_m03*.py' -q
python3 -m unittest discover -s tests -p 'test_m02*.py' -q
python3 -m unittest discover -s tests -p 'test_m01*.py' -q
```

With Vivado 2025.2 previously sourced, for **offline IP catalog only** (NO BOARD):

```bash
bash -n scripts/run_m05_12_ip_catalog.sh
bash scripts/run_m05_12_ip_catalog.sh
export DMA_CATALOG="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12_ip_catalog_* | head -n 1)"
cat "$DMA_CATALOG/result.txt"
cat "$DMA_CATALOG/commit.txt"
cat "$DMA_CATALOG/capabilities.txt"
tail -n 90 "$DMA_CATALOG/01_catalog.log"
cat "$DMA_CATALOG/source_sha256.txt"
```

Report exact IP VLNV and available properties, not a fabricated BD. An IP probe failure must keep its original result/logs untouched and be diagnosed in script or Vivado, not in the neural engine. For real BD design, actual peripheral/DDR address assignments, and physical operations, obtain separate approval/architecture review.

## 5. Existing accepted evidence preserved

- M05.11a genuine standalone XSim PASS: `neuromorphic_v1_m05_11_bridge_20261108T224957Z_AQzMlG`.
- M05.11b genuine standalone XSim PASS: `neuromorphic_v1_m05_11_axil_20261108T230817Z_HFWBlw`.
- First M05.11c integrated XSim PASS but full replay FAIL: `neuromorphic_v1_m05_11c_real_hls_20261108T235448Z_NzKhyY` (exit_status=1).
- **Accepted M05.11c genuine integrated XSim and independent replay PASS**: `neuromorphic_v1_m05_11c_real_hls_20261109T000446Z_keEFQy` (exit_status=0).
- M05.12a **249 M05 native methods + 91 M01–M04 =340 PASS** at source commit `9577fc9b8f98b1d7a2c5f5334de8ba914fe4fdd7`, GitHub Actions [M05 run 42538766750](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/42538766750). M05.12b adds 2 source-only safety methods; final HEAD CI must be inspected to establish combined count **251 M05 +91 =342**.
