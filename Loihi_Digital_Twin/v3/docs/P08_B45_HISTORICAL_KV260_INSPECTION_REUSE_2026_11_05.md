# P08-B4.5 — reuse existing KV260 observations before any new board inspection

**Git history reconciliation (2026-11-05 UTC).** This ledger is a
source-evidence review of original historical Git records, not new
contact with the KV260, not an active boot attestation, and not
permission to execute JTAG/DDR/FSBL operations. Original raw instrument
logs generally remain on the operator's PC under
`/home/dna/Thesis_Evidence`; Git preserves user-reported observations,
paths and digests. Do not promote historical or source-only evidence
into current physical security proof.

## Latest user-supplied source audit — accept the PC-only result

The operator reran `scripts/p08_b45_fsbl_source_channel_gate.py`
on the original XSA and generated sources. Terminal markers:
```text
P08_B45_ORIGINAL_C_H_TCL_AND_PREVIOUS_REPORT_MATCH=1
P08_B45_FSBL_C_VS_XSDB_TCL_CHANNELS_INVENTORIED=1
P08_B45_GENERATED_C_DDR_PORTS_RECONCILED=6
P08_B45_ACTIVE_BOOT_FSBL_PROTECTION_PROVEN=0
P08_B45_BOARD_OR_BOOT_MEDIA_WRITES_AUTHORIZED=0
```

The operator's original local report:
`/home/dna/Thesis_Evidence/p08_b45_fsbl_c_tcl_20261105T071335Z.json`;
posted SHA-256:
`61e4b668e08b760800e69b39fdb61c5382aa23c0df568a31c3a49beff6c16bde`.

The report pinned preceding accepted 4.5.4.5 SHA
`2d6f9e079b3bf9845ebd07d69b2de4611b90dc821341b0c9ada6458b2daa74a0`,
matched original P03 XSA `52aea12b...93af6f` and
`psu_init.c/.h/.tcl` digests. All six generated DDR XMPU C
helper bodies were reported as 21 source bytes, with no named
calls, obvious writes or pointer assignments under this heuristic.
They are *possible source-level stubs*, **not** proof of the
effective linked/booted FSBL or live XMPU policy. Tcl references
to each helper did **not** include a
`proc psu_ddr_xmpuN_data` declaration under the accepted
literal scanner, and are not automatically FSBL instructions.
`psu_protection_lock_data` showed no obvious write call.
The prior JSON listed **zero operator-supplied optional host boot
candidates**: this means none were submitted, NOT that none exist.
No physical owner, AXI ID, priority/mask or real lock was proven.
The original JSON and local XSA were not uploaded to Git; the
source result was reported via terminal transcript and report SHA.

## Already recorded historical hardware evidence — DO NOT REPEAT

| Evidence already in Git | Genuine source-supported scope | Reuse decision |
| --- | --- | --- |
| `P07_B4G_P08_SEVEN_RUN_WIDTH_ROOT_CAUSE_UPDATE.md` + machine ledger | October 17: **19** prior Track A `ps_width.log` records FPD/LPD 128-bit. October 18–19: **7** prior P08-A `ps_width.log` records FPD/LPD 128-bit. Original XSA/BIT/LTX hashes documented. | Keep original archived receipts; do **not** rerun the 26 old physical sessions. |
| Same P07-B4g retrospective and `P07_B4G_TRACK_A_19_RUN_WIDTHS_AND_OVERLAY_EVIDENCE.md` | October 21 PuTTY screenshot: Ubuntu 24.04.2 LTS, kernel `/proc/cmdline`, `xmutil bootfw_status` requested/last Image A and both slots `K26-BootFW-01.02-06140626`; `k26-starter-kits_image_1` configfs overlay directory observed. `xmutil unloadapp` succeeded but did **not** change FPD/LPD width. No historical October 17–19 FSBL binary digest was recorded. | These **are already documented snapshots**, not a reason to retype `uname`, `cat /proc/cmdline` or `xmutil bootfw_status` for historical information. Any later current-boot check must be separately time-stamped and justified. |
| `P07_B4G_PS_ONLY_64BIT_RECHECK_LEDGER.json` / `P07_B4G_REAL_XSDB_FPD64_TIMEOUT_LEDGER.json` | October 21 XSDB PSU FPD raw `0x00002560` (64-bit) and LPD raw `0x00000512` (64-bit); one `0xA4000000` PL AP timeout before P03 bitstream was known loaded. | Do not repeat risky PL `mrd` or rewrite static width selectors. |
| `P07_B4I_TRACK_A_DERIVED_PHYSICAL_PILOT.md` | October 22 **same-boot Linux `devmem` and XSDB width reads disagreed** (Linux FPD/LPD128 vs XSDB FPD/LPD64). Attribution was unresolved; preserve both observations rather than forcing a simplistic boot-firmware explanation. | Do not claim old 64-bit read proves stable current width. Any future PS register action needs a separate gated design. |
| `P07_B4I_2026_10_22_PHYSICAL_TAKEOVER_WIDTH_PASS_LEDGER.json` and `P07_B4L_2026_10_23_REAL_CPU_TAKEOVER_ACCEPTANCE.json` | User-reported dedicated board JTAG stop and width gate passed, CPU states accounted, FPD/LPD128; B4l thereafter staged/read back original 27 P02 records and physically verified three-slot paging. | Reuse successful admission and DDR source integrity evidence; these did **not** prove exclusive real boot/DDR owner or permanent immutable backup. |
| `P08_B44_A53_EXTERNAL_DEBUG_READONLY_DIAG.md` | November 2–3 **read-only** XSDB target scans: PS TAP/PMU/PL only; ARM DAP JTAG seen, actual A53 access not established in those snapshots. The first reset profile failed at a secondary-core external-debug halt. | Do not rerun target-discovery work merely for this source investigation. |
| `P08_B4_4_2_RESET_PROFILE_PHYSICAL_RESULTS.md` | Later November 3 separate **successful retry**, genuinely accepted 1,024-image profiling session: complete neural/FNV parity, distinct profiler ELF, independent 1,024 reset records. This supersedes the impression that the old failed A53 halt is an ongoing proven blocker. | Reuse accepted real physical baseline; do not repeat profiling as a preflight for trusted boot design. |
| `P08_B4_5_4_1_OPERATOR_STATIC_DDR_GAP_ACCEPTANCE_2026_11_05.md` | 27 immutable backup records `[0x43000000,0x43D80000)` = 13.5MiB; XMPU 1MiB-aligned candidate cover `[0x43000000,0x43E00000)` consumes **extra 512KiB** with unverified owner. Static address nonoverlap only. | Don't repeat source geometry admission or overwrite the accepted freeze. |
| `P08_B4_5_4_2_OPERATOR_SYMBOLIC_XMPU_POLICY_ACCEPTANCE_2026_11_05.md` and .3/.4/.5 | Six-port 10-bit master-ID symbolic policy, 2025.2 FSBL source bypass vs generated protection/lock, original XSA C/H/Tcl hashes and new source-channel split all reviewed on host. **No original active BOOT.BIN / compiled FSBL linkage or XMPU register readback**. | Preserve source audits; no more invented 4.5.4.x microstages. |

## What Git evidence does NOT establish

1. Exact **currently running** boot medium and boot-image/FSBL bytes,
   actual FSBL build flags and secure privilege, staged backup
   authentication and order of XMPU provisioning/lock.
2. Effective **current** per-port XMPU regions, 10-bit AXI master IDs,
   priority/mask/secure state, allowed trusted A53/PL readers and
   excluded PS/PL DMA/other masters. No genuine XMPU permission
   readback was found in the accepted source/physical ledgers.
3. Ownership of the extra 512KiB cover, safe ROM/FSBL/TF-A/Linux/RPU
   handoff and low-DDR A53 ELF memory across a *new* trusted-boot
   configuration. Prior accepted standalone JTAG tests acknowledged
   residual owner risk; they did **not** establish physical exclusion.
4. A trusted one-time SHA-before-lock process and continuing
   fail-closed A53 backup-protection attestation in a newly verified
   firmware. Existing B4.5 original A53 guard deliberately returns
   failure, and no protected pilot has run.

## Prioritize existing PC artifacts BEFORE fresh board contact

Review the historical log paths above and the source reports. The
new source report's empty `optional_host_existing_boot_candidates`
array is **not** evidence of absence. Use read-only *PC-side* searches
for host-resident BOOT.BIN/BIF, FSBL ELF/map/compiler flags and
historical `bootfw_status` capture. Do not modify any original archive,
and do not assume a located file was actually booted:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
find "$HOME/Thesis_Evidence" -type f \( -iname '*bootfw*' -o -iname '*boot*.log' -o -name ps_width.log \) -print
find "$HOME/Git/Thesis" -type f \( -iname 'BOOT.BIN' -o -name '*.bif' -o -iname '*fsbl*.elf' -o -name 'compile_commands.json' \) -print
```

Even if an existing host BOOT.BIN is found, comparing it to live
boot must happen in a separately approved, read-only provenance step.
Do not rebuild, install or change boot media based on an unmatched
host file.

## If genuinely necessary later: PuTTY-friendly physical plan

User has a PuTTY serial connection with impractical paste support.
**No board inspection is requested or authorized by this Git audit.**
Before an approved future observation, specify the exact informational
gap and collect one short command at a time. Prefer familiar
one-line, **read-only** commands rather than loops, multiline shell
scripts, JTAG, raw `devmem`, XMPU writes, or boot-loader commands.
Possible fresh **context-only** commands (not a physical protection
attestation) are `sudo xmutil bootfw_status`, `lsblk -f`,
`cat /proc/mtd`, and `cat /proc/iomem`, depending on the exact
remaining need and the current OS. Even these do not establish
active compiled FSBL identity or XMPU permissions. No new board
command should be sent automatically.

**Gate to physical tests remains closed.** New signed/recoverable
secure boot, XMPU owner proof, trusted original-backup staging,
verified A53 read permissions, a newly admitted fail-closed guard and
explicit board approval must precede any 16-image pilot. The
1024-image paired optimized-reset study must follow 16-image exact
original scalar/FNV/neural acceptance. Official MNIST TEST remains
SEALED_NOT_ACCESSED; original P03 shell, Vitis ELF pairs and
trained P02 freeze remain untouched.

**Workflow:** maintain current work under P08-B4.5 named packages
in draft PR #61; don't create another 4.5.4.6 submilestone,
don't merge PRs #60/#61 without explicit user authorization.
