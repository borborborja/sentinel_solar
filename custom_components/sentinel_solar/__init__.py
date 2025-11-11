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
PLATFORMS: list[str] = ["sensor", "number"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configurar la integración cuando se carga una entrada de configuración."""
    session = aiohttp_client.async_get_clientsession(hass)
    base_url = entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL)
    token = entry.data[CONF_TOKEN]
    asset_general = entry.data[CONF_ASSET_GENERAL]

    # Obtener opciones de configuración
    update_minutes = entry.options.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES)
    share_factor = entry.options.get(CONF_SHARE_FACTOR)
    
    client = SentinelClient(session, base_url, token)
    
    # Obtener y cachear información del asset
    asset_info = {}
    try:
        asset_info = await client.fetch_asset_info(asset_general)
        asset_name = asset_info.get("name") or asset_info.get("assetName") or asset_general
        _LOGGER.info("Información del asset obtenida: %s", asset_name)
    except Exception as e:
        _LOGGER.warning("No se pudo obtener información del asset: %s", e)
        asset_info = {"name": asset_general}
    
    # Intentar obtener el share_factor desde la API si no está configurado
    if share_factor is None:
        try:
            api_share_factor = await client.get_share_factor(asset_general)
            if api_share_factor is not None:
                # Actualizar las opciones con el share_factor obtenido de la API
                new_options = dict(entry.options)
                new_options[CONF_SHARE_FACTOR] = api_share_factor
                hass.config_entries.async_update_entry(entry, options=new_options)
                share_factor = api_share_factor
                _LOGGER.info("Share factor obtenido desde la API: %s", share_factor)
            else:
                share_factor = DEFAULT_SHARE_FACTOR
                _LOGGER.warning("No se pudo obtener el share_factor desde la API, usando valor por defecto: %s", share_factor)
        except Exception as e:
            _LOGGER.warning("Error al obtener share_factor desde la API: %s. Usando valor por defecto.", e)
            share_factor = DEFAULT_SHARE_FACTOR
    else:
        share_factor = float(share_factor)

    async def _async_update():
        try:
            general = await client.fetch_power_instant(asset_general)
            return {"general": general}
        except Exception as e:
            raise UpdateFailed(str(e)) from e

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="sentinel_solar_coordinator",
        update_method=_async_update,
        update_interval=timedelta(minutes=update_minutes),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "asset_general": asset_general,
        "asset_info": asset_info,  # Cachear información del asset
    }

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

