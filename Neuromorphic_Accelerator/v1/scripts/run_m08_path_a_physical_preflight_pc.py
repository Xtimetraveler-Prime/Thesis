#!/usr/bin/env python3
"""M08.2b PC-side READ-ONLY SSH deployment preflight, original SHA evidence.

This is intentionally NOT a deployment runner. Does not install firmware,
unload/load an app, manipulate a fan, open /dev/uio, or access registers.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

BIT_SHA = 'a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b'
DTBO_SHA = '2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed'
STEM = 'm08-v1-fan-page-uio-review'
EXPECTED_WINDOWS = {
    'm08-identity': {'base': '0xa0000000', 'bytes': 4096},
    'm08-page': {'base': '0xa0001000', 'bytes': 4096},
}
TARGET = 'ubuntu@10.42.0.135'

class PreflightRejected(RuntimeError):
    pass


def require(condition: bool, why: str) -> None:
    if not condition:
        raise PreflightRejected(why)


def digest(p: Path) -> str:
    h = sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verify_ledger(directory: Path, filename: str) -> dict[str, str]:
    require(directory.is_dir() and not directory.is_symlink(), 'missing or symlinked evidence directory')
    ledger = directory / filename
    require(ledger.is_file() and not ledger.is_symlink(), 'missing or symlinked evidence ledger')
    entries = {}
    for row in ledger.read_text().splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_./-]+)', row)
        require(match is not None, 'invalid SHA ledger row')
        expected, name = match.groups()
        rel = Path(name)
        require(not rel.is_absolute() and '..' not in rel.parts and name not in entries,
                'unsafe or duplicate SHA ledger path')
        item = directory / rel
        require(item.is_file() and not item.is_symlink() and digest(item) == expected,
                'evidence SHA mismatch: ' + name)
        entries[name] = expected
    return entries


def validate_candidate(candidate: Path) -> dict:
    require(candidate.name.startswith('m08_2b_path_a_uio_overlay_REVIEW_ONLY_'),
            'requires corrected candidate, not original first-stage package')
    rows = verify_ledger(candidate, '99_evidence_sha256.txt')
    bit_name = f'{STEM}/{STEM}.bit.bin'
    dtbo_name = f'{STEM}/{STEM}.dtbo'
    for name in (bit_name, dtbo_name, f'{STEM}/shell.json',
                 '01_dtc_compile.log', '02_dtbo_decompiled.log',
                 '03_review.json', '98_status.txt'):
        require(name in rows, 'missing corrected original candidate SHA row: ' + name)
    require(rows[bit_name] == BIT_SHA and rows[dtbo_name] == DTBO_SHA,
            'corrected binary SHA differs from accepted owner original')
    review = json.loads((candidate / '03_review.json').read_text())
    require(review.get('status') == 'OFFLINE_DUAL_UIO_CANDIDATE_NOT_INSTALLED' and
            review.get('bit_bin_sha256') == BIT_SHA and review.get('dtbo_sha256') == DTBO_SHA and
            review.get('identity_and_page') == EXPECTED_WINDOWS and
            review.get('dtc_diagnostics', {}).get('compile_warnings') == 0 and
            review.get('compiler_reg_format_clean') is True and
            review.get('active_pl_replaced') is False and
            review.get('uio_mmap_verified') is False,
            'corrected candidate review fails closed')
    require((candidate/'01_dtc_compile.log').stat().st_size == 0,
            'corrected native dtc compiler diagnostics not empty')
    require(json.loads((candidate/STEM/'shell.json').read_text()) ==
            {'shell_type': 'PL_FLAT', 'num_slots': '1'}, 'unexpected shell.json')
    require((candidate/'98_status.txt').read_text() == 'staging_status=success\n',
            'candidate staging status failed')
    return {'corrected_candidate_dir': str(candidate.resolve()),
            'candidate_ledger_sha256': digest(candidate/'99_evidence_sha256.txt'),
            'bit_bin_sha256': BIT_SHA, 'dtbo_sha256': DTBO_SHA,
            'kernel_ownership_confirmed': False, 'fan_gap_cooling_confirmed': False}


def evidence_ledger(directory: Path) -> None:
    lines = [f'{digest(item)}  {item.relative_to(directory)}' for item in
             sorted(directory.rglob('*')) if item.is_file() and item.name != '99_evidence_sha256.txt']
    (directory/'99_evidence_sha256.txt').write_text('\n'.join(lines)+'\n')


def capture(candidate: Path, base: Path, board_script: Path, target: str = TARGET) -> tuple[Path, bool]:
    require(target == TARGET, 'unexpected board target; manual review required')
    require(base.is_dir() and not base.is_symlink() and
            base.resolve() != candidate.resolve() and
            candidate.resolve() not in base.resolve().parents,
            'invalid owner evidence parent')
    require(board_script.is_file() and not board_script.is_symlink(),
            'board read-only script not found')
    info = validate_candidate(candidate)  # All original binaries verified BEFORE SSH.
    script = board_script.read_bytes()
    require(script.startswith(b'#!/usr/bin/env bash\n') and
            b'M08_PHYSICAL_PREFLIGHT_END_NO_FPGA_CHANGES' in script,
            'bad board script source')
    folder = Path(tempfile.mkdtemp(prefix='m08_2b_physical_READONLY_', dir=base))
    (folder/'00_board_source.sh').write_bytes(script)
    (folder/'00_inputs.json').write_text(json.dumps({
        'schema':'m08-physical-preflight-pc-v1', **info,
        'target':target, 'board_script_sha256':sha256(script).hexdigest(),
        'physical_programming_authorized':False,
        'linux_firmware_install_authorized':False,
    }, indent=2, sort_keys=True)+'\n')
    stdout = folder/'01_ssh_stdout.log'
    stderr = folder/'02_ssh_stderr.log'
    resultcode = 99
    try:
        with (folder/'00_board_source.sh').open('rb') as input_file, \
             stdout.open('xb') as output_file, stderr.open('xb') as error_file:
            result = subprocess.run(
                ['ssh', '-T', '-o', 'ConnectTimeout=12', '-o', 'StrictHostKeyChecking=ask',
                 target, 'bash -s'], stdin=input_file, stdout=output_file,
                stderr=error_file, check=False)
            resultcode = result.returncode
    except OSError as e:
        stderr.write_text(str(e)+'\n')
    (folder/'03_ssh_exit.txt').write_text(f'exit_status={resultcode}\n')
    log = stdout.read_text(errors='replace') if stdout.is_file() else ''
    complete = (resultcode == 0 and
                log.startswith('M08_PHYSICAL_PREFLIGHT_BEGIN_READ_ONLY\n') and
                log.rstrip().endswith('M08_PHYSICAL_PREFLIGHT_END_NO_FPGA_CHANGES'))
    # Overall SSH exit 0 is NOT proof that every named probe succeeded.
    individual = {}
    for line in log.splitlines():
        if line.startswith('M08_GATE_PROBE_END|'):
            fields = line.split('|')
            if len(fields) == 3 and fields[2].startswith('rc='):
                individual[fields[1]] = int(fields[2][3:])
    failed_probes = sorted(name for name, rc in individual.items() if rc != 0)
    stock_listing_verified = individual.get('xmutil_listapps') == 0
    status = ('READ_ONLY_CAPTURE_INCOMPLETE_STOP' if not complete else
              'READ_ONLY_BASELINE_CAPTURED_WITH_NONZERO_PROBES_FOR_REVIEW'
              if failed_probes else
              'READ_ONLY_BASELINE_CAPTURED_FOR_OPERATOR_REVIEW')
    (folder/'04_review.json').write_text(json.dumps({
        'schema':'m08-physical-preflight-readonly-v1',
        'status':status,
        'individual_probe_exit_codes':individual,
        'failed_individual_probes':failed_probes,
        'authenticated_xmutil_inventory_verified':stock_listing_verified,
        'ssh_exit_status': resultcode,
        'source_sha256': sha256(script).hexdigest(),
        'candidate_byte_hash_checked_on_pc':True,
        'cooling_safe_during_reconfiguration':'NOT_VERIFIED',
        'pl_flat_accepted_by_running_manager':'NOT_VERIFIED',
        'm08_board_programmed':False,
        'linux_overlay_installed':False,
        'm08_kernel_binding_verified':False,
        'm08_identity_readback_verified':False,
        'rollback_verified':False,
        'deployment_authorized':False,
    }, sort_keys=True, indent=2)+'\n')
    evidence_ledger(folder)
    return folder, complete


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-dir', type=Path, required=True)
    parser.add_argument('--evidence-base', type=Path, required=True)
    parser.add_argument('--ssh-target', default=TARGET)
    args=parser.parse_args()
    script=Path(__file__).with_name('m08_path_a_physical_gate_board_readonly.sh')
    try:
        folder, good=capture(args.candidate_dir,args.evidence_base,script,args.ssh_target)
    except (PreflightRejected, ValueError, OSError, json.JSONDecodeError) as e:
        print('M08_PHYSICAL_PREFLIGHT_REJECTED:',str(e),file=sys.stderr)
        return 2
    print('M08_PHYSICAL_PREFLIGHT_EVIDENCE_DIR='+str(folder))
    print('M08_PHYSICAL_READONLY_CAPTURE_COMPLETE_NOT_DEPLOYMENT_APPROVAL' if good
          else 'M08_PHYSICAL_READONLY_CAPTURE_INCOMPLETE_STOP')
    return 0 if good else 3


if __name__ == '__main__':
    raise SystemExit(main())
