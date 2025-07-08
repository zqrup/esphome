#pragma once

#ifdef USE_ESP_IDF

#include "audio_pipeline.h"

#include "esphome/components/audio/audio.h"

#include "esphome/components/media_player/media_player.h"
#include "esphome/components/speaker/speaker.h"

#include "esphome/core/automation.h"
#include "esphome/core/component.h"
#include "esphome/core/preferences.h"

#include <deque>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>

namespace esphome {
namespace speaker {

struct MediaCallCommand {
  optional<media_player::MediaPlayerCommand> command;
  optional<float> volume;
  optional<bool> announce;
  optional<std::string *> url;  // Must be manually deleted after receiving this struct from a queue
  optional<audio::AudioFile *> file;
  optional<bool> enqueue;
};

struct PlaylistItem {
  optional<std::string> url;
  optional<audio::AudioFile *> file;
};

struct VolumeRestoreState {
  float volume;
  bool is_muted;
};

class SpeakerMediaPlayer : public Component, public media_player::MediaPlayer {
 public:
  float get_setup_priority() const override { return esphome::setup_priority::PROCESSOR; }
  void setup() override;
  void loop() override;

  // MediaPlayer implementations
  media_player::MediaPlayerTraits get_traits() override;
  bool is_muted() const override { return this->is_muted_; }

  void set_buffer_size(size_t buffer_size) { this->buffer_size_ = buffer_size; }
  void set_task_stack_in_psram(bool task_stack_in_psram) { this->task_stack_in_psram_ = task_stack_in_psram; }

  // Percentage to increase or decrease the volume for volume up or volume down commands
  void set_volume_increment(float volume_increment) { this->volume_increment_ = volume_increment; }

  // Volume used initially on first boot when no volume had been previously saved
  void set_volume_initial(float volume_initial) { this->volume_initial_ = volume_initial; }

  void set_volume_max(float volume_max) { this->volume_max_ = volume_max; }
  void set_volume_min(float volume_min) { this->volume_min_ = volume_min; }

  void set_announcement_speaker(Speaker *announcement_speaker) { this->announcement_speaker_ = announcement_speaker; }
  void set_announcement_format(const media_player::MediaPlayerSupportedFormat &announcement_format) {
    this->announcement_format_ = announcement_format;
  }
  void set_media_speaker(Speaker *media_speaker) { this->media_speaker_ = media_speaker; }
  void set_media_format(const media_player::MediaPlayerSupportedFormat &media_format) {
    this->media_format_ = media_format;
  }

  Trigger<> *get_mute_trigger() const { return this->mute_trigger_; }
  Trigger<> *get_unmute_trigger() const { return this->unmute_trigger_; }
  Trigger<float> *get_volume_trigger() const { return this->volume_trigger_; }

  void play_file(audio::AudioFile *media_file, bool announcement, bool enqueue);

  void set_playlist_delay_ms(AudioPipelineType pipeline_type, uint32_t delay_ms);

 protected:
  // Receives commands from HA or from the voice assistant component
  // Sends commands to the media_control_commanda_queue_
  void control(const media_player::MediaPlayerCall &call) override;

  /// @brief Updates this->volume and saves volume/mute state to flash for restortation if publish is true.
  void set_volume_(float volume, bool publish = true);

  /// @brief Sets the mute state. Restores previous volume if unmuting. Always saves volume/mute state to flash for
  /// restoration.
  /// @param mute_state If true, audio will be muted. If false, audio will be unmuted
  void set_mute_state_(bool mute_state);

  /// @brief Saves the current volume and mute state to the flash for restoration.
  void save_volume_restore_state_();

  /// Returns true if the media player has only the announcement pipeline defined, false if both the announcement and
  /// media pipelines are defined.
  inline bool single_pipeline_() { return (this->media_speaker_ == nullptr); }

  // Processes commands from media_control_command_queue_.
  void watch_media_commands_();

  std::unique_ptr<AudioPipeline> announcement_pipeline_;
  std::unique_ptr<AudioPipeline> media_pipeline_;
  Speaker *media_speaker_{nullptr};
  Speaker *announcement_speaker_{nullptr};

  optional<media_player::MediaPlayerSupportedFormat> media_format_;
  AudioPipelineState media_pipeline_state_{AudioPipelineState::STOPPED};
  bool media_repeat_one_{false};
  uint32_t media_playlist_delay_ms_{0};

  optional<media_player::MediaPlayerSupportedFormat> announcement_format_;
  AudioPipelineState announcement_pipeline_state_{AudioPipelineState::STOPPED};
  bool announcement_repeat_one_{false};
  uint32_t announcement_playlist_delay_ms_{0};

  QueueHandle_t media_control_command_queue_;

  std::deque<PlaylistItem> announcement_playlist_;
  std::deque<PlaylistItem> media_playlist_;

  size_t buffer_size_;

  bool task_stack_in_psram_;

  bool is_paused_{false};
  bool is_muted_{false};

  // The amount to change the volume on volume up/down commands
  float volume_increment_;

  // The initial volume used by Setup when no previous volume was saved
  float volume_initial_;

  float volume_max_;
  float volume_min_;

  // Used to save volume/mute state for restoration on reboot
  ESPPreferenceObject pref_;

  Trigger<> *mute_trigger_ = new Trigger<>();
  Trigger<> *unmute_trigger_ = new Trigger<>();
  Trigger<float> *volume_trigger_ = new Trigger<float>();
};

}  // namespace speaker
}  // namespace esphome

#endif
