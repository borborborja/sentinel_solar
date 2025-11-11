from __future__ import annotations
from typing import Any, Optional
from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN, CONF_SHARE_FACTOR, DEFAULT_SHARE_FACTOR, 
    CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES,
    DEFAULT_BASE_URL
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Configurar los sensores de la integración."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    # Sensores de potencia (W) y energía (kWh)
    power_sensor = SentinelPowerSensor(coordinator, entry)
    energy_sensor = SentinelEnergySensor(coordinator, entry)

    async_add_entities([power_sensor, energy_sensor])


# ------------------------ Potencia (W) ------------------------

class SentinelPowerSensor(CoordinatorEntity, SensorEntity):
    """Sensor de potencia instantánea."""
    _attr_native_unit_of_measurement = "W"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "Potencia"
        self._attr_unique_id = f"{entry.entry_id}_power"

    @property
    def _node(self) -> dict:
        return (self.coordinator.data or {}).get("general") or {}

    @property
    def api_timestamp(self) -> Optional[str]:
        return self._node.get("timestamp")

    def _get_power_w(self) -> float:
        """Obtiene la potencia en vatios."""
        raw_power = float(self._node.get("power", 0.0))
        # Aplicar factor de participación
        factor = float(self._entry.options.get(CONF_SHARE_FACTOR, DEFAULT_SHARE_FACTOR))
        return round(raw_power * factor, 1)
    
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
    def native_value(self) -> Optional[float]:
        return self._get_power_w()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        factor = float(self._entry.options.get(CONF_SHARE_FACTOR, DEFAULT_SHARE_FACTOR))
        raw_power = float(self._node.get("power", 0.0))
        return {
            "api_timestamp": self.api_timestamp,
            "source": "power-data/instant",
            "share_factor": factor,
            "raw_power": raw_power,
        }


# ------------------------ Energía acumulada (kWh) ------------------------

class SentinelEnergySensor(CoordinatorEntity, RestoreEntity, SensorEntity):
    """Integra potencia (W) -> energía (kWh) usando el timestamp de la API."""
    _attr_native_unit_of_measurement = "kWh"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "Energía"
        self._attr_unique_id = f"{entry.entry_id}_energy"
        self._energy_kwh: Optional[float] = None
        self._last_api_ts: Optional[str] = None
        self._last_ha_utc: Optional[datetime] = None  # fallback si no hay ts API

        self._update_minutes = int(self._entry.options.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES))
        self._max_delta = timedelta(
            minutes=max(5, min(self._update_minutes * 3, 6 * 60))
        )
    
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
    def extra_state_attributes(self) -> dict[str, Any]:
        factor = float(self._entry.options.get(CONF_SHARE_FACTOR, DEFAULT_SHARE_FACTOR))
        return {
            "api_timestamp": self._last_api_ts,
            "source": "power-data/instant",
            "integration": "rectangular_api_ts",
            "share_factor": factor,
        }

    def _get_power_w(self) -> float:
        """Obtiene la potencia en vatios aplicando el factor de participación."""
        node = (self.coordinator.data or {}).get("general") or {}
        raw_power = float(node.get("power", 0.0))
        factor = float(self._entry.options.get(CONF_SHARE_FACTOR, DEFAULT_SHARE_FACTOR))
        return raw_power * factor

    def _get_api_ts_str(self) -> Optional[str]:
        """Obtiene el timestamp de la API desde los datos del coordinador."""
        node = (self.coordinator.data or {}).get("general") or {}
        return node.get("timestamp")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "", "unknown", "unavailable"):
            try:
                self._energy_kwh = float(last_state.state)
            except (TypeError, ValueError):
                self._energy_kwh = 0.0
            self._last_api_ts = last_state.attributes.get("api_timestamp")
        else:
            self._energy_kwh = 0.0
        self._last_ha_utc = dt_util.utcnow()

    @property
    def native_value(self) -> Optional[float]:
        return round(self._energy_kwh or 0.0, 6)

    def _integrate(self, power_w: float, dt_seconds: float) -> None:
        """Integra potencia (W) durante un tiempo (segundos) para obtener energía (kWh)."""
        if dt_seconds <= 0:
            return
        dt_h = dt_seconds / 3600.0
        self._energy_kwh = (self._energy_kwh or 0.0) + (power_w / 1000.0) * dt_h

    def _bounded_delta(self, start: datetime, end: datetime) -> float:
        """Calcula el delta de tiempo limitado entre dos fechas."""
        delta = end - start
        if delta < timedelta(0):
            return 0.0
        if delta > self._max_delta:
            delta = self._max_delta
        return delta.total_seconds()

    def _parse_ts(self, ts: str) -> Optional[datetime]:
        """Parsea un timestamp string a datetime UTC."""
        dt = dt_util.parse_datetime(ts)
        if dt is not None:
            return dt_util.as_utc(dt)
        return None

    def _on_coordinator_update(self) -> None:
        api_ts = self._get_api_ts_str()
        power_w = self._get_power_w()
        now_utc = dt_util.utcnow()

        if api_ts:
            if api_ts == self._last_api_ts:
                return
            new_dt = self._parse_ts(api_ts)
            last_dt = self._parse_ts(self._last_api_ts) if self._last_api_ts else None

            if last_dt is None:
                self._last_api_ts = api_ts
                return

            dt_sec = self._bounded_delta(last_dt, new_dt)
            if dt_sec > 0:
                self._integrate(power_w, dt_sec)
                self._last_api_ts = api_ts
        else:
            if self._last_ha_utc is None:
                self._last_ha_utc = now_utc
                return
            dt_sec = self._bounded_delta(self._last_ha_utc, now_utc)
            if dt_sec > 0:
                self._integrate(power_w, dt_sec)
                self._last_ha_utc = now_utc

        self.async_write_ha_state()

    async def async_update(self) -> None:
        return

    @property
    def should_poll(self) -> bool:
        return False

    def _handle_coordinator_update(self) -> None:
        """Handle coordinator update."""
        super()._handle_coordinator_update()
        self._on_coordinator_update()
