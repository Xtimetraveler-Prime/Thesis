"""P08.3.4 Loihi-mantissa correction layer for ANN-to-SNN conversion.

The first P08.3.4 gate correctly exposed that a conventional signed-int8 range
is not Loihi's mixed-sign 8-bit mantissa representation. This module keeps the
accepted calibration/normalization/graph/compiler path from :mod:`conversion`
but replaces only its weight quantizer with the source-backed Loihi rule:

- mixed-sign 8-bit mantissa range: -256 .. +254;
- representable step: 2;
- static initialization rounding: toward zero;
- weight exponent: 0.

No clipping is permitted. Bias quantization remains the conservative project
rule already frozen for P08.3.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from . import conversion as _base
from .policy import CONVERSION_POLICY

# Re-export stable artifact/constants/helpers used by the verification gate.
CONVERSION_ARTIFACT_FILENAME = _base.CONVERSION_ARTIFACT_FILENAME
CONVERSION_MANIFEST_FILENAME = _base.CONVERSION_MANIFEST_FILENAME
CONVERSION_SCHEMA = _base.CONVERSION_SCHEMA
CONVERTED_NETWORK_FILENAME = _base.CONVERTED_NETWORK_FILENAME
COMPILED_DEPLOYMENT_FILENAME = _base.COMPILED_DEPLOYMENT_FILENAME
INTEGER_THRESHOLD_SCALE = _base.INTEGER_THRESHOLD_SCALE
NORMALIZATION_PERCENTILE = _base.NORMALIZATION_PERCENTILE
ConversionResult = _base.ConversionResult
build_converted_network = _base.build_converted_network
calibrate_activation_maxima = _base.calibrate_activation_maxima
conv_geometries = _base.conv_geometries
normalize_layer_parameters = _base.normalize_layer_parameters
_arrays_fingerprint = _base._arrays_fingerprint


def quantize_normalized_parameters(
    normalized_kernel: np.ndarray,
    normalized_bias: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Quantize with Loihi mixed-sign 8-bit mantissa semantics.

    The normalized mathematical threshold is 1 and the project stores the Loihi
    threshold mantissa directly as 512. With weight exponent 0, the common native
    Loihi 2**6 factor on threshold and weight cancels at this architectural
    boundary. Static mixed-sign mantissas are rounded toward zero to a multiple
    of two, matching the documented nwb=8 mixed-sign precision.
    """

    if CONVERSION_POLICY.weight_sign_mode != "mixed":
        raise AssertionError("P08.3.4 requires mixed-sign Loihi weights")
    if CONVERSION_POLICY.weight_quantization_step != 2:
        raise AssertionError("P08.3.4 Loihi weight step must be two")
    if CONVERSION_POLICY.weight_rounding != "toward_zero":
        raise AssertionError("P08.3.4 Loihi static weights must round toward zero")

    scale = float(INTEGER_THRESHOLD_SCALE)
    step = float(CONVERSION_POLICY.weight_quantization_step)
    raw_kernel = np.asarray(normalized_kernel, dtype=np.float64) * scale
    q_kernel_64 = (
        np.trunc(raw_kernel / step) * step
    ).astype(np.int64)

    # Biases remain the previously frozen project adaptation. The Loihi bias
    # representation is independently exponent-scaled; P08 has not claimed an
    # exact native bias bitfield emulation.
    q_bias_64 = np.rint(
        np.asarray(normalized_bias, dtype=np.float64) * scale
    ).astype(np.int64)

    if q_kernel_64.size and (
        int(q_kernel_64.min()) < CONVERSION_POLICY.signed_weight_min
        or int(q_kernel_64.max()) > CONVERSION_POLICY.signed_weight_max
    ):
        raise OverflowError(
            "P08.3 normalized weight does not fit the Loihi mixed-sign 8-bit "
            "mantissa range after step-2 rounding: "
            f"observed=[{int(q_kernel_64.min())},{int(q_kernel_64.max())}] "
            f"allowed=[{CONVERSION_POLICY.signed_weight_min},"
            f"{CONVERSION_POLICY.signed_weight_max}]"
        )
    if q_bias_64.size and (
        int(q_bias_64.min()) < CONVERSION_POLICY.signed_bias_min
        or int(q_bias_64.max()) > CONVERSION_POLICY.signed_bias_max
    ):
        raise OverflowError(
            "P08.3 normalized bias does not fit the frozen project bias range: "
            f"observed=[{int(q_bias_64.min())},{int(q_bias_64.max())}] "
            f"allowed=[{CONVERSION_POLICY.signed_bias_min},"
            f"{CONVERSION_POLICY.signed_bias_max}]"
        )
    return q_kernel_64.astype(np.int16), q_bias_64.astype(np.int16)


# Patch only the function looked up by conversion.convert_parameter_arrays at
# runtime. All other conversion logic remains the already-reviewed P08.3.4 path.
_base.quantize_normalized_parameters = quantize_normalized_parameters
convert_parameter_arrays = _base.convert_parameter_arrays


def _manifest_fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def run_conversion(
    checkpoint_path: str | Path,
    training_manifest_path: str | Path,
    output_dir: str | Path,
) -> ConversionResult:
    result = _base.run_conversion(checkpoint_path, training_manifest_path, output_dir)

    # Correct the representation description written by the base module and bind
    # the manifest fingerprint to the actual Loihi-mantissa rule used here.
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    manifest.pop("manifest_fingerprint", None)
    manifest["integer_quantization"] = (
        "weights: trunc_toward_zero(normalized_weight * threshold_mantissa / 2) * 2; "
        "biases: round(normalized_bias * threshold_mantissa); reject overflow; no clipping"
    )
    manifest["weight_sign_mode"] = CONVERSION_POLICY.weight_sign_mode
    manifest["weight_quantization_step"] = CONVERSION_POLICY.weight_quantization_step
    manifest["weight_rounding"] = CONVERSION_POLICY.weight_rounding
    manifest["weight_exponent"] = CONVERSION_POLICY.weight_exponent
    manifest["weight_range"] = [
        CONVERSION_POLICY.signed_weight_min,
        CONVERSION_POLICY.signed_weight_max,
    ]
    manifest["representation_correction"] = (
        "P08.3.4 initial conventional-int8 assumption rejected by overflow gate; "
        "replaced before SNN accuracy evaluation with Loihi mixed-sign 8-bit mantissa semantics"
    )
    manifest["manifest_fingerprint"] = _manifest_fingerprint(manifest)
    result.manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert accepted P08 ANN using corrected Loihi mantissa semantics"
    )
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--training-manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_conversion(args.checkpoint, args.training_manifest, args.output_dir)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    ranges = ",".join(
        f"{layer['name']}:[{layer['integer_weight_min']},{layer['integer_weight_max']}]"
        for layer in manifest["layers"]
    )
    print(
        "PASS: P08.3.4 corrected Loihi mantissa conversion "
        f"step={CONVERSION_POLICY.weight_quantization_step} "
        f"range=[{CONVERSION_POLICY.signed_weight_min},{CONVERSION_POLICY.signed_weight_max}] "
        f"rounding={CONVERSION_POLICY.weight_rounding}"
    )
    print(
        "PASS: P08.3.4 integer conversion "
        f"threshold={INTEGER_THRESHOLD_SCALE} weight_ranges={ranges} overflow=0 clipping=0"
    )
    print(
        "PASS: P08.3.4 P06 compile "
        f"logical_cores={result.logical_core_count} network={result.network_fingerprint} "
        f"compiled={result.compiled_fingerprint}"
    )
    print(
        "PASS: P08.3.4 test lock official_test_used=false test_examples_observed=0 "
        f"conversion_fingerprint={result.conversion_fingerprint}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
