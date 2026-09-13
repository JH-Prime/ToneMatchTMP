#ifndef TONEMATCH_DSP_H
#define TONEMATCH_DSP_H

#include <stdint.h>

#if defined(_WIN32)
#define TM_DSP_API __declspec(dllexport)
#else
#define TM_DSP_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
#define TM_DSP_NOEXCEPT noexcept
extern "C" {
#else
#define TM_DSP_NOEXCEPT
#endif

/* C ABI 버전을 반환한다. 이 헤더의 계약은 버전 1이다. */
TM_DSP_API uint32_t tm_dsp_abi_version(void) TM_DSP_NOEXCEPT;

/*
 * 스트리밍 상태와 모든 작업 메모리를 한 번 할당한다. 실패하면 NULL이다.
 * sample_rate: 8000..192000, channels: 1..32,
 * fft_size: 128..32768의 2의 거듭제곱, history_size: 1..64.
 * 유한한 0 < min_hz < max_hz가 필요하며 max_hz는 Nyquist로 제한한다.
 * 범위에 실제 FFT bin이 없으면 실패한다. 입력 PCM은 정규화 실수이다.
 * 한 핸들에 대한 모든 호출은 같은 스레드 또는 외부 잠금으로 직렬화한다.
 */
TM_DSP_API void *tm_dsp_create(uint32_t sample_rate, uint32_t channels,
                             uint32_t fft_size, uint32_t history_size,
                             double min_hz, double max_hz) TM_DSP_NOEXCEPT;

/* create에서 얻은 핸들을 한 번 해제한다. NULL은 허용한다. */
TM_DSP_API void tm_dsp_destroy(void *handle) TM_DSP_NOEXCEPT;

/* 부분 PCM과 모든 평활화 이력을 지운다. 성공 0, NULL 핸들은 -1이다. */
TM_DSP_API int tm_dsp_reset(void *handle) TM_DSP_NOEXCEPT;

/* 고정 주파수 격자의 bin 수를 반환한다. NULL 핸들은 0이다. */
TM_DSP_API uint32_t tm_dsp_bin_count(void *handle) TM_DSP_NOEXCEPT;

/* 주파수 격자를 out에 복사한다. 성공은 bin 수, 잘못된 인수는 -1이다. */
TM_DSP_API int tm_dsp_frequencies(void *handle, double *out,
                                uint32_t capacity) TM_DSP_NOEXCEPT;

/*
 * frames개의 인터리브 PCM을 누적하고 완성된 비중첩 FFT 창 수를 반환한다.
 * 0이면 출력 버퍼는 바뀌지 않는다. -1은 잘못된 인수, -2는 내부 오류이다.
 * 한 호출에서 frames는 최대 10000000이다. frames=0일 때만 입력 NULL 허용.
 * waveform에는 최신 완성 창의 채널 평균 PCM fft_size개를 복사한다.
 * magnitudes에는 최근 history_size개 창의 선형 파워 평균을 dBFS로 쓴다.
 * stats[0:3]은 평활 RMS dBFS, 이력 최대 peak dBFS, 평활 centroid Hz이다.
 * 출력 용량은 각각 fft_size, bin_count, 3 이상이어야 한다. 용량 부족은
 * PCM/이력/출력을 바꾸지 않는다. 버퍼는 서로/핸들/입력과 겹치지 않아야 한다.
 * NaN은 0, +Inf는 1, -Inf는 -1로 바꾸며 모든 PCM을 [-1, 1]로 제한한다.
 * 부분 창은 다음 호출까지 보존하며 push 중 동적 메모리를 할당하지 않는다.
 * 핸들은 유효한 create 반환값 또는 NULL이어야 한다. 해제 후 재사용은 금지한다.
 */
TM_DSP_API int tm_dsp_push(void *handle, const double *interleaved,
                         uint32_t frames, double *waveform,
                         uint32_t waveform_capacity, double *magnitudes,
                         uint32_t magnitude_capacity, double *stats,
                         uint32_t stats_capacity) TM_DSP_NOEXCEPT;

#ifdef __cplusplus
}
#endif

#endif
