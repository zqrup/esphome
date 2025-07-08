#include "i2s_audio.h"

#ifdef USE_ESP32

#include "esphome/core/log.h"

namespace esphome {
namespace i2s_audio {

static const char *const TAG = "i2s_audio";

#if defined(USE_ESP_IDF) && (ESP_IDF_VERSION_MAJOR >= 5)
static const uint8_t I2S_NUM_MAX = SOC_I2S_NUM;  // because IDF 5+ took this away :(
#endif

void I2SAudioComponent::setup() {
  ESP_LOGCONFIG(TAG, "Running setup");

  static i2s_port_t next_port_num = I2S_NUM_0;
  if (next_port_num >= I2S_NUM_MAX) {
    ESP_LOGE(TAG, "Too many components");
    this->mark_failed();
    return;
  }

  this->port_ = next_port_num;
  next_port_num = (i2s_port_t) (next_port_num + 1);
}

}  // namespace i2s_audio
}  // namespace esphome

#endif  // USE_ESP32
