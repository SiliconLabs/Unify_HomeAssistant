"""
Copyright 2022 Silicon Laboratories, www.silabs.com

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

# Standard packages
import logging
import json
from typing import final

# HA Packages
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)

# MQTT
from homeassistant.components import mqtt
from homeassistant.components.mqtt.models import ReceiveMessage

# Integration components
from .base_unify_entity import BaseUnifyEntity, setup_device_data_structure
from .const import DOMAIN, DEVICES

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
        hass: HomeAssistant,
        config,
        async_add_entities: AddEntitiesCallback,
        discovery_info=None):
    unid = discovery_info["unid"]
    endpoint = discovery_info["endpoint"]
    setup_device_data_structure(unid, endpoint, hass.data[DOMAIN][DEVICES])
    hass.data[DOMAIN][DEVICES][unid][endpoint]["light"] = UnifyLight(
        hass, unid, endpoint)
    device = hass.data[DOMAIN][DEVICES][unid][endpoint]["light"]
    async_add_entities([device])


class UnifyLight(LightEntity, BaseUnifyEntity):
    """Representation of a Unify Light (dimmer or colorcontrol)"""

    def __init__(self, hass, unid, endpoint):
        BaseUnifyEntity.__init__(self, hass, unid, endpoint)
        self._supported_color_modes = set()
        self._attr_hs_color = None  # tuple()
        self._effect_list = {}
        self._effect = None
        self._is_on = False
        self._supported_commands = {}

    @final
    async def async_added_to_hass(self):
        """Start the Switch entity"""
        await self.async_subscribe(f"ucl/by-unid/{self._unid}/{self._ep}/ColorControl/Attributes/CurrentHue/Reported", self._on_message_change_hue)
        await self.async_subscribe(f"ucl/by-unid/{self._unid}/{self._ep}/ColorControl/Attributes/CurrentSaturation/Reported", self._on_message_change_saturation)
        await self.async_subscribe(f"ucl/by-unid/{self._unid}/{self._ep}/ColorControl/SupportedCommands", self._on_message_supported_commands_color_control)
        await self.async_subscribe(f"ucl/by-unid/{self._unid}/{self._ep}/Level/Attributes/CurrentLevel/Reported", self._on_message_change_level)
        await self.async_subscribe(f"ucl/by-unid/{self._unid}/{self._ep}/Level/SupportedCommands", self._on_message_supported_commands_level)
        await self.async_subscribe(f"ucl/by-unid/{self._unid}/{self._ep}/OnOff/Attributes/OnOff/Reported", self._on_message_on_off)
        await self.async_subscribe(f"ucl/by-unid/{self._unid}/{self._ep}/OnOff/SupportedCommands", self._on_message_supported_commands_on_off)

        return self

    @ property
    def unique_id(self):
        """Unique Id."""
        entity_unid = f"light_{self._unid}_{self._ep}"
        entity_unid = entity_unid.replace("-", "_")
        return entity_unid

    @property
    def hs_color(self):
        """Return the hs color value."""
        return self._attr_hs_color

    @property
    def effect_list(self):
        """Return the list of supported effects."""
        return self._effect_list

    @property
    def effect(self):
        """Return the current effect."""
        return self._effect

    @property
    def color_mode(self):
        """Return the color mode of the light."""
        if ColorMode.HS in self.supported_color_modes:
            return ColorMode.HS
        elif ColorMode.BRIGHTNESS in self.supported_color_modes:
            return ColorMode.BRIGHTNESS
        elif ColorMode.ONOFF in self.supported_color_modes:
            return ColorMode.ONOFF
        return ColorMode.UNKNOWN

    @property
    def supported_color_modes(self):
        """Flag supported color modes."""
        return self._supported_color_modes

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._attr_brightness

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._is_on

    async def _on_message_change_hue(self, message: ReceiveMessage):
        try:
            _LOGGER.debug("UnifyLight: Hue state changed for %s to %s with payload %s",
                          self.name, message.topic, message.payload)
            msg = json.loads(message.payload)
            #new_hue = msg["value"]
            #hue, sat = self._attr_hs_color
            #self._attr_hs_color = (new_hue, sat)
        except json.decoder.JSONDecodeError:
            return
        except ValueError:
            return

    async def _on_message_change_saturation(self, message: ReceiveMessage):
        _LOGGER.debug("UnifyLight: Saturation state changed for %s to %s with payload %s ",
                      self.name, message.topic, message.payload)
        try:
            msg = json.loads(message.payload)
            #new_sat = msg["value"]
            #hue, sat = self._attr_hs_color
            #self._attr_hs_color = (hue, new_sat)
        except json.decoder.JSONDecodeError:
            return
        except ValueError:
            return

    async def _on_message_change_level(self, message: ReceiveMessage):
        _LOGGER.debug("UnifyLight: Level state changed for %s to %s ",
                      self.name, message.topic)
        try:
            msg = json.loads(message.payload)
            # Convert brightness to 0-255, in Unify it's 0-100
            self._attr_brightness = round(msg["value"] * 2.55)
        except json.decoder.JSONDecodeError:
            return
        except ValueError:
            return

    async def _on_message_supported_commands_color_control(self, message: ReceiveMessage):
        self._supported_commands["colorcontrol"] = message.payload
        if "MoveToHueAndSaturation" in self._supported_commands["colorcontrol"]:
            _LOGGER.debug("UnifyLight: ColorControl %s supports MoveToHueAndSaturation", self._supported_commands)
            self._supported_color_modes.add(ColorMode.HS)

    async def _on_message_supported_commands_level(self, message: ReceiveMessage):
        self._supported_commands["level"] = message.payload
        self._supported_color_modes.add(ColorMode.BRIGHTNESS)

    async def _on_message_supported_commands_on_off(self, message: ReceiveMessage):
        self._supported_commands["onoff"] = message.payload

    async def _on_message_on_off(self, message: ReceiveMessage):
        _LOGGER.debug("UnifyLight: state changed for %s to %s ",
                      self.name, message.topic)
        try:
            msg = json.loads(message.payload)
        except json.decoder.JSONDecodeError:
            return

        if msg["value"] is True:
            _LOGGER.debug("UnifyLight: state detected True ")
            self._is_on = True
        else:
            _LOGGER.debug("UnifyLight: state detected False ")
            self._is_on = False

        try:
            self.async_schedule_update_ha_state(False)
        except Exception as err:
            _LOGGER.error("UnifyLight: Exception on State Update: %s", err)

    async def async_turn_on(self, **kwargs):
        if hs := kwargs.get(ATTR_HS_COLOR):
            self._attr_hs_color = hs
            if "MoveToHueAndSaturation" in self._supported_commands["colorcontrol"]:
                topic = f"ucl/by-unid/{self._unid}/{self._ep}/ColorControl/Commands/MoveToHueAndSaturation"

                hue, sat = self._attr_hs_color
                hue = (1 - (360 - hue) / 360) * 255
                sat = sat / 100 * 255
                payload = {
                    "Hue": int(hue),
                    "Saturation": int(sat),
                    "TransitionTime": 0,
                    "OptionsMask": {
                        "ExecuteIfOff": False
                    },
                    "OptionsOverride": {
                        "ExecuteIfOf": False
                    }
                }

                _LOGGER.debug("UnifyLight: MoveToHueAndSaturation %s %s", topic, payload)
                await self.async_send_message(topic, json.dumps(payload), False)
                return
        if brightness := kwargs.get(ATTR_BRIGHTNESS):
            self._attr_brightness = brightness
            if "MoveToLevelWithOnOff" in self._supported_commands["level"]:
                topic = f"ucl/by-unid/{self._unid}/{self._ep}/Level/Commands/MoveToLevelWithOnOff"
                payload = {
                    "Level": round((self._attr_brightness * 100) / 255),
                    "TransitionTime": 0,
                    "OptionsMask": {
                        "ExecuteIfOff": False,
                        "CoupleColorTempToLevel": False
                    },
                    "OptionsOverride": {
                        "ExecuteIfOff": False,
                        "CoupleColorTempToLevel": False
                    }
                }
                _LOGGER.debug("UnifyLight: %s", topic)
                await self.async_send_message(topic, json.dumps(payload), False)
                return
        if "On" in self._supported_commands["onoff"]:
            topic = f"ucl/by-unid/{self._unid}/{self._ep}/OnOff/Commands/On"
            payload = "{}"
            _LOGGER.debug("TurnOn %s", topic)
            await self.async_send_message(topic, payload, False)
        else:
            _LOGGER.warning("UnifyLight: Unsupported ON command")
            return

    async def async_turn_off(self, **kwargs):
        if not "Off" in self._supported_commands["onoff"]:
            _LOGGER.warning("UnifyLight: Unsupported OFF command")
            return

        off_topic = f"ucl/by-unid/{self._unid}/{self._ep}/OnOff/Commands/Off"
        off_payload = "{}"
        _LOGGER.debug("UnifyLight: TurnOff %s", off_topic)
        await self.async_send_message(off_topic, off_payload, False)

    async def async_send_message(self, topic, payload, retain):
        await mqtt.async_publish(self.hass, topic, payload, 0, retain)
