# P07-A4.2b — User-native Vitis acceptance of persistent Cortex-A53 ELF

**Status:** CLOSED / USER VITIS BUILD ACCEPTED, 2026-10-17.
**Hardware functional inference:** NOT RUN; this acceptance closes *build* only.
**Official canonical MNIST TEST:** SEALED / NOT READ.

The user independently built the new dedicated P07-A4.2b persistent A53
application in Vitis, including required frozen XSA identity and
reserved DDR ELF LOAD-section isolation. The user reported
the following terminal markers and immutable SHA256; they
are attested user-terminal results, **not** a repository copy of the ELF.

```text
Build Finished successfully
P07_A4_XPFM=/tmp/v3_p07_a4_persistent_20261017T190943/vitis_workspace/p07_a4_platform/export/p07_a4_platform/p07_a4_platform.xpfm
P07_A4_ELF=/tmp/v3_p07_a4_persistent_20261017T190943/vitis_workspace/p07_a4_board.elf
P07_A4_A53_VITIS_BUILD_PASS=1
P07_A4_BOARD_STATUS=NOT_RUN
PASS: P07-A4.2b standalone ELF stays outside reserved 64MiB PS/PL DDR region
P07_A4_XSA_SHA256=52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f
P07_A4_ELF_SHA256=dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb
P07_A4_VITIS_NATIVE_GATE_PASS=1
P07_A4_KV260_STATUS=NOT_RUN
```

A second independent `sha256sum` on the exact ELF
reproduced `dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb`.

**Acceptance:** isolated new Vitis Cortex-A53 firmware successfully built
against the already user-accepted routed P03.2c 128-bit XSA,
with build marker and LOAD section guards. It is NOT the
accepted old `p07_a2_board.elf`; it is a *new candidate*.

**Next:** A4.2c first guarded KV260 physical ramp16 pilot,
using the above exact ELF SHA and original accepted bitstream.
Physical terminal success alone is UNVERIFIED NUMERICS:
full 1 MiB result journal and 64 KiB selected full trace
MUST agree with the independent P03 packed replay before
closing the first pilot. The official TEST data remains SEALED.
Do not merge into main without explicit approval.
