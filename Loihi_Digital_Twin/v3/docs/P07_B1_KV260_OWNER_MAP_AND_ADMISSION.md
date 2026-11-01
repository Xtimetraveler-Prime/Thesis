# P07-B.1 — KV260 scaled runtime feasibility and owner map (candidate v1)

**State:** first P07-B design/native-C acceptance **candidate** on a new branch based on merged main commit a540b68eeab0f2c4ef37d9f1680e1619deb7c98d. User-native verification is **pending**. No new board program, Vivado project, B2 official MNIST TEST access, physical 27-core inference, or measured scaled page traffic is claimed.

## 1. Source authority and accepted boundary

This stage uses the existing accepted P02 record/HP0 architecture (docs/P02_1_DDR_ABI.md, docs/P02_3B2_HP0_INTEGRATION.md), the real P03 A53 standalone runtime (software/p03/p03_finish_run.c, p03_hw_adapter.c, p03_runtime.c and their headers), P05 diagnostics (software/p05/p05_regression_run.c and include/p05_deployment.h), P07-A firmware as a compact **different checkpoint** reference, the proposed B1.3 host wire protocol (src/loihi_twin_v2/p06_b13_streaming.py), and the B2.4/B2.5 frozen snapshot integrity/evidence.

- Frozen B2 model: original 784→1000→10 signed24 LIF, 794,000 dense source connections including signed zeros, **27** compiled logical contexts (26 hidden shards plus one readout), 25 external input ticks plus 1 drain tick.
- Original B2.3 compiled fingerprint: 02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a.
- Original B2.3 B1.1 capacity audit: 82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498.
- Frozen manifest and all 27 P02 initial context identities remain owned by the **original user-local B2.4 directory**, not by this B.1 candidate. The original B2 official TEST protocol stays sealed. B2's 97.08% is TRAIN-derived validation, not a TEST result.

The P05 physical A53 deployment accepts **one sole registered external axon per core**. It has no accepted implementation of the B1.3 many-channel P06B13I1 ingress or B1.3 P06B13R1 packet framing. Reusing P05's DDR payload **address** does not make these wire formats interchangeable.

## 2. Proposed physical DDR owner allocation

All intervals are **half-open [base,end)** and physical addresses. The accepted project reservation is [0x40000000,0x44000000), 64 MiB, **only while an appropriately initialized standalone/JTAG workload is sole owner**. B.1 does not itself prove Linux is halted, DDR isolated, or any ELF is safely linked.

| Address range | Size | P07-B owner / status |
| --- | ---: | --- |
| [0x40000000,0x40D80000) | 14,155,776 B | 27 original initial P02 images at 0x80000/core; core 26 begins 0x40D00000 and ends 0x40D80000. Software-frozen initial bytes only; runtime mutable images NOT board-verified. |
| [0x40D80000,0x43F00000) | unassigned | Reserved/unowned by B.1. May contain stale prior-stage data; no implicit permission to reuse or overwrite. |
| [0x43F00000,0x43FE0000) | 917,504 B | Proposed versioned B.2 frame / route staging within the former P05 payload region; **buffer subdivisions and lifetimes not yet finalized**. |
| [0x43FE0000,0x43FE0100) | 256 B | Proposed new P07-B descriptor, separate from both P05G and P07A4P01. Needs B.2 CRC/digest/length validation. |
| [0x43FE0100,0x43FF0000) | 65,280 B | Unassigned, no P07-B.1 writes. |
| [0x43FF0000,0x44000000) | 65,536 B | Proposed P07-B result/first-error journal; no board mailbox implementation yet. |

Track A's P07-A4 old immutable master occupied part of [0x43F00000,0x43FE0000). **The P07-B planned use intentionally conflicts with that past firmware profile**: old and new profiles must not run together. No accepted Track A files or physical evidence are modified.

Old accepted P03 MMIO shell: [0xA4000000,0xA4001000), ID 0x4C543302, VERSION 0x00010000, CAPABILITIES 0x0001031F; 128-bit FPD HPM0, SmartConnect AXI4-to-32-bit-AXI4-Lite conversion; page register offsets +0x020..+0x054, dispatch +0x080..+0x0AC, debug +0x100..+0x130 (see original software/p03/include/p03_mmio.h). Original independent PL HP0 page path: 256-byte bursts, full page-in 0x6B000 = 438,272 B (1,712 bursts), dirty mutable page-out 0x1A000 = 106,496 B (416 bursts). The **0x80000 DDR record** is not a per-page transfer amount. There is one physical HLS engine and three resident URAM slots, not 27 engines.

## 3. Runtime resource and semantic admission

The original B1.3 deterministic ingress map has 784 × 26 = **20,384** six-byte (pixel,core,axon) routes. Each P06B13I1 image frame occupies **128 + 20,384×6 + 784 = 123,216 bytes**, smaller than the proposed 917,504-byte staging region. This check does NOT validate the actual compiled map, wire CRC, SHA, packet frame storage, or A53 linker RAM.

Each logical core has maximum **4,096 CURRENT bank events and 4,096 emitted packets**. The accepted B2 audit reports **1,000 maximum worst CURRENT/core** in its topology, and 39 outgoing packets for its largest hidden shard, but full 4,096/4,097 boundaries must still be enforced on hardware. Per-destination CURRENT demand includes both external spikes and previous-tick routed NEXT packets. Source pixel indexing must use the exact B1.3 compiled mapping, not pixel=axon shortcuts.

The trained model uses deterministic quota/phase17 input on logical ticks 0..24 and no external spikes on drain tick 25, signed24 saturating LIF, strict greater-than threshold, original refractory/reset, hidden→readout NEXT-only routing, a 26-tick output spike counter and lowest-index argmax (all-silent outputs classify as 0). All 27 cores (even silent ones) must be visited each tick: **702 dispatches/image**, **26 global barriers/image**. B1.5's ~341–382 MB 27-core modeled page-engine traffic is not a measured physical result, nor is this estimate an admission proof.

## 4. Ownership, abort, and physical NO-GO boundaries

The new portable C11 header software/p07/include/p07_b1_owner_map.h defines a **read-only structural validator**, p07_b1_validate(), with statuses OK=0, BAD_ARGUMENT=-1, BAD_TOPOLOGY=-2, BAD_OWNER=-3, BAD_SHELL=-4 and BAD_CAPACITY=-5. It enforces exact B2 profile geometry, source-linked P03/P05 constants, fixed DDR/MMIO addresses, expected shell ID/capabilities/FPD width, and per-core 4,096 limits. It performs **no MMIO, DDR, FPGA or input-file access**. The active B.1 code explicitly hard-disables both P07-B scaled physical execution GO and B2 TEST unseal GO.

Before permitting any real A53 dispatch, later stages must independently prove: (a) correct DDR/boot/Linux exclusion and **new ELF LOAD/BSS/heap/stack/buffer memory map** without collision with the 64-MiB region; (b) verified XSA/bitstream/PL shell and actual width; (c) complete new SHA/CRC-checked B1.3 C ingress and per-core route admission, all-or-nothing rejection; (d) resident-slot page cache, evictions, dirty final writeback and coherency; (e) synchronized CURRENT/NEXT barrier, per-image zero/reset, no partial epoch commit and sticky first-error; (f) all 27 true 26-tick FPGA-vs-independent-host state/spike/packet parity over a predeclared TRAIN-derived corpus. The existing P03 adapter alone is not proof that CPU queues and the approximately 65-KiB static axon bitset fit the eventual A53 ELF. Check actual linker scripts, memory maps and load segments; no compiled P07-B ELF exists in B.1.

On invalid deployment, checksum, out-of-range address, overflow, mismatched board capabilities or a dirty-writeback fault, the future runtime must **fail closed with a durable first error**, never proceed with a partial input/packet bank or silently recover a half-run by calling it a PASS. Firmware-specific error mailbox ABI and rollback/reset policy are deliverables for B.2/B.3; B.1 C return codes are not firmware mailbox codes. Physical SRAM/DDR ownership and admission will be independently tested on-board in B.4. **Official B2 MNIST TEST remains sealed** until post-acceptance explicit user authorization.

## 5. Native verification and user acceptance gate

The native C harness tests the expected 27×P02 address geometry, staging capacity, 26-tick/one-engine/three-slot topology, P03/P05 header drift, page burst arithmetic, physical shell identity and the **4,096 pass / 4,097 reject** boundaries. It is compiled by tests/test_p07_b1_owner_map.py against *real existing repository C headers* with -std=c11 -Wall -Wextra -Werror -pedantic. This is a host-native geometry and fail-closed regression, not a board runtime check.

From your workstation (no dataset/test unseal and no FPGA programming):

    cd ~/Git/Thesis
    git fetch origin
    git switch agent/v3-p07-b-scaled-physical-inference
    git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
    source ~/Git/Thesis/.venv-p08/bin/activate
    cd Loihi_Digital_Twin/v3
    PYTHONPATH="$PWD/src" python -m pytest -q -rs tests/test_p07_b1_owner_map.py

Read-only accepted predecessor regressions (no B2 official TEST):

    PYTHONPATH="$PWD/src" python -m pytest -q -rs \
      tests/test_p06_b25_acceptance.py tests/test_p06_b24_freeze.py \
      tests/test_p06_b23_trained_audit.py tests/test_p06_b13_streaming.py \
      tests/test_p06_b1_contract.py

Optional original frozen package read-only deep integrity:

    PYTHONPATH="$PWD/src" python scripts/p06_b25_acceptance.py \
      --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" --deep

**Gate:** user posts native B.1 PASS plus predecessor regression results; only then begin B.2. Keep the draft P07-B PR unmerged until separately authorized. Physical scaled execution and B2 TEST remain NO-GO irrespective of this test.
