#ifndef LOIHI_TWIN_V3_P07_A2_SHA256_H
#define LOIHI_TWIN_V3_P07_A2_SHA256_H
/* Portable SHA-256 for immutable 512KiB P02 image identity verification. */
#include <stddef.h>
#include <stdint.h>
void p07_a2_sha256(const uint8_t *bytes, size_t length, uint8_t out[32]);
#endif
