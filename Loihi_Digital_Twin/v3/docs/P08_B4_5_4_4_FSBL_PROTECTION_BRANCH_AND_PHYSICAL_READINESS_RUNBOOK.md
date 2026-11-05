# P08-B4.5.4.4 — original Vitis FSBL protection bypass and boot readiness

**Purpose:** Inspect actual original Vitis 2025.2 FSBL C source,
2025.2 FSBL header configuration, and EXACT original XSA-generated
P03 `psu_init.c`. Record which paths exist and are eligible for a
**future separately built and independently verified** trusted boot
candidate. This stage is PC-only, is not secure boot and cannot enable
the accepted unprovisioned A53 backup-guard callbacks.

## Accepted original evidence

The operator's actual B4.5.4.3 source inventory was:
`/home/dna/Thesis_Evidence/p08_b4543_fsbl_xsa_inventory_20261105T060831Z.json`
SHA-256:
`9c2a142bc62dc7bbfe73e5f85bd819adcf3854dfc3e02701ee18c9e7162667f5`.

Accepted local Vitis `xfsbl_handoff.c` SHA:
`161ffc06037594fd14be856dce29ec6643eb97c8dcbe2872abc414b8c4d5d80a`.
Accepted original generated P03 `psu_init.c` SHA:
`049ae8a025fab04526218d351b74d06313f7f163633dfcfde2cb5579e22b8679`.
The latter equals the SHA of the root `psu_init.c` inside the
accepted routed P03 XSA. Accepted XSA SHA:
`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.

The actual accepted P03 XSA contains generated `psu_init.c`,
`psu_init.tcl` and HWH hardware description entries with XMPU
symbols. This is source evidence **not** current register readback.

## New source finding: FSBL disables full protection by default

Unlike merely reading a source file name or counting XMPU labels,
P08-B4.5.4.4 disambiguates a critical compile-time choice:

1. The AMD/Xilinx tagged **`xlnx_rel_v2025.2`**
   `xfsbl_hw.h` explicitly defines
   `XFSBL_PROT_BYPASS` unless the compiler defines
   **`FSBL_PROT_BYPASS_EXCLUDE`**.
2. In the tagged 2025.2 `xfsbl_handoff.c`,
   `XFsbl_ProtectionConfig()` calls
   `psu_apply_master_tz()` and `psu_ocm_protection()`
   when the bypass macro is active, **NOT the full generated
   `psu_protection()` plus `psu_protection_lock()`**.
3. Under the opposite compile-time branch, it calls
   `psu_protection()` followed by
   `psu_protection_lock()` before the ordinary
   `XFsbl_HookBeforeHandoff()` call.
4. The default protection-bypass branch in AMD's PUBLIC
   versioned source is a **source-level default**. We DO NOT
   know whether `FSBL_PROT_BYPASS_EXCLUDE` was actually
   supplied to the **specific currently booted KV260 FSBL**.
   Existing BOOT.BIN, BIF, ELF, toolchain and compiler flags
   have NOT been tied to current boot media.

**Engineering consequence:** just changing a handoff hook or assuming
Vivado-generated XMPU code executes is not sufficient. The real
compile/link choice must be demonstrably enabled, the 13.5MiB original
context partition must be staged and authenticated before lock, and
the *actual permitted A53 reader AXI master IDs* (plus all PL/PS
write masters) must be proven. Enabling the alternate compilation
path without auditing *all original generated XMPU regions and
security effects* could make the boot unbootable. This stage does
**not** modify any boot compile flag or generator.

**Original vendor sources (adaptation; not thesis-invented protection):**

- [Xilinx/AMD `xfsbl_hw.h` at tagged 2025.2](https://github.com/Xilinx/embeddedsw/blob/xlnx_rel_v2025.2/lib/sw_apps/zynqmp_fsbl/src/xfsbl_hw.h) — defines the default bypass and exclusion macro.
- [Xilinx/AMD `xfsbl_handoff.c` at tagged 2025.2](https://github.com/Xilinx/embeddedsw/blob/xlnx_rel_v2025.2/lib/sw_apps/zynqmp_fsbl/src/xfsbl_handoff.c) — guarded `XFsbl_ProtectionConfig`, its full `psu_protection`/lock path and placement before handoff.
- [AMD UG1085, Program the DDR XMPUs](https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Program-the-DDR-XMPUs) — six DDR XMPU paths and example region permissions.
- [AMD UG1085, XMPU Instances](https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Instances) — DDR port routing: APU/CCI traffic traverses DDR XMPU1/2 and PS/PL write masters can traverse other DDR ports.
- [AMD UG1085, XMPU Regions](https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/XMPU-Regions) — 1MiB alignment and higher-priority region overlap semantics.
- [AMD UG1137, FSBL/Handoff](https://docs.amd.com/r/en-US/ug1137-zynq-ultrascale-mpsoc-swdev/Handoff) — trusted protection step and A53 handoff ordering.

**Attribution:** All named FSBL macros and `psu_protection`
functions are AMD/Xilinx mechanisms; this thesis adds
source-integrity-pinned analysis for the particular frozen
neuromorphic FPGA/DDR backing and compares reset modes. The
checker implementation is independent and has no copied AMD
programming register sequences.

## Exact local verification with EVERY required export

Run these commands from a fresh VS Code terminal. They use exactly
the real original source paths and accepted SHA previously posted by
the operator. **No Vitis compile, Git merge, board or XSDB.**

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-b4544-fsbl-protection-review
git pull --ff-only origin agent/v3-p08-b4544-fsbl-protection-review
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# ALL SIX required input/output environment variables:
export P08_B4544_PREVIOUS_SOURCE_REPORT="$HOME/Thesis_Evidence/p08_b4543_fsbl_xsa_inventory_20261105T060831Z.json"
export P08_B4544_FSBL_HANDOFF="$HOME/Vivado/2025.2/data/embeddedsw/lib/sw_apps/zynqmp_fsbl/src/xfsbl_handoff.c"
export P08_B4544_FSBL_HW_HEADER="$HOME/Vivado/2025.2/data/embeddedsw/lib/sw_apps/zynqmp_fsbl/src/xfsbl_hw.h"
export P08_B4544_PSU_INIT="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/project/loihi_twin_v3_p03_mmio_impl.gen/sources_1/bd/loihi_twin_v3_p03_mmio_impl/ip/loihi_twin_v3_p03_mmio_impl_zynq_ultra_ps_e_0_0/psu_init.c"
export P08_B4544_ORIGINAL_XSA="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports/p03_2_ps_mmio.xsa"
export P08_B4544_OUT="$HOME/Thesis_Evidence/p08_b4544_fsbl_protection_branch_$(date -u +%Y%m%dT%H%M%SZ).json"
```

If a file has moved, use the following read-only searches to
**discover, verify and explicitly assign its ACTUAL original path**.
Do not point the script at a different generated P03 revision:

```bash
find "$HOME/Thesis_Evidence" -type f -name 'p08_b4543_fsbl_xsa_inventory_*.json' -print
find "$HOME/Vivado/2025.2" -type f -name xfsbl_handoff.c -print 2>/dev/null
find "$HOME/Vivado/2025.2" -type f -name xfsbl_hw.h -print 2>/dev/null
find "$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z" \
  -type f -name psu_init.c -print 2>/dev/null
find "$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z" \
  -type f -name p03_2_ps_mmio.xsa -print 2>/dev/null
```

Preflight (only proceed after `..._INPUTS_PRESENT=1`):

```bash
test -s "$P08_B4544_PREVIOUS_SOURCE_REPORT" &&
test -s "$P08_B4544_FSBL_HANDOFF" &&
test -s "$P08_B4544_FSBL_HW_HEADER" &&
test -s "$P08_B4544_PSU_INIT" &&
test -s "$P08_B4544_ORIGINAL_XSA" &&
test ! -e "$P08_B4544_OUT" &&
echo "P08_B4544_PC_ONLY_INPUTS_PRESENT=1"

sha256sum \
  "$P08_B4544_PREVIOUS_SOURCE_REPORT" \
  "$P08_B4544_FSBL_HANDOFF" \
  "$P08_B4544_PSU_INIT" \
  "$P08_B4544_ORIGINAL_XSA"
```

Expected SHA values in this order:

```text
9c2a142bc62dc7bbfe73e5f85bd819adcf3854dfc3e02701ee18c9e7162667f5
161ffc06037594fd14be856dce29ec6643eb97c8dcbe2872abc414b8c4d5d80a
049ae8a025fab04526218d351b74d06313f7f163633dfcfde2cb5579e22b8679
52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f
```

Run native tests first:

```bash
PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
  tests/test_p08_b4544_fsbl_protection_path.py
```

Then run original-file source review:

```bash
PYTHONPATH="$PWD/scripts:$PWD/src" python3 \
  scripts/p08_b4544_fsbl_protection_path.py \
  --prior-report "$P08_B4544_PREVIOUS_SOURCE_REPORT" \
  --fsbl-handoff "$P08_B4544_FSBL_HANDOFF" \
  --fsbl-hw-header "$P08_B4544_FSBL_HW_HEADER" \
  --psu-init "$P08_B4544_PSU_INIT" \
  --xsa "$P08_B4544_ORIGINAL_XSA" \
  --out "$P08_B4544_OUT"

sha256sum "$P08_B4544_OUT"
python3 -m json.tool "$P08_B4544_OUT"
```

Expected markers after successful source analysis:

```text
P08_B4544_ACTUAL_LOCAL_FSBL_TWO_BRANCHES_PARSED=1
P08_B4544_VITIS_HEADER_DEFAULT_PROTECTION_BYPASS=1
P08_B4544_XSA_TO_GENERATED_PSU_INIT_EXACT_SHA_MATCH=1
P08_B4544_REAL_FSBL_BUILD_COMPILE_FLAGS_PROVEN=0
P08_B4544_REAL_DDR_XMPU_PERMISSIONS_PROVEN=0
P08_B4544_BOARD_JTAG_BOOT_DDR_WRITES_AUTHORIZED=0
```

**Do not change** `FSBL_PROT_BYPASS_EXCLUDE` merely to get a
different result. The report's correct source-level verdict is
`FSBL_SOURCE_BYPASS_PATH_IDENTIFIED_REAL_BOOT_AND_XMPU_NO_GO`.
It identifies how a properly controlled *future* secure FSBL
could be constructed, NOT that existing DDR backup is immutable.

## Shortest remaining route to an actual 16-image physical pilot

1. **Read-only boot provenance:** identify which existing boot
   medium is selected, preserve a read-only full image/FSBL,
   inspect the matching BOOT.BIN/BIF and compiler flags
   (including `FSBL_PROT_BYPASS_EXCLUDE`). Do not copy arbitrary
   files from installation into the live boot chain.
2. **Exact protected-boot design:** reserve 14MiB
   `[0x43000000,0x43E00000)` (13.5MiB contexts + 512KiB guard);
   prove no FSBL/TF-A/U-Boot/Linux/DDR/PL/debug collisions. Identify
   *actual* AXI IDs/permissions and reserved XMPU slots on
   each connected DDR path; never blindly enable source
   `psu_protection` or the symbolic region index 14/15.
3. **Trusted stage/lock:** on independent recoverable development
   media only, create a separate compatible FSBL/boot candidate that
   stages the exact frozen 27x512KiB backup, verifies SHA-256,
   and locks correctly scoped RO permissions *before* A53
   handoff. The A53 may **read** backup; all conflicting write
   masters must be blocked. No guessed runtime register writes.
4. **Real attestation and fresh firmware:** separately implement
   a trusted read-only continuing XMPU/owner attestation interface
   consumed by a NEW B4.5 guard-enabled A53 ELF. Preserve original
   unprovisioned A/B ELFs as independent offline references.
   Re-run frozen neural and ELF admission on new outputs.
5. **Operator-approved bounded test:** only after reproducible
   recovery and preflight, explicitly obtain approval for a
   controlled 16-image physical session. Verify backups and parity
   before the optional 1024-image sessions, measure both reset and
   whole inference service with the same current hardware build.
   Official MNIST TEST stays sealed.

**B4.5.4.4 is a necessary source-based step toward this sequence,
NOT a physical permission.**
