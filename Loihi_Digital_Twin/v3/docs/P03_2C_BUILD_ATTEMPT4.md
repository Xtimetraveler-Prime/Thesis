# P03.2c Build Attempt 4 — Hello-World UART Validation Failure

**Date:** 2026-10-08  
**Phase:** P03.2c — Physical Cortex-A53 MMIO smoke  
**Result:** Standalone platform/BSP successful; `hello_world` application template rejected because the hardware platform exposes no serial instance.

## Evidence

The build used the installed A53 standalone compiler:

```text
P03_2C_A53_GCC=/home/dna/Vivado/2025.2/Vitis/gnu/aarch64/lin/aarch64-none/bin/aarch64-none-elf-gcc
```

The standalone A53 domain and platform completed successfully:

```text
Domain standalone_psu_cortexa53_0 added successfully.
Platform creation finished successfully.
Platform Build Finished successfully.
```

Application creation then failed with:

```text
Invalid Template 'hello_world' selected for Domain 'standalone_psu_cortexa53_0'.
hello_world requires at least one serial hardware instance to be present
```

## Interpretation

This is a template validation failure, not a compiler, BSP, XSA, linker, or
P03.2 hardware failure.

The P03.2 hardware shell does not need a UART for the smoke because physical
acceptance is communicated through a DDR mailbox.

## Correct embedded template

AMD/Xilinx's embedded Vitis scripting flow lists:

```text
empty_application
```

as the valid embedded empty-application template.

The underlying embedded-software application generator also explicitly
supports `empty_application` as a C/C++ template.

This differs from the generic accelerated-application API example, which uses
the shorter template name `empty`.

## Correction

P03.2c now:

1. queries `client.get_templates(type="EMBD_APP")`;
2. requires `empty_application` to be present;
3. creates the standalone component with
   `template="empty_application"`;
4. imports only:
   - `p03_2c_smoke.c`
   - `p03_mmio.h`
   - `p03_2c_fixture.h`;
5. asserts that `p03_2c_smoke.c` is the only C/C++ application source;
6. builds the application.

No UART is required by the P03.2c acceptance protocol.

## Acceptance impact

P03.2c remains open until:

- the standalone ELF builds;
- its LOAD segments avoid the reserved DDR backing window;
- the physical A53 MMIO smoke runs;
- the DDR mailbox verifies PASS.
