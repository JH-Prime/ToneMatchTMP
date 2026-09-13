// 외부 DSP 라이브러리 없이 고정 창 스트리밍 분석을 제공하는 C++17 엔진이다.
#include "tonematch_dsp.h"

#include <algorithm>
#include <cmath>
#include <complex>
#include <cstddef>
#include <limits>
#include <vector>

namespace {

constexpr double kPi = 3.141592653589793238462643383279502884;
constexpr double kDbfsFloor = -120.0;
constexpr uint32_t kMaximumFramesPerPush = 10000000;

// 표시 하한 이하의 파워를 정확한 무음으로 바꿔 Python 평활화 규칙과 맞춘다.
double history_power(double power) noexcept {
    if (power <= 0.0) {
        return 0.0;
    }
    const double level = 10.0 * std::log10(power);
    return level > kDbfsFloor ? power : 0.0;
}

// 0 파워에서 로그 특이점 없이 유한한 dBFS 표시값을 계산한다.
double power_to_dbfs(double power) noexcept {
    return power > 0.0 ? std::max(kDbfsFloor, 10.0 * std::log10(power))
                       : kDbfsFloor;
}

// NaN과 무한대를 정해진 PCM 값으로 치환한 뒤 정규화 범위로 제한한다.
double sanitize_sample(double value) noexcept {
    if (std::isnan(value)) {
        return 0.0;
    }
    return std::max(-1.0, std::min(1.0, value));
}

// 생성 전에 정수 곱의 overflow, 메모리 규모, 주파수 격자를 함께 검증한다.
bool valid_configuration(uint32_t sample_rate, uint32_t channels,
                         uint32_t fft_size, uint32_t history_size,
                         double min_hz, double max_hz) noexcept {
    if (sample_rate < 8000 || sample_rate > 192000 || channels < 1 || channels > 32 ||
        fft_size < 128 || fft_size > 32768 || (fft_size & (fft_size - 1)) != 0 ||
        history_size < 1 || history_size > 64 || !std::isfinite(min_hz) ||
        !std::isfinite(max_hz) || min_hz <= 0.0 || max_hz <= min_hz) {
        return false;
    }
    const std::size_t maximum_elements =
        std::numeric_limits<std::size_t>::max() / sizeof(double);
    if (static_cast<std::size_t>(fft_size) > maximum_elements / channels ||
        static_cast<std::size_t>(fft_size / 2 + 1) > maximum_elements / history_size) {
        return false;
    }
    const double capped_max = std::min(max_hz, sample_rate / 2.0);
    const double spacing = 1.0 / (fft_size * (1.0 / sample_rate));
    for (uint32_t bin = 0; bin <= fft_size / 2; ++bin) {
        const double frequency = bin * spacing;
        if (frequency >= min_hz && frequency <= capped_max) {
            return true;
        }
    }
    return false;
}

class DspEngine {
public:
    // FFT 계획, 채널 PCM 창, 최신 파형과 평활화 이력 저장소를 미리 할당한다.
    DspEngine(uint32_t sample_rate, uint32_t channels, uint32_t fft_size,
              uint32_t history_size, double min_hz, double max_hz)
        : channels_(channels), fft_size_(fft_size), history_size_(history_size),
          pcm_(static_cast<std::size_t>(fft_size) * channels, 0.0),
          waveform_(fft_size, 0.0), hann_(fft_size), bit_reversal_(fft_size),
          twiddles_(fft_size / 2), transformed_(fft_size),
          rms_history_(history_size, 0.0), peak_history_(history_size, kDbfsFloor) {
        const double capped_max = std::min(max_hz, sample_rate / 2.0);
        const double spacing = 1.0 / (fft_size * (1.0 / sample_rate));
        for (uint32_t bin = 0; bin <= fft_size / 2; ++bin) {
            const double frequency = bin * spacing;
            if (frequency >= min_hz && frequency <= capped_max) {
                bins_.push_back(bin);
                frequencies_.push_back(frequency);
            }
        }
        selected_power_.resize(bins_.size(), 0.0);
        power_history_.resize(static_cast<std::size_t>(history_size) * bins_.size(), 0.0);

        uint32_t bits = 0;
        for (uint32_t count = fft_size; count > 1; count >>= 1) {
            ++bits;
        }
        for (uint32_t index = 0; index < fft_size; ++index) {
            uint32_t original = index;
            uint32_t reversed = 0;
            for (uint32_t bit = 0; bit < bits; ++bit) {
                reversed = (reversed << 1) | (original & 1);
                original >>= 1;
            }
            bit_reversal_[index] = reversed;
            hann_[index] = 0.5 - 0.5 * std::cos(2.0 * kPi * index / (fft_size - 1));
            coherent_gain_ += hann_[index];
        }
        for (uint32_t index = 0; index < fft_size / 2; ++index) {
            const double angle = -2.0 * kPi * index / fft_size;
            twiddles_[index] = std::complex<double>(std::cos(angle), std::sin(angle));
        }
    }

    // 미완성 입력과 이전 장치의 표시 이력을 할당 없이 모두 초기화한다.
    void reset() noexcept {
        filled_frames_ = 0;
        history_count_ = 0;
        history_next_ = 0;
        std::fill(pcm_.begin(), pcm_.end(), 0.0);
        std::fill(waveform_.begin(), waveform_.end(), 0.0);
        std::fill(selected_power_.begin(), selected_power_.end(), 0.0);
        std::fill(power_history_.begin(), power_history_.end(), 0.0);
        std::fill(rms_history_.begin(), rms_history_.end(), 0.0);
        std::fill(peak_history_.begin(), peak_history_.end(), kDbfsFloor);
        std::fill(transformed_.begin(), transformed_.end(), std::complex<double>(0.0, 0.0));
    }

    // 고정된 FFT 창의 길이를 반환한다.
    uint32_t fft_size() const noexcept { return fft_size_; }

    // 버퍼 곱 검증에 사용할 입력 채널 수를 반환한다.
    uint32_t channels() const noexcept { return channels_; }

    // 선택된 주파수 격자의 길이를 반환한다.
    uint32_t bin_count() const noexcept { return static_cast<uint32_t>(bins_.size()); }

    // 호출자가 제공한 충분한 크기의 배열로 주파수 격자를 복사한다.
    void copy_frequencies(double *out) const noexcept {
        std::copy(frequencies_.begin(), frequencies_.end(), out);
    }

    // 임의 길이의 블록을 고정 창으로 나누고 최신 완성 창의 결과만 출력한다.
    int push(const double *interleaved, uint32_t frames, double *waveform,
             double *magnitudes, double *stats) noexcept {
        uint32_t consumed = 0;
        int completed = 0;
        while (consumed < frames) {
            const uint32_t take = std::min(frames - consumed, fft_size_ - filled_frames_);
            const std::size_t source_offset = static_cast<std::size_t>(consumed) * channels_;
            const std::size_t destination_offset = static_cast<std::size_t>(filled_frames_) * channels_;
            const std::size_t sample_count = static_cast<std::size_t>(take) * channels_;
            for (std::size_t sample = 0; sample < sample_count; ++sample) {
                pcm_[destination_offset + sample] = sanitize_sample(interleaved[source_offset + sample]);
            }
            filled_frames_ += take;
            consumed += take;
            if (filled_frames_ == fft_size_) {
                analyze_complete_window();
                filled_frames_ = 0;
                ++completed;
            }
        }
        if (completed > 0) {
            write_output(waveform, magnitudes, stats);
        }
        return completed;
    }

private:
    // 비트 역순으로 준비한 입력에 미리 계산한 회전 인자를 쓰는 radix-2 FFT이다.
    void transform() noexcept {
        for (uint32_t length = 2; length <= fft_size_; length <<= 1) {
            const uint32_t half = length / 2;
            const uint32_t stride = fft_size_ / length;
            for (uint32_t start = 0; start < fft_size_; start += length) {
                for (uint32_t offset = 0; offset < half; ++offset) {
                    const std::complex<double> even = transformed_[start + offset];
                    const std::complex<double> odd =
                        transformed_[start + offset + half] * twiddles_[offset * stride];
                    transformed_[start + offset] = even + odd;
                    transformed_[start + offset + half] = even - odd;
                }
            }
        }
    }

    // 채널별 DC 제거와 FFT 후 파워를 평균하여 역상 스테레오 상쇄를 방지한다.
    void analyze_complete_window() noexcept {
        std::fill(selected_power_.begin(), selected_power_.end(), 0.0);
        double square_sum = 0.0;
        double peak_amplitude = 0.0;
        for (uint32_t frame = 0; frame < fft_size_; ++frame) {
            double mono = 0.0;
            const std::size_t base = static_cast<std::size_t>(frame) * channels_;
            for (uint32_t channel = 0; channel < channels_; ++channel) {
                const double sample = pcm_[base + channel];
                mono += sample;
                square_sum += sample * sample;
                peak_amplitude = std::max(peak_amplitude, std::abs(sample));
            }
            waveform_[frame] = std::max(-1.0, std::min(1.0, mono / channels_));
        }

        const double amplitude_scale = 2.0 / coherent_gain_;
        for (uint32_t channel = 0; channel < channels_; ++channel) {
            double mean = 0.0;
            for (uint32_t frame = 0; frame < fft_size_; ++frame) {
                mean += pcm_[static_cast<std::size_t>(frame) * channels_ + channel];
            }
            mean /= fft_size_;
            for (uint32_t frame = 0; frame < fft_size_; ++frame) {
                const double centered =
                    pcm_[static_cast<std::size_t>(frame) * channels_ + channel] - mean;
                transformed_[bit_reversal_[frame]] =
                    std::complex<double>(centered * hann_[frame], 0.0);
            }
            transform();
            for (std::size_t selected = 0; selected < bins_.size(); ++selected) {
                const uint32_t bin = bins_[selected];
                const double scale = (bin == 0 || bin == fft_size_ / 2)
                                         ? amplitude_scale * 0.5 : amplitude_scale;
                selected_power_[selected] += std::norm(transformed_[bin]) * scale * scale;
            }
        }

        const std::size_t slot = static_cast<std::size_t>(history_next_) * bins_.size();
        for (std::size_t selected = 0; selected < bins_.size(); ++selected) {
            power_history_[slot + selected] = history_power(selected_power_[selected] / channels_);
        }
        rms_history_[history_next_] =
            history_power(square_sum / (static_cast<double>(fft_size_) * channels_));
        peak_history_[history_next_] = power_to_dbfs(peak_amplitude * peak_amplitude);
        history_count_ = std::min(history_count_ + 1, history_size_);
        history_next_ = (history_next_ + 1) % history_size_;
    }

    // 유효 이력 개수로 파워를 평균하고 최신 파형 및 가중 무게중심을 출력한다.
    void write_output(double *waveform, double *magnitudes, double *stats) const noexcept {
        std::copy(waveform_.begin(), waveform_.end(), waveform);
        double total_power = 0.0;
        double weighted_power = 0.0;
        for (std::size_t selected = 0; selected < bins_.size(); ++selected) {
            double sum = 0.0;
            for (uint32_t history = 0; history < history_count_; ++history) {
                sum += power_history_[static_cast<std::size_t>(history) * bins_.size() + selected];
            }
            const double mean_power = sum / history_count_;
            magnitudes[selected] = power_to_dbfs(mean_power);
            total_power += mean_power;
            weighted_power += frequencies_[selected] * mean_power;
        }
        double rms_power = 0.0;
        double peak_dbfs = kDbfsFloor;
        for (uint32_t history = 0; history < history_count_; ++history) {
            rms_power += rms_history_[history];
            peak_dbfs = std::max(peak_dbfs, peak_history_[history]);
        }
        stats[0] = power_to_dbfs(rms_power / history_count_);
        stats[1] = peak_dbfs;
        stats[2] = total_power > 1e-24 ? weighted_power / total_power : 0.0;
    }

    uint32_t channels_;
    uint32_t fft_size_;
    uint32_t history_size_;
    uint32_t filled_frames_ = 0;
    uint32_t history_count_ = 0;
    uint32_t history_next_ = 0;
    double coherent_gain_ = 0.0;
    std::vector<double> pcm_;
    std::vector<double> waveform_;
    std::vector<double> hann_;
    std::vector<uint32_t> bit_reversal_;
    std::vector<std::complex<double>> twiddles_;
    std::vector<std::complex<double>> transformed_;
    std::vector<uint32_t> bins_;
    std::vector<double> frequencies_;
    std::vector<double> selected_power_;
    std::vector<double> power_history_;
    std::vector<double> rms_history_;
    std::vector<double> peak_history_;
};

}  // namespace

// 로더가 DLL과 Python bridge의 C ABI 호환성을 검사할 수 있게 한다.
uint32_t tm_dsp_abi_version(void) noexcept { return 1; }

// 유효하지 않은 설정과 할당 실패를 모두 NULL로 반환하여 예외 전파를 막는다.
void *tm_dsp_create(uint32_t sample_rate, uint32_t channels, uint32_t fft_size,
                    uint32_t history_size, double min_hz, double max_hz) noexcept {
    if (!valid_configuration(sample_rate, channels, fft_size, history_size, min_hz, max_hz)) {
        return nullptr;
    }
    try {
        return new DspEngine(sample_rate, channels, fft_size, history_size, min_hz, max_hz);
    } catch (...) {
        return nullptr;
    }
}

// DLL에서 만든 상태는 같은 DLL에서 파괴하여 CRT 간 메모리 소유권을 유지한다.
void tm_dsp_destroy(void *handle) noexcept {
    try {
        delete static_cast<DspEngine *>(handle);
    } catch (...) {
        // C 경계를 넘어가는 예외는 허용하지 않는다.
    }
}

// NULL을 거부하고 재사용 가능한 스트리밍 상태를 초기화한다.
int tm_dsp_reset(void *handle) noexcept {
    if (handle == nullptr) {
        return -1;
    }
    try {
        static_cast<DspEngine *>(handle)->reset();
        return 0;
    } catch (...) {
        return -2;
    }
}

// 외부 코드가 결과 버퍼를 만들 수 있도록 bin 개수를 조회한다.
uint32_t tm_dsp_bin_count(void *handle) noexcept {
    if (handle == nullptr) {
        return 0;
    }
    try {
        return static_cast<DspEngine *>(handle)->bin_count();
    } catch (...) {
        return 0;
    }
}

// 복사 전 출력 용량을 검증하여 실패 시 출력 배열도 보존한다.
int tm_dsp_frequencies(void *handle, double *out, uint32_t capacity) noexcept {
    if (handle == nullptr || out == nullptr) {
        return -1;
    }
    try {
        const DspEngine &engine = *static_cast<DspEngine *>(handle);
        if (capacity < engine.bin_count()) {
            return -1;
        }
        engine.copy_frequencies(out);
        return static_cast<int>(engine.bin_count());
    } catch (...) {
        return -2;
    }
}

// 입력과 모든 출력 용량을 먼저 검증한 뒤 할당 없는 블록 처리를 호출한다.
int tm_dsp_push(void *handle, const double *interleaved, uint32_t frames,
                double *waveform, uint32_t waveform_capacity, double *magnitudes,
                uint32_t magnitude_capacity, double *stats, uint32_t stats_capacity) noexcept {
    if (handle == nullptr || (frames > 0 && interleaved == nullptr) ||
        waveform == nullptr || magnitudes == nullptr || stats == nullptr ||
        frames > kMaximumFramesPerPush) {
        return -1;
    }
    try {
        DspEngine &engine = *static_cast<DspEngine *>(handle);
        if (waveform_capacity < engine.fft_size() || magnitude_capacity < engine.bin_count() ||
            stats_capacity < 3 || static_cast<std::size_t>(frames) >
                std::numeric_limits<std::size_t>::max() / sizeof(double) / engine.channels()) {
            return -1;
        }
        return engine.push(interleaved, frames, waveform, magnitudes, stats);
    } catch (...) {
        return -2;
    }
}
