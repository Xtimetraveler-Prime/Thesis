# M06 G3 real original AMD IP: owner XCI lookup failure and corrected rerun

**2026-11-09 America/Denver. M06 OPEN. PR #80 DRAFT/UNMERGED.** No physical FPGA, JTAG, bitstream, PS/Linux DDR or original D3 project edits.

## Genuine owner Vivado 2025.2 FAILURE: preserve original evidence

Owner ran the original new scratch-only vendor AXI data-width converter generator at commit 15e6aad81185adfb598e8dd569ad1d5123ca91b2 and received:

- Original owner evidence: /home/dna/Thesis_Evidence/m06_g3_real_amd_dwc_20261110T031107Z_linVJf
- result.txt: exit_status=1.
- Vivado genuine version 2025.2 / SW build 6299465.
- Real original AMD IP catalog repository loaded /home/dna/Vivado/2025.2/data/ip.
- IP 'm06_g3_read_dwc' successfully created, real CONFIG fields accepted/read back.
- FIRST failure: 'AMD genuine IP XCI file list is missing: m06_g3_read_dwc' from *our own* Tcl check: 'get_files -quiet -of_objects $ip' returned an empty list. This is NOT a measured AXI-converter functional error, a statement that no .xci exists on disk, or a failure of HLS/SmartConnect integrated RTL.

Do NOT overwrite or delete the failed evidence. No need to upload old run logs unless the *new* run exposes an unexpected difference.

## Root issue and scoped correction

The original Tcl code incorrectly assumed the Vivado IP object returned by 'get_ips' always enumerates its *own XCI customization* through 'get_files -of_objects $ip'. AMD's UG896 documents querying IP customization FILE objects and the ordinary fresh-project .srcs/sources_1/ip/<name>/<name>.xci layout. Existing source-identity, Vivado version, target part, exact two IP roles and parameter readback gates remain unchanged.

New pure Tcl helper 'scripts/m06_g3_xci_path.tcl':
- Requires only the two expected scratch IP instance names (m06_g3_read_dwc / m06_g3_write_dwc).
- Resolves the exact file path under the newly created project at:
  <evidence>/new_scratch_project/m06_g3_amd_dwc.srcs/sources_1/ip/<name>/<name>.xci.
- Requires a real nonempty XCI file. Never recursively searches prior/original AMD D3 sources.
- Fails closed if missing/renamed/empty. Does not spoof/create IP.
- Allows fully synthetic Tcl negative tests using tclsh without Vivado.

Corrected 'scripts/m06_g3_generate_amd_dwc.tcl' sources that pure Tcl helper, verifies the genuine XCI file on disk and records '<ip>.xci_source_path' into 02_amd_dwc_configuration.tsv, then attempts 'generate_target all $ip' and 'export_ip_user_files' with the real AMD IP object. We DO NOT claim that latter step passes until owner rerun.

'scripts/run_m06_g3_amd_dwc_ip.sh' additionally hashes the new helper before/after the vendor run; 'scripts/m06_g3_amd_dwc_evidence_audit.py' requires exactly these three generator source digests, exact XCI path readback, and both generated .xci digests after final exit0. Existing synthetic test fixture adopts real project .srcs path and adds fail-closed tests for incorrect/original-D3 XCI substitution plus true pure-Tcl path resolution and negative cases. No original vendor RTL or accepted neural source modified.

## Exact owner next verification and evidence commands

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git rev-parse HEAD
    cd Neuromorphic_Accelerator/v1
    python3 -m compileall -q src scripts tests
    bash -n scripts/run_m06_g3_amd_dwc_ip.sh
    python3 -m unittest discover -s tests -p 'test_m06_g3_amd_dwc_evidence_audit.py' -v
    python3 -m unittest discover -s tests -p 'test_m06*.py' -v
    source "$HOME/Vivado/2025.2/Vivado/settings64.sh"
    vivado -version
    bash scripts/run_m06_g3_amd_dwc_ip.sh
    echo "M06 G3 corrected DWC generation exit: $?"

Runner ALWAYS creates a fresh directory under ~/Thesis_Evidence/m06_g3_real_amd_dwc_*. On exit_status=0, run independent auditor on newest folder, output new m06_g3_amd_dwc_audit_*.json OUTSIDE original evidence. On any failure retain original new folder with status1 and first vendor/our diagnostic; no silent rerun.

**Exact upload (one ZIP)**: same eight named items in updated runbook 'docs/M06_G3_REAL_AMD_WIDTH_IP_OWNER_RUNBOOK_2026_11_09.md': $DW/{result.txt,commit.txt,vivado_version.txt,01_vivado_amd_dwc.log,02_amd_dwc_configuration.tsv,03_real_amd_dwc_xci_paths.txt,04_real_amd_dwc_xci_sha256.txt}, plus latest independent m06_g3_amd_dwc_audit_*.json if exit0. The user-facing terminal command packs these automatically into ~/Thesis_Evidence/M06_G3_AMD_DWC_IP_REVIEW.zip, marking missing files explicitly on failure. Do not upload proprietary IP source or repeat earlier G1/G2 runs.

## Subsequent G3/G4 remain open

Owner genuine successful creation of two AMD 32→256 IP does not prove connection. Need original AMD SmartConnect S00/S03, corrected generated-HLS RTL, guarded 64→32 address bridge, ID/USER/LOCK mapping, common 64KiB scratch, real XSim B→AR coherency, full independent M02/M03 neural trace/state and fault/timeout/poison before M06 closeout. No M06 merge or M07 without authorization.
