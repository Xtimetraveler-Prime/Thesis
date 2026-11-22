"""Genuine host C tests and source policy for source-only kernel DMA preflight.

This does NOT compile the module against the owner's real 6.8 kernel,
load/install drivers, allocate physical DMA or run Vivado/hardware.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
HEADER=ROOT/"kernel/m08_m085_dma_contract.h"
DRIVER=ROOT/"kernel/m08_m085_dma_preflight.c"
FIXTURE=ROOT/"tests/cases/m08_m085_dma_contract_host.c"
PASS="M08_M085_PORTABLE_C_DMA_49BIT_HP0LOW_7SLOT_BOUNDARY_PASS checks=57"


class M085DMAPreflightSourceTests(unittest.TestCase):
    def test_kernel_candidate_keeps_hardware_all_grant_paths_disabled(self):
        s=DRIVER.read_text()
        for required in (
            "devm_platform_ioremap_resource(pdev, 0)",
            "dma_set_mask_and_coherent(dev, DMA_BIT_MASK(49))",
            "dma_alloc_coherent(dev, state->bytes,",
            "dma_free_coherent(s->dma_dev, s->bytes, s->cpu_virt,",
            "state->never_shared_with_pl = true;",
            "if (WARN_ON_ONCE(!s->never_shared_with_pl))",
            "m085_dma_candidate_hp0_low_valid((u64)state->dma_handle,",
            "platform_get_resource(pdev, IORESOURCE_MEM, 0)",
            "resource_size(res) != M085_CSR_MIN_BYTES",
            "cap != M085_CAP_MAGIC || version != M085_ABI_V11",
            'compatible = "thesis,m08-m085-preflight-quarantined"',
            "module_platform_driver(m085_driver)",
            "M085_ABI_V11       0x00010001U",
            "M085_CAP_MAGIC     0x4d303835U",
            "return -ENODEV;",
        ):
            self.assertIn(required,s)
        for unsafe_call in (
            "writel(", "writeq(", "writeb(", "ioread32_rep(",
            "dma_map_single(", "dma_sync_single_for_device(",
            "virt_to_phys(", "remap_pfn_range(", "debugfs_create_file(",
            "misc_register(", "request_irq(", "request_firmware(",
            "platform_device_register(", "of_platform_populate(",
        ):
            self.assertNotIn(unsafe_call,s)
        self.assertNotIn("0x40000000",s)
        self.assertNotIn("dma-coherent",s)
        self.assertNotIn("devm_kfree(",s)

    def test_portable_guard_rejects_49bit_boundary_and_epoch_6(self):
        h=HEADER.read_text()
        for required in (
            "#define M085_DMA_AXI_LIMIT (1ULL << 49)",
            "#define M085_DMA_PAGE_BYTES 256ULL",
            "#define M085_DMA_SLOT_COUNT 7ULL",
            "generation > M085_DMA_ALLOC_FIELD_MAX",
            "allocation_bytes < M085_DMA_USED_BYTES",
            "allocation_bytes > M085_DMA_ALLOC_FIELD_MAX",
            "dma_base & (M085_DMA_PAGE_BYTES - 1ULL)",
            "allocation_bytes >= M085_DMA_AXI_LIMIT - dma_base",
            "slot != 6ULL || tick == 0ULL",
            "#define M085_CANDIDATE_HP0_LOW_EXCLUSIVE 0x80000000ULL",
            "m085_dma_candidate_hp0_low_valid",
            "allocation_bytes <= M085_CANDIDATE_HP0_LOW_EXCLUSIVE - dma_base",
        ):
            self.assertIn(required,h)
        self.assertNotIn("0x40000000",h)
        self.assertEqual(FIXTURE.read_text().count("check_descriptor("),18)
        self.assertEqual(FIXTURE.read_text().count("check_hp0_route("),9)

    def _compile(self,source: Path, output: Path):
        compiler=shutil.which("cc") or shutil.which("gcc")
        if compiler is None:
            self.skipTest("real host C compiler unavailable; no mock result")
        p=subprocess.run(
            [compiler,"-std=c11","-Wall","-Wextra","-Werror","-pedantic",
             "-O2",str(source),"-o",str(output)],
            capture_output=True,text=True,timeout=45
        )
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)

    def test_real_compiled_portable_contract_49_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/"dma_contract"
            self._compile(FIXTURE,exe)
            p=subprocess.run([str(exe)],capture_output=True,text=True,timeout=15)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertEqual(p.stdout.strip(),PASS)

    def test_mutated_strict_upper_bound_is_caught_by_real_compiled_test(self):
        original=HEADER.read_text()
        strict="allocation_bytes >= M085_DMA_AXI_LIMIT - dma_base"
        self.assertIn(strict,original)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"kernel").mkdir()
            (root/"tests/cases").mkdir(parents=True)
            (root/"kernel/m08_m085_dma_contract.h").write_text(
                original.replace(strict,"allocation_bytes > M085_DMA_AXI_LIMIT - dma_base")
            )
            copied=root/"tests/cases/m08_m085_dma_contract_host.c"
            copied.write_text(FIXTURE.read_text())
            exe=root/"mutated_contract"
            self._compile(copied,exe)
            p=subprocess.run([str(exe)],capture_output=True,text=True,timeout=15)
            self.assertNotEqual(p.returncode,0)
            self.assertIn("BAD_DESCRIPTOR",p.stderr)


if __name__=="__main__":
    unittest.main()
