# P03.2c Build Attempt 2 — A53 Compiler Not Exported on PATH

**Date:** 2026-10-07  
**Phase:** P03.2c — Physical Cortex-A53 MMIO smoke  
**Result:** Vitis launcher present; `aarch64-none-elf-gcc` absent from shell PATH.

## Observed environment

After sourcing:

```text
/home/dna/Vivado/2025.2/Vitis/settings64.sh
```

the shell reported:

```text
XILINX_VITIS=/home/dna/Vivado/2025.2/Vitis
/home/dna/Vivado/2025.2/Vitis/bin/vitis
aarch64-none-elf-gcc: command not found
```

## Interpretation

This only proves the A53 standalone compiler was not exported on `PATH`.
It does not by itself prove the compiler is absent from the Vitis installation.

AMD documents the Cortex-A53/A72 standalone compiler as:

```text
aarch64-none-elf-gcc
```

and the processor-specific GNU tools live under the Vitis
`gnu/aarch64` installation tree.

## Correction

The P03.2c build gate now:

1. sources the Vitis environment;
2. checks the shell PATH;
3. checks known bundled locations including
   `$XILINX_VITIS/gnu/aarch64/lin/aarch64-none/bin`;
4. searches `$XILINX_VITIS/gnu/aarch64` for an executable
   `aarch64-none-elf-gcc` as a fallback;
5. prepends the discovered compiler directory to PATH;
6. reports an incomplete embedded Arm GNU toolchain installation only if no
   compiler can be found.

No hardware, MMIO, XSA, fixture, or smoke application semantics changed.
