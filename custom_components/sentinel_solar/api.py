from __future__ import annotations
from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta
import asyncio
import aiohttp
import logging
import time

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=20)
MAX_RETRIES = 3
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_POWER_KW = 10000  # 10 MW máximo razonable
MIN_POWER_W = -100000  # Permitir consumo negativo hasta -100kW

class SentinelClient:
    def __init__(self, session: aiohttp.ClientSession, base_url: str, token: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._headers = {"X-AUTH-TOKEN": token, "Accept": "application/json"}
        self._lock = asyncio.Lock()
        
        # Métricas de rendimiento
        self._metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_retries": 0,
            "avg_response_time": 0.0,
            "last_request_time": None,
        }

    async def _get_json_with_retry(self, path: str, retries: int = MAX_RETRIES) -> Any:
        """Obtiene datos JSON de la API con reintentos automáticos y backoff exponencial."""
        url = f"{self._base_url}{path}"
        
        for attempt in range(retries):
            try:
                async with self._lock:
                    async with self._session.get(url, headers=self._headers, timeout=TIMEOUT) as resp:
                        # Si el código de estado requiere reintento y no es el último intento
                        if resp.status in RETRY_STATUS_CODES and attempt < retries - 1:
                            wait_time = 2 ** attempt  # Backoff exponencial: 1s, 2s, 4s...
                            self._metrics["total_retries"] += 1
                            _LOGGER.warning(
                                "Error %s en intento %d/%d para %s. Reintentando en %d segundos...",
                                resp.status, attempt + 1, retries, path, wait_time
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        
                        # Errores que no deben reintentar
                        if resp.status == 401:
                            raise PermissionError("Unauthorized (401) – token inválido o sin permisos")
                        if resp.status == 404:
                            raise FileNotFoundError(f"404 Not Found: {url}")
                        
                        resp.raise_for_status()
                        return await resp.json()
                        
            except asyncio.TimeoutError:
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    self._metrics["total_retries"] += 1
                    _LOGGER.warning(
                        "Timeout en intento %d/%d para %s. Reintentando en %d segundos...", 
                        attempt + 1, retries, path, wait_time
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise
            except aiohttp.ClientError as e:
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    self._metrics["total_retries"] += 1
                    _LOGGER.warning(
                        "Error de conexión en intento %d/%d para %s: %s. Reintentando...", 
                        attempt + 1, retries, path, str(e)
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise
        
        raise Exception(f"Falló después de {retries} intentos para {path}")

    async def _get_json(self, path: str) -> Any:
        """Obtiene datos JSON de la API con manejo de errores, reintentos y métricas."""
        start_time = time.time()
        self._metrics["total_requests"] += 1
        
        try:
            result = await self._get_json_with_retry(path)
            self._metrics["successful_requests"] += 1
            
            response_time = time.time() - start_time
            self._metrics["last_request_time"] = response_time
            
            # Actualizar promedio de tiempo de respuesta
            total = self._metrics["successful_requests"]
            self._metrics["avg_response_time"] = (
                (self._metrics["avg_response_time"] * (total - 1) + response_time) / total
            )
            
            _LOGGER.debug("Request a %s completado en %.2fs", path, response_time)
            return result
            
        except Exception as e:
            self._metrics["failed_requests"] += 1
            _LOGGER.error("Error en request a %s después de todos los reintentos: %s", path, str(e))
            raise

    def _extract_power_and_ts(self, payload: Any) -> Dict[str, Optional[Union[float, str]]]:
        """Extrae potencia y timestamp de diferentes formatos de respuesta de la API con validación."""
        power = 0.0
        ts: Optional[str] = None
        j = payload
        
        # Extraer potencia del payload
        if isinstance(j, (int, float)):
            power = float(j)
        elif isinstance(j, dict):
            # Buscar powerProduction primero (API de Sentinel Solar devuelve kW)
            if "powerProduction" in j and j["powerProduction"] is not None:
                power = float(j["powerProduction"]) * 1000  # Convertir kW a W
            elif "power" in j:
                power = float(j["power"])
            elif "activePower" in j:
                power = float(j["activePower"])
            elif "data" in j and isinstance(j["data"], dict):
                d = j["data"]
                if "powerProduction" in d and d["powerProduction"] is not None:
                    power = float(d["powerProduction"]) * 1000  # Convertir kW a W
                elif "power" in d:
                    power = float(d["power"])
                elif "activePower" in d:
                    power = float(d["activePower"])
            
            # Extraer timestamp (buscar "time" primero)
            if "time" in j:
                ts = j["time"]
            elif "timestamp" in j:
                ts = j["timestamp"]
            elif "ts" in j:
                ts = j["ts"]
            elif "updatedAt" in j:
                ts = j["updatedAt"]
        
        # Validar potencia - detectar valores anormales
        max_power_w = MAX_POWER_KW * 1000
        if power > max_power_w:
            _LOGGER.warning(
                "Potencia muy alta detectada: %.2f W (máx esperado: %.2f W). Limitando valor.",
                power, max_power_w
            )
            power = max_power_w
        elif power < MIN_POWER_W:
            _LOGGER.warning(
                "Potencia muy baja detectada: %.2f W (mín esperado: %.2f W). Limitando valor.",
                power, MIN_POWER_W
            )
            power = MIN_POWER_W
        
        # Validar timestamp
        if ts:
            try:
                from homeassistant.util import dt as dt_util
                dt = dt_util.parse_datetime(ts)
                if dt:
                    now = dt_util.utcnow()
                    # Verificar que no sea un timestamp muy antiguo (>7 días) o futuro (>1 hora)
                    if dt > now + timedelta(hours=1):
                        _LOGGER.warning("Timestamp en el futuro detectado: %s (ahora: %s)", ts, now)
                    elif dt < now - timedelta(days=7):
                        _LOGGER.warning("Timestamp muy antiguo detectado: %s (ahora: %s)", ts, now)
            except Exception as e:
                _LOGGER.warning("Error al validar timestamp '%s': %s", ts, str(e))
        
        return {"power": power, "timestamp": ts}

    async def fetch_power_instant(self, asset_id: str) -> Dict[str, Any]:
        """Obtiene la potencia instantánea de un asset."""
        data = await self._get_json(f"/api/asset/{asset_id}/power-data/instant")
        _LOGGER.debug("Datos recibidos de la API: %s", data)
        result = self._extract_power_and_ts(data)
        _LOGGER.debug("Datos extraídos - Potencia: %.2f W, Timestamp: %s", result.get("power", 0), result.get("timestamp"))
        return result

    async def fetch_asset_info(self, asset_id: str) -> Dict[str, Any]:
        """Obtiene información del asset, incluyendo el share_factor si está disponible."""
        try:
            data = await self._get_json(f"/api/asset/{asset_id}")
            return data
        except Exception:
            # Si no se puede obtener, devolvemos un dict vacío
            return {}

    async def get_share_factor(self, asset_id: str) -> Optional[float]:
        """Intenta obtener el share_factor desde la API."""
        try:
            asset_info = await self.fetch_asset_info(asset_id)
            # Buscar el share_factor en diferentes campos posibles
            if isinstance(asset_info, dict):
                if "shareFactor" in asset_info:
                    return float(asset_info["shareFactor"])
                elif "share_factor" in asset_info:
                    return float(asset_info["share_factor"])
                elif "participationFactor" in asset_info:
                    return float(asset_info["participationFactor"])
                elif "participation_factor" in asset_info:
                    return float(asset_info["participation_factor"])
            return None
        except Exception:
            return None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de rendimiento del cliente API."""
        return self._metrics.copy()
