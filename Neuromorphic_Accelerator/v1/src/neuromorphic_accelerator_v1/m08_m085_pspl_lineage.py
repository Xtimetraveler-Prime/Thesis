"""M08.5 read-only review of *actual first-party* Loihi v3 PS/PL DDR route.

This is a source/topology audit, not access to a live K26 or the owner's
original physical logs. Prior v3 P02.4b physically moved pages to DDR under
a debug-halted/disposable PS execution boundary; that does NOT grant current
M08 signed16 PL/PS memory ownership. Never reuse v3's 0x40000000 base.
"""
from __future__ import annotations

from hashlib import sha256

SCHEMA = "m08-5-twin-pspl-reuse-source-only-v1"
PRIOR = (
    "Loihi_Digital_Twin/v3/vivado/create_p02_ddr_impl_project.tcl",
    "Loihi_Digital_Twin/v3/vivado/create_p03_mmio_impl_project.tcl",
    "Loihi_Digital_Twin/v3/rtl/p02_ddr_backing_range_guard.v",
    "Loihi_Digital_Twin/v3/rtl/p02_axi128_burst_adapter.v",
    "Loihi_Digital_Twin/v3/docs/P02_4B_ACCEPTANCE.md",
    "Loihi_Digital_Twin/v3/docs/P03_2C_MMIO_ROOT_CAUSE_AND_FIX.md",
    "Loihi_Digital_Twin/v3/docs/P08_B4_5_4_1_OPERATOR_STATIC_DDR_GAP_ACCEPTANCE_2026_11_05.md",
    "Neuromorphic_Accelerator/v1/scripts/m08_paged_m06_lif_build.tcl",
)
# Required semantic connections, not just presence of "DDR" in a comment.
P02_CHECKS = (
    "CONFIG.PSU__USE__S_AXI_GP2 {1}",
    "CONFIG.PSU__SAXIGP2__DATA_WIDTH {128}",
    "p02_context_page_bank_walker_0/ddr_req p02_ddr_backing_range_guard_0/req",
    "p02_ddr_backing_range_guard_0/downstream_req p02_axi128_burst_adapter_0/req",
    "p02_axi128_burst_adapter_0/M_AXI",
    "p02_hp0_smartconnect_0/S00_AXI",
    "p02_hp0_smartconnect_0/M00_AXI",
    "zynq_ultra_ps_e_0/S_AXI_HP0_FPD",
    "SAXIGP2/HP0_DDR_LOW",
    "assign_bd_address -offset 0x00000000 -range 0x80000000",
)
P03_CHECKS = (
    "CONFIG.PSU__USE__M_AXI_GP0 {1}",
    "CONFIG.PSU__MAXIGP0__DATA_WIDTH $p03_ps_hpm0_width",
    "CONFIG.PSU__SAXIGP2__DATA_WIDTH {128}",
    "p03_hpm0_width_smartconnect_0",
    "p03_ps_control_regs",
    "p02_axi128_burst_adapter_0/M_AXI",
    "zynq_ultra_ps_e_0/S_AXI_HP0_FPD",
)
M08_CHECKS = (
    "CONFIG.PSU__USE__M_AXI_GP0 0",
    "CONFIG.PSU__USE__M_AXI_GP1 0",
    "CONFIG.PSU__USE__M_AXI_GP2 0",
    "Forbidden PS-to-PL AXI master was enabled",
    "get_bd_intf_pins -quiet $iface",
    "jtag_axi:1.2",
    "assign_bd_address -offset 0xA0000000",
    "assign_bd_address -offset 0xA0001000",
    "physical_m06_ddr=NO",
    "kernel_owned_dma_buffer=NO",
)


class LineageError(ValueError):
    pass


def audit_sources(sources: dict[str, str]) -> dict:
    """Accept exact source-tree paths, never device paths or arbitrary files."""
    if type(sources) is not dict or set(sources) != set(PRIOR):
        raise LineageError("missing or injected first-party lineage file")
    if any(type(v) is not str or not v.strip() for v in sources.values()):
        raise LineageError("source file missing or malformed")
    ddr, mmio, guard, adapter, physical, width, owner_gap, m08 = (
        sources[path] for path in PRIOR
    )
    for name, source, needles in (
        ("v3 P02 HP0 DDR", ddr, P02_CHECKS),
        ("v3 P03 HPM0 control", mmio, P03_CHECKS),
        ("current accepted M08 JTAG-only shell", m08, M08_CHECKS),
    ):
        for needle in needles:
            if needle not in source:
                raise LineageError(name + " connection/width/ownership drift: " + needle)
    for needle in (
        "parameter [63:0] BACKING_BASE = 64'h0000_0000_4000_0000",
        "parameter [63:0] BACKING_BYTES = 64'h0000_0000_0400_0000",
        "(request_end <= allowed_end)",
    ):
        if needle not in guard:
            raise LineageError("v3 DDR guard witness missing: " + needle)
    for needle in ("DATA_WIDTH 128", "MAX_BURST_LENGTH 16",
                   "NUM_READ_OUTSTANDING 1", "NUM_WRITE_OUTSTANDING 1"):
        if needle not in adapter:
            raise LineageError("v3 real AXI4 transport metadata drifted: " + needle)
    for needle in (
        "K26 DDR, not PC RAM", "page-ins:            60",
        "page-outs:           60", "AXI bytes moved:     32686080",
        "halt visible Cortex-A53",
    ):
        if needle not in physical:
            raise LineageError("v3 P02.4b physical acceptance boundary drift: " + needle)
    for needle in (
        "dw_ss0_sel[9:8] = 2",
        "128-bit AXI4 to 32-bit AXI4-Lite",
        "separate", "width mismatch",
    ):
        if needle not in width:
            raise LineageError("v3 boot-PS HPM0 width pathology unrecorded: " + needle)
    for needle in (
        "all_DDR_port_and_master_permissions_proven=false",
        "low_DDR_exclusive_A53_ownership_proven=false",
        "PC_STATIC_GEOMETRY_PASS_PHYSICAL_OWNER_NO_GO",
    ):
        if needle not in owner_gap:
            raise LineageError("later Twin source owner gap unrecorded: " + needle)
    if "get_bd_intf_pins ps/S_AXI_HP0_FPD" in m08 or "ps/S_AXI_HP0_FPD]" in m08:
        raise LineageError("M08 topology changed: re-review exact native XSA before classifying")
    return {
        "schema": SCHEMA,
        "status": "SOURCE_LINEAGE_PASS_M08_DDR_NOT_CONNECTED_OR_OWNED",
        "source_sha256": {path: sha256(sources[path].encode("utf-8")).hexdigest()
                          for path in PRIOR},
        "v3_p02_physically_accepted_ddr_paging_historical": True,
        "v3_p02_transport": "PL_AXI128_MASTER_SMARTCONNECT_PS_S_AXI_HP0_FPD",
        "v3_p03_control": "PS_M_AXI_HPM0_FPD_SMARTCONNECT_PL_AXIL",
        "v3_p02_physical_access_boundary": "HALT_A53_DEBUG_RESERVED_DDR_NOT_LIVE_LINUX",
        "v3_512k_context_format_reusable_for_m08": False,
        "v3_0x40000000_window_reusable_for_m08": False,
        "v3_prior_bitstream_reusable_for_m08": False,
        "boot_time_HPM0_width_must_be_verified_again": True,
        "m08_current_accepted_transport": "JTAG_AXI_TO_PL_BRAM_AND_256B_NEURAL_BANK",
        "m08_ps_pl_hp0_axi_path_connected": False,
        "m08_kernel_dma_buffer_owned": False,
        "owner_real_ddr_ready": False,
        "m08_page_bytes": 256,
        "m08_logic_page_count": 6,
        "m08_resident_page_count": 1,
        "physical_ddr_transactions_measured_for_m08": None,
        "permitted_next_action": "OFFLINE_RTL_AND_OWNER_READONLY_MEMORY_ROUTE_AUDIT",
        "new_bitstream_or_board_action_authorized": False,
    }
