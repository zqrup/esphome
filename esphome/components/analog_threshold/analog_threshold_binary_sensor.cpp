#include "analog_threshold_binary_sensor.h"
#include "esphome/core/log.h"

namespace esphome {
namespace analog_threshold {

static const char *const TAG = "analog_threshold.binary_sensor";

void AnalogThresholdBinarySensor::setup() {
  float sensor_value = this->sensor_->get_state();

  // TRUE state is defined to be when sensor is >= threshold
  // so when undefined sensor value initialize to FALSE
  if (std::isnan(sensor_value)) {
    this->publish_initial_state(false);
  } else {
    this->publish_initial_state(sensor_value >=
                                (this->lower_threshold_.value() + this->upper_threshold_.value()) / 2.0f);
  }
}

void AnalogThresholdBinarySensor::set_sensor(sensor::Sensor *analog_sensor) {
  this->sensor_ = analog_sensor;

  this->sensor_->add_on_state_callback([this](float sensor_value) {
    // if there is an invalid sensor reading, ignore the change and keep the current state
    if (!std::isnan(sensor_value)) {
      this->publish_state(sensor_value >=
                          (this->state ? this->lower_threshold_.value() : this->upper_threshold_.value()));
    }
  });
}

void AnalogThresholdBinarySensor::dump_config() {
  LOG_BINARY_SENSOR("", "Analog Threshold Binary Sensor", this);
  LOG_SENSOR("  ", "Sensor", this->sensor_);
  ESP_LOGCONFIG(TAG,
                "  Upper threshold: %.11f\n"
                "  Lower threshold: %.11f",
                this->upper_threshold_.value(), this->lower_threshold_.value());
}

}  // namespace analog_threshold
}  // namespace esphome
