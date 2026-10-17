#ifndef LOIHI_V3_P07_A4_SUPERVISOR_H
#define LOIHI_V3_P07_A4_SUPERVISOR_H
/* A4.2b: independent portable C11 no-HW persistent image loop.
 * Per-image callback MUST commit full 96B result before returning success.
 * Progress callback must durably commit header after the result.
 */
#include <stdint.h>
#define P07_A4_RUN_OK 0
#define P07_A4_RUN_BAD_ARGS -1
#define P07_A4_RUN_IMAGE_FAIL -2
#define P07_A4_RUN_JOURNAL_FAIL -3
typedef struct {
    void *cookie;
    int (*execute_and_commit_image)(void *cookie,uint32_t image_index);
    int (*commit_progress)(void *cookie,uint32_t status,
                           uint32_t completed,uint32_t first_fault);
} p07_a4_callbacks;
/* No retry/drop/substitute, and never reports success for partial results. */
int p07_a4_run_images(uint32_t count,const p07_a4_callbacks *ops,
                      uint32_t *completed,uint32_t *first_fault);
#endif
