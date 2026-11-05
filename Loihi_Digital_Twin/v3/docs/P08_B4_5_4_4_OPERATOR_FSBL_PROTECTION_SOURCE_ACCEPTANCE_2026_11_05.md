# P08-B4.5.4.4 — operator-accepted local FSBL protection source gate

**Acceptance level:** PC-only C-source and XSA provenance; **NOT**
physical execution, compiled boot identity, persistent XMPU protection,
A53 backup ownership, or firmware launch authorization.

**Operator local result (2026-11-05 UTC):**
```text
P08_B4544_INPUTS_FOUND=1
16 tests: ................ [100%]
P08_B4544_ACTUAL_LOCAL_FSBL_TWO_BRANCHES_PARSED=1
P08_B4544_VITIS_HEADER_DEFAULT_PROTECTION_BYPASS=1
P08_B4544_XSA_TO_GENERATED_PSU_INIT_EXACT_SHA_MATCH=1
P08_B4544_REAL_FSBL_BUILD_COMPILE_FLAGS_PROVEN=0
P08_B4544_REAL_DDR_XMPU_PERMISSIONS_PROVEN=0
P08_B4544_BOARD_JTAG_BOOT_DDR_WRITES_AUTHORIZED=0
```

**Original report (do not overwrite):**
`/home/dna/Thesis_Evidence/p08_b4544_fsbl_protection_branch_20261105T062334Z.json`

**SHA-256:**
`e2c40e2c58a1a58d4c5611be7f95a58671b2c9e172a236323915dcb7368961a9`.

**Pinned local inputs independently checked by the operator:**

| Input | SHA-256 |
| --- | --- |
| B4.5.4.3 accepted report | `9c2a142bc62dc7bbfe73e5f85bd819adcf3854dfc3e02701ee18c9e7162667f5` |
| Vitis 2025.2 `xfsbl_handoff.c` | `161ffc06037594fd14be856dce29ec6643eb97c8dcbe2872abc414b8c4d5d80a` |
| Vitis 2025.2 `xfsbl_hw.h` | `f8dc576e02f3f8678600e210eda7ee7b7a6713c15b112078da88036d6cb5d1f7` |
| Original P03 generated `psu_init.c` (also root P03 XSA member) | `049ae8a025fab04526218d351b74d06313f7f163633dfcfde2cb5579e22b8679` |
| Original routed P03 XSA | `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f` |

**Source facts admitted:**

- Installed FSBL source calls `XFsbl_ProtectionConfig()` **before**
  `XFsbl_HookBeforeHandoff()`.
- `xfsbl_hw.h` defines `XFSBL_PROT_BYPASS` unless the compile
  configuration defines `FSBL_PROT_BYPASS_EXCLUDE`.
- Bypass branch calls `psu_apply_master_tz()` and
  `psu_ocm_protection()`, not the full `psu_protection()` and
  `psu_protection_lock()`.
- Non-bypass branch calls `psu_protection()` followed by
  `psu_protection_lock()`, but **we do not know** which branch was
  compiled into the FSBL actually executed on the KV260.
- The reported source body sizes are 130 B for `psu_protection`
  and 43 B for `psu_protection_lock`; they are likely wrappers or
  dispatcher entry points. **The zero direct-literal register-address
  matches do not mean there are no actual XMPU registers configured.**
  Resolve real function call graphs, generated `psu_init.h`,
  `psu_init.tcl`, register tables and actual compiled path next.
- No boot BIF, active `BOOT.BIN`, actual FSBL ELF/build flags,
  independent XMPU register readback, DDR master ID ownership,
  persistent read-only backup, backup staging, low-DDR A53 owner,
  or secure guard-enabled A53 firmware is established.

**Accepted final decision:**
`FSBL_SOURCE_BYPASS_PATH_IDENTIFIED_REAL_BOOT_AND_XMPU_NO_GO`.

Source attribution: AMD/Xilinx 2025.2 versioned
[`xfsbl_hw.h`](https://github.com/Xilinx/embeddedsw/blob/xlnx_rel_v2025.2/lib/sw_apps/zynqmp_fsbl/src/xfsbl_hw.h),
[`xfsbl_handoff.c`](https://github.com/Xilinx/embeddedsw/blob/xlnx_rel_v2025.2/lib/sw_apps/zynqmp_fsbl/src/xfsbl_handoff.c),
and [UG1085 DDR XMPU](https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Program-the-DDR-XMPUs).
Source-analysis tools are thesis-specific; the underlying XMPU/FSBL
security mechanism was developed by AMD/Xilinx, not by the thesis team.

**Next submilestone:** B4.5.4.5 generated PSU protection call-graph,
tables, configuration-mapping and active-boot provenance **PC-only**.
No new B4.5 physical run, QSPI writes, PS/XMPU register writes,
JTAG/XSDB actions, A53 DDR downloads, or changes to the accepted
fail-closed guard are authorized by this result. Keep official
MNIST TEST SEALED_NOT_ACCESSED.
