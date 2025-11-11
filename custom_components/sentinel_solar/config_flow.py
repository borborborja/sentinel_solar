from __future__ import annotations
from typing import Any, Optional
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client

from .const import (
    DOMAIN, CONF_TOKEN, CONF_ASSET_GENERAL,
    CONF_BASE_URL, CONF_UPDATE_MINUTES, CONF_SHARE_FACTOR,
    DEFAULT_BASE_URL, DEFAULT_UPDATE_MINUTES, DEFAULT_SHARE_FACTOR
)
from .api import SentinelClient

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ConfigFlow para la integración sentinel_solar (proyecto no oficial)."""
    
    VERSION = 1

    async def async_step_user(self, user_input: Optional[dict[str, Any]] = None):
        errors = {}
        if user_input is not None:
            session = aiohttp_client.async_get_clientsession(self.hass)
            client = SentinelClient(
                session,
                user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL),
                user_input[CONF_TOKEN]
            )
            try:
                await client.fetch_power_instant(user_input[CONF_ASSET_GENERAL])
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                # Obtener share_factor del input
                share_factor = user_input.get(CONF_SHARE_FACTOR)
                
                # Si es string, convertir a float (acepta punto o coma)
                if isinstance(share_factor, str) and share_factor.strip():
                    try:
                        # Reemplazar coma por punto
                        share_factor = float(share_factor.replace(",", "."))
                        if not (0 <= share_factor <= 1):
                            errors[CONF_SHARE_FACTOR] = "formato_invalido"
                            share_factor = None
                    except (ValueError, AttributeError):
                        errors[CONF_SHARE_FACTOR] = "formato_invalido"
                        share_factor = None
                elif share_factor is None or (isinstance(share_factor, str) and not share_factor.strip()):
                    share_factor = None
                else:
                    # Ya es float o int
                    share_factor = float(share_factor)
                    if not (0 <= share_factor <= 1):
                        errors[CONF_SHARE_FACTOR] = "formato_invalido"
                        share_factor = None
                
                # Si no hay share_factor, intentar obtenerlo de la API
                if share_factor is None and not errors:
                    try:
                        api_share_factor = await client.get_share_factor(user_input[CONF_ASSET_GENERAL])
                        if api_share_factor is not None:
                            share_factor = api_share_factor
                        else:
                            share_factor = DEFAULT_SHARE_FACTOR
                    except Exception:
                        share_factor = DEFAULT_SHARE_FACTOR
                
                if errors:
                    schema = vol.Schema({
                        vol.Optional(CONF_BASE_URL, default=user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL)): str,
                        vol.Required(CONF_TOKEN, default=user_input.get(CONF_TOKEN, "")): str,
                        vol.Required(CONF_ASSET_GENERAL, default=user_input.get(CONF_ASSET_GENERAL, "")): str,
                        vol.Optional(CONF_UPDATE_MINUTES, default=user_input.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES)): vol.All(int, vol.Range(min=1, max=1440)),
                        vol.Optional(CONF_SHARE_FACTOR, default=""): str,
                    })
                    return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
                
                return self.async_create_entry(
                    title="sentinel_solar",
                    data={
                        CONF_BASE_URL: user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL),
                        CONF_TOKEN: user_input[CONF_TOKEN],
                        CONF_ASSET_GENERAL: user_input[CONF_ASSET_GENERAL],
                    },
                    options={
                        CONF_UPDATE_MINUTES: user_input.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES),
                        CONF_SHARE_FACTOR: share_factor,
                    }
                )

        schema = vol.Schema({
            vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
            vol.Required(CONF_TOKEN): str,
            vol.Required(CONF_ASSET_GENERAL): str,
            vol.Optional(CONF_UPDATE_MINUTES, default=DEFAULT_UPDATE_MINUTES): vol.All(int, vol.Range(min=1, max=1440)),
            vol.Optional(CONF_SHARE_FACTOR, default=""): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlow(config_entry)

class OptionsFlow(config_entries.OptionsFlow):
    """OptionsFlow para configurar opciones de la integración."""
    
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Validar share_factor si se proporciona
            if CONF_SHARE_FACTOR in user_input:
                share_factor_value = user_input[CONF_SHARE_FACTOR]
                if isinstance(share_factor_value, str) and share_factor_value.strip():
                    try:
                        # Reemplazar coma por punto y convertir a float
                        share_factor_float = float(share_factor_value.replace(",", "."))
                        if not (0 <= share_factor_float <= 1):
                            errors[CONF_SHARE_FACTOR] = "formato_invalido"
                        else:
                            user_input[CONF_SHARE_FACTOR] = share_factor_float
                    except (ValueError, AttributeError):
                        errors[CONF_SHARE_FACTOR] = "formato_invalido"
                elif not share_factor_value or (isinstance(share_factor_value, str) and not share_factor_value.strip()):
                    # Si está vacío, mantener el valor actual
                    user_input[CONF_SHARE_FACTOR] = self.entry.options.get(CONF_SHARE_FACTOR, DEFAULT_SHARE_FACTOR)
            
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        # Convertir el valor actual a string para mostrarlo
        current_share = self.entry.options.get(CONF_SHARE_FACTOR, DEFAULT_SHARE_FACTOR)
        if isinstance(current_share, (int, float)):
            current_share_str = str(current_share)
        else:
            current_share_str = str(current_share) if current_share else ""

        schema = vol.Schema({
            vol.Optional(
                CONF_UPDATE_MINUTES,
                default=self.entry.options.get(CONF_UPDATE_MINUTES, DEFAULT_UPDATE_MINUTES)
            ): vol.All(int, vol.Range(min=1, max=1440)),
            vol.Optional(
                CONF_SHARE_FACTOR,
                default=current_share_str
            ): str,
        })
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
