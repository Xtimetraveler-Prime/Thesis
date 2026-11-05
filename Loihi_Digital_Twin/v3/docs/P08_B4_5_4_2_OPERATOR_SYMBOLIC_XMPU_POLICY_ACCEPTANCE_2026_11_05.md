# P08-B4.5.4.2 — operator-accepted symbolic six-port XMPU policy

**Accepted:** original, PC-only operator verification on 2026-11-05 UTC.
No actual DDR XMPU was programmed, configured, read, or proven.

Original operator report path:
`/home/dna/Thesis_Evidence/p08_b4542_xmpu_policy_pc_20261105T054738Z.json`

**Original report SHA-256:**
`ba89166f826425bcd69c86ee7b249f70cd39f359382fa69bd331a366678899f2`

Source-proposed JSON policy SHA-256 at operator audit:
`7f78e7582e7fee12a06d83f14e45f1de1faf877ce1429af441dd83db3e851d2a`.

Confirmed operator terminal markers:
```text
P08_B4542_SIX_PORT_SYMBOLIC_WRITE_DENIAL_PC_ONLY_PASS=1
P08_B4542_MODELED_TRANSACTIONS=147456
P08_B4542_REAL_READER_ALLOWLIST_READY=0
P08_B4542_FSBL_BOOT_PROTECTION_PROVEN=0
P08_B4542_XMPU_REGISTERS_PROGRAMMED=0
P08_B4542_NEW_A53_FIRMWARE_PROVISIONED=0
P08_B4542_BOARD_JTAG_DDR_ACTION_AUTHORIZED=0
```

The JSON confirms:
`decision=SYMBOLIC_WRITE_DENY_CONTRACT_PASS_READERS_AND_REAL_BOOT_NOT_READY_NO_GO`,
`candidate_port_count=6`, `AXI_master_ID_width=10`,
`candidate_real_readers_authorized=false`,
`all_six_real_DDR_ports_confirmed_and_locked=false`,
`verified_FSBL_hook_after_staging=false`,
`existing_XMPU_region_slot_14_15_free_proven=false`,
`any_physical_DDR_master_exclusivity_proven=false`,
`physical_KV260_contact=false`,
`physical_execution_authorized=false`, and
`official_MNIST_TEST=SEALED_NOT_ACCESSED`.

**Result:** B4.5.4.2 *static policy hypothesis and symbolic-model
validation* ACCEPTED; no physical backup read-only guarantee,
real reader whitelist or permitted KV260 boot.

## Research discovered at transition to B4.5.4.3

The public AMD/Xilinx FSBL `xfsbl_handoff.c` on the upstream
`master` branch calls `XFsbl_ProtectionConfig()` before
`XFsbl_HookBeforeHandoff(EarlyHandoff)`.
Therefore the earlier proposed handoff hook must not be assumed
suitable for changing XMPU configuration; it may run **after**
the XMPU protection config has locked the registers.

Reference:
https://github.com/Xilinx/embeddedsw/blob/master/lib/sw_apps/zynqmp_fsbl/src/xfsbl_handoff.c

AMD UG1137 describes the protection configuration in handoff:
https://docs.amd.com/r/en-US/ug1137-zynq-ultrascale-mpsoc-swdev/Handoff

This is an **upstream source observation**, not proof that the
operator's installed Vitis 2025.2 FSBL or actual KV260 boot media
contains that exact source, lock order or boot partitions. Before
writing any boot code, require a read-only exact local FSBL/Vivado
configuration inventory and a reproducible boot-image provenance chain.
Neither B4.5.3 accepted A53 ELF may be modified or run.
