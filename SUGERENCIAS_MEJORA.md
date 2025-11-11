# Sugerencias de Mejora para sentinel_solar (proyecto no oficial)

## Análisis del Código Actual

### Endpoints de API Utilizados
- `/api/asset/{asset_id}/power-data/instant` - Potencia instantánea
- `/api/asset/{asset_id}` - Información del asset

---

## 1. **Agregar Device Info (CRÍTICO)**

**Problema**: Los sensores no están agrupados en un dispositivo, lo que dificulta la organización en Home Assistant.

**Solución**: Implementar `device_info` para agrupar todos los sensores bajo un dispositivo común.

**Beneficios**:
- Organización mejorada en Home Assistant
- Mejor experiencia de usuario
- Compatible con el panel de energía

**Implementación sugerida**:
```python
# En sensor.py, agregar a las clases base:
from homeassistant.helpers.entity import DeviceInfo

@property
def device_info(self) -> DeviceInfo:
    """Return device information."""
    data = self.hass.data[DOMAIN][self._entry.entry_id]
    asset_info = data.get("asset_info", {})
    
    return DeviceInfo(
        identifiers={(DOMAIN, self._entry.entry_id)},
        name=asset_info.get("name", "sentinel_solar"),
        manufacturer="sentinel_solar (no oficial de Sentinel Solar)",
        model=asset_info.get("type", "Asset"),
        sw_version=asset_info.get("firmware_version"),
        configuration_url=f"{self._entry.data.get('base_url', DEFAULT_BASE_URL)}",
    )
```

---

## 2. **Mejorar Manejo de Errores y Reintentos**

**Problema**: No hay reintentos automáticos en caso de fallos temporales de la API.

**Solución**: Implementar reintentos con backoff exponencial.

**Mejoras sugeridas**:
- Reintentos automáticos para errores temporales (429, 503, 500)
- Backoff exponencial para evitar sobrecarga
- Logging mejorado de errores
- Contador de reintentos en atributos

**Implementación sugerida**:
```python
# En api.py, agregar:
import asyncio
from typing import Optional

MAX_RETRIES = 3
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

async def _get_json_with_retry(self, path: str, retries: int = MAX_RETRIES) -> Any:
    """Get JSON with automatic retry logic."""
    url = f"{self._base_url}{path}"
    
    for attempt in range(retries):
        try:
            async with self._lock:
                async with self._session.get(url, headers=self._headers, timeout=TIMEOUT) as resp:
                    if resp.status in RETRY_STATUS_CODES and attempt < retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        _LOGGER.warning(
                            "Error %s en intento %d/%d. Reintentando en %d segundos...",
                            resp.status, attempt + 1, retries, wait_time
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    
                    if resp.status == 401:
                        raise PermissionError("Unauthorized (401) – token inválido o sin permisos")
                    if resp.status == 404:
                        raise FileNotFoundError(f"404 Not Found: {url}")
                    resp.raise_for_status()
                    return await resp.json()
        except asyncio.TimeoutError:
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                _LOGGER.warning("Timeout en intento %d/%d. Reintentando...", attempt + 1, retries)
                await asyncio.sleep(wait_time)
                continue
            raise
    raise Exception(f"Falló después de {retries} intentos")
```

---

## 3. **Cachear Información del Asset**

**Problema**: La información del asset se obtiene varias veces pero no se cachea.

**Solución**: Cachear la información del asset al inicio y actualizarla periódicamente.

**Implementación sugerida**:
```python
# En __init__.py, agregar:
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # ... código existente ...
    
    # Obtener y cachear información del asset
    asset_info = {}
    try:
        asset_info = await client.fetch_asset_info(asset_general)
        _LOGGER.info("Información del asset obtenida: %s", asset_info.get("name", asset_general))
    except Exception as e:
        _LOGGER.warning("No se pudo obtener información del asset: %s", e)
    
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "asset_general": asset_general,
        "asset_info": asset_info,  # Cachear información
    }
```

---

## 4. **Agregar Más Información del Asset**

**Problema**: Solo se obtiene el share_factor, pero la API puede proporcionar más información útil.

**Sugerencias de campos adicionales**:
- Nombre del asset (`name`)
- Tipo de instalación (`type`)
- Ubicación (`location`, `address`)
- Capacidad instalada (`installed_capacity`, `power_capacity`)
- Fecha de instalación (`installation_date`)
- Estado de la instalación (`status`)
- Información de la comunidad energética

**Implementación sugerida**:
```python
# En api.py, agregar método:
async def get_asset_details(self, asset_id: str) -> Dict[str, Any]:
    """Obtiene información detallada del asset."""
    asset_info = await self.fetch_asset_info(asset_id)
    return {
        "name": asset_info.get("name", asset_id),
        "type": asset_info.get("type", "Unknown"),
        "location": asset_info.get("location", {}),
        "capacity_kw": asset_info.get("installedCapacity", asset_info.get("installed_capacity")),
        "share_factor": await self.get_share_factor(asset_id),
        "status": asset_info.get("status", "unknown"),
        "installation_date": asset_info.get("installationDate", asset_info.get("installation_date")),
    }
```

---

## 5. **Sensores Adicionales Sugeridos**

Basándose en posibles endpoints de la API:

### 5.1. Sensor de Capacidad Instalada
```python
class SentinelCapacitySensor(CoordinatorEntity, SensorEntity):
    _attr_native_unit_of_measurement = "kW"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_icon = "mdi:solar-power"
    
    @property
    def native_value(self) -> Optional[float]:
        data = self.hass.data[DOMAIN][self._entry.entry_id]
        capacity = data.get("asset_info", {}).get("installedCapacity")
        return float(capacity) if capacity else None
```

### 5.2. Sensor de Estado de Conexión
```python
class SentinelConnectionSensor(CoordinatorEntity, SensorEntity):
    _attr_icon = "mdi:connection"
    
    @property
    def native_value(self) -> str:
        if self.coordinator.last_update_success:
            return "online"
        return "offline"
```

### 5.3. Sensor de Última Actualización
```python
class SentinelLastUpdateSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-outline"
    
    @property
    def native_value(self) -> Optional[datetime]:
        if self.coordinator.data:
            ts = self.coordinator.data.get("general", {}).get("timestamp")
            if ts:
                return dt_util.parse_datetime(ts)
        return None
```

---

## 6. **Mejorar Logging y Métricas**

**Problema**: El logging es básico y no hay métricas de rendimiento.

**Mejoras sugeridas**:
- Logging estructurado con contexto
- Métricas de tiempo de respuesta de la API
- Contador de errores y reintentos
- Estadísticas de actualizaciones

**Implementación sugerida**:
```python
# En api.py, agregar métricas:
import time
from typing import Dict

class SentinelClient:
    def __init__(self, ...):
        # ... código existente ...
        self._metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_retries": 0,
            "avg_response_time": 0.0,
        }
    
    async def _get_json(self, path: str) -> Any:
        start_time = time.time()
        self._metrics["total_requests"] += 1
        
        try:
            result = await self._get_json_with_retry(path)
            self._metrics["successful_requests"] += 1
            
            response_time = time.time() - start_time
            # Actualizar promedio de tiempo de respuesta
            total = self._metrics["successful_requests"]
            self._metrics["avg_response_time"] = (
                (self._metrics["avg_response_time"] * (total - 1) + response_time) / total
            )
            
            _LOGGER.debug("Request a %s completado en %.2fs", path, response_time)
            return result
        except Exception as e:
            self._metrics["failed_requests"] += 1
            _LOGGER.error("Error en request a %s: %s", path, e)
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de rendimiento."""
        return self._metrics.copy()
```

---

## 7. **Validación de Datos Mejorada**

**Problema**: La validación de datos es básica y puede fallar silenciosamente.

**Mejoras sugeridas**:
- Validar que los valores de potencia sean razonables
- Validar formato de timestamps
- Detectar valores atípicos (outliers)
- Alertas cuando los datos no se actualizan

**Implementación sugerida**:
```python
# En api.py, agregar validación:
MAX_POWER_KW = 10000  # 10 MW máximo razonable
MIN_POWER_W = -1000   # Permitir consumo negativo

def _extract_power_and_ts(self, payload: Any) -> Dict[str, Optional[Union[float, str]]]:
    result = self._extract_power_and_ts(payload)
    
    # Validar potencia
    power = result.get("power", 0.0)
    if power > MAX_POWER_KW * 1000:
        _LOGGER.warning("Potencia muy alta detectada: %.2f W (máx esperado: %.2f W)", 
                       power, MAX_POWER_KW * 1000)
        result["power"] = MAX_POWER_KW * 1000
    
    # Validar timestamp
    ts = result.get("timestamp")
    if ts:
        try:
            dt = dt_util.parse_datetime(ts)
            if dt and dt > dt_util.utcnow() + timedelta(hours=1):
                _LOGGER.warning("Timestamp en el futuro detectado: %s", ts)
        except Exception:
            _LOGGER.warning("Timestamp inválido: %s", ts)
            result["timestamp"] = None
    
    return result
```

---

## 8. **Optimización de Llamadas a la API**

**Problema**: Se hacen múltiples llamadas para obtener información del asset.

**Solución**: Combinar llamadas cuando sea posible y cachear resultados.

**Mejoras sugeridas**:
- Cachear información del asset durante 1 hora
- Hacer llamadas en paralelo cuando sea posible
- Reducir frecuencia de actualización de información estática

---

## 9. **Soporte para Múltiples Assets (Futuro)**

**Mejora a largo plazo**: Permitir configurar múltiples assets desde una sola integración.

**Implementación sugerida**:
- Modificar config_flow para permitir agregar múltiples assets
- Crear sensores por asset
- Agregar selector de asset en opciones

---

## 10. **Mejoras en Traducciones**

**Sugerencias**:
- Agregar traducciones en inglés
- Mejorar mensajes de error descriptivos
- Agregar ayuda contextual en el config_flow

---

## 11. **Documentación y Testing**

**Sugerencias**:
- Agregar docstrings completos
- Crear tests unitarios
- Documentar endpoints de API utilizados
- Agregar ejemplos de configuración

---

## Prioridades de Implementación

### Alta Prioridad (Implementar primero)
1. ✅ Device Info - Agrupar sensores
2. ✅ Cachear información del asset
3. ✅ Mejorar manejo de errores

### Media Prioridad
4. ✅ Reintentos automáticos
5. ✅ Validación de datos mejorada
6. ✅ Logging y métricas

### Baja Prioridad (Mejoras futuras)
7. Sensores adicionales
8. Soporte para múltiples assets
9. Traducciones adicionales
10. Testing automatizado

---

## Notas Finales

- Estas mejoras están basadas en las mejores prácticas de Home Assistant
- Algunas mejoras requieren verificar qué endpoints adicionales están disponibles en la API
- Se recomienda implementar gradualmente y probar cada mejora
- Considerar feedback de usuarios para priorizar mejoras

