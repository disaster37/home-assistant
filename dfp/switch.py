import logging
import requests
import voluptuous as vol

from homeassistant.components.switch import PLATFORM_SCHEMA, SwitchEntity
from homeassistant.const import CONF_NAME, CONF_RESOURCE
import homeassistant.helpers.config_validation as cv

from .client import Client

_LOGGER = logging.getLogger(__name__)

CONF_ACTIONS = "actions"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_MODULE = "module"
CONF_TURN_ON_ACTION = "turn_on_action"
CONF_TURN_OFF_ACTION = "turn_off_action"
CONF_STATE = "state"

DEFAULT_NAME = "DFP switch"

ACTION_FUNCTION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_MODULE): cv.string,
        vol.Required(CONF_TURN_ON_ACTION): cv.string,
        vol.Required(CONF_TURN_OFF_ACTION): cv.string,
        vol.Required(CONF_STATE): cv.string,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_RESOURCE): cv.url,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_ACTIONS): vol.Schema(
            {cv.string: ACTION_FUNCTION_SCHEMA}
        ),
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the DFP switches."""

    dev = []

    actions = config[CONF_ACTIONS]
    for actionName, action in actions.items():
        try:
            dfpSwitch = DFPSwitchAction(
                config[CONF_NAME],
                action.get(CONF_NAME),
                config[CONF_RESOURCE],
                config[CONF_USERNAME],
                config[CONF_PASSWORD],
                action.get(CONF_MODULE),
                action.get(CONF_TURN_ON_ACTION),
                action.get(CONF_TURN_OFF_ACTION),
                action.get(CONF_STATE)
            )
        except requests.exceptions.MissingSchema:
            _LOGGER.error(
                "Missing resource or schema in configuration. Add http:// to your URL"
            )
            return False
        except requests.exceptions.ConnectionError:
            _LOGGER.error("No route to device at %s", config[CONF_RESOURCE])
        
        dev.append(dfpSwitch)

    add_entities(dev)



class DFPSwitchAction(SwitchEntity):
    """Representation of an DFP switch."""

    def __init__(self, location,  name, url, username, password, module, action_turn_on, action_turn_off, state):
        """Initialize the switch."""
        self._name = f"{location.title()} {name.title()}"
        self._module = module
        self._url = url
        self._action_turn_on = action_turn_on
        self._action_turn_off = action_turn_off
        self._item = state
        self._state = None
        self._available = True
        self._client = Client(url, username, password)


        # Check if we can get status
        if self._item == "none":
            return
        try:
            if self._module == "dfp":
                self._state = self._client.dfpStatus(self._item)
            elif self._module == "tfp":
                self._state = self._client.tfpStatus(self._item)
            else:
                raise KeyError("Module must be dfp or tfp")
        except requests.exceptions.ConnectionError:
            _LOGGER.warning("No route to device %s", self._url)
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
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def available(self):
        """Could the device be accessed during the last update call."""
        return self._available


    def turn_on(self, **kwargs):
        """Turn the device on."""
        try:
            if self._module == "dfp":
                self._client.dfpAction(self._action_turn_on)
            elif self._module == "tfp":
                self._client.tfpAction(self._action_turn_on)
        except Exception as e:
            _LOGGER.error("Can't turn on function %s/%s at %s: %s", self._module, self._action_turn_off, self._resource, e)

    def turn_off(self, **kwargs):
        """Turn the device off."""
        try:
            if self._action_turn_off == "none":
                return
            if self._module == "dfp":
                self._client.dfpAction(self._action_turn_off)
            elif self._module == "tfp":
                self._client.tfpAction(self._action_turn_off)
        except Exception as e:
                _LOGGER.error("Can't turn off function %s/%s at %s: %s", self._module, self._action_turn_off, self._resource, e)

    def update(self):
        """Get the latest data from aREST API and update the state."""
        if self._item == "none":
            return
        try:
            if self._module == "dfp":
                self._state = self._client.dfpStatus(self._item)
            elif self._module == "tfp":
                self._state = self._client.tfpStatus(self._item)
            
            self._available = True
        except requests.exceptions.ConnectionError:
            _LOGGER.warning("No route to device %s", self._url)
            self._available = False
        except Exception as e:
            _LOGGER.error("Error when update %s", e)
            self._available = False
