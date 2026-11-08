# P08-B4.5.4.1 — PC-only DDR geometry/owner gap acceptance

**Accepted:** operator ran `scripts/p08_b454_ddr_owner_preflight.py` from
the new standalone B4.5.4.1 branch and supplied a complete JSON report and
SHA-256. Local time November 4, 2026; UTC November 5, 2026.
The operator additionally said all prescribed testing went well; CI native
regression also passed. This report is **not** a physical ownership
attestation or permission to use JTAG.

**Report:** `/home/dna/Thesis_Evidence/p08_b454_ddr_owner_gap_20261105T051850Z.json`

**Accepted SHA-256:**
`7a1d87cf3278245a4a5ed612773ac228097e506f464861c3e1b69856f6ba56f2`.

Source `schema=p08-b454-ddr-owner-gap-pc-only-preflight-v1`.
Accepted parent paired A53 ELF report SHA:
`03b433527901a9d51dfb8a8ca99c0321d81335859d1be14505eb6a7be9369ec1`.

Both original new A53 ELFs had `PT_LOAD`
`[0x00000000,0x00109BC0)` (1,088,448 B memory,
118,868 B file, start 0, matching read-only on-disk ELF64/AArch64).
These are **bare-metal LOAD segments**, not proof that low DDR has
an exclusively admitted runtime owner.

Source-declared static DDR nonoverlap check passed for original
27 mutable P02 records, frozen B4M route/frame sources, 1024 raw
images, result journal, whole service meter, B4.5 sidecar, immutable
backup, B4L binding/route output and terminal mailbox.

The required 27-core backup is
`[0x43000000,0x43D80000)` (13.5 MiB).
A conservative 1-MiB-region prospective DDR-XMPU cover is
`[0x43000000,0x43E00000)`, including an *extra*
`[0x43D80000,0x43E00000)` 512KiB not allocated by the observed
B4.5 firmware. **No independent physical owner proof exists for
that 512KiB.**

The operator report explicitly states:
- `decision=PC_STATIC_GEOMETRY_PASS_PHYSICAL_OWNER_NO_GO`;
- `all_DDR_port_and_master_permissions_proven=false`;
- `all_processor_DDR_owners_excluded=false`;
- `low_DDR_exclusive_A53_ownership_proven=false`;
- `physical_backup_immutable_after_one_time_sha_proven=false`;
- `xmpu_region_programmed_or_readback=false`;
- `new_guard_enabled_ELF_built=false`;
- `board_contact=false`;
- `operator_authorized_KV260_board_action=false`;
- `16_image_pilot_or_1024_session_performed=false`;
- `official_MNIST_TEST=SEALED_NOT_ACCESSED`.

All 14 owner categories (FSBL, TF-A, U-Boot, Linux, other A53, RPU,
PMU/CSU, PL/DMA, six DDR XMPUs, FPD/CCI DMA, debug,
low-DDR, backup staging and sidecar) remain
`NOT_ESTABLISHED`. No optional independent boot observations were
supplied. This is expected and **requires a subsequent independent
boot/protection engineering and hardware verification stage**.

**Conclusion:** accept B4.5.4.1 as PC-only owner-gap baseline, advance
to a separately versioned boot-time protection design *without
enabling existing fail-closed A53 backup lock callbacks*.
No PR merge or board run authorized by this acceptance.
