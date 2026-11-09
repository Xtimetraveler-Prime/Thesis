# M05.12c — Four-direction AXI DMA v7.1 offline IP customization gate

**2026-11-08 local / 2026-11-09 UTC · Active M05 branch, draft PR #79, NO HARDWARE**

## 1. Verified prerequisite: genuine M05.12b catalog discovery

Original operator evidence directory: `~/Thesis_Evidence/neuromorphic_v1_m05_12_ip_catalog_20261109T001921Z_4ZocHi`; original source commit `1dc439c9e06e8580008857db52ccba63d25965ca`, **exit_status=0**. Vivado 2025.2 successfully instantiated an *unconnected* catalog-only AXI DMA 7.1 IP against `xck26-sfvc784-2LV-c`. The reported defaults were **SG1; 32-bit MM2S/S2MM streams and AXI data; length14; address32; MM2S and S2MM both enabled; micro0; DRE0; async0**. This is **original user-supplied real Vivado evidence**, not synthetic CI. Preserve this evidence folder verbatim. It did not test DMA read/write or clock/reset connections.

Previously accepted M05.11c: real original signed32 HLS generated RTL + transport shell XSim and independent frame replay **PASS** on checkout `bf20f33aa07df2b187bfb837ee5ba2a946cb7098` in `neuromorphic_v1_m05_11c_real_hls_20261109T000446Z_keEFQy`; 24/status0/committed24, 8/status4/committed0, 148 HLS and output stall cycles. HLS kernel, prior proof and generated Verilog remain unchanged.

## 2. Why a *separate four-IP configuration* gate?

The current shell exposes **three distinct 256-bit AXI4-Stream ingress channels** (neurons, synapses, external) and **one 256-bit stream egress** (trace). Its wrapper expects one TLAST at the last packet beat; the original neural engine's native streams remain 128/192/128/192 bits and unchanged. An initial MM2S direct-mode transfer per nonempty input is architecturally simple and corresponds to exactly one TLAST; RX is armed first and the S2MM packet contains neural traces plus a terminal TLAST footer.

The real M05.12b defaults **cannot** prove compatible with this shell: SG is enabled, widths are 32 bits, and 14-bit length is insufficient for larger workloads. M05.12c therefore attempts to configure four **unconnected, single-direction** AXI DMA v7.1 instances *without* committing to the final physical IP count or PS interconnect architecture.

| Temporary IP instance | Direction | AXIS | AXI memory-map | Requested length width | Requested mode |
| --- | --- | --- | --- | --- | --- |
| `dma_neurons` | MM2S only | 256b | 256b | 24 | direct (SG0), micro0 |
| `dma_synapses` | MM2S only | 256b | 256b | 24 | direct (SG0), micro0 |
| `dma_external` | MM2S only | 256b | 256b | 24 | direct (SG0), micro0 |
| `dma_trace` | S2MM only | 256b | 256b | 24 | direct (SG0), micro0 |

All candidates request synchronous clock option, DRE off, and **provisional 32-bit addressing only for the candidate check**. The address width is NOT approval to use a specific DDR region or assertion that future Linux-allocated buffers sit below 4 GiB. With DRE disabled, any eventual buffer address must satisfy the actual IP alignment constraints. No physical memory address is assigned by the script.

The native M05.12a planner calculates maximum worst-case packet lengths: **262144 external events ×32 = 8,388,608 input bytes**; **1024 neurons ×64 ticks + terminal = 2,097,184 output bytes**. A 24-bit length field holds up to `2^24−1 = 16,777,215` bytes. This is a **logical length admission bound**, not proof that a single contiguous physical buffer of that size is available or cache-coherent.

Reference: AMD [PG021 v7.1 User Parameters](https://docs.amd.com/r/en-US/pg021_axi_dma/User-Parameters) for supported properties; [Direct Register Mode](https://docs.amd.com/r/en-US/pg021_axi_dma/Direct-Register-Mode-Simple-DMA) for RS, address and LENGTH-last; [S2MM_LENGTH](https://docs.amd.com/r/en-US/pg021_axi_dma/S2MM_LENGTH-S2MM-DMA-Buffer-Length-Register-Offset-58h) for receive-first packet capacity, actual byte count and undefined short-buffer behavior. Those are normative IP rules; this stage has not shown the customized K26 IP can satisfy them until the user runs genuine Vivado.

## 3. Actual new files and evidence contract

- `scripts/m05_12_dma_candidate.tcl`: requires genuine `xilinx.com:ip:axi_dma:7.1` from current Vivado catalog, creates a **new in-memory project** on the specified K26 part, adds exactly three candidate MM2S-only and one S2MM-only AXI DMA IP cells, applies required CONFIG settings, then **re-reads every required CONFIG key and direction-specific AXI/AXIS interface**. It fails on readback mismatch; it deliberately does not connect PS, clocks, resets or DDR. `create_bd_design` may stage temporary `.bd` contents **inside its new dedicated evidence directory**; it never opens/modifies an existing project.
- `scripts/run_m05_12_dma_candidate.sh`: refuses wrong parameters/Vivado version, creates a fresh unique evidence folder, saves commit + working-tree status + SHA256 manifests, runs offline `vivado -mode batch`, checks actual Tcl PASS, invokes independent Python audit, and records `result.txt` even on script failures *after* evidence creation. It never invokes JTAG, board programming, synthesis, routing or bitstream generation.
- `scripts/m05_12_dma_candidate_audit.py`: read-only strict parser of actual Vivado IP-property/pin transcript. Requires all four exact directional cells and expected properties/pins, K26 part, v7.1 VLNV and an explicit **UNCONNECTED** scope marker. Missing, duplicate, malformed or mismatched values fail. Synthetic fixtures are separate from actual Vivado.
- `tests/test_m05_12_dma_candidate.py`: **seven** synthetic host regression methods (see M05_TESTS_EXPLAINED.md); they do not run Vivado.

**Acceptance status:** M05.12b genuine catalog discovery **PASSED**. New M05.12c source and synthetic tests **DEVELOPED**; operator's genuine Vivado 2025.2 customized four-IP readback **NOT YET PROVIDED**. Even a future M05.12c PASS proves only that four disconnected IP instances expose the required configuration, **not an integrated PS/PL, functional DMA, DDR cache, CDC, routability or throughput**.

## 4. No-board operator commands

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD
git status --short
cd Neuromorphic_Accelerator/v1

python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m05_12*.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -q
python3 -m unittest discover -s tests -p 'test_m04*.py' -q
python3 -m unittest discover -s tests -p 'test_m03*.py' -q
python3 -m unittest discover -s tests -p 'test_m02*.py' -q
python3 -m unittest discover -s tests -p 'test_m01*.py' -q

# With Vivado 2025.2 already sourced: OFFLINE; NO BOARD.
bash -n scripts/run_m05_12_dma_candidate.sh
bash scripts/run_m05_12_dma_candidate.sh

export DMA_CANDIDATE="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12c_dma_candidate_* | head -n 1)"
echo "M05_12C_EVIDENCE=$DMA_CANDIDATE"
cat "$DMA_CANDIDATE/result.txt"
cat "$DMA_CANDIDATE/commit.txt"
cat "$DMA_CANDIDATE/working_tree_status.txt"
cat "$DMA_CANDIDATE/01_candidate.txt" 2>/dev/null || true
tail -n 150 "$DMA_CANDIDATE/02_vivado.log" 2>/dev/null || true
cat "$DMA_CANDIDATE/03_independent_audit.log" 2>/dev/null || true
cat "$DMA_CANDIDATE/source_sha256.txt"
```

**PASS requires:** `result.txt exit_status=0`, original genuine Vivado configuration PASS, independent Python audit PASS, 4 exact candidate cells with correct 256b/24bit/directions/simple-mode readback and actual expected IP interface pins; verify K26 part, VLNV, original evidence folder and source commit. **On FAIL:** preserve original candidate evidence unchanged; investigate actual first property/pin/permission issue. Do not weaken requirements or change the signed32 neural engine, and do not relabel previous catalog discovery as a four-IP PASS.

## 5. Pending engineering gates after M05.12c

M05.12d: build and validate an *offline connected* design candidate: choose PS/PL AXI master/slave and DDR interface roles, two separate AXI4-Lite base regions, DMA register apertures, coherent/noncoherent DMA buffer ownership (with explicit Linux driver model), clocks/resets/CDC, interrupts and error/abort/isolation strategy. Check connected BD interface widths/timing constraints and the PG021 simple-DMA ordering: program S2MM receive-first and length last; read/arm MM2S direction(s), then issue HLS ap_start exactly once; concurrently drain trace until actual HLS ap_done/ap_return, then FINISH/footer/TLAST; verify S2MM actual byte count, memory write completion, cache invalidation, bridge COMPLETE and ACK before atomic publication. Disable reuse after failures until independently verified isolation/reset. A physical board run, JTAG, DDR writes, any actual system performance/timing/power claim remain separate and require authorization.

**Do not merge PR #79 or mark M05 complete.**
