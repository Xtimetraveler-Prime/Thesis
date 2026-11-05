# P08-B4.5.4.3 — FSBL / Vivado PS-XSA boot-source inventory (PC ONLY)

**Current stage:** code/CI implemented, operator-local original-file
verification pending. Separate from accepted B4.5.4.2 symbolic policy.
No real XMPU programming, no KV260/JTAG/DDR action, no boot-image
modification, no XFSBL hook patch and no authorization to run either
accepted B4.5.3 A53 ELF.

## Source-derived discovery: original assumption corrected

The AMD/Xilinx open-source Zynq UltraScale+ FSBL
`lib/sw_apps/zynqmp_fsbl/src/xfsbl_handoff.c` invokes
`XFsbl_ProtectionConfig()` **before**
`XFsbl_HookBeforeHandoff(EarlyHandoff)` in its current public source.
Therefore the previously considered `XFsbl_HookBeforeHandoff` is
**NOT** an automatically safe place to set/override the DDR XMPU
region configuration, because a preceding protection step might have
already locked the XMPUs. AMD UG1137 explicitly describes the
protection-config handoff phase.

**This is a public upstream source observation, not proof the user's
Vitis 2025.2 installation or QSPI/SD boot image contains that code.**
It must be reconciled against the actual boot artifacts, C source and
Vivado-generated PS registers before ANY platform patch.

Vendor sources and previously accepted ownership context:

- AMD/Xilinx public FSBL handoff source, including call order:
  https://github.com/Xilinx/embeddedsw/blob/master/lib/sw_apps/zynqmp_fsbl/src/xfsbl_handoff.c
- AMD UG1137, Handoff and Hooks in FSBL:
  https://docs.amd.com/r/en-US/ug1137-zynq-ultrascale-mpsoc-swdev/Handoff
  https://docs.amd.com/r/en-US/ug1137-zynq-ultrascale-mpsoc-swdev/Hooks-in-FSBL
- AMD UG1085, Configuration, Region Priority and Master ID Validation:
  https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Configuration
  https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/XMPU-Regions
  https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Master-ID-Validation
- AMD UG1085, Programming Example:
  https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Program-the-DDR-XMPUs

**Further important vendor nuance:** the AMD UG1085 programming
example uses DDR XMPU ports 1 and 2 for APU/CCI traffic and
configures ports 0, 3, 4 and 5 as default-deny. This is an EXAMPLE,
not proof of how the K26 board is actually routed/configured.
Our previous six-port priority-14/15 scheme was only a SYMBOLIC
security design; do not assume region 14/15 are unused or that
all six DDR ports have the same active master IDs/permissions.

## What this submilestone implements

`scripts/p08_b4543_fsbl_boot_source_inventory.py`:

1. Requires the exact **operator-accepted B4.5.4.2 original report
   SHA-256**, checks its NO-GO flags and original symbolic policy SHA.
2. Checks the exact accepted original P03 routed XSA SHA-256, opens the
   XSA *in memory* as a ZIP and scans selected bounded metadata
   members (`psu_init`, `psu_protection`, XMPU/XPPU, HWH and BIF).
   **It does not extract or modify** the original XSA.
3. Optionally accepts each actual user-local candidate
   `xfsbl_handoff.c`, `xfsbl_hooks.c`, `psu_init.c`,
   `psu_protection.c`, boot `.bif`, FSBL `.elf`.
   The scanner hashes existing files and counts concrete symbols.
   For `xfsbl_handoff.c`, it reports whether the observed local source
   calls protection configuration before or after the handoff hook.
4. Never presumes a source file is linked into a particular boot ELF,
   that a BIF produced the active `BOOT.BIN`, that a local FSBL
   produced the KV260's QSPI/SD image, that the board's boot source
   has a known SHA, or that any XMPU permissions are active.
5. Writes only a new external JSON with all physical-ownership
   and execution flags **FALSE**. There is no Vitis/bootgen/XSDB call,
   DRAM write, PL access, XMPU register access or physical boot.

### Exact operator-reported accepted parent provenance

Accepted B4.5.4.2 policy JSON:

`/home/dna/Thesis_Evidence/p08_b4542_xmpu_policy_pc_20261105T054738Z.json`

SHA-256: `ba89166f826425bcd69c86ee7b249f70cd39f359382fa69bd331a366678899f2`.

Accepted B4.5.4.2 source policy digest:
`7f78e7582e7fee12a06d83f14e45f1de1faf877ce1429af441dd83db3e851d2a`.

Accepted P03 routed XSA SHA-256:
`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.

## Step 1 — complete branch checkout and required exports

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b4543-fsbl-boot-inventory
git pull --ff-only origin agent/v3-p08-b4543-fsbl-boot-inventory
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# All REQUIRED environment variables (no assumed old terminal exports):
export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P08_B4543_ORIGINAL_XSA="$P07_B4L_REPORTS/p03_2_ps_mmio.xsa"
export P08_B4542_ACCEPTED_POLICY_REPORT="$HOME/Thesis_Evidence/p08_b4542_xmpu_policy_pc_20261105T054738Z.json"
export P08_B4543_OUT="$HOME/Thesis_Evidence/p08_b4543_fsbl_xsa_inventory_$(date -u +%Y%m%dT%H%M%SZ).json"

# Operator's Vitis install to SEARCH, not a build output:
export P08_B4543_VITIS_ROOT="$HOME/Vivado/2025.2"

# Optional physical host candidate paths: leave EMPTY unless independently found.
export P08_B4543_FSBL_HANDOFF=""
export P08_B4543_FSBL_HOOKS=""
export P08_B4543_PSU_INIT=""
export P08_B4543_PSU_PROTECTION=""
export P08_B4543_BOOT_BIF=""
export P08_B4543_FSBL_ELF=""
```

## Step 2 — find actual local candidates (read-only)

The filesystem *may not contain* source matching the active boot image;
do not invent paths. Typical Vitis installs include multiple FSBL
source variants/versions and the project can include generated PS config.

```bash
find "$P08_B4543_VITIS_ROOT" "$PWD/vivado/build" "$HOME/Thesis_Evidence" \
  -type f \( -name 'xfsbl_handoff.c' -o -name 'xfsbl_hooks.c' \
          -o -name 'psu_init.c' -o -name 'psu_protection.c' \
          -o -name '*boot*.bif' -o -name 'BOOT.BIN' \
          -o -name '*fsbl*.elf' \) -print 2>/dev/null | head -100

# Smaller/direct searches if the full search is slow:
find "$HOME/Thesis_Evidence" -type f -name '*.bif' -print
find "$PWD/vivado/build" -type f -name 'psu_init.c' -print 2>/dev/null
find "$P08_B4543_VITIS_ROOT/Vitis" -type f \
  -name 'xfsbl_handoff.c' -print 2>/dev/null | head -30
```

After examining the results, set ONLY the paths you actually find.
Copy the full path *returned by find* between the quotes in each
optional export. Example format (replace `/actual/.../file.c`):

```bash
# Example only; DON'T run using these placeholder paths:
# export P08_B4543_FSBL_HANDOFF="/actual/.../xfsbl_handoff.c"
# export P08_B4543_FSBL_HOOKS="/actual/.../xfsbl_hooks.c"
# export P08_B4543_PSU_INIT="/actual/.../psu_init.c"
# export P08_B4543_PSU_PROTECTION="/actual/.../psu_protection.c"
# export P08_B4543_BOOT_BIF="/actual/.../boot.bif"
# export P08_B4543_FSBL_ELF="/actual/.../fsbl.elf"
```

Leave unknown variables empty. The scanner reports missing sources
truthfully and STILL makes an XSA-only inventory (not a hardware proof).
If multiple candidate copies exist, prefer those with accompanying
project build provenance and record each selected file's printed SHA.
Do not claim an installed embeddedsw source is your board's active FSBL.

## Step 3 — verify the accepted original files and run regression tests

```bash
test -s "$P08_B4543_ORIGINAL_XSA" &&
test -s "$P08_B4542_ACCEPTED_POLICY_REPORT" &&
test ! -e "$P08_B4543_OUT" &&
echo "P08_B4543_PC_ONLY_REQUIRED_INPUTS_PRESENT=1"

sha256sum "$P08_B4543_ORIGINAL_XSA"
# 52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f
sha256sum "$P08_B4542_ACCEPTED_POLICY_REPORT"
# ba89166f826425bcd69c86ee7b249f70cd39f359382fa69bd331a366678899f2

PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
  tests/test_p08_b4543_fsbl_boot_source_inventory.py
```

## Step 4 — generate the new PC-only source inventory

Use a Bash argument array so **unlocated optional source files are
not passed as fake paths**. This works with the required exports alone,
and includes every optional file whose export you populated:

```bash
P08_B4543_OPTIONAL_ARGS=()

[[ -z "$P08_B4543_FSBL_HANDOFF" ]] || \
  P08_B4543_OPTIONAL_ARGS+=(--fsbl-handoff "$P08_B4543_FSBL_HANDOFF")
[[ -z "$P08_B4543_FSBL_HOOKS" ]] || \
  P08_B4543_OPTIONAL_ARGS+=(--fsbl-hooks "$P08_B4543_FSBL_HOOKS")
[[ -z "$P08_B4543_PSU_INIT" ]] || \
  P08_B4543_OPTIONAL_ARGS+=(--psu-init "$P08_B4543_PSU_INIT")
[[ -z "$P08_B4543_PSU_PROTECTION" ]] || \
  P08_B4543_OPTIONAL_ARGS+=(--psu-protection "$P08_B4543_PSU_PROTECTION")
[[ -z "$P08_B4543_BOOT_BIF" ]] || \
  P08_B4543_OPTIONAL_ARGS+=(--boot-bif "$P08_B4543_BOOT_BIF")
[[ -z "$P08_B4543_FSBL_ELF" ]] || \
  P08_B4543_OPTIONAL_ARGS+=(--fsbl-elf "$P08_B4543_FSBL_ELF")

PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
  scripts/p08_b4543_fsbl_boot_source_inventory.py \
  --policy-report "$P08_B4542_ACCEPTED_POLICY_REPORT" \
  --xsa "$P08_B4543_ORIGINAL_XSA" \
  "${P08_B4543_OPTIONAL_ARGS[@]}" \
  --out "$P08_B4543_OUT"

sha256sum "$P08_B4543_OUT"
python3 -m json.tool "$P08_B4543_OUT"
```

Expected markers:
```text
P08_B4543_ACCEPTED_XSA_PC_ONLY_SOURCE_INVENTORY_PASS=1
P08_B4543_ACTIVE_KV260_BOOT_FSBL_PROVEN=0
P08_B4543_PROTECTION_CONFIG_AND_MASTER_IDS_PROVEN=0
P08_B4543_FSBL_HOOK_APPROVED_FOR_XMPU_CHANGES=0
P08_B4543_KV260_BOARD_CONTACT=0
P08_B4543_BOARD_JTAG_DDR_EXECUTION_AUTHORIZED=0
```

The local call order is `NOT_SUPPLIED` if no FSBL handoff file was
found, or a source-specific observation if one was supplied.
**Do not mark this phase complete as active boot evidence merely
because the XSA inventory prints PASS.**

## Next physical owner chain (NOT currently authorized)

To turn source observations into a trusted functional backup policy:
verify the exact FSBL ELF, boot BIF/partition hash and BOOT.BIN against
the machine's actual boot media with independent provenance; inspect
`XFsbl_ProtectionConfig` in the exact Vitis 2025.2 source and actual
`psu_protection` output; determine region-slot allocation and secure
read/write master IDs on the routes the frozen PL/A53 actually uses.
Prove DDR and low A53 memory ownership through boot/RPU/PL/DMA,
including the extra 512KiB. Select a **pre-lock** secure integration
point, stage and authenticate P02 before locking, and independently
verify readback and persistent lock.

Only after this work should an alternate boot candidate, new signed
firmware and explicit separately authorized physical pilot be
considered. None are produced or invoked by B4.5.4.3.
