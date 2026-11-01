/* Native C11 check: no FPGA or official MNIST TEST side effects. */
#include <stdint.h>
#include <stdio.h>
#include "p07_b1_owner_map.h"
#define CHECK(x) do { if (!(x)) { \
    fprintf(stderr, "failed: %s at %d\n", #x, __LINE__); return 1; \
} } while (0)
static p07_b1_admission expected(void) {
    p07_b1_admission p={0};
    p.logical_cores=P07_B1_CORES; p.slots=P07_B1_SLOTS; p.engines=P07_B1_ENGINES;
    p.input_ticks=P07_B1_INPUT_TICKS; p.total_ticks=P07_B1_TOTAL_TICKS;
    p.ingress_routes=P07_B1_INGRESS_ROUTES; p.ingress_bytes=P07_B1_INGRESS_BYTES;
    p.current_events=1000u; p.emitted_packets=39u; p.backing_base=P03_HW_BACKING_BASE;
    p.staging_base=P07_B1_STAGING_BASE; p.descriptor_base=P07_B1_DESCRIPTOR_BASE;
    p.result_base=P07_B1_RESULT_BASE; p.shell_id=P03_MMIO_ID_VALUE;
    p.shell_caps=P07_B1_SHELL_CAPABILITIES; p.mmio_base=(uint32_t)P03_MMIO_BASE;
    p.fpd_hpm0_width_bits=128u; return p;
}
int main(void) {
    p07_b1_admission p=expected();
    uint32_t i;
    CHECK(P07_B1_SCALED_PHYSICAL_EXECUTION_GO==0u);
    CHECK(P07_B1_OFFICIAL_MNIST_TEST_UNSEAL_GO==0u);
    CHECK(P07_B1_INGRESS_ROUTES==20384u);
    CHECK(P07_B1_INGRESS_BYTES==123216u);
    CHECK((uint64_t)P07_B1_CORES*P03_HW_RECORD_BYTES==14155776u);
    CHECK(p07_b1_validate(&p)==P07_B1_OK);
    CHECK(p07_b1_validate(0)==P07_B1_BAD_ARGUMENT);
    for(i=0u;i<P07_B1_CORES;i++)
        CHECK(p07_b1_core_address(i)==P03_HW_BACKING_BASE+(uint64_t)i*0x80000u);
    CHECK(p07_b1_core_address(26u)==UINT64_C(0x40D00000));
    CHECK(p07_b1_core_address(26u)+P03_HW_RECORD_BYTES==UINT64_C(0x40D80000));
    CHECK(p07_b1_core_address(27u)==UINT64_MAX);
    CHECK(P03_HW_FULL_PAGE_BYTES/P07_B1_BURST_BYTES==1712u);
    CHECK(P03_HW_MUTABLE_BYTES/P07_B1_BURST_BYTES==416u);
    p.logical_cores=28u; CHECK(p07_b1_validate(&p)==P07_B1_BAD_TOPOLOGY); p=expected();
    p.slots=4u; CHECK(p07_b1_validate(&p)==P07_B1_BAD_TOPOLOGY); p=expected();
    p.engines=2u; CHECK(p07_b1_validate(&p)==P07_B1_BAD_TOPOLOGY); p=expected();
    p.total_ticks=25u; CHECK(p07_b1_validate(&p)==P07_B1_BAD_TOPOLOGY); p=expected();
    p.ingress_routes--; CHECK(p07_b1_validate(&p)==P07_B1_BAD_TOPOLOGY); p=expected();
    p.ingress_bytes++; CHECK(p07_b1_validate(&p)==P07_B1_BAD_TOPOLOGY); p=expected();
    p.staging_base=UINT64_C(0x40D00000); CHECK(p07_b1_validate(&p)==P07_B1_BAD_OWNER); p=expected();
    p.result_base=UINT64_C(0x43FE0000); CHECK(p07_b1_validate(&p)==P07_B1_BAD_OWNER); p=expected();
    p.backing_base++; CHECK(p07_b1_validate(&p)==P07_B1_BAD_OWNER); p=expected();
    p.shell_id=0u; CHECK(p07_b1_validate(&p)==P07_B1_BAD_SHELL); p=expected();
    p.shell_caps=0u; CHECK(p07_b1_validate(&p)==P07_B1_BAD_SHELL); p=expected();
    p.mmio_base=UINT32_C(0x80000000); CHECK(p07_b1_validate(&p)==P07_B1_BAD_SHELL); p=expected();
    p.fpd_hpm0_width_bits=32u; CHECK(p07_b1_validate(&p)==P07_B1_BAD_SHELL); p=expected();
    p.current_events=4096u; p.emitted_packets=4096u;
    CHECK(p07_b1_validate(&p)==P07_B1_OK);
    p.current_events=4097u; CHECK(p07_b1_validate(&p)==P07_B1_BAD_CAPACITY); p=expected();
    p.emitted_packets=4097u; CHECK(p07_b1_validate(&p)==P07_B1_BAD_CAPACITY);
    puts("P07_B1_NATIVE_OWNER_MAP_PASS=1"); return 0;
}
