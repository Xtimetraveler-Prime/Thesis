# M08.5 — first SSH-only KV260 Linux PS/PL/DMA inventory (owner-PC runbook)

**Status:** M08.5 source-only read-only capture PREPARED; **NO live board observation yet from this increment**. Existing M08.4 original owner evidence is physically accepted and immutable; draft PR #95 stays open and unmerged. The inventory supplies environmental facts for a future driver/HDL review, **not** a green light for DDR reads/writes, hardware programming, PS register access, DMA allocation or memory release.

## Why and what it captures

Current M08.5 has source-simulated signed16 recurrent LIF on seven 256-byte backing slots with one real 64×32-bit neural bank, AXI4 16-beat page transfer, kernel-lease arithmetic, and a synthetic trusted CSR/drain protocol. Before connecting PS HPM0 AXI-Lite and PL AXI128 → PS HP0 to Linux DDR, we need the **actual booted Linux platform facts**. Inherited M08.3 and D3.2 evidence still classifies DMA owner and PS HPM0/AFI/HP0 boot provenance as **UNKNOWN/BLOCKED**, not verified.

New first-party files:
- `scripts/m08_m085_ssh_linux_probe.sh`: executes as a streamed `bash -s` on a normally booted KV260 **over SSH**. Reads bounded: board model, /proc kernel/boot metadata, OS release, FPGA manager state, applied device-tree symbol/property metadata, overlay names, DMA heap/platform-device/IOMMU-group names, candidate device driver/IOMMU symlink metadata, `dma_mask_bits` if readable, hardware sensor text. Does not write remotely. **It does not inspect a real `dma_addr_t`, retrieve a full live DTB, read arbitrary PS MMIO, prove kernel binding to a future accelerator or authenticate XSA/firmware.**
- `scripts/run_m08_m085_ssh_readonly_pc.sh`: owner PC-only launcher, exact historical target `ubuntu@10.42.0.135`, SSH strict known host-key verification, at most one password prompt or available key, bounded timeout. Streams the reviewed probe as stdin. Creates a **new PC evidence folder only**, copies exact probe source, original stdout/stderr, exit and context, writes a SHA-256 ledger. Stops on wrong board model, nonzero SSH exit or missing completion markers, preserving failed original logs. It does NOT create files on the KV260 and will refuse a different target; do not silently change the target if network or board identity differs.
- `tests/test_m08_m085_ssh_readonly.py`: local source parsing, no-MMIO policy, genuine shell syntax and **MOCK-SSH** positive/negative capture/receipt/target failure tests. None of those tests communicate with the board.

A system service status, platform device path, DMA-heap directory, DT compatible string or optional `dma_mask_bits` value is metadata, **not** proof that a Linux driver allocated and owns the device-visible PL DMA buffer. The future verified device mask, IOMMU/dma-ranges, actual `dma_addr_t`, SMMU and XMPU mapping, clock and HPM0 AFI width, real AXI physical drain/isolation, driver lifetime, and protected PS→PL CSR path remain separate engineering gates.

## Owner PC VS Code commands (SSH ONLY for KV260)

Run the following **on the development PC**, not in an on-board console. The PC must already reach the KV260 by SSH on the reviewed Ethernet path. The historical hostname/IP may have changed; stop and review rather than connecting to an unexpected board. SSH host keys are **not** accepted automatically. If unknown/changed, establish trusted host identity out of band; do not bypass `StrictHostKeyChecking=yes`.

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-matched-experiments
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-matched-experiments
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
command -v ssh && command -v timeout && command -v sha256sum
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_m085_ssh_readonly.py' -v
bash -n scripts/m08_m085_ssh_linux_probe.sh
bash -n scripts/run_m08_m085_ssh_readonly_pc.sh

# Existing parent only; never clean or overwrite historical receipts.
mkdir -p "$HOME/Thesis_Evidence/M08"
bash scripts/run_m08_m085_ssh_readonly_pc.sh ubuntu@10.42.0.135
```

The launcher prints `M08_5_SSH_READONLY_EVIDENCE_DIR=<NEW_PC_FOLDER>`. Copy the exact output folder path into `D` below. No board-local checkout, Python, or evidence directory is required for this streamed shell probe.

```bash
# Replace this placeholder with the exact new path printed by the launcher:
D="$HOME/Thesis_Evidence/M08/m08_m085_ssh_readonly_<PRINTED_UNIQUE_SUFFIX>"
( cd "$D" && sha256sum -c 99_evidence_sha256.txt )
sed -n '1,240p' "$D/02_original_stdout.log"
cat "$D/03_original_stderr.log"
cat "$D/04_ssh_exit_status.txt"
```

If SSH fails, preserve and report the **new** folder path and original stderr; do not erase/overwrite, accept a different host key automatically, retry physical hardware operations, or interpret a failed SSH capture as an absent DMA capability. If you need credentials, SSH may prompt once. Do not paste passwords into this chat. Redact sensitive machine/network details before sharing output if needed.

## What we review from the original logs before expanding scope

1. **Identity/boot**: KV260 model, kernel, release, boot cmdline, PS PL clock/fan hints, FPGA-manager/active overlay state, applied DT symbols.
2. **Kernel and candidate device**: full but bounded platform-device inventory, actual named bindings/compatible and IOMMU-group hints; absence of binding means **UNKNOWN/not yet implemented**, not that DDR is impossible.
3. **Memory address translation**: observed `dma-ranges`, `iommus`, candidate mask names, but **no DMA handle exists yet**. Identify what live DT/firmware/XSA originals would be needed to establish 49-bit master aperture and consistent software mapping.
4. **Control and safety**: potential HPM0/HP0/AFI width mismatch, clock/reset and interrupt paths, late-response drain/protected MMIO not confirmed by this probe. Need separate implementation and tests.
5. **Physical release**: only after reviewed device/DT/driver, source-pinned offline new Vivado route/DRC/timing/resource, true DMA allocation/guard/drain ownership, source-identical signed16 full oracle, and separately owner-armed new one-shot experiment with independent new evidence. No M08.4 evidence mutation.

**Next action after capture:** present the original PC evidence (or its relevant bounded sections and folder hash) for a concrete per-item `OBSERVED / UNKNOWN / BLOCKED` review. A next expanded read-only inspection must itself be reviewed before execution. Nothing in this runbook authorizes a memory buffer allocation, kernel module binding, board programming or access to DDR.
