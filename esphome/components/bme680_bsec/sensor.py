import esphome.codegen as cg
from esphome.components import sensor
import esphome.config_validation as cv
from esphome.const import (
    CONF_GAS_RESISTANCE,
    CONF_HUMIDITY,
    CONF_IAQ_ACCURACY,
    CONF_PRESSURE,
    CONF_SAMPLE_RATE,
    CONF_TEMPERATURE,
    DEVICE_CLASS_ATMOSPHERIC_PRESSURE,
    DEVICE_CLASS_CARBON_DIOXIDE,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_VOLATILE_ORGANIC_COMPOUNDS_PARTS,
    ICON_GAS_CYLINDER,
    ICON_GAUGE,
    ICON_THERMOMETER,
    ICON_WATER_PERCENT,
    STATE_CLASS_MEASUREMENT,
    UNIT_CELSIUS,
    UNIT_HECTOPASCAL,
    UNIT_OHM,
    UNIT_PARTS_PER_MILLION,
    UNIT_PERCENT,
)

from . import CONF_BME680_BSEC_ID, SAMPLE_RATE_OPTIONS, BME680BSECComponent

DEPENDENCIES = ["bme680_bsec"]

CONF_BREATH_VOC_EQUIVALENT = "breath_voc_equivalent"
CONF_CO2_EQUIVALENT = "co2_equivalent"
CONF_IAQ = "iaq"
ICON_ACCURACY = "mdi:checkbox-marked-circle-outline"
UNIT_IAQ = "IAQ"

TYPES = [
    CONF_TEMPERATURE,
    CONF_PRESSURE,
    CONF_HUMIDITY,
    CONF_GAS_RESISTANCE,
    CONF_IAQ,
    CONF_IAQ_ACCURACY,
    CONF_CO2_EQUIVALENT,
    CONF_BREATH_VOC_EQUIVALENT,
]

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_BME680_BSEC_ID): cv.use_id(BME680BSECComponent),
        cv.Optional(CONF_TEMPERATURE): sensor.sensor_schema(
            unit_of_measurement=UNIT_CELSIUS,
            icon=ICON_THERMOMETER,
            accuracy_decimals=1,
            device_class=DEVICE_CLASS_TEMPERATURE,
            state_class=STATE_CLASS_MEASUREMENT,
        ).extend(
            {cv.Optional(CONF_SAMPLE_RATE): cv.enum(SAMPLE_RATE_OPTIONS, upper=True)}
        ),
        cv.Optional(CONF_PRESSURE): sensor.sensor_schema(
            unit_of_measurement=UNIT_HECTOPASCAL,
            accuracy_decimals=1,
            device_class=DEVICE_CLASS_ATMOSPHERIC_PRESSURE,
            state_class=STATE_CLASS_MEASUREMENT,
        ).extend(
            {cv.Optional(CONF_SAMPLE_RATE): cv.enum(SAMPLE_RATE_OPTIONS, upper=True)}
        ),
        cv.Optional(CONF_HUMIDITY): sensor.sensor_schema(
            unit_of_measurement=UNIT_PERCENT,
            icon=ICON_WATER_PERCENT,
            accuracy_decimals=1,
            device_class=DEVICE_CLASS_HUMIDITY,
            state_class=STATE_CLASS_MEASUREMENT,
        ).extend(
            {cv.Optional(CONF_SAMPLE_RATE): cv.enum(SAMPLE_RATE_OPTIONS, upper=True)}
        ),
        cv.Optional(CONF_GAS_RESISTANCE): sensor.sensor_schema(
            unit_of_measurement=UNIT_OHM,
            icon=ICON_GAS_CYLINDER,
            accuracy_decimals=0,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_IAQ): sensor.sensor_schema(
            unit_of_measurement=UNIT_IAQ,
            icon=ICON_GAUGE,
            accuracy_decimals=0,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_IAQ_ACCURACY): sensor.sensor_schema(
            icon=ICON_ACCURACY,
            accuracy_decimals=0,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_CO2_EQUIVALENT): sensor.sensor_schema(
            unit_of_measurement=UNIT_PARTS_PER_MILLION,
            accuracy_decimals=1,
            device_class=DEVICE_CLASS_CARBON_DIOXIDE,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_BREATH_VOC_EQUIVALENT): sensor.sensor_schema(
            unit_of_measurement=UNIT_PARTS_PER_MILLION,
            accuracy_decimals=1,
            device_class=DEVICE_CLASS_VOLATILE_ORGANIC_COMPOUNDS_PARTS,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
    }
)


async def setup_conf(config, key, hub):
    if sensor_config := config.get(key):
        sens = await sensor.new_sensor(sensor_config)
        cg.add(getattr(hub, f"set_{key}_sensor")(sens))
        if CONF_SAMPLE_RATE in sensor_config:
            cg.add(
                getattr(hub, f"set_{key}_sample_rate")(sensor_config[CONF_SAMPLE_RATE])
            )


async def to_code(config):
    hub = await cg.get_variable(config[CONF_BME680_BSEC_ID])
    for key in TYPES:
        await setup_conf(config, key, hub)
