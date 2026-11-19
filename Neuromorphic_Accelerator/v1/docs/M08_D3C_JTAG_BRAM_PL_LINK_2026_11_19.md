# M08 D3.C — Linux-optional PL JTAG communication proof

**Date:** 2026-11-19. **Branch:** `agent/neuromorphic-accelerator-v1-m08-d3c-jtag-pl-link`. **Stage:** new standalone PL transport subcheckpoint within M08; not a finished neural engine or a claim of fully independent system clocking.

## Why we changed direction

Owner's second actual KV260 JTAG test programmed the D3.2 **passive** fan image with the expected SHA and Vivado startup HIGH, while Linux then lost SSH. The owner power cycled, observed normal stock SSH/ICMP and the stock overlay restored. The fan was observed working. Owner explicitly prioritizes out-of-band FPGA results over preserving a live Linux session. We therefore distinguish:

- **Standalone verification:** program a new FPGA image through USB/JTAG, read test/inference results back over JTAG without SSH, then power-cycle when necessary.
- **Linux-integrated system mode:** independent, later validation of `dfx-mgr`, PS HPM AXI, DDR paging, network and kernel services.

The first mode is a research validation path, **not** a claim that the FPGA is PS-independent: its initial AXI and debug clocks are sourced from **PS `pl_clk0` nominal 100 MHz**. Whether they continue if Linux fails is an essential empirical question. Original suspect HPM0 image SHA `a8ed0e4...` remains quarantined; original D3.2 passive .bit SHA `07af9e26905fd72b4d6b5845cbb4e309ecbefa83745a7c371769648cd0bdd547` cannot provide an inference/result channel.

## Implemented D3.C test circuit

```text
Owner PC (Vivado Hardware Manager)
        │ USB JTAG
        ▼
JTAG-to-AXI Master v1.2 (inside PL)
        │ 32-bit AXI master
        ▼
AXI SmartConnect v1.0
        │
        ▼
AXI BRAM Controller v4.1
        │
        ▼
Block Memory Generator v8.4
  1,024 x 32-bit (4 KiB)
  address 0xA0000000–0xA0000FFF

PS8 from KV260 board preset:
  - HPM0_FPD, HPM1_FPD, HPM0_LPD: DISABLED.
  - nominal PS pl_clk0 100 MHz → PL JTAG/AXI/BRAM clock
  - PS pl_resetn0 → synchronized proc_sys_reset
  - TTC0 WAVEOUT channel 2 → fan A12 / LVCMOS33
```

**Communication test:** write `A5A55A5A`, `12345678`, `DEADBEEF`, `0BADF00D` to four successive 32-bit BRAM locations; read each location back via JTAG; compare byte-exact word. An accepted receipt proves bidirectional JTAG-to-PL AXI/BRAM access **for that observed run**, including the clock/reset and vendor debug core in the observed conditions. It is **not** a hardware-generated neural result, performance benchmark, tested SRAM throughput, DDR paging or demonstration of Linux shutdown tolerance unless captured during Linux unavailability. Initial JTAG transactions are diagnostic, not high-speed runtime transport.

The initial Vivado BD is a **first-party offline script** built from the same KV260 PS board preset and TTC0 EMIO fan route as the previously physically programmed passive candidate. No PS-to-PL master is connected, no Linux DTBO is created and no AXI UIO/MMIO node is used.

### New files

- `scripts/m08_d3c_jtag_bram_build.tcl` — creates NEW project, PS fan route, JTAG AXI → SmartConnect → AXI BRAM Ctrl → BRAM, 4 KiB address map, PS PL0 clock/reset, validates BD, runs genuine native synthesis/place/route and writes a new **UNRELEASED** bitstream candidate **on the owner PC**. It cannot access the physical board.
- `scripts/run_m08_d3c_jtag_bram_pc.sh` — runs native Vivado 2025.2 in a fresh owner PC `~/Thesis_Evidence/M08/m08_d3c_jtag_link_*` directory, writes 99 SHA receipt and runs source+native auditor. It never reuses earlier bitstreams.
- `scripts/m08_d3c_jtag_bram_gate.py` — rejects changed source/deployment actions, malformed/changed native artifacts, nonzero Vivado exit, found DRC violations, incorrect K26/board/PS HPM/fan/native mapping, original bad/passive image reuse and false physical claims. It now also requires nonnegative routed setup/hold timing and accepts **only an exact, scoped, owner-reviewed seven-warning vendor JTAG/debug DRC profile** (or genuinely zero DRC findings); all changed/unknown/error/critical DRC findings remain blocking.
- `scripts/m08_d3c_jtag_bram_readback_once.tcl` — **separate future physical experiment**, only on explicit `M08_D3C_ALLOW_PROGRAM=YES`; rehashes native candidate, checks cable/part, programs once, discovers JTAG AXI and performs four read/write pairs, saves PC-only result. No SSH/PS register transactions/DFX-manager changes.
- `scripts/run_m08_d3c_jtag_bram_physical_once.sh` — checks owner native receipt and arms bounded single hardware attempt with a timeout, separate journal/log/hash evidence; no automatic retry.
- `tests/test_m08_d3c_jtag_bram_gate.py` — synthetic negative tests for source, identity, tampering and hardware independence. No physical hardware access.

## Owner PC source and native build instructions

On owner Linux VS Code terminal, with local Vivado **2025.2** installed (do not use the original D3.2 passive run folder):

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3c-jtag-pl-link
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3c-jtag-pl-link
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1

python3 -m compileall -q src scripts tests
bash -n scripts/run_m08_d3c_jtag_bram_pc.sh
bash -n scripts/run_m08_d3c_jtag_bram_physical_once.sh
python3 -m unittest discover -s tests -p 'test_m08_d3c_jtag_bram_gate.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -v
python3 scripts/m08_d3c_jtag_bram_gate.py --source-only

source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
bash scripts/run_m08_d3c_jtag_bram_pc.sh
```

The last command is the native synthesis/route/bitgen phase. It requires the actual owner PC Vivado installation and prints a **new** `M08_D3C_PC_NATIVE_BRAM_CANDIDATE_UNRELEASED=<run>` directory only after all evidence succeeds. Then:

```bash
RUN="<NEW_m08_d3c_jtag_link_RUN_PRINTED_ABOVE>"
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt)
python3 scripts/m08_d3c_jtag_bram_gate.py --run-dir "$RUN"
cat "$RUN/reports/30_native_result.txt"
sha256sum "$RUN/bitstream_candidate/m08_d3c_jtag_bram_UNRELEASED.bit"
```

**If native Vivado fails, stop and share:** `$RUN/00_vivado.log`, `$RUN/01_vivado.jou`, any generated `reports/` files, and the original error. Do not re-run against the same output directory or edit its hash receipt. The Tcl is new and has **not** been verified by real owner Vivado yet; synthetic tests are not evidence of a successful hardware bitgen.

## Physical JTAG write/read after native image is accepted (explicit operator action only)

With the board powered, USB JTAG connected, independent backup fan verified, UART recording if desired, and once source/native gate is accepted:

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
RUN="<NATIVE_D3C_RUN_ALREADY_VERIFIED>"
export M08_D3C_ALLOW_PROGRAM=YES
bash scripts/run_m08_d3c_jtag_bram_physical_once.sh "$RUN"
unset M08_D3C_ALLOW_PROGRAM
```

Expected `M08_D3C_HARDWARE_FOUR_WORD_BRAM_READBACK_SUCCEEDED`, output directory `M08_D3C_HARDWARE_RESULT_DIR` containing `80_four_word_readback.txt`, Vivado journal/log, original executed Tcl and 99 SHA receipt. The program command may cause SSH loss; the test **does not use SSH**. If JTAG AXI master cannot be discovered, AXI clock/reset stalls, BRAM doesn't echo expected values, or Vivado times out, preserve evidence, do not retry automatically, capture UART state and power-cycle back to stock. Hardware runner has bounded timeout; it cannot guarantee a stalled AXI transaction completes.

After successful hardware evidence, **next engineering checkpoint is** a PL AXI-Lite command/result interface tied to a bounded existing M06 LIF/event engine (deterministic input pattern, completed event count, membrane/spike digest); compare actual FPGA result with the Python/M02 oracle and save SHA-trace. Replace BRAM echo with actual neural computations, add ILA if necessary, and later investigate throughput/DDR separately. Do not call this BRAM proof neural inference.

## Acceptance and nonclaims

1. **Source gate and negative tests** prove only source-level constraints.
2. **Genuine owner-PC native build** must pass Vivado BD, synthesis, route, DRC and byte-hash checks; a generated `.bit` alone does not validate FPGA execution.
3. **Physical link validation** requires the exact JTAG readback receipt and matching PC-side expected values from all four addresses. A successful program or available soft debug master alone does not count.
4. **OS independence** remains an empirical question; a JTAG BRAM PASS while Linux is responsive is still valuable, but JTAG access after SSH loss must be separately demonstrated before claiming independence.
5. Original M08 PS HPM0 image remains quarantined. No inference/DDR/paging assertions are attached to D3.C.

## 2026-11-19 owner native build result — read-only IP property warnings (NO PHYSICAL RELEASE)

Owner original `m08_d3c_jtag_link_EFPQEfJu`: genuine Vivado 2025.2 synthesis/route/bitgen completed; all **10/10** SHA256 receipt entries matched, bitstream size **7,797,837 bytes**. However, the native log contains two **CRITICAL WARNING [BD 41-737]** diagnostics: `C_EXT_RESET_HIGH` on `rst_pl0` and `MEM_DEPTH` on `bram_ctrl` are read-only, so attempted settings were rejected. Python acceptance correctly **REJECTED** this entire immutable original candidate. Final bitgen's local zero-warning summary does not supersede earlier critical warnings. The first attempt must never be relabeled as accepted or programmed.

Source correction: remove the two forbidden writes, retain the PS active-low reset connection and exact 4 KiB AXI address mapping, and **fail closed** after `validate_bd_design` unless native readbacks show `C_EXT_RESET_HIGH=0`, controller-derived depth positive, and connected BRAM 1024 × 32-bit. The native result receipt now records the actual derived reset and memory properties, which the Python acceptance gate separately checks. No DRC/timing/physical waiver. These checks require a **fresh** owner Vivado 2025.2 run in a new `m08_d3c_jtag_link_*` directory; old files and SHA receipt stay untouched. If derived properties differ, stop and inspect actual BD/connection automation; do not force read-only values, edit evidence, or program hardware. Physical JTAG remains blocked until new owner-native build, original SHA review, timing/DRC review and separate owner approval.

## 2026-11-19 next owner result — fully routed bitstream, constrained timing met, vendor JTAG warnings (NO BOARD)

Owner candidate `m08_d3c_jtag_link_A2SUrkhI` was successfully generated with genuine Vivado 2025.2, the native log no longer reported the earlier rejected read-only property critical warnings, and all 10 SHA256 evidence artifacts were accepted. Owner pasted the original `20_route_drc.rpt` and timing summary without editing the evidence. **Timing closes** at 100 MHz PS PL0, WNS +5.907 ns, TNS 0, WHS +0.011 ns, THS 0, no failing setup/hold endpoints.

**Important:** Vivado DRC reported **seven actual Warning-level findings**, not zero checks. Original gate's `Checks found: 0` requirement was too strict for this vendor JTAG/debug transport design; it correctly blocked the build under the former gate but is not by itself evidence of a design error. All seven items were reviewed from the owner's pasted report:
- 3× `PDCN-1569`: LUT equation pins in `dbg_hub/inst/...` (BSCAN/debug hub).
- 1× `REQP-1857`: JTAG AXI `rx_fifo_i` RAMB18E2 WRITE_FIRST collision advisory.
- 2× `REQP-1858`: JTAG AXI `rd_cmd_fifo_i`, `wr_cmd_fifo_i` RAMB36E2 WRITE_FIRST collision advisories.
- 1× `RTSTAT-10`: 47 no-routable-load nets, reported visible sample of 15 paths all in `dbg_hub/inst/...` or `m08_d3c_jtag_link_i/jtag_axi/inst/...`. The report lists a sample, **not all 47 nets**; do not claim every unlisted net was examined.

The revised independent gate checks that the full, **unchanged** native DRC report has exactly those seven codes/severities/counts/descriptions, all seven matching details, expected vendor locations and the specific observed net sample. Unexpected DRC warning types/counts/severities/locations, critical warnings, malformed reports, negative timing slack, failed endpoint count, false board assertions, and original SHA drift all still cause rejection. Negative regression tests cover altered warnings/paths/counts and negative slack. Passing this gate constitutes **offline candidate acceptance with explicitly documented vendor-IP warnings for this bounded diagnostic experiment only**, **not** a claim that these vendor core advisories cannot affect functional behavior or that JTAG has been proven on KV260.

**Do not rerun native synthesis or change any original evidence.** In the owner PC (after pulling the updated branch), run:
```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
RUN="$HOME/Thesis_Evidence/M08/m08_d3c_jtag_link_A2SUrkhI"
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt)
python3 -m unittest discover -s tests -p 'test_m08_d3c_jtag_bram_gate.py' -v
python3 scripts/m08_d3c_jtag_bram_gate.py --run-dir "$RUN"
sha256sum "$RUN/bitstream_candidate/m08_d3c_jtag_bram_UNRELEASED.bit"
```

If the gate accepts, independently review the original SHA, board/part, reset polarity and memory dimensions, timing, fan A12 route, plus UART/fan/recovery readiness before a **separately owner-authorized**, bounded one-shot physical JTAG BRAM write/read test. No hardware programming has been performed by the changes in this section. Original HPM0 image remains quarantined. A JTAG communication PASS validates one observed diagnostic sequence only and does **not** close the vendor-IP warnings, demonstrate Linux/PL clock independence, or prove neural inference.
