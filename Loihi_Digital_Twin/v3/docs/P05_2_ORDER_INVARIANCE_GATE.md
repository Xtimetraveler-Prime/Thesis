# P05.2c — Physical service-order invariance gate (NOT YET run)

**Status:** Development implemented on
`agent/v3-p05-board-regression`. Native tests and independent
KV260 physical acceptance **PENDING**. P05.2a deliberately
incorrect checkpoint detection and P05.2b fast/no-checkpoint
neural equivalence have both passed independent physical
verification. P05.1 and the accepted FPGA bitstream remain intact.

## New directed coverage

This tests a scheduler property not covered by the original
P05.1/P05.2 tests: **the service order of logical cores must not
change any neural result when all network packets are delivered
to NEXT timestep and the global barrier prevents premature
bank advancement.**

The accepted P05.1 threshold-4, weight-3 triangle has
logical core IDs `0,1,2`, three resident FPGA context slots,
five timesteps, routes 0→1, 1→2, 2→0, and one external input
axon 10+ID/core/timestep. The new deployment intentionally
changes the A53 logical service order from `[0,1,2]` to
**`[2,0,1]`**. This changes slot-to-core placement and the
order of dispatch/packet observations, but **not** any neural
initial image, packet destination, input event or neural
parameter.

Unlike a simple report-order permutation, the new PS
`p03_rt_init` consumes the descriptor order and genuinely
pages cores into its slots in that order, then services
the cores that way on every timestep. The external ingress
and 15 state checkpoints are *also* sorted by the new
service rank to satisfy the fail-closed ABI.

**No changes to C, Vitis, PL RTL, or accepted ELF.**

| Physical evidence | Required |
|---|---:|
| New A53 core service order | 2, 0, 1 |
| Timesteps | 5 |
| Hardware dispatches | 15 |
| Emitted/routed packets | 12 |
| Direct-to-resident deliveries | 12 |
| Intermediate `state0` checkpoints | 15 passing |
| Global barriers | 5 |
| Initial page-in commands | 3 |
| Replacement page-ins, evictions | 0 |
| Final dirty page-outs | 3 |
| Total PL page commands | 6 |
| Physical final 512 KiB records | 3, byte-exact to fresh reordered-model goldens **and** original-order Python goldens **and** previously accepted KV260 SHA256s |

The **original** physical SHA identities of these three
logical cores, as independently accepted in P05.1 diagnostic
and P05.2b fast mode, are:

- core0: `5c4288e41e1599aea5f854a4022fb88a6b04ddc003b01238e16f5a7c59665381`
- core1: `2767f8cbca59d8e9bb85d0f37d055a7b4a7c4e94676d56bbd3efeff4f4f6c0f2`
- core2: `d6c8982882023c8b0065ca856a3caf35a1b6fa54196a6fb546b774deca32c82f`

For a **new** Python reference, `p05_2_order_fixture.py`
imports an isolated instance of the accepted P02
`LogicalChip` oracle through the accepted P05.1 triangle
configuration, sets `SERVICE_ORDER=(2,0,1)`, and independently
generates a fresh `reordered_golden/` model including the
per-step state0 vectors, packet expectations and all three
initial/final DDR records. It checks that the new model's
**every per-timestep/per-core state and full record image**
equals the independently regenerated original order.
The trace digest can differ because normalized trace
ordering is allowed to reflect schedule order;
**trace SHA equality is not required**.

The new device verifier is similarly strict: it
rechecks P05G core/event ordering and 15 model-derived
CRC observations, model oracle trace/manifest identities,
the physical P05R mailbox, and **actual complete** DDR
images using BOTH independently generated models and
pinned accepted diagnostic KV260 SHA hashes. A result
mailbox PASS without final DDR PASS is rejected.

## First independent checkpoint: native Python/C + host simulator

Pull the existing development branch:

```bash
cd ~/Git/Thesis
git switch agent/v3-p05-board-regression
git pull --ff-only origin agent/v3-p05-board-regression
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python -m pytest -q \
  tests/test_p05_2_order.py \
  tests/test_p05_2_fast.py \
  tests/test_p05_2_fault.py \
  tests/test_p05_1_triangle.py \
  tests/test_p05_1_physical_probe.py \
  tests/test_p05_1_deployment.py \
  tests/test_p05_1_runtime_source.py
```

The new test generates real baseline and reordered
LogicalChip golden records, verifies all 15 expected
checkpoints and synthetic P05R processing, and tests
deliberately corrupt DDR records, permutation mismatch,
wrong packet/counter fields, changed ingress despite
recomputed checksums and FPGA source/ELF identity guards.
Host synthetic mailboxes are **not** physical evidence.

## Offline prepare — NEVER touches the board

```bash
export P05_2_ORDER="/tmp/v3_p05_2_order_$(date -u +%Y%m%dT%H%M%SZ)"

set -o pipefail
bash scripts/run_p05_2_order.sh prepare "$P05_2_ORDER" \
  2>&1 | tee /tmp/v3_p05_2_order_prepare.log

cat "$P05_2_ORDER/p05_2_order_gate.json"
cat "$P05_2_ORDER/p05_artifacts/p05_manifest.json"
```

Check `permuted_service_order=[2,0,1]`,
`expected_dispatches=15`, `expected_packets=12`,
`expected_resident_deliveries=12`,
`expected_checkpoints=15`,
`expected_final_page_outs=3` and
`expected_hw_page_commands=6`.
If the independent model fails the byte-exact
order-invariance comparison, **stop before hardware**;
investigate the semantics rather than weakening the oracle.

## Physical KV260 verification — only after native PASS

There is **no new FPGA/Vitis build**. Reuse the existing
accepted P05 ELF and FPD128 XSA/bitstream. Restore
the environment variables if starting a new terminal:

```bash
export P03_DIAG_REPORTS="$(ls -dt "$PWD"/vivado/build/p03_2c_fpd128_route_*/reports | head -1)"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"

# Only if previously successful Vitis build location was lost:
# export P05_1_BUILD_DIR="<existing successful P05 A53 build dir>"
ls -lh "$P05_1_BUILD_DIR/vitis_workspace/p05_regression_run.elf"
```

**Reboot the KV260 first**, let boot firmware
initialize physical DDR, confirm JTAG/hw_server access.
The physical test **halts Linux** and overwrites reserved
DDR `0x40000000..0x43FFFFFF`; do not use the range if it
holds another active process's or OS data. It provisions
the five-step three-core network once, runs one autonomous
A53 executable, passively polls the P05R terminal and
dumps complete final DDR; the PC does **not** select
individual dispatches, page slots or packet routes.

```bash
export P05_2_CONFIRM_KV260_DDR_OVERWRITE=YES
set -o pipefail
bash scripts/run_p05_2_order.sh physical "$P05_2_ORDER" \
  2>&1 | tee /tmp/v3_p05_2_order_physical.log

cat "$P05_2_ORDER/verify.log"
```

Expected markers **only if** the real KV260 passed:

```text
PASS: P05.2c permuted service-order physical golden order=2,0,1 timesteps=5 dispatches=15 packets=12 resident_deliveries=12 barriers=5 events=15 checkpoints=15
PASS: P05.2c three full 512KiB DDR records byte-exact to BOTH independently reordered and baseline Python models and previously accepted original-order KV260 physical SHA256s
P05_2_ORDER_VERIFY_EXIT=0
PASS: P05.2c SERVICE-ORDER 2,0,1 invariance physical gate
```

**Reboot the KV260 afterward even on failure, and do not
resume halted Linux.** Preserve entire evidence folder
if verification fails.

This covers **one legal service-order permutation with no
paging replacement**, not exhaustive scheduling
invariance for arbitrary virtualized topologies.
Pending P05.2: arithmetic boundary/decay, multi-destination
fanout, saturation/backpressure, pathological paging/
barriers, AXI/PS/PL counter-provenance and any additional
physical observations needed to support the claim.
P05.2 remains IN PROGRESS and branch remains unmerged.
