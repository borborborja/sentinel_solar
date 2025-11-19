from __future__ import annotations
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN, CONF_TOKEN, CONF_ASSET_GENERAL,
    CONF_BASE_URL, CONF_UPDATE_MINUTES, CONF_SHARE_FACTOR,
    DEFAULT_BASE_URL, DEFAULT_UPDATE_MINUTES, DEFAULT_SHARE_FACTOR
)
from .api import SentinelClient

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[str] = ["sensor", "number", "switch"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configurar la integración cuando se carga una entrada de configuración."""
    session = aiohttp_client.async_get_clientsession(hass)
    base_url = entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
    token = entry.data[CONF_TOKEN]
    asset_general = entry.data[CONF_ASSET_GENERAL]

    # Obtener opciones de configuración
    update_minutes = entry.options.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES)
    
    client = SentinelClient(session, base_url, token)
    
    # Inicializar datos en hass.data antes del coordinador
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "asset_general": asset_general,
        "asset_info": {"name": asset_general},  # Info por defecto
        "night_mode": False,  # Estado por defecto del modo noche
        "last_data": {"general": {}},  # Últimos datos conocidos
        "initialized_info": False,
    }

    async def _async_update():
        data_store = hass.data[DOMAIN][entry.entry_id]
        
        # 1. Lazy load de información del asset (solo la primera vez)
        if not data_store.get("initialized_info"):
            try:
                asset_info = await client.fetch_asset_info(asset_general)
                data_store["asset_info"] = asset_info
                _LOGGER.info("Información del asset obtenida en segundo plano: %s", asset_info.get("name"))
                
                # Lógica de share_factor
                share_factor = entry.options.get(CONF_SHARE_FACTOR)
                if share_factor is None:
                    api_share_factor = await client.get_share_factor(asset_general)
                    if api_share_factor is not None:
                        new_options = dict(entry.options)
                        new_options[CONF_SHARE_FACTOR] = api_share_factor
                        hass.config_entries.async_update_entry(entry, options=new_options)
                        _LOGGER.info("Share factor actualizado desde API: %s", api_share_factor)
                
                data_store["initialized_info"] = True
            except Exception as e:
                _LOGGER.warning("Error obteniendo info inicial del asset (se reintentará): %s", e)

        # 2. Lógica de Modo Noche
        if data_store.get("night_mode", False):
            sun = hass.states.get("sun.sun")
            if sun and sun.state == "below_horizon":
                _LOGGER.debug("Modo Noche activo: Pausando llamadas a la API y reportando 0W")
                # Devolver 0 de potencia para que no cuente consumo/generación fantasma
                return {"general": {"power": 0.0}}

        # 3. Obtener datos
        try:
            general = await client.fetch_power_instant(asset_general)
            result = {"general": general}
            data_store["last_data"] = result
            return result
        except Exception as e:
            raise UpdateFailed(str(e)) from e

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="sentinel_solar_coordinator",
        update_method=_async_update,
        update_interval=timedelta(minutes=update_minutes),
    )
    
    # Guardar coordinador en hass.data
    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recargar la entrada cuando se actualizan las opciones."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descargar la integración cuando se elimina."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

