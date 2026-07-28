"""Run a two-neuron core and print tick-by-tick internal state."""

from neuromorphic_twin import NeuronConfig, NeuromorphicCore, Synapse


def main() -> None:
    configs = [
        NeuronConfig(
            current_decay=1024,   # remove 1/4 of current per tick
            voltage_decay=512,    # remove 1/8 of voltage per tick
            threshold=20,
            refractory_ticks=1,
        ),
        NeuronConfig(
            current_decay=2048,   # remove 1/2 of current per tick
            voltage_decay=1024,   # remove 1/4 of voltage per tick
            threshold=16,
            bias=1,
        ),
    ]

    synapses = [
        Synapse(axon_id=0, target_neuron=0, weight=8),
        Synapse(axon_id=0, target_neuron=1, weight=5),
        Synapse(axon_id=1, target_neuron=0, weight=-3),
    ]

    core = NeuromorphicCore(configs, synapses)
    input_schedule = [
        (0,),
        (0,),
        (),
        (1,),
        (0, 0),  # two spikes on axon 0 in the same tick
        (),
    ]

    print("tick | inputs | synaptic | current | voltage | spikes")
    print("-----+--------+----------+---------+---------+-------")
    for input_axons in input_schedule:
        trace = core.step(input_axons)
        spike_ids = [spike.neuron_id for spike in trace.spikes]
        print(
            f"{trace.tick:>4} | "
            f"{str(trace.input_axons):>6} | "
            f"{str(trace.synaptic_input):>8} | "
            f"{str(trace.current_after):>7} | "
            f"{str(trace.voltage_after):>7} | "
            f"{spike_ids}"
        )


if __name__ == "__main__":
    main()
