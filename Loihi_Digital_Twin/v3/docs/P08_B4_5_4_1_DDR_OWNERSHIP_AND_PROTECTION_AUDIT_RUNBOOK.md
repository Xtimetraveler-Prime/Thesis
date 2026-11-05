# P08-B4.5.4.1 — DDR ownership and immutable backup-protection audit

**Submilestone:** PC-only structural risk assessment, not physical approval.
**Starting point:** P08-B4.5.3 accepted two real A53 Vitis builds plus
an independently recomputed and SHA-pinned paired-ELF report (2026-11-05 UTC).
Keep draft B4.5.3 PR #55 and every original ELF, map, JSON, model and
B4.4.2 physical baseline untouched.

## Why this gate exists

B4.5.1 authenticates 27 original 512KiB backup contexts ONCE, then
restores them without repeating source/destination SHA-256. This is
integrity-preserving ONLY if the full immutable backup stays
read-only/exclusively owned throughout the session. B4.5.2 deliberately
does not check context content, but it also requires operational DDR
ownership and protection before any board execution.

The original backup is `[0x43000000,0x43D80000)` (13.5 MiB). Its
**conservative 1MiB-granularity DDR-XMPU cover** is
`[0x43000000,0x43E00000)`: this includes **512KiB beyond the
backup**. The additional 512KiB must be independently cleared as an
existing write consumer before any boot-time protection design is
approved. This is an *address calculation*, not proof that a
particular XMPU region has been programmed, aligned, locked, or made
readable to A53 and all necessary PL masters. XMPU settings can have
master-ID and secure/nonsecure implications; all six DDR XMPU paths and
access priorities must be covered.

**Do not attempt to write XMPU registers in the already generated A53
ELFs or XSDB scripts.** AMD UG1085 says XMPU registers are accessible
only to secure masters, recommends boot-time configuration and a
locked state until reset, and describes the hardware's separate
read/write permissions. Any genuine solution must prove backup
provisioning *before* protection, continued sanctioned reads, and
prevention of *all* other writes; this is an architectural design
and boot integration task, not a safe ad-hoc runtime patch.

Sources (AMD):
- [UG1085 AMD Memory Protection Unit](https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/AMD-Memory-Protection-Unit)
- [UG1085 XMPU Configuration](https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Configuration)
- [UG1085 Region Checking Operation](https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Region-Checking-Operation)
- [UG1085 Master and Slave Security Profiles](https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Master-and-Slave-Security-Profiles)

The PC-only script explicitly inventories the current A53-mode firmware
DDR declarations: 27 mutable P02 contexts, frozen B4M route input and
frame staging, raw image pool, result journal, whole-service timing,
B4.5 reset sidecar, immutable backup, P07 B4L binding/route output,
and terminal mailbox. It rereads both real A53 ELFs' PT_LOAD from
disk. **This is not a complete physical master/OS/boot DDR owner map.**
It records the full list of missing proof categories instead.

## Step 1 — pull the new B4.5.4.1 branch

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b454-ddr-owner-audit
git pull --ff-only origin agent/v3-p08-b454-ddr-owner-audit
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
```

**All required exports**, using your exact accepted paths:

```bash
# Original accepted frozen build inputs; no rebuilding or editing:
export P08_B45_ORIGINAL_ELF="$HOME/Thesis_Evidence/p08_b2_3_image_only_build_20261102T040903Z/vitis_workspace/p08_b2_3_image_only_1024.elf"
export P08_B2_RESET_PINS="$HOME/Thesis_Evidence/p08_b2_2_original_reset_pins_20261102T005118Z"
export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"

# Original accepted DISTINCT B4.5.3 Vitis build roots:
export P08_B45_ONCE_BUILD_DIR="$HOME/Thesis_Evidence/p08_b45_once_build_20261105T041935Z"
export P08_B45_UNCHECKED_BUILD_DIR="$HOME/Thesis_Evidence/p08_b45_unchecked_build_20261105T042140Z"

# YOUR previously accepted exact independent paired A53 report:
export P08_B454_ACCEPTED_PAIR="$HOME/Thesis_Evidence/p08_b45_pair_independent_20261105T045733Z.json"

# NEW external no-overwrite PC-only risk-gap output (never replace evidence):
export P08_B454_GAP_REPORT="$HOME/Thesis_Evidence/p08_b454_ddr_owner_gap_$(date -u +%Y%m%dT%H%M%SZ).json"
```

If ANY path has moved, use the following **read-only discovery commands**
and then change the corresponding `export` to the actual accepted
directory, **never** to a similarly named file with unverified bytes:

```bash
find "$HOME/Thesis_Evidence" -type f -name "p08_b2_3_image_only_1024.elf" -print
find "$HOME/Thesis_Evidence" -type f -name "p08_b2_2_original_context_sha256.h" -print
find "$PWD/vivado/build" "$HOME/Thesis_Evidence" -type f -name "p03_2_post_route_metrics.txt" -print 2>/dev/null
find "$PWD/vivado/build" "$HOME/Thesis_Evidence" -type f -name "p03_2_ps_mmio.xsa" -print 2>/dev/null
find "$HOME/Thesis_Evidence" -type f -name "p08_b45_auth_once_1024.elf" -print
find "$HOME/Thesis_Evidence" -type f -name "p08_b45_unchecked_1024.elf" -print
find "$HOME/Thesis_Evidence" -type f -name "p08_b45_pair_independent_*.json" -print
```

## Step 2 — confirm pinned evidence and run native tests (NO board)

```bash
test -s "$P08_B454_ACCEPTED_PAIR" &&
test -s "$P08_B45_ONCE_BUILD_DIR/vitis_workspace/p08_b45_auth_once_1024.elf" &&
test -s "$P08_B45_UNCHECKED_BUILD_DIR/vitis_workspace/p08_b45_unchecked_1024.elf" &&
test ! -e "$P08_B454_GAP_REPORT" &&
echo "P08_B454_PC_ONLY_INPUTS_FOUND=1"

sha256sum "$P08_B454_ACCEPTED_PAIR"
# EXACT required SHA:
# 03b433527901a9d51dfb8a8ca99c0321d81335859d1be14505eb6a7be9369ec1

PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
  tests/test_p08_b454_ddr_owner_preflight.py
```

## Step 3 — produce original-path-pinned PC-only DDR audit

```bash
PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
  scripts/p08_b454_ddr_owner_preflight.py \
  --paired-report "$P08_B454_ACCEPTED_PAIR" \
  --once-build "$P08_B45_ONCE_BUILD_DIR" \
  --unchecked-build "$P08_B45_UNCHECKED_BUILD_DIR" \
  --out "$P08_B454_GAP_REPORT"

sha256sum "$P08_B454_GAP_REPORT"
python3 -m json.tool "$P08_B454_GAP_REPORT"
```

Expected PC-only markers, **including the important hard stop**:

```text
P08_B454_HOST_ONLY_GENUINE_A53_MEMORY_GEOMETRY_PASS=1
P08_B454_DDR_MASTER_OWNER_PROOF=0
P08_B454_PERSISTENT_BACKUP_PROTECTION_PROVEN=0
P08_B454_BOARD_JTAG_AND_DDR_ACTION_AUTHORIZED=0
```

Do NOT interpret the static geometry PASS as physical GO. The report
will always retain `board_contact=false`,
`physical_backup_immutable_after_one_time_sha_proven=false`,
`operator_authorized_KV260_board_action=false`.

## Optional: include already-available read-only boot inventory snapshots

If you ALREADY possess prior boot-side observational text files, place
copies in an **external** directory named by this export (no KV260
commands needed or requested here):

```bash
export P08_B454_OBSERVATIONS_DIR="$HOME/Thesis_Evidence/p08_b454_readonly_boot_observations"
```

The script optionally accepts
`--inventory-dir "$P08_B454_OBSERVATIONS_DIR"` with files named:
`proc_iomem.txt`, `reserved_memory.txt`, `boot_log.txt`,
`boot_image_manifest.json`, `xmpu_readback.json`, and
`masters_snapshot.json`. It hashes them (no hardware access) and
labels **every supplied snapshot as unverified observational evidence**.
Merely providing these files cannot cause the output to claim hardware
write exclusion or grant board launch permission. Do not invent files
or manipulate XMPU to satisfy this step.

## Next blocked gates (not part of this PC-only submilestone)

1. Establish verified boot/PS state and actual DDR ownership under a
   single reproducible **separate** boot/launch configuration.
2. Audit FSBL, TF-A/BL31, U-Boot, Linux, APU cores, RPU, PMU/CSU,
   all six DDR XMPU ports and their PS/PL DMA masters, and debug/JTAG.
3. Document who stages immutable records before XMPU lockdown, the
   protected 1MiB-aligned coverage, allowed reads and prohibited writes,
   and evidence that the lock persists through every image reset.
4. Design a **separate** trusted protection provider. No no-op lock,
   no A53 runtime speculative XMPU writes. A newly admitted ELF/map is
   required if code changes. Keep accepted B4.5.3 binaries immutable.
5. Revisit low-DDR A53 load/stack/heap/cache ownership. Obtain recovery
   plan and fresh explicit operator approval before even a bounded
   16-image physical pilot. Then validate scalar oracle/FNV/neural
   parity before interpreting timings.
6. Official MNIST TEST remains sealed, and B4.5.5 full differential
   conclusion is blocked until actual physical sessions exist.
