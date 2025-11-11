from __future__ import annotations
from typing import Any, Optional

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN, CONF_SHARE_FACTOR, DEFAULT_SHARE_FACTOR,
    CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES, DEFAULT_BASE_URL
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Configurar los controles numéricos de la integración."""
    data = hass.data[DOMAIN][entry.entry_id]

    # Controles de configuración
    share_factor_number = ShareFactorNumber(entry, data)
    update_interval_number = UpdateIntervalNumber(entry, data)

    async_add_entities([share_factor_number, update_interval_number])


class ShareFactorNumber(NumberEntity):
    """Control para ajustar el factor de participación."""
    
    _attr_has_entity_name = True
    _attr_icon = "mdi:percent"
    _attr_native_min_value = 0.0
    _attr_native_max_value = 1.0
    _attr_native_step = 0.001
    _attr_mode = NumberMode.BOX

    def __init__(self, entry: ConfigEntry, data: dict) -> None:
        self._entry = entry
        self._data = data
        self._attr_name = "Factor de Participación"
        self._attr_unique_id = f"{entry.entry_id}_share_factor"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        asset_info = self._data.get("asset_info", {})
        asset_name = asset_info.get("name") or asset_info.get("assetName") or self._data.get("asset_general", "sentinel_solar")
        
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=asset_name,
            manufacturer="sentinel_solar (proyecto no oficial de Sentinel Solar)",
            model=asset_info.get("type") or asset_info.get("assetType") or "Asset",
            sw_version=asset_info.get("firmwareVersion") or asset_info.get("firmware_version"),
            configuration_url=f"{self._entry.data.get('base_url', DEFAULT_BASE_URL)}",
        )

    @property
    def native_value(self) -> Optional[float]:
        """Devuelve el valor actual del factor de participación."""
        return float(self._entry.options.get(CONF_SHARE_FACTOR, DEFAULT_SHARE_FACTOR))

    async def async_set_native_value(self, value: float) -> None:
        """Actualiza el factor de participación."""
        new_options = dict(self._entry.options)
        new_options[CONF_SHARE_FACTOR] = value
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.async_write_ha_state()


class UpdateIntervalNumber(NumberEntity):
    """Control para ajustar el intervalo de actualización."""
    
    _attr_has_entity_name = True
    _attr_icon = "mdi:timer"
    _attr_native_min_value = 1
    _attr_native_max_value = 1440
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = "min"

    def __init__(self, entry: ConfigEntry, data: dict) -> None:
        self._entry = entry
        self._data = data
        self._attr_name = "Intervalo de Actualización"
        self._attr_unique_id = f"{entry.entry_id}_update_interval"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        asset_info = self._data.get("asset_info", {})
        asset_name = asset_info.get("name") or asset_info.get("assetName") or self._data.get("asset_general", "sentinel_solar")
        
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=asset_name,
            manufacturer="sentinel_solar (proyecto no oficial de Sentinel Solar)",
            model=asset_info.get("type") or asset_info.get("assetType") or "Asset",
            sw_version=asset_info.get("firmwareVersion") or asset_info.get("firmware_version"),
            configuration_url=f"{self._entry.data.get('base_url', DEFAULT_BASE_URL)}",
        )

    @property
    def native_value(self) -> Optional[int]:
        """Devuelve el valor actual del intervalo de actualización."""
        return int(self._entry.options.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES))

    async def async_set_native_value(self, value: float) -> None:
        """Actualiza el intervalo de actualización."""
        new_options = dict(self._entry.options)
        new_options[CONF_UPDATE_MINUTES] = int(value)
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.async_write_ha_state()

