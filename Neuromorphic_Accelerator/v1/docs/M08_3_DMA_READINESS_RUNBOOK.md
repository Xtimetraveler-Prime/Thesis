# M08.3.1 — Linux DMA ownership readiness: read-only evidence before physical DDR

**Status 2026-11-11:** Implementation begun; **SOURCE-ONLY and BOARD-LOCAL READ-ONLY OBSERVATIONS**, NOT DDR ownership, M08.3 completion or DMA execution. [M08.2 accepted limited offline PS→PL identity BD](M08_2_IDENTITY_BD_SCOPED_ACCEPTANCE_2026_11_11.md) is a prerequisite, **not** a replacement for a real kernel driver.

## Research boundary

The standalone M08.2 identity slave is a **PL AXI-Lite slave** reached from the PS FPD HPM0 *master*. It has **no PL DMA master**; its 4 KiB `0xa0000000` address is a **Vivado candidate** only. It is not a kernel-owned DMA address or proof of Linux access.

The future signed16 M06 canonical page engine requires a new verified PS↔PL memory service architecture, a real Linux-bound device capable of DMA, validated mask/IOMMU/cache coherency and kernel-owned buffer lifecycle. Presence of `/sys/class/dma_heap/system`, a Linux device node, or an `axi_dma*`-named platform device does not establish *any* of those requirements. Never infer a physical/bus address from an application-supplied integer, or use `/dev/mem` for bare-buffer writes.

**Gate prerequisites** (must be evidenced independently before an actual DMA allocation):
1. Exact booted Linux kernel, DTB/PS-PL address mapping, PL bitstream/XSA with relevant physically connected **master** or the alternative verified PS-paged service interface. No full system is connected yet.
2. Real Linux *device binding* to the particular PL AXI master/data mover (or PS-managed alternative) with ownership and reset semantics. A folder or driver filename is not sufficient.
3. The device's real `dma_mask` / coherent mask and address-width compatibility; DMA addresses may differ from CPU physical addresses, especially through IOMMU/SMMU or bus aliases.
4. Kernel DMA API allocation or a bound DMA-BUF attachment+mapping, lifetime tracking, coherency/CPU-sync rules and IOMMU ownership; no address guessed by user space.
5. Stop/quiesce/reset and outstanding transaction drainage before release, with M06 G4 poison quarantine and explicit state reinitialization before a subsequent run.
6. Genuine original hardware traces for AXI completion/order, memory writes, cache ownership and neural oracle parity. M07 service models and HLS offline simulations are **not** physical DDR proof.

## Source artifact: safe board-local introspection only

`src/neuromorphic_accelerator_v1/m08_dma_readiness.py` and `scripts/m08_3_dma_readonly.py` use only allowlisted **reads** from `/proc/device-tree/model`, `/proc/version`, `/etc/os-release`, and directory **name listings** of `/sys/class/dma_heap`, `/sys/class/fpga_manager`, `/sys/bus/platform/devices` and `/sys/kernel/iommu_groups`. No arbitrary filename selection, command execution, root privileges, sysfs writes, /dev/mem, mmap, ioctl, allocator, PL programming, or network access. Files have 4 KiB bounds, directory listings 128 entries, refuse symlinked component paths, and redact no values silently: `UNREADABLE`, `TOO_LARGE`, `TOO_MANY_ENTRIES` or `MISSING` is recorded without pretending readiness.

The output always has `physical_dma_ready=false`, lists the seven unresolved safeguards, declares `permitted_next_action=REVIEW_READ_ONLY_EVIDENCE_ONLY` and is **not a remotely authenticated hardware attestation**. Tests use a clearly fake OS filesystem and negative mutations; they do not access a real KV260.

## A. Development PC: independent source verification

From the same M08 development branch in VS Code Linux:

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
git status --short
git branch --show-current
git fetch origin
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-kv260-bringup
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_m07*.py' -v
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s tests -p 'test_m08_dma_readiness.py' -v
~~~

These are **host/software checks only**. Confirm the exact new commit SHA and the eight M01–M08 source CI workflows before gathering additional owner evidence.

## B. Later, only on the **booted KV260 Linux shell**, with the same reviewed project checkout

This is not a command for the PC or a request to open the board remotely. Use only when the owner has confirmed a normal Linux boot and the path to the reviewed source. It does not invoke `sudo` or `xmutil unloadapp` and does not access hardware devices.

~~~bash
cd ~/Thesis/Neuromorphic_Accelerator/v1
mkdir -p "$HOME/Thesis_Evidence/M08"
D="$(mktemp -d "$HOME/Thesis_Evidence/M08/m08_3_1_dma_observation_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
# The collector requires an ABSENT output directory; remove only this
# empty directory we just created (NOT an historical evidence directory).
rmdir "$D"
python3 scripts/m08_3_dma_readonly.py --output-dir "$D"
python3 scripts/m08_3_dma_readonly.py --audit-only --output-dir "$D"
ls -lah "$D"
cat "$D/m08_3_dma_readiness.sha256"
( cd "$D" && sha256sum -c m08_3_dma_readiness.sha256 )
~~~

The temporary `rmdir` only applies to the **just-created empty path**, never historical data. If checkout path differs, change only the initial `cd`. If board-local project sources are unavailable, do not fabricate capture output or transfer scripts without owner action; a safe alternate packaging workflow can be designed later.

**The board-local capture itself is not an M08.3 DMA-ownership PASS.** It identifies questions for a later device-specific driver design. Preserve every original evidence folder and stop prior to any DDR access.

## C. Engineering handoff

After first original board-local observations, collect via owner-reviewed interfaces a **real bound device/driver relationship**, kernel `dma_mask`, memory/IOMMU map and a concrete bitstream/source SHA manifest for the *future PL master path*. Only then write an actual kernel DMA allocation/attach plan and functional experiments. M06 signed16 G4 reset-and-quarantine must remain intact. No performance claims from file presence or OS inventory alone.
