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

# Integration components
from .base_unify_entity import BaseUnifyEntity, setup_device_data_structure
from .const import DOMAIN, DEVICES

# HA packages
from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components import mqtt
from homeassistant.components.mqtt.models import ReceiveMessage


_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
):
    unid = discovery_info["unid"]
    endpoint = discovery_info["endpoint"]
    setup_device_data_structure(unid, endpoint, hass.data[DOMAIN][DEVICES])
    hass.data[DOMAIN][DEVICES][unid][endpoint]["lock"] = UnifyLock(hass, unid, endpoint)
    device = hass.data[DOMAIN][DEVICES][unid][endpoint]["lock"]
    async_add_entities([device])


class UnifyLock(LockEntity, BaseUnifyEntity):
    """Representation of a Unify Lock."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, hass, unid, endpoint):
        self._attr_is_locked = False
        BaseUnifyEntity.__init__(self, hass, unid, endpoint)

    @final
    async def async_added_to_hass(self) -> None:
        """Start the Lock entity"""
        await self.async_subscribe(
            f"ucl/by-unid/{self._unid}/{self._ep}/DoorLock/Attributes/LockState/Reported",
            self._on_message_state,
        )
        await self.async_subscribe(
            f"ucl/by-unid/{self._unid}/{self._ep}/DoorLock/SupportedCommands",
            self._on_message_supported_commands,
        )

    @final
    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        for _unsubscribe_cb in self._async_mqtt_remove:
            _unsubscribe_cb()

    async def _on_message_supported_commands(self, message: ReceiveMessage):
        self.supported_commands = message.payload

    async def _on_message_state(self, message: ReceiveMessage):
        _LOGGER.debug(
            "UnifyLock: state changed for %s to %s ", self.name, message.topic
        )
        try:
            msg = json.loads(message.payload)
        except json.decoder.JSONDecodeError:
            return

        if msg["value"] == "Locked":
            _LOGGER.debug("UnifyLock: state detected True ")
            self._attr_is_locked = True
        elif msg["value"] == "Unlocked":
            _LOGGER.debug("UnifyLock: state detected False ")
            self._attr_is_locked = False

        try:
            self.async_schedule_update_ha_state(False)
        except Exception as err:
            _LOGGER.error("UnifyLock: Exception on State Update: %s", err)

    @property
    def unique_id(self):
        """Force update."""
        entity_unid = f"lock_{self._unid}_{self._ep}"
        entity_unid = entity_unid.replace("-", "_")
        return entity_unid

    @property
    def is_locked(self):
        """Return true if door is locked"""
        return self._attr_is_locked

    async def async_lock(self, **kwargs):
        if not "LockDoor" in self.supported_commands:
            _LOGGER.warning("UnifyLock: Unsupported LockDoor command")
            return

        lock_topic = f"ucl/by-unid/{self._unid}/{self._ep}/DoorLock/Commands/LockDoor"
        lock_payload = '{"PINOrRFIDCode":""}'
        _LOGGER.debug("UnifyLock: LookDoor %s %s", lock_topic, lock_payload)
        await self.async_send_message(lock_topic, lock_payload, False)

    async def async_unlock(self, **kwargs):
        if not "UnlockDoor" in self.supported_commands:
            _LOGGER.warning("UnifyLock: Unsupported UnlockDoor command")
            return

        unlock_topic = f"ucl/by-unid/{self._unid}/{self._ep}/DoorLock/Commands/UnlockDoor"
        unlock_payload = '{"PINOrRFIDCode":""}'
        _LOGGER.debug("UnifyLock: UnlookDoor %s %s", unlock_topic, unlock_payload)
        await self.async_send_message(unlock_topic, unlock_payload, False)

    async def async_send_message(self, topic, payload, retain):
        await mqtt.async_publish(self.hass, topic, payload, 0, retain)