#include "m05_stream.hpp"

// Provisional Vitis HLS top: native g++ exercises this SAME loop and the
// real M04 C++ arithmetic, but cannot validate hardware ready/valid or II.
std::uint32_t m05_stream_eval(
    hls::stream<M04Request> &requests,
    hls::stream<M04Response> &responses,
    std::uint32_t request_count) {
#pragma HLS INTERFACE axis port=requests
#pragma HLS INTERFACE axis port=responses
#pragma HLS INTERFACE s_axilite port=request_count bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control

    // Fail before consuming requests if host supplies an invalid batch size.
    if (request_count > M05_MAX_BATCH) {
        return M05_BATCH_TOO_LARGE;
    }

run_batch:
    for (std::uint32_t i = 0; i < request_count; ++i) {
#pragma HLS PIPELINE II=1
        const M04Request request = requests.read();
        M04Response response{};
        m04_eval_one(request, response);
        responses.write(response);
    }
    return M05_BATCH_OK;
}
