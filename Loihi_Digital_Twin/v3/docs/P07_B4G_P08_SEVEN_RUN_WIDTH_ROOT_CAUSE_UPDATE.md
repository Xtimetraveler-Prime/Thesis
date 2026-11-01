# P07-B.4g — P08 physical PS-width retrospective: seven 128-bit runs vs current 64-bit boot

**Recorded:** 2026-10-21. **Source:** user-pasted terminal output, reading seven preserved `ps_width.log` files under `/home/dna/Thesis_Evidence`; not independently re-read by this assistant or an instrument-connected plugin. Companion machine-readable ledger: `docs/P07_B4G_P08_7_RUN_WIDTH_RECONCILIATION_LEDGER.json`.

## Result — no ambiguity about the historical widths

All **seven** surviving P08 physical-test logs, including the single P08-A3.1 pilot and **all six** paired P08-A3.2 A2.1/A2.2 runs, printed:

```text
P03_2C_PS_FPD_AXIFS_RAW=0x00000A00
P03_2C_PS_FPD_HPM0_WIDTH_BITS=128
P03_2C_PS_LPD_AXIFS_RAW=0x00000200
P03_2C_PS_LPD_HPM0_WIDTH_BITS=128
```

| Physical experiment | On-PC original read-only evidence path |
|---|---|
| P08-A3.1 pilot, 2026-10-18 | `/home/dna/Thesis_Evidence/p08_a3_1_pilot_20261018T203342Z/ps_width.log` |
| P08-A3.2 pair 1, A2.1 | `/home/dna/Thesis_Evidence/p08_a3_2_A2_1_1024_20261019T003224Z/ps_width.log` |
| P08-A3.2 pair 1, A2.2 | `/home/dna/Thesis_Evidence/p08_a3_2_A2_2_1024_20261019T003249Z/ps_width.log` |
| P08-A3.2 pair 2, A2.2 | `/home/dna/Thesis_Evidence/p08_a3_2_pair2_A2_2_20261019T010354Z/ps_width.log` |
| P08-A3.2 pair 2, A2.1 | `/home/dna/Thesis_Evidence/p08_a3_2_pair2_A2_1_20261019T011226Z/ps_width.log` |
| P08-A3.2 pair 3, A2.1 | `/home/dna/Thesis_Evidence/p08_a3_2_pair3_A2_1_20261019T012641Z/ps_width.log` |
| P08-A3.2 pair 3, A2.2 (latest archived) | `/home/dna/Thesis_Evidence/p08_a3_2_pair3_A2_2_20261019T013054Z/ps_width.log` |

The user previously provided **19 Track A** P07-A2/A3/A4 `ps_width.log` records from 2026-10-17; **all** FPD/LPD widths were also 128 bits. Three Track A physical acceptance receipts independently identified the same routed FPGA artifacts: XSA `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`, BIT `beb7324decacf1c39d1cda97b6f13f347ecb1901a9670e75479f27a669d988a4`, LTX `31f5771432ffb8c72b35a55e1ef7e88e9d96d406fe8cb306733df474df360238`.

**Current Track B observations on 2026-10-21:**

| Context | FPD SLCR `0xFD615000` | LPD SLCR `0xFF419000` |
|---|---|---|
| All accepted Track A/P08 runs | `0x00000A00` = 128-bit | `0x00000200` = 128-bit |
| Before `xmutil unloadapp` | `0x00002560` = 64-bit | `0x00000512` = 64-bit |
| After successful `sudo xmutil unloadapp` | **unchanged 64-bit** | **unchanged 64-bit** |

The current booted KV260 is on Ubuntu 24.04.2 LTS; `xmutil bootfw_status` screenshot displayed requested/last boot Image A, both slots BootFW `K26-BootFW-01.02-06140626`; this is current state only. **No comparable October 17/19 FSBL/BootFW binary hashes or slot inventory are available**. Earlier `ls -la /sys/kernel/config/device-tree/overlays/` displayed `k26-starter-kits_image_1` before the later verified unload; its post-unload status and FPGA manager `state` still need a valid read. A failed attempt to type a multiline `for` command through PuTTY produced a Bash syntax error, **not** proof of FPGA state.

## Interpretation

1. **P08 did not exhibit a width misalignment during its seven successful physical sessions.** The 128-bit PS configuration was demonstrably present at least as late as the last archived P08-A3.2 session (directory timestamp `20261019T013054Z`). The different 64-bit state was first measured during Track B on October 21. The transition time, reset mechanism and causal trigger remain **unknown**.
2. Independent original P08 source audit shows hardware runners first **read and require live FPD128**, then stage DDR, program the accepted P03 bitstream, and run bare-metal A53. Inspected P08 shell scripts and C programs **do not** change the static FPD/LPD SLCR widths or update boot firmware. They do halt/reset Cortex-A53 execution and use 64MiB reserved DDR; these actions demand a proper reboot, but source review supplies **no mechanism proving persistent width changes**.
3. **`xmutil unloadapp` cannot be treated as the restoration step.** User's before/after experiment proved it removed the accelerator (`remove from slot 0 returns: 0 (Ok)`) while **leaving PS width unchanged**.
4. Initial new B.4g `mrd 0xA4000000` returned AP transaction timeout **without first programming our accepted P03 PL bitstream** on that boot. The missing slave is plausible, but PS64 vs design FPD128 is **a separate established incompatibility**. Neither cause is proven solely by that timeout.
5. The historical FPD128 design and artifacts remain physically accepted; **do not rebuild for FPD64 or program the old FPD128 BIT while the PS remains 64** merely to attempt recovery.

## Next safest investigation for a new chat

- On KV260 Linux (PuTTY, **one-line commands only**, or SSH if user establishes its IP), gather *read-only* current post-`unloadapp` state: `cat /sys/class/fpga_manager/*/state`, `cat /sys/kernel/config/device-tree/overlays/*/status`, `sudo xmutil listapps`, and `hostname -I`. Do not manipulate kernel overlays.
- Compare stored physical P08 `ps_width.log` evidence (now user-attested all seven=128) with exact boot image/boot logs/firmware provenance still on disk if available; do not invent that boot firmware changed. Determine how the earlier boot was initialized to 128 and whether current warm/cold restart or selected FSBL differs.
- **Stop before** PS SLCR runtime `mwr`, XSDB PL `mrd 0xA4000000`, `vivado/p03_2c_program_bitstream.tcl` when FPD64, A53 `dow`, P07-A/P08-A destructive DDR JTAG scripts, and B2 official TEST.
- Only with a separately verified PS width=128 boot, deliberate operator-approved programming/provenance and low DDR/OS ownership plan should B.4g PL MMIO and eventual standalone read-only A53 probe be reconsidered.

Additional source docs: `docs/P07_B4G_P08_A_PERSISTENT_WIDTH_CAUSE_AUDIT.md`, `docs/P07_B4G_TRACK_A_19_RUN_WIDTHS_AND_OVERLAY_EVIDENCE.md`, `docs/P07_B4G_P08_7_RUN_WIDTH_RECONCILIATION_LEDGER.json`, `docs/P03_2C_MMIO_ROOT_CAUSE_AND_FIX.md`, `docs/P07_B4G_FPD64_AP_TIMEOUT_RECOVERY_GATE.md`.

**State:** P07-B physical B.4g **FAIL/NO-GO**; B.4c real offline ELF+map gate **PASS**; B.4f user-native accepted; B.4g/h fake-XSDB native PASS; PR #49 draft/unmerged; accepted Track A/B/P03/P05 unchanged; B2 official MNIST TEST sealed.
