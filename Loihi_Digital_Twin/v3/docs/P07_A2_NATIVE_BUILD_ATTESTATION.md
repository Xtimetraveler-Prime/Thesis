# P07-A2.2 user-native Vitis A53 build acceptance (2026-10-17)

**Status: NATIVE VITIS BUILD PASSED; PHYSICAL KV260 RUN NOT YET EXECUTED.**

The user supplied direct successful Vitis/ELF build output from a local
standalone A53 build on 2026-10-17. The build did **not** verify the
FPGA inference result or board execution.

| Item | User-confirmed value |
|---|---|
| Build directory | `/tmp/v3_p07_a2_20261017T123554` |
| Routed FPD128 XSA SHA-256 | `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f` |
| Built A53 ELF SHA-256 | `64601cc0ea491f9ae3e3ba8287cd9d52640b8c1d12273e8c8601c1f1aeac4c96` |
| XPFM | `/tmp/v3_p07_a2_20261017T123554/vitis_workspace/p07_a2_platform/export/p07_a2_platform/p07_a2_platform.xpfm` |
| ELF | `/tmp/v3_p07_a2_20261017T123554/vitis_workspace/p07_a2_board.elf` |
| Vitis reported | `Build Finished successfully` |
| Native compile marker | `P07_A2_A53_VITIS_BUILD_PASS=1` |
| Firmware memory-segment audit | `PASS: P07-A2 standalone ELF stays outside reserved 64MiB PS/PL DDR region` |
| Native acceptance marker | `P07_A2_VITIS_NATIVE_GATE_PASS=1` |
| KV260 status at acceptance | `P07_A2_KV260_STATUS=NOT_RUN` |

**Important supersession:** Before physical staging, a source audit identified
that the first A53 candidate read the timestep for *full trace capture*
from a different, permanently zero-initialized static `p03_rt` object
instead of the P03 scheduler's actual runtime object. This made tick
0..25 trace capture indexing incorrect despite successful compilation
and mock tests. The issue is fixed in the same development branch,
beginning with commit `d98598e9213204d020b7dc068f113f827a4f3b37`.
The corrected standalone firmware embeds the distinct build identity
`P07_A2_KV260_A53_FROZEN_TRACK_A_V1_TRACE_CONTEXT_FIX` and the
Vitis build shell now requires that exact ELF identity string.

Thus the user's **original built ELF (SHA-256
`64601cc0…ac4c96`) must NOT be deployed to the FPGA**. The
native *toolchain/XSA* gate is user-accepted, but the corrected-source
ELF must be rebuilt into a **NEW isolated Vitis directory**, and its
new SHA-256 must be captured before physical execution. No accepted
P03/P05 goldens, RTL, HLS or P06 training/checkpoint data are modified.

The immutable P02 context full-file SHA-256 remains
`9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955`.
The frozen compiled ingress deployment fingerprint remains
`e612a971cda11fae3f1be215c0ca3ed7de7b2af7339446e926ce559658db2f7f`.

Next: rerun native regression suite, **rebuild** standalone P07-A2 ELF,
prepare the synthetic P07 input batch (black, white, ramp), stage into
dedicated bare-metal DDR and capture a 64KiB result mailbox. Only real
hardware/independent comparator evidence can close P07-A2.
