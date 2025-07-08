from esphome import automation
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import (
    CONF_ENTITY_CATEGORY,
    CONF_ICON,
    CONF_ID,
    CONF_ON_IDLE,
    CONF_ON_STATE,
    CONF_TRIGGER_ID,
    CONF_VOLUME,
)
from esphome.core import CORE
from esphome.coroutine import coroutine_with_priority
from esphome.cpp_generator import MockObjClass
from esphome.cpp_helpers import setup_entity

CODEOWNERS = ["@jesserockz"]

IS_PLATFORM_COMPONENT = True

media_player_ns = cg.esphome_ns.namespace("media_player")

MediaPlayer = media_player_ns.class_("MediaPlayer")

MediaPlayerSupportedFormat = media_player_ns.struct("MediaPlayerSupportedFormat")

MediaPlayerFormatPurpose = media_player_ns.enum(
    "MediaPlayerFormatPurpose", is_class=True
)
MEDIA_PLAYER_FORMAT_PURPOSE_ENUM = {
    "default": MediaPlayerFormatPurpose.PURPOSE_DEFAULT,
    "announcement": MediaPlayerFormatPurpose.PURPOSE_ANNOUNCEMENT,
}


PlayAction = media_player_ns.class_(
    "PlayAction", automation.Action, cg.Parented.template(MediaPlayer)
)
PlayMediaAction = media_player_ns.class_(
    "PlayMediaAction", automation.Action, cg.Parented.template(MediaPlayer)
)
ToggleAction = media_player_ns.class_(
    "ToggleAction", automation.Action, cg.Parented.template(MediaPlayer)
)
PauseAction = media_player_ns.class_(
    "PauseAction", automation.Action, cg.Parented.template(MediaPlayer)
)
StopAction = media_player_ns.class_(
    "StopAction", automation.Action, cg.Parented.template(MediaPlayer)
)
VolumeUpAction = media_player_ns.class_(
    "VolumeUpAction", automation.Action, cg.Parented.template(MediaPlayer)
)
VolumeDownAction = media_player_ns.class_(
    "VolumeDownAction", automation.Action, cg.Parented.template(MediaPlayer)
)
VolumeSetAction = media_player_ns.class_(
    "VolumeSetAction", automation.Action, cg.Parented.template(MediaPlayer)
)

CONF_ANNOUNCEMENT = "announcement"
CONF_ON_PLAY = "on_play"
CONF_ON_PAUSE = "on_pause"
CONF_ON_ANNOUNCEMENT = "on_announcement"
CONF_MEDIA_URL = "media_url"

StateTrigger = media_player_ns.class_("StateTrigger", automation.Trigger.template())
IdleTrigger = media_player_ns.class_("IdleTrigger", automation.Trigger.template())
PlayTrigger = media_player_ns.class_("PlayTrigger", automation.Trigger.template())
PauseTrigger = media_player_ns.class_("PauseTrigger", automation.Trigger.template())
AnnoucementTrigger = media_player_ns.class_(
    "AnnouncementTrigger", automation.Trigger.template()
)
IsIdleCondition = media_player_ns.class_("IsIdleCondition", automation.Condition)
IsPausedCondition = media_player_ns.class_("IsPausedCondition", automation.Condition)
IsPlayingCondition = media_player_ns.class_("IsPlayingCondition", automation.Condition)
IsAnnouncingCondition = media_player_ns.class_(
    "IsAnnouncingCondition", automation.Condition
)


async def setup_media_player_core_(var, config):
    await setup_entity(var, config)
    for conf in config.get(CONF_ON_STATE, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)
    for conf in config.get(CONF_ON_IDLE, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)
    for conf in config.get(CONF_ON_PLAY, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)
    for conf in config.get(CONF_ON_PAUSE, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)
    for conf in config.get(CONF_ON_ANNOUNCEMENT, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)


async def register_media_player(var, config):
    if not CORE.has_id(config[CONF_ID]):
        var = cg.Pvariable(config[CONF_ID], var)
    cg.add(cg.App.register_media_player(var))
    CORE.register_platform_component("media_player", var)
    await setup_media_player_core_(var, config)


async def new_media_player(config, *args):
    var = cg.new_Pvariable(config[CONF_ID], *args)
    await register_media_player(var, config)
    return var


_MEDIA_PLAYER_SCHEMA = cv.ENTITY_BASE_SCHEMA.extend(
    {
        cv.Optional(CONF_ON_STATE): automation.validate_automation(
            {
                cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(StateTrigger),
            }
        ),
        cv.Optional(CONF_ON_IDLE): automation.validate_automation(
            {
                cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(IdleTrigger),
            }
        ),
        cv.Optional(CONF_ON_PLAY): automation.validate_automation(
            {
                cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(PlayTrigger),
            }
        ),
        cv.Optional(CONF_ON_PAUSE): automation.validate_automation(
            {
                cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(PauseTrigger),
            }
        ),
        cv.Optional(CONF_ON_ANNOUNCEMENT): automation.validate_automation(
            {
                cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(AnnoucementTrigger),
            }
        ),
    }
)


def media_player_schema(
    class_: MockObjClass,
    *,
    entity_category: str = cv.UNDEFINED,
    icon: str = cv.UNDEFINED,
) -> cv.Schema:
    schema = {cv.GenerateID(CONF_ID): cv.declare_id(class_)}

    for key, default, validator in [
        (CONF_ENTITY_CATEGORY, entity_category, cv.entity_category),
        (CONF_ICON, icon, cv.icon),
    ]:
        if default is not cv.UNDEFINED:
            schema[cv.Optional(key, default=default)] = validator

    return _MEDIA_PLAYER_SCHEMA.extend(schema)


# Remove before 2025.11.0
MEDIA_PLAYER_SCHEMA = media_player_schema(MediaPlayer)
MEDIA_PLAYER_SCHEMA.add_extra(cv.deprecated_schema_constant("media_player"))


MEDIA_PLAYER_ACTION_SCHEMA = automation.maybe_simple_id(
    cv.Schema(
        {
            cv.GenerateID(): cv.use_id(MediaPlayer),
            cv.Optional(CONF_ANNOUNCEMENT, default=False): cv.templatable(cv.boolean),
        }
    )
)

MEDIA_PLAYER_CONDITION_SCHEMA = automation.maybe_simple_id(
    {cv.GenerateID(): cv.use_id(MediaPlayer)}
)


@automation.register_action(
    "media_player.play_media",
    PlayMediaAction,
    cv.maybe_simple_value(
        {
            cv.GenerateID(): cv.use_id(MediaPlayer),
            cv.Required(CONF_MEDIA_URL): cv.templatable(cv.url),
            cv.Optional(CONF_ANNOUNCEMENT, default=False): cv.templatable(cv.boolean),
        },
        key=CONF_MEDIA_URL,
    ),
)
async def media_player_play_media_action(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    media_url = await cg.templatable(config[CONF_MEDIA_URL], args, cg.std_string)
    announcement = await cg.templatable(config[CONF_ANNOUNCEMENT], args, cg.bool_)
    cg.add(var.set_media_url(media_url))
    cg.add(var.set_announcement(announcement))
    return var


@automation.register_action("media_player.play", PlayAction, MEDIA_PLAYER_ACTION_SCHEMA)
@automation.register_action(
    "media_player.toggle", ToggleAction, MEDIA_PLAYER_ACTION_SCHEMA
)
@automation.register_action(
    "media_player.pause", PauseAction, MEDIA_PLAYER_ACTION_SCHEMA
)
@automation.register_action("media_player.stop", StopAction, MEDIA_PLAYER_ACTION_SCHEMA)
@automation.register_action(
    "media_player.volume_up", VolumeUpAction, MEDIA_PLAYER_ACTION_SCHEMA
)
@automation.register_action(
    "media_player.volume_down", VolumeDownAction, MEDIA_PLAYER_ACTION_SCHEMA
)
async def media_player_action(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    announcement = await cg.templatable(config[CONF_ANNOUNCEMENT], args, cg.bool_)
    cg.add(var.set_announcement(announcement))
    return var


@automation.register_condition(
    "media_player.is_idle", IsIdleCondition, MEDIA_PLAYER_CONDITION_SCHEMA
)
@automation.register_condition(
    "media_player.is_paused", IsPausedCondition, MEDIA_PLAYER_CONDITION_SCHEMA
)
@automation.register_condition(
    "media_player.is_playing", IsPlayingCondition, MEDIA_PLAYER_CONDITION_SCHEMA
)
@automation.register_condition(
    "media_player.is_announcing", IsAnnouncingCondition, MEDIA_PLAYER_CONDITION_SCHEMA
)
async def media_player_condition(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    return var


@automation.register_action(
    "media_player.volume_set",
    VolumeSetAction,
    cv.maybe_simple_value(
        {
            cv.GenerateID(): cv.use_id(MediaPlayer),
            cv.Required(CONF_VOLUME): cv.templatable(cv.percentage),
        },
        key=CONF_VOLUME,
    ),
)
async def media_player_volume_set_action(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    volume = await cg.templatable(config[CONF_VOLUME], args, float)
    cg.add(var.set_volume(volume))
    return var


@coroutine_with_priority(100.0)
async def to_code(config):
    cg.add_global(media_player_ns.using)
    cg.add_define("USE_MEDIA_PLAYER")
