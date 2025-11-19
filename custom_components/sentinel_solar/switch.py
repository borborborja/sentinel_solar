from __future__ import annotations
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, DEFAULT_BASE_URL

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sentinel Solar switch."""
    async_add_entities([SentinelNightModeSwitch(entry)])

class SentinelNightModeSwitch(SwitchEntity, RestoreEntity):
    """Switch to enable/disable Night Mode (pause API at night)."""

    _attr_has_entity_name = True
    _attr_name = "Modo Noche"
    _attr_icon = "mdi:weather-night"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_night_mode"
        self._is_on = False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        data = self.hass.data[DOMAIN][self._entry.entry_id]
        asset_info = data.get("asset_info", {})
        asset_name = asset_info.get("name") or asset_info.get("assetName") or data.get("asset_general", "sentinel_solar")
        
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=asset_name,
            manufacturer="sentinel_solar (proyecto no oficial de Sentinel Solar)",
            model=asset_info.get("type") or asset_info.get("assetType") or "Asset",
            sw_version=asset_info.get("firmwareVersion") or asset_info.get("firmware_version"),
            configuration_url=f"{self._entry.data.get('base_url', DEFAULT_BASE_URL)}",
        )

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self._is_on = True
        self.hass.data[DOMAIN][self._entry.entry_id]["night_mode"] = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self._is_on = False
        self.hass.data[DOMAIN][self._entry.entry_id]["night_mode"] = False
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore state when added to HA."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state:
            self._is_on = state.state == "on"
        
        # Initialize the value in hass.data
        self.hass.data[DOMAIN][self._entry.entry_id]["night_mode"] = self._is_on
