# M08 D3.1 — versioned, passive KV260 fan-first architecture (SOURCE ONLY)

**2026-11-12.** This is the first **D3 candidate source gate** after the M08 D0–D2 incident review. D3.1 is a new, independent KV260 Vivado 2025.2 **passive** block design. D3.2 is a later PS-side protected-AXI candidate. There is **no corrected protected bitstream**, **no stock firmware overwrite**, **no DTBO deployment**, and **no authorization to run hardware tests**.

**Relationship to prior work:** D3.1 branch `agent/neuromorphic-accelerator-v1-m08-d3-failsafe-candidate` starts from the quarantined M08 incident branch `agent/neuromorphic-accelerator-v1-m08-kv260-bringup`. Draft stacked PR #84 targets the original D2 incident branch; PR #83 and its original source/evidence are kept as-is, draft/unmerged. The original owner M08 `.bit.bin` SHA256 `a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b` is NEVER reusable for MMIO.

## 1. Design decomposition and reason

**D3.1: PS + fan-only with no exposed PS-to-PL AXI.**

```text
           KV260 K26 zynq_ultra_ps_e (genuine SOM BOARD_PART preset)
           ├─ PS TTC0 WAVEOUT channel 2 → EMIO[2] → xlslice[2] ──┐
           │                                                      │
           │                  M08_FAN_PWM ─ LVCMOS33 A12 ──────────┘
           │                            (physical PWM not yet proven)
           ├─ pl_clk0: native requested 100MHz (frequency readback only)
           │             no fabric AXI consumer in D3.1
           ├─ M_AXI_HPM0_FPD: DISABLED
           ├─ M_AXI_HPM1_FPD: DISABLED
           └─ M_AXI_HPM0_LPD: DISABLED

  SmartConnect: NONE          Identity/page slave: NONE
  /dev/uio mapping: NONE      AXI physical access: UNAUTHORIZED
  D2 simulation-only PS timeout: NOT INSTALLED, NOT SYNTHESIZABLE
```

The original M08 PS→SmartConnect→identity/page design ran its PS HPM0 interface, interconnect and slaves from `pl_clk0`; a stopped PL0 might prevent a response. *D3.1 intentionally avoids creating this access path.* It is not an accelerator and cannot run inference. It is a **fan-preserving pre-integration scaffold** for future versioned builds, not a finished recovery image. Native validation of the BD does not prove physical fan cooling or runtime clock enable.

**D3.2: guarded AXI version planned but intentionally unimplemented until PS-side dependency closure.**

```text
PS/ARM→ FPD interconnect
     │  ATB INSTANCE 4 (PS-domain, exact enable/timeout/error semantics REQUIRED)
     │  AIB INSTANCE 13 (PS FPD→M_AXI_HPM0_FPD isolation/quiescence REQUIRED)
     ▼
  M_AXI_HPM0_FPD width 128 only when AFI ownership proven
     │  PL clock and reset ownership / bridge sequencing proven first
     ▼
  SmartConnect → read-only identity and disabled-compute page shell
     │
  Linux access: no UIO mapping before ready; ONE read then stop on first error
```

This is **only a requirements diagram**, not valid RTL/ATB configuration or a safe DTBO. AMD UG1085 identifies ATB4 and AIB13 on these respective FPD paths. It warns ATB tracks fewer than 16 transactions and recommends restarting after the first timeout; native PS/boot owner, ATB configuration and late-response disposition remain unproven.

## 2. New source artifacts and safety contracts

`scripts/m08_d3a_passive_fan_bd_candidate.tcl` is a standalone native Vivado 2025.2 Tcl source. It must be invoked only on the **owner PC**, with a NEW, empty output directory. It selects K26 part `xck26-sfvc784-2LV-c` and installed KV260 SOM board part, applies the authentic PS board preset, requests 100MHz PL0 (checks propagated `FREQ_HZ` within ±1000Hz), explicitly disables PS HPM0/HPM1 FPD and HPM0 LPD, checks their master/clock pins are absent, configures TTC0 EMIO waveout and `xlslice` bit 2, exports `M08_FAN_PWM`, writes new XDC for A12/LVCMOS33/slow/drive4, validates/exports BD, and writes a native readback report. It **does not source** the original active PS HPM0 design, add original RTL, connect any AXI interface or assign a PS address. It **never synthesizes/implements/generates bitstream/DTBO** or communicates with the board. A future physical version would still require route/DRC and cooling proof.

`docs/M08_D3A_PASSIVE_CANDIDATE_MANIFEST.json` records identity, source-only status, no UIO/SmartConnect/PL AXI, fan route, clock request, original bitstream quarantine and seven D3.2 blockers in UNKNOWN/NOT_AUTHORIZED state. It explicitly **forbids hardware programming or MMIO**.

`scripts/m08_d3a_passive_candidate_source_gate.py` verifies immutable original source SHA pin receipts, the independent candidate, source-only manifest, all three HPM disable properties, full TTC0→A12 fan route and explicit anti-hardware flags. It rejects scripts that source the original HPM0 design, add AXI, enable an HPM port or invoke programming. With optional `--native-evidence-dir`, it checks genuine owner PC-generated report, XDC and BD export for expected status fields, board/part/frequency and fan constraints; it never writes files or runs Vivado. This is a **reported native BD contract**, not proof of actual operation.

`tests/test_m08_d3a_passive_architecture.py` uses synthetic native readbacks and fail-closed mutations (re-enabled HPM0, altered A12, changed original source, unauthorized manifest changes, forbidden programming/inheritance, compromised XDC, symlinks). A `tclsh` **info-complete** check evaluates only syntactic brace/quote completion, not vendor Vivado commands. GitHub Actions executes these tests (plus inherited D0–D2 suites) without board operations. Actual native Vivado compilation is an **owner-PC gate** with distinct receipts and is **not claimed from GitHub Actions**.

## 3. Local verification and genuine owner Vivado 2025.2 offline BD gate

**No KV260 access.** In a terminal on the PC with the connected repo:

```bash
cd /home/dna/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3-failsafe-candidate
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3-failsafe-candidate
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1

python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_d3a_passive_architecture.py' -v
python3 scripts/m08_d3a_passive_candidate_source_gate.py
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

**If and only if owner already has local Vivado 2025.2 installed**, run this *offline* project-creation gate, which does not generate an image or touch the board:

```bash
# Set ROOT before cd; only the owner PC runs Vivado.
ROOT="/home/dna/Git/Thesis/Neuromorphic_Accelerator/v1"
EVIDENCE_BASE="$HOME/Thesis_Evidence/M08"
RUN="$(mktemp -d "$EVIDENCE_BASE/m08_d3a_PASSIVE_NATIVE_PC_XXXXXXXX")"
mkdir "$RUN/output"
cd "$RUN"
vivado -mode batch \
  -source "$ROOT/scripts/m08_d3a_passive_fan_bd_candidate.tcl" \
  -log "$RUN/01_native_vivado.log" \
  -journal "$RUN/02_native_vivado.jou" \
  -tclargs "$ROOT" "$RUN/output"

cd "$ROOT"
python3 scripts/m08_d3a_passive_candidate_source_gate.py \
  --native-evidence-dir "$RUN/output"

# Preserve original native reports as they are; hash the run files on PC:
(cd "$RUN" && find . -type f ! -name 99_evidence_sha256.txt \
  -print0 | sort -z | xargs -0 sha256sum > 99_evidence_sha256.txt)
printf '%s\n' "$RUN"
```

If Vivado fails, **do not manually edit its report to pass**; preserve the first error and original log. Send `01_native_vivado.log` and/or `output/10_d3a_passive_bd_readback.txt`, `output/11_d3a_passive_bd_export.tcl`, `output/12_d3a_fan_a12.xdc` as applicable, with SHA receipt, before any D3.1 extension. The native script's project/report paths are unique to this candidate; no original D2 reports overwritten.

**Known tool limitation:** the assistant/GitHub Actions runner lacks owner native Vivado 2025.2 and any KV260 physical instrumentation. Tcl syntax and Python source CI are not native BD validation.

## 4. D3.2 protected AXI entry gates (all still BLOCKED)

| Gate | Required evidence | Status |
| --- | --- | --- |
| PS-side timeout | Review **boot-time** ATB4 FPD programming/ownership (not recovered-stock runtime writes), response enable/type and timeout under missing PL0, fault IRQ/stop-on-first-error | UNKNOWN |
| PS isolation/late replies | AIB13 identification, protocol-correct quiesce/drain, no orphan AR/R or AW/W/B; restart policy after first ATB indication | UNKNOWN |
| PL0 ownership | Clock framework/FPGA manager/FSBL/PMU/boot role, actual PS PL0 clock enabled through M08 region lifecycle; reset deassertion sequence | UNKNOWN |
| AXI AFI configuration | Derive HPM0 128-bit width and FPD AFI programming from the native Vivado XSA + actual PS boot/DT; do not paste guessed register values | UNKNOWN |
| Linux UIO ordering | No `&amba` UIO before manager/bridge/PL ready; decide whether children belong under `&fpga_full` and validate platform driver behavior | UNKNOWN |
| Fan + rollback | Verify original stock boot and independent cooling while PL replaced, physical rollback on error, untouched stock hash receipt | UNKNOWN |
| D3 native hardware | Genuine new versioned BD synthesis/implementation/DRC/CDC/reset/timing, firmware shell provenance, owner review, **new separate hardware authorization** | NOT PERMITTED |

**No safe 128-bit HPM0 bitstream is approved just because D3.1 source tests pass.** D3.1 does not enable PS MMIO and is not a completed board safety gate. Preserve original M08 quarantine until a new, separately reviewed D3.2 design is genuinely proven.

## 5. References

- Original incident and quarantine: `docs/M08_2B_3_FIRST_IDENTITY_RCU_STALL_INCIDENT_AND_FIX_PLAN_2026_11_12.md`.
- D2 PS-PL AXI fault containment: `docs/M08_D2_PS_PL_FAILURE_CONTAINMENT_DESIGN_REVIEW_2026_11_12.md`.
- Original decoded overlay: `docs/M08_D2_OWNER_ORIGINAL_M08_DECODED_OVERLAY_FINDINGS_2026_11_12.md`.
- AMD ATB instances: https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Instances .
- AMD AIB instances: https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Instances?contentId=0AQgBby0rplaLkOjKRLYMA .
- AMD ATB programming and limitations: https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Programming .
- AMD Linux FPGA Manager: https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/18841847 .
