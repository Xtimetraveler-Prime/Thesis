# P08-B4.5.4.3 — operator PC-only FSBL/XSA source inventory accepted

**Original operator report:** `/home/dna/Thesis_Evidence/p08_b4543_fsbl_xsa_inventory_20261105T060831Z.json`

**Original report SHA-256:** `9c2a142bc62dc7bbfe73e5f85bd819adcf3854dfc3e02701ee18c9e7162667f5`.

```text
P08_B4543_ACCEPTED_XSA_PC_ONLY_SOURCE_INVENTORY_PASS=1
P08_B4543_LOCAL_FSBL_HANDOFF_ORDER=PROTECTION_CONFIG_CALLED_BEFORE_BEFOREHANDOFF_HOOK
P08_B4543_ACTIVE_KV260_BOOT_FSBL_PROVEN=0
P08_B4543_PROTECTION_CONFIG_AND_MASTER_IDS_PROVEN=0
P08_B4543_FSBL_HOOK_APPROVED_FOR_XMPU_CHANGES=0
P08_B4543_KV260_BOARD_CONTACT=0
P08_B4543_BOARD_JTAG_DDR_EXECUTION_AUTHORIZED=0
```

Original local installed Vitis 2025.2 handoff source SHA-256:
`161ffc06037594fd14be856dce29ec6643eb97c8dcbe2872abc414b8c4d5d80a`;
hooks source SHA:
`35d0fe1f292166c36b09addb2aebb239c97583e66ceea3379a494689a4dd1f20`;
routed original P03 PS initialization source:
`049ae8a025fab04526218d351b74d06313f7f163633dfcfde2cb5579e22b8679`.

Accepted P03 routed XSA SHA-256:
`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.
The internal XSA `psu_init.c` SHA matches the selected Vivado-generated
local PS source exactly:
`049ae8a025fab04526218d351b74d06313f7f163633dfcfde2cb5579e22b8679`.
Other relevant XSA files included `psu_init.tcl`, `psu_init_gpl.c`
and the original routed HWH.

**Observations:** Vendor FSBL handoff calls protection configuration BEFORE
the before-handoff hook; XSA contains PS DDR/XMPU configuration symbols.
No actual active boot BIF, FSBL ELF, device DDR XMPU readbacks or
real AXI reader MIDs were supplied.

**Hard NO-GO:** `current_boot_image_provenance_independently_established=false`,
`true_protection_config_lock_timing_verified_on_active_boot=false`,
`effective_per_port_AXI_reader_master_IDs_verified=false`,
`physical_execution_authorized=false`. This acceptance is a file-source
provenance gate, not a hardware-read/write or board permission.

Next permitted work: source/compile-option branch analysis of the
exact installed 2025.2 FSBL and original XSA-generated protection
functions, a candidate *no-board* protection compile/boot state matrix
and independent read-only test procedures. Do not modify QSPI,
FSBL/boot media, the two accepted B4.5.3 A53 ELFs, XMPU registers or
PL until full physical owner/protection evidence and separate approval.
