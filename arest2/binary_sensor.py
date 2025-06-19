"""Support for an exposed aREST RESTful API of a device."""
from __future__ import annotations

from datetime import timedelta
from http import HTTPStatus
import logging

import requests
import voluptuous as vol

from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES_SCHEMA,
    PLATFORM_SCHEMA,
    BinarySensorEntity,
)
from homeassistant.const import CONF_DEVICE_CLASS, CONF_NAME, CONF_PIN, CONF_RESOURCE
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

CONF_VARIABLE = "variable"

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_RESOURCE): cv.url,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_PIN): cv.string,
        vol.Optional(CONF_VARIABLE): cv.string,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the aREST binary sensor."""
    resource = config[CONF_RESOURCE]
    device_class = config.get(CONF_DEVICE_CLASS)
    isAvailable = True

    try:
        response = requests.get(resource, timeout=10).json()
    except requests.exceptions.MissingSchema:
        _LOGGER.error(
            "Missing resource or schema in configuration. Add http:// to your URL"
        )
        return
    except requests.exceptions.ConnectionError:
        _LOGGER.error("No route to device at %s", resource)
        isAvailable = False

    if CONF_PIN in config:
        pin = config[CONF_PIN]
        if pin is not None:
            add_entities(
                [
                    ArestBinarySensorPin(
                        resource,
                        config.get(CONF_NAME),
                        pin,
                        isAvailable,
                    )
                ],
                True,
            )

    if CONF_VARIABLE in config:
        variable = config[CONF_VARIABLE]
        if variable is not None:
            add_entities(
                [
                    ArestBinarySensorVariable(
                        resource,
                        config.get(CONF_NAME),
                        variable,
                        isAvailable,
                    )
                ],
                True,
            )


class ArestBinarySensorPin(BinarySensorEntity):
    """Implement an aREST binary sensor for a pin."""

    def __init__(self, resource, name, pin, available):

        if pin is None:
            _LOGGER.error("You must set the pin number for %s", resource)
            raise KeyError("You must set the pin number")

        """Initialize the aREST device."""
        self._resource = resource
        self._pin = pin
        self._attr_name = name
        self._attr_is_on = False
        self._attr_available = available

        if available is True:
            try:
                self.__set_pin_input()
            except requests.exceptions.ConnectionError:
                _LOGGER.warning("No route to device %s", self._resource)
                self._attr_available = False
            

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self) -> None:
        """Get the latest data from aREST API."""
        try:
            response = requests.get(f"{self._resource}/digital/{self._pin}", timeout=10)
            self._attr_is_on = bool(response.json()["return_value"])
            if self._attr_available is False:
                self.__set_pin_input()
        except requests.exceptions.ConnectionError:
            _LOGGER.error("No route to device '%s'", self._resource)
    
    def __set_pin_input(self) -> None:
        request = requests.get(f"{self._resource}/mode/{self._pin}/i", timeout=10)
        if request.status_code != HTTPStatus.OK:
            _LOGGER.error("Can't set mode")
            self._attr_available = False
        else:
            self._attr_available = True


class ArestBinarySensorVariable(BinarySensorEntity):
    """Implement an aREST binary sensor for a variable."""

    def __init__(self, resource, name, variable, available):
        if variable is None:
            _LOGGER.error("You must set the variable for %s", resource)
            raise KeyError("You must set the variable name")

        """Initialize the aREST device."""
        self._resource = resource
        self._variable = variable
        self._attr_name = name
        self._attr_is_on = False
        self._attr_available = available

        if available is True:
            self.__check_variable()


    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self) -> None:
        """Get the latest data from aREST API."""
        try:
            response = requests.get(f"{self._resource}/{self._variable}", timeout=10)
            self._attr_is_on = bool(response.json()[self._variable])
            if self._attr_available is False:
                self._attr_available = True
        except requests.exceptions.ConnectionError:
            _LOGGER.error("No route to device '%s'", self._resource)
            self._attr_available = False

    def __check_variable(self) -> None:
        request = requests.get(f"{self._resource}/{self._variable}", timeout=10)
        if request.status_code != HTTPStatus.OK:
            _LOGGER.error("Problem appear when get variable %s", self._resource)
        if request.json()[self._variable] is None:
            _LOGGER.error("Variable not found %s", self._resource)

