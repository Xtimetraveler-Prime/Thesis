# P03.2c Build Attempt 1 — Vitis Platform Creation RPC Failure

**Date:** 2026-10-06  
**Phase:** P03.2c — Physical Cortex-A53 MMIO smoke  
**Result:** Fixture generation passed; Vitis failed while creating the standalone platform before the application was compiled.

## Observed result

The deterministic fixture generated successfully:

```text
PASS: P03.2c smoke fixture generated
record_sha256=e092ce8ecccb52de635b3f317b9b339e2424d621164e53ac5c0ef9ab4e995a21
config0=0x14001000
metadata=0x400040080
```

Vitis 2025.2 then started the platform flow and reported:

```text
Platform p03_2c_platform creation started.
SDT generated successfully.
```

but `client.create_platform_component(...)` terminated with:

```text
StatusCode.UNKNOWN
Application error processing RPC
```

No application compilation occurred.

## Interpretation

The accepted fixed XSA was readable enough for Vitis to generate the System
Device Tree, so this attempt does not implicate:

- the P03.2b fixed-XSA hash;
- the A53 smoke C source;
- the application import/build step;
- the physical MMIO shell.

The failure is in standalone platform/domain creation after SDT generation.

## Corrections

Two changes were made before retry.

### 1. Suppress unused boot components

The smoke application is downloaded by XSDB onto an already initialized
ZynqMP. It does not consume a Vitis-generated FSBL/PMUFW boot image.

Platform creation now uses:

```python
client.create_platform_component(
    name="p03_2c_platform",
    hw_design=xsa,
    os="standalone",
    cpu="psu_cortexa53_0",
    domain_name="standalone_psu_cortexa53_0",
    no_boot_bsp=True,
)
```

rather than requesting extra architecture/compiler/generate-DTB options.

AMD's embedded scripting flow documents `no_boot_bsp=True` for Zynq
UltraScale+ designs when automatic boot artifacts are not required.

### 2. Require the A53 embedded toolchain

P03.2c now explicitly initializes the Vitis embedded environment and requires:

```text
aarch64-none-elf-gcc
```

before invoking the Python Vitis API.

AMD documents this compiler as the GNU compiler for Cortex-A53/A72 standalone
software.

The build gate prints:

```text
P03_2C_XILINX_VITIS=...
P03_2C_A53_GCC=...
```

so environment problems are visible immediately.

### 3. Preserve Vitis diagnostics

If platform creation still fails, the Python build script now reports the
workspace, partial platform files, discovered Vitis logs, and log tails before
exiting.

## Acceptance impact

P03.2c remains open.

No RTL, routed bitstream, P03.2b artifact, MMIO register contract, or physical
test semantics changed.
