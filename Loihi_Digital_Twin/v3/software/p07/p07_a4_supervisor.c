#include "include/p07_a4_supervisor.h"
#include "include/p07_a4_stream.h"
#include <stddef.h>
#include <stdint.h>
int p07_a4_run_images(uint32_t count,const p07_a4_callbacks *ops,
                      uint32_t *completed,uint32_t *first_fault)
{
    uint32_t i,done=0u,failed=UINT32_MAX;
    if(completed)*completed=0u;
    if(first_fault)*first_fault=UINT32_MAX;
    if(!completed || !first_fault || !ops ||
       !ops->execute_and_commit_image || !ops->commit_progress ||
       !count || count>P07_A4_MAX_FRAMES) return P07_A4_RUN_BAD_ARGS;
    if(ops->commit_progress(0u,0u,UINT32_MAX)!=0)
        return P07_A4_RUN_JOURNAL_FAIL;
    for(i=0u;i<count;++i) {
        if(ops->execute_and_commit_image(ops->cookie,i)!=0) {
            failed=i;
            *first_fault=failed;
            /* Preserve most recent successfully committed count; if even
             * fail-reporting fails the native wrapper still halts. */
            (void)ops->commit_progress(0xDEAD0001u,done,failed);
            return P07_A4_RUN_IMAGE_FAIL;
        }
        done=i+1u;
        *completed=done;
        if(ops->commit_progress(0u,done,UINT32_MAX)!=0) {
            failed=i;
            *first_fault=failed;
            (void)ops->commit_progress(0xDEAD0002u,done,failed);
            return P07_A4_RUN_JOURNAL_FAIL;
        }
    }
    if(ops->commit_progress(P07_A4_OK_STATUS,done,UINT32_MAX)!=0) {
        *first_fault=count-1u;
        (void)ops->commit_progress(0xDEAD0003u,done,*first_fault);
        return P07_A4_RUN_JOURNAL_FAIL;
    }
    return P07_A4_RUN_OK;
}
