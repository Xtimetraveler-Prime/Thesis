# P08.3.3 Full ANN Training Acceptance

**Status:** Accepted  
**Accepted:** 2026-09-30  
**Selection boundary:** fixed 55,000/5,000 training/validation split only  
**Official MNIST test split:** not observed

P08.3.3 executed the frozen ANN training policy established in P08.3.1 and the deterministic training/checkpoint machinery validated in P08.3.2.

The accepted run reported:

```text
epochs run:                  18
selected epoch:              13
best validation accuracy:    0.992600
best validation loss:        0.030356
engineering sanity floor:    0.95
model parameters:            7,006
official test used:          false
test examples observed:      0
selection source:            fixed_validation_split_only
```

The selected model is bound by both archive and tensor identities:

```text
checkpoint SHA-256:
61f60eaa789dcf04131f658edb86db880999a5f0ad2c8f1bd06426d464dba7d2

selected-weight fingerprint:
e5c07133b8d534d29596cbde9d637db695942dfb224a82c2533f59a17f1c74ce
```

The 99.26% validation accuracy is an observed result, not a new tuning target. No topology, optimizer, dropout, training horizon, checkpoint rule, or conversion choice may be changed merely to improve agreement with the NxTF paper after seeing this result.

The selected local artifact is expected at:

```text
applications/mnist_v2_nxtf/artifacts/p08_3_3_full_ann/selected_ann.keras
applications/mnist_v2_nxtf/artifacts/p08_3_3_full_ann/training_manifest.json
applications/mnist_v2_nxtf/artifacts/p08_3_3_full_ann/gate_result.json
```

These generated files remain Git-ignored. P08.3.4 must validate the recorded identities before conversion and must continue to exclude the official test split.

## Advancement decision

P08.3.3 is accepted. P08.3.4 may now convert exactly this checkpoint under the already frozen rate-conversion policy. Conversion calibration may use only the frozen training remainder. Official-test evaluation remains locked until conversion and decoder behavior are accepted.
