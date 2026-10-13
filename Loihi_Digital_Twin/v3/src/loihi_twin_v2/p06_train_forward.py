"""P06-A2.5 training-time *integer-valued* forward with surrogate gradients.

The forward trajectory must equal P06-A2's separate scalar/dense integer oracle
when its trainable weights are exported. Only gradients are approximated. This
module requires PyTorch, but existing P03/P05/P06 oracle modules do not.

This is not an MNIST trainer, a trained checkpoint, an HLS implementation, or
an alternative numerical specification. No official test labels are used.
"""
from __future__ import annotations

import math

import torch
from torch import nn

from .p06_compact_inference import CompactNetwork
from .p06_input_contract import INPUT_CHANNELS, HIDDEN_NEURONS, OUTPUT_CLASSES, INPUT_TICKS, TOTAL_TICKS
from .p06_integer_oracle import LIFParameters, STATE_MIN, STATE_MAX


class _StrictSpike(torch.autograd.Function):
    """Strict FPGA > comparison forward; fast-sigmoid surrogate backward."""

    @staticmethod
    def forward(ctx, voltage: torch.Tensor, threshold: float, width: float):
        ctx.save_for_backward(voltage)
        ctx.threshold = threshold
        ctx.width = width
        return (voltage > threshold).to(voltage.dtype)

    @staticmethod
    def backward(ctx, grad_output):
        (voltage,) = ctx.saved_tensors
        width = ctx.width
        # d/dV of a smooth fast-sigmoid proxy, never the binary comparator.
        approx = 1.0 / (width * (1.0 + (voltage - ctx.threshold).abs() / width).square())
        return grad_output * approx, None, None


def _ste_round_half_away(value: torch.Tensor) -> torch.Tensor:
    rounded = value.sign() * (value.abs() + 0.5).floor()
    return value + (rounded - value).detach()


def _ste_ceil_away(value: torch.Tensor) -> torch.Tensor:
    rounded = value.sign() * value.abs().ceil()
    return value + (rounded - value).detach()


def _ste_saturate24(value: torch.Tensor) -> torch.Tensor:
    clipped = value.clamp(STATE_MIN, STATE_MAX)
    return value + (clipped - value).detach()


def _integer_step(
    current: torch.Tensor,
    voltage: torch.Tensor,
    refractory: torch.Tensor,
    synaptic_input: torch.Tensor,
    params: LIFParameters,
    surrogate_width: float,
):
    """Vectorized accepted P03 state-update ORDER; round/saturate use STE."""
    current_work = _ste_saturate24(current + synaptic_input)
    current_decay = _ste_ceil_away(current_work * (params.current_decay / 4096))
    next_current = _ste_saturate24(current_work - current_decay)

    voltage_decay = _ste_ceil_away(voltage * (params.voltage_decay / 4096))
    voltage_decayed = _ste_saturate24(voltage - voltage_decay)
    candidate = _ste_saturate24(voltage_decayed + current_work + params.bias)

    available = refractory == 0
    spiked = _StrictSpike.apply(candidate, float(params.threshold), surrogate_width)
    spiked = spiked * available.to(spiked.dtype)
    next_voltage = torch.where(
        available, candidate + spiked * (params.reset_voltage - candidate),
        torch.full_like(candidate, float(params.reset_voltage)),
    )
    next_ref = torch.where(
        available,
        (spiked.detach() > 0).to(torch.int64) * max(params.refractory_ticks - 1, 0),
        refractory - 1,
    )
    return next_current, next_voltage, next_ref, spiked


class IntegerForwardSNN(nn.Module):
    """Dense compact SNN, FPGA-exact integer forward and approximate gradients.

    Parameters are *real* weights trained through signed-24 rounding and
    straight-through quantization. The initial training profile deliberately
    uses FIXED, UNIFORM per-layer LIF configs, matching the existing compiler's
    PopulationSpec. No independently learned per-neuron bias is claimed.

    IEEE float64 operations are deliberate: all legal signed24 weighted sums
    over 784 inputs are integral and exactly representable (<2**53).
    Float32 accumulation is not guaranteed parity at saturation boundaries.
    Disable AMP/autocast for this reference mode.
    """

    def __init__(
        self,
        hidden: LIFParameters,
        output: LIFParameters,
        *,
        surrogate_width: float = 128.0,
    ) -> None:
        super().__init__()
        if not isinstance(hidden, LIFParameters) or not isinstance(output, LIFParameters):
            raise TypeError("neuron configs must be independently validated LIFParameters")
        if type(surrogate_width) not in (float, int) or not math.isfinite(surrogate_width) or surrogate_width <= 0:
            raise ValueError("surrogate_width must be a positive finite number")
        self.hidden_config = hidden
        self.output_config = output
        self.surrogate_width = float(surrogate_width)
        # Zero is an intentionally neutral start; training may set seeded
        # initial values explicitly in P06-A3. No RNG is consumed here.
        self.w_input_hidden = nn.Parameter(torch.zeros(HIDDEN_NEURONS, INPUT_CHANNELS, dtype=torch.float32))
        self.w_hidden_output = nn.Parameter(torch.zeros(OUTPUT_CLASSES, HIDDEN_NEURONS, dtype=torch.float32))
        self.register_buffer("phase_offsets", (17 * torch.arange(INPUT_CHANNELS, dtype=torch.int64)) % INPUT_TICKS)

    def _effective_weights(self) -> tuple[torch.Tensor, torch.Tensor]:
        # With float64 accumulation, each effective weight is exactly integral.
        return (
            _ste_saturate24(_ste_round_half_away(self.w_input_hidden.to(torch.float64))),
            _ste_saturate24(_ste_round_half_away(self.w_hidden_output.to(torch.float64))),
        )

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        """Return [batch,10] exact integer-valued spike counts with gradients.

        The final tick has NO external pixel spikes. Output neurons consume
        the PRIOR tick's hidden spikes. All neuron states and pending packets
        start at zero each call; tick-25 hidden packets cannot leak into another
        sample. Rows are raw 784-byte pixel intensities, not normalized floats.
        """
        if images.ndim != 2 or images.shape[1] != INPUT_CHANNELS:
            raise ValueError("expected [batch,784] raw uint8 images")
        if images.dtype != torch.uint8:
            raise TypeError("input images must be torch.uint8; no analog normalization")
        if images.device != self.w_input_hidden.device:
            raise ValueError("input image tensor must use module device")
        if images.shape[0] < 1:
            raise ValueError("batch must contain at least one image")
        pixels = images.to(torch.int64)
        weights_ih, weights_ho = self._effective_weights()
        batch = images.shape[0]
        hc = torch.zeros((batch, HIDDEN_NEURONS), dtype=torch.float64, device=images.device)
        hv = torch.zeros_like(hc)
        hr = torch.zeros_like(hc, dtype=torch.int64)
        oc = torch.zeros((batch, OUTPUT_CLASSES), dtype=torch.float64, device=images.device)
        ov = torch.zeros_like(oc)
        orefr = torch.zeros_like(oc, dtype=torch.int64)
        last_hidden_spikes = torch.zeros_like(hc)
        output_counts = torch.zeros_like(oc)
        for tick in range(TOTAL_TICKS):
            if tick < INPUT_TICKS:
                phase = (self.phase_offsets + tick) % INPUT_TICKS
                input_spikes = (
                    ((phase + 1) * pixels) // 255 > (phase * pixels) // 255
                ).to(torch.float64)
                ih_input = input_spikes @ weights_ih.T
            else:
                ih_input = torch.zeros_like(hc)
            # IMPORTANT: output uses the PREVIOUS, not this tick's hidden spikes.
            ho_input = last_hidden_spikes @ weights_ho.T
            hc, hv, hr, hidden_spikes = _integer_step(
                hc, hv, hr, ih_input, self.hidden_config, self.surrogate_width,
            )
            oc, ov, orefr, output_spikes = _integer_step(
                oc, ov, orefr, ho_input, self.output_config, self.surrogate_width,
            )
            output_counts = output_counts + output_spikes
            last_hidden_spikes = hidden_spikes
        return output_counts

    @torch.no_grad()
    def to_integer_network(self) -> CompactNetwork:
        """Fail-closed signed24 export; never silently clip trained weights."""
        result = []
        for name, parameter in (("input_hidden", self.w_input_hidden),
                                ("hidden_output", self.w_hidden_output)):
            if not torch.isfinite(parameter).all():
                raise ValueError(f"{name} contains nonfinite weights")
            weights = _ste_round_half_away(parameter.detach().to(torch.float64))
            if ((weights < STATE_MIN) | (weights > STATE_MAX)).any():
                raise ValueError(f"{name} has weights outside signed24 packer range")
            result.append(tuple(tuple(int(v) for v in row) for row in weights.cpu().tolist()))
        return CompactNetwork.from_uniform_parameters(
            result[0], result[1], self.hidden_config, self.output_config,
        )
