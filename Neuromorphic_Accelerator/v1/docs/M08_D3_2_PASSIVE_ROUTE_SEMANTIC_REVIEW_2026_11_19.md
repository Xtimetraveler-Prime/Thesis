# M08 D3.2 — passive route evidence semantics and next blocked release decisions

**2026-11-19, owner PC only.** This is part of **M08 → D3 → D3.2**, not a new numbered milestone. **No new bitstream, board interrogation, KV260 programming, Linux MMIO, JTAG or firmware actions permitted.** The original problematic M08 \`bit.bin\` (SHA256 a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b) stays **QUARANTINED**.

## Original owner passive implementation

Owner's visible VS Code console (Vivado 2025.2, 2026-11-19 local time) shows **both synthesis and routing SHA receipts verified** for:

\`/home/dna/Thesis_Evidence/M08/m08_d3_2_passive_synth_77Ols9zt\`

No original report bytes were committed to this repository. The owner's independent route source/native checker accepted the file class, but intentionally returned false for separate DRC and timing signoff. Original evidence reported:

| Signal | Owner report | Meaning |
| --- | --- | --- |
| Route | \`route_design Complete!\`, 100%, \`Fully Routed\` | Passive design routed in Vivado PC only. |
| Vivado DRC | \`Checks found: 0\`, default ruledeck | No DRC findings in this report, **not a cooling/PS boot or physical hardware guarantee**. |
| Timing | \`WNS=NA\`, \`TNS=NA\`, zero total endpoints | **No timing path measured; cannot claim positive slack or neural engine timing closure.** The generic \`All user specified timing constraints are met.\` string is not an informative timing score when no timed paths exist. |
| Resources | 0 CLB LUTs; 0 CLB registers; 0 BRAM; 0 DSP; 1 PS8; 1 OBUF; 1 IOB | No clocked fabric and no neural computation in this passive scaffold. |
| Clocks | \`clk_pl_0\` / \`clk_pl_1\` nominal 10 ns period (100 MHz) | Native routed clock definitions, **not actual Linux runtime PLCLK availability or fan PWM measurement**. |
| Fan | \`M08_FAN_PWM\` A12 LVCMOS33 | Configured/reported netlist connection only; thermal output behavior **unknown**. |
| Warnings | Unrelated board store parts \`[Board 49-26]\` and \`[Place 30-2953]\` no critical terminals | Consistent with passive design; don't ignore any **new warning family** in a subsequent run. |
| Exposure | \`ps_to_pl_axi=DISABLED\`, no DTBO or bitstream | No Linux identity/page path, no inference; hardware remains blocked. |

**Do not describe WNS/TNS as zero or positive, do not say '100 MHz validated under Linux', and do not call this an HPM0 protected checkpoint.**

## New owner-PC independent semantic gate

\`scripts/m08_d3_2_passive_route_report_review.py\` augments the existing \`scripts/m08_d3_2_passive_route_gate.py\`. It **does not write any files**, launch Vivado, or access firmware or hardware. It:
- Reuses the original native D3.1/synth/route status/evidence gate.
- Rehashes every original entry from both immutable owner \`99_evidence_sha256.txt\` and \`98_route_evidence_sha256.txt\` ledgers, rejecting duplicates, unknown paths, symlinks and modified bytes.
- Requires the routed native timing and DRC report states, parses **zero default-ruledeck DRC findings** and **NA timing endpoints with no clocked fabric**.
- Checks one original PS8 and fan OBUF/IOB, no LUT/register/BRAM/DSP, and expected native PL clocks without claiming operational clock ownership.
- Rejects changed/new warning families rather than silently claiming acceptance.
- Returns \`PASSIVE_ROUTE_DRC_ZERO_NO_TIMED_FABRIC_PATHS_HARDWARE_BLOCKED\`; **never** returns safe-to-load/bitstream or protected-HPM approval.

\`tests/test_m08_d3_2_passive_route_report_review.py\` uses synthetic receipts and explicitly rehashed adverse DRC/timing/resource/clock/thermal claims; no fake "native Vivado pass" is allowed. The owner's genuine original report must be rerun through this read-only gate, and its output separately reviewed.

## Owner independent PC commands

\`\`\`bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit
git rev-parse HEAD

cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_d3_2_passive_route_report_review.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v

RUN="$HOME/Thesis_Evidence/M08/m08_d3_2_passive_synth_77Ols9zt"
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt && sha256sum -c 98_route_evidence_sha256.txt)
python3 scripts/m08_d3_2_passive_route_report_review.py --run-dir "$RUN"
\`\`\`

**If the read-only gate fails:** preserve originals and send the first rejection line plus original reports. An unexpected register count, nonzero DRC findings, positive WNS on newly clocked fabric, warning categories, or broken SHA receipt is a **new design/evidence review**, not permission to edit source evidence to pass.

## What is actually missing before an FPGA bitstream and physical hardware test?

**Offline passive image generation remains a separate approval gate, not this step.** Native default DRC=0 and trivial passive routing do not establish that the PS TTC0 control remains alive through FPGA region/programming changes, whether A12 drives the fan as needed, or whether Linux clock/reset/firmware/thermal monitoring will preserve independent cooling. Need a separately checked fan/stock-rollback plan and evidence, independent recovery safety review, and explicit user authorization before even proceeding to a new passive bitstream candidate. Do not build/load an original or protected HPM0 bitstream as a shortcut.

**Protected Linux AXI:** still missing authentic board boot platform XSA/PS init/firmware versions, correctly configured independent PS ATB4 and AIB13 quiescence/late response handling, HPM0 128-bit AFI boot ownership, PL0/reset/kernel/FPGA-region lifecycle, driver mapping, fan and recovery. Successful offline abstract AXI simulation is not those silicon guarantees.

Next useful **offline** engineering work after this semantic receipt audit: independently review fan owner and stock recovery source, define a verifiable passive-image release gate, then (only if genuinely satisfiable) prepare a separately authorized new passive bitstream. **Hardware MMIO and physical device programming remain prohibited.**
