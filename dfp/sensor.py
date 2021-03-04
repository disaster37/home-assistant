import logging
import requests
from datetime import timedelta

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_MONITORED_VARIABLES,
    CONF_NAME,
    CONF_RESOURCE,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_VALUE_TEMPLATE,
    HTTP_OK,
)
from homeassistant.exceptions import TemplateError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

from .client import Client

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=1)

CONF_SENSORS = "sensors"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_MODULE = "module"
CONF_STATE = "state"

DEFAULT_NAME = "DFP sensor"

SENSOR_FUNCTION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_MODULE): cv.string,
        vol.Required(CONF_STATE): cv.string,
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
        vol.Optional(CONF_VALUE_TEMPLATE): cv.template
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_RESOURCE): cv.url,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_SENSORS): vol.Schema(
            {cv.string: SENSOR_FUNCTION_SCHEMA}
        ),
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the DFP sensors."""

    def make_renderer(value_template):
        """Create a renderer based on variable_template value."""
        if value_template is None:
            return lambda value: value

        value_template.hass = hass

        def _render(value):
            try:
                return value_template.async_render({"value": value}, parse_result=False)
            except TemplateError:
                _LOGGER.exception("Error parsing value")
                return value

        return _render

    dev = []

    sensors = config[CONF_SENSORS]
    for sensorName, sensor in sensors.items():
        renderer = make_renderer(sensor.get(CONF_VALUE_TEMPLATE))
        try:
            dfpSensor = DFPSensor(
                config[CONF_NAME],
                sensor.get(CONF_NAME),
                config[CONF_RESOURCE],
                config[CONF_USERNAME],
                config[CONF_PASSWORD],
                sensor.get(CONF_MODULE),
                sensor.get(CONF_STATE),
                sensor.get(CONF_UNIT_OF_MEASUREMENT),
                renderer
            )
        except requests.exceptions.MissingSchema:
            _LOGGER.error(
                "Missing resource or schema in configuration. Add http:// to your URL"
            )
            return False
        except requests.exceptions.ConnectionError:
            _LOGGER.error("No route to device at %s", config[CONF_RESOURCE])
            return False    


        dev.append(dfpSensor)

    add_entities(dev)



class DFPSensor(Entity):
    """Representation of an DFP switch."""

    def __init__(self, location,  name, url, username, password, module, state, unit_of_measurement=None, renderer=None):
        """Initialize the switch."""
        self._name = f"{location.title()} {name.title()}"
        self._module = module
        self._item = state
        self._url = url
        self._value = None
        self._client = Client(url, username, password)
        self._unit_of_measurement = unit_of_measurement
        self._renderer = renderer
        self._available = True

        self._client.addCache(self._module)

        # Check if we can get status
        try:
            if self._module == "dfp":
                self._value = self._client.dfpStatus(self._item)
        except requests.HTTPError as e:
            _LOGGER.error("Resource not found: %s", e)
        except KeyError:
            _LOGGER.error("No return_value received")
        except ValueError:
            _LOGGER.error("Response invalid")

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def available(self):
        """Could the device be accessed during the last update call."""
        return self._available
    
    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement
    

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._renderer(self._value)


    def update(self):
        """Get the latest data from aREST API and update the state."""
        try:
            if self._module == "dfp":
                self._value = self._client.dfpStatus(self._item)
        except requests.exceptions.ConnectionError:
            _LOGGER.warning("No route to device %s", self._url)
        except Exception as e:
            _LOGGER.error("Error when update %s", e)

        self._available = self._client.isAvailable()

