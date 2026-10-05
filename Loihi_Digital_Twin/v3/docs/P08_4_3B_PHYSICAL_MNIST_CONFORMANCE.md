# P08.4.3b Representative Physical MNIST Conformance

## Purpose

P08.4.2 established exact 100-timestep compiled execution and paging-order invariance for the frozen representative official-test frame. P08.4.3a established a routed K26 shell whose hardware boundary matches the accepted P08 host-paging design. P08.4.3b joins those two results by executing one real deep-network dispatch from that exact inference on programmable logic.

This is a representative physical conformance gate, not a claim that the host/JTAG harness physically replays all 500 logical-core dispatches of the 100-timestep inference. The exhaustive logical paging sequence remains covered by P08.4.2; P08.4.3b tests the physical memory-image, page-replacement, HLS arithmetic, trace, packet, and output-state boundary on a frozen deep-network snapshot.

## Frozen identities

The gate requires the P08.4.3a physical artifacts:

```text
p08_host_paged.bit SHA-256 = 3538b8f7a23dbd923c77471cb533cd844af548c0d50d7679cd40844f465e8f83
p08_host_paged.ltx SHA-256 = e32376f31486b96b070b0b12c6131d7bed067e0dd05e0461b029baf3eeea6936
```

and the accepted P08.3.5c/P08.4.2 compiled deployment:

```text
compiled fingerprint = 5dc7c9af692ca375283ede186b81d135bd1c76708b114cc64e3f99c085cd856b
```

The representative frame remains fixed:

```text
official MNIST test index = 0
label                     = 7
physical timestep         = 99
target logical core       = 4
physical resident slot    = 0
```

No model or conversion selection occurs after test-set observation.

## Corpus generation

`mnist_v2_nxtf.physical_conformance_vectors` replays the already accepted compiled deployment only far enough to capture logical core 4 immediately before its final timestep-99 evaluation. From that snapshot it emits:

- P03-compatible compartment configuration words;
- exact pre-dispatch compartment states;
- sparse axon/template and route tables;
- current-timestep input-event axon IDs;
- expected post-dispatch state words;
- expected trace words;
- expected output packet words;
- the ten conv4 output-compartment IDs; and
- the accepted ten-class evidence vector.

The expected final evidence remains:

```text
[-284, -1203, 104, 109, -2253, -599, -2659, 1446, -436, -63]
```

with class-7 argmax.

## Physical protocol

The Vivado hardware-manager harness performs the following sequence:

1. program the exact accepted P08.4.3a bitstream and probes;
2. verify reset release and a live PL heartbeat;
3. write and read back a decoy logical-core marker in physical slot 0;
4. overwrite slot 0 with the frozen logical-core-4 backing image;
5. load the timestep-99 event image into the correct double-buffered event bank;
6. dispatch logical core 4 through the one P03-compatible HLS engine;
7. require zero controller/HLS/address errors;
8. compare every post-dispatch compartment-state word exactly;
9. compare every retained trace word exactly;
10. compare the complete packet image as an unordered multiset; and
11. read the ten conv4 output voltages from physical state memory and require exact equality with the accepted P08.4.2 evidence vector.

The decoy-to-core-4 overwrite is an explicit physical resident-slot replacement. Cross-page packet delivery and the global barrier are not reimplemented in PL; their exhaustive behavior remains the P08.4.2 host-paged conformance result.

## Run

With `.venv-p08` active, Vivado 2025.2 on `PATH`, the K26 connected through hardware manager/JTAG, and the accepted P08.4.2 artifacts present:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v2
bash hardware/run_p08_4_3b_physical.sh
```

## Acceptance

P08.4.3b is accepted only if the physical result reports `result=PASS` with exact state/trace, packet, and output-evidence matches, the expected bitstream/probe/compiled identities, and `model_or_conversion_selection_after_test=0`.
