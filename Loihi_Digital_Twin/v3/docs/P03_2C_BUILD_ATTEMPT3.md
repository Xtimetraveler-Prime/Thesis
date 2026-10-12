# P03.2c Build Attempt 3 — Embedded Empty-Template Failure

**Date:** 2026-10-08  
**Phase:** P03.2c — Physical Cortex-A53 MMIO smoke  
**Result:** Platform/domain/BSP complete; application creation failed before source compilation because the embedded Vitis server rejected the generic `empty` template.

## Evidence

The corrected environment found and used the standalone A53 compiler:

```text
P03_2C_A53_GCC=/home/dna/Vivado/2025.2/Vitis/gnu/aarch64/lin/aarch64-none/bin/aarch64-none-elf-gcc
aarch64-xilinx-elf-gcc.real (GCC) 13.3.0
```

Vitis then successfully created the platform and standalone domain:

```text
SDT generated successfully.
Successfully created Domain ...
Domain standalone_psu_cortexa53_0 added successfully.
Platform creation finished successfully.
```

The BSP completed all 161 build steps and produced:

```text
libxil.a
libxilstandalone.a
libxiltimer.a
```

followed by:

```text
Platform Build Finished successfully.
```

The failure then occurred only at application-component creation:

```text
Invalid Template 'empty' selected for Domain 'standalone_psu_cortexa53_0'.
[ERROR]: Couldnt find the src directory for empty
```

## Interpretation

The toolchain, fixed XSA, standalone platform, domain, and BSP are now proven
usable.

No P03.2c application source was compiled in this attempt.

AMD's embedded Vitis examples use the `hello_world` application template for
standalone domains. The generic application documentation also supports
importing arbitrary user source files into an application component.

## Correction

P03.2c now creates the application component with:

```python
template="hello_world"
```

only as a Vitis-recognized scaffold.

Immediately after creation, the build script:

1. preserves non-source component/build metadata, including the linker script;
2. removes generated C/C++/header example files from the component `src`
   directory;
3. imports only:
   - `p03_2c_smoke.c`
   - `p03_mmio.h`
   - `p03_2c_fixture.h`
4. asserts that exactly one C/C++ source remains:
   `p03_2c_smoke.c`;
5. builds the application.

The smoke application's semantics and the accepted P03.2b hardware artifacts
are unchanged.
