# sentinel_solar

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2023.1+-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

> **Aviso:** sentinel_solar es un proyecto comunitario no oficial y no está afiliado ni respaldado por Sentinel Solar.

Integración personalizada para Home Assistant que permite monitorizar la producción de energía solar de una comunidad energética gestionada a través de los datos públicos de Sentinel Solar.

## 📋 Características

- ✅ **Monitorización en tiempo real** de potencia y energía
- ✅ **Compatible con el Panel de Energía** de Home Assistant
- ✅ **Controles en tiempo real** para ajustar factor de participación e intervalo
- ✅ **Múltiples configuraciones** - Añade varios assets (total comunidad + tu porción)
- ✅ **Reintentos automáticos** con backoff exponencial
- ✅ **Validación de datos** con detección de valores anómalos
- ✅ **Métricas de rendimiento** del cliente API
- ✅ **Interfaz de configuración gráfica** (Config Flow)
- ✅ **Multiidioma**: Español, Inglés y Catalán

## 📊 Entidades Disponibles

Cada configuración crea **4 entidades**:

### 📈 Sensores (2)

1. **`sensor.potencia`** - Potencia instantánea (W)
   - Lee `powerProduction` de la API y aplica tu factor de participación
   - Ejemplo: API = 5.727 kW × factor 0.025 = **143.18 W**
   - Atributos:
     - `raw_power`: Potencia sin aplicar factor (5727 W)
     - `share_factor`: Factor aplicado (0.025)

2. **`sensor.energia`** - Energía acumulada (kWh)
   - Integra la potencia a lo largo del tiempo
   - Compatible con el **Panel de Energía** de Home Assistant
   - Se acumula automáticamente y persiste tras reinicios

### 🎛️ Controles (2)

3. **`number.factor_de_participacion`** - Factor de participación (0..1)
   - Ajusta tu porcentaje en tiempo real sin recargar
   - Ejemplo: 0.025 = 2.5% de la instalación
   - Rango: 0.0 (0%) a 1.0 (100%)

4. **`number.intervalo_de_actualizacion`** - Minutos entre lecturas (1-1440)
   - Cambia la frecuencia de actualización dinámicamente
   - Por defecto: 60 minutos

## 🎯 Casos de Uso

### Escenario 1: Ver Total + Tu Porción

Añade **dos configuraciones** de la integración:

**Configuración 1 - Total de la Comunidad**
- Asset ID: `tu_asset_id`
- Factor: `1.0` (100%)
- Nombre del dispositivo: "Comunidad Solar Total"
- Sensores: `sensor.potencia` (5727 W), `sensor.energia` (acumulado total)

**Configuración 2 - Tu Porción**
- Asset ID: `tu_asset_id` (el mismo)
- Factor: `0.025` (2.5%)
- Nombre del dispositivo: "Mi Porción Solar"
- Sensores: `sensor.potencia` (143 W), `sensor.energia` (acumulado tuyo)

### Escenario 2: Solo Tu Porción

Añade **una configuración**:
- Asset ID: `tu_asset_id`
- Factor: `0.025`
- ¡Listo! Verás solo tu porción

### 📡 Datos de la API

Endpoint: `/api/asset/{assetId}/power-data/instant`
- **`powerProduction`**: Potencia de producción solar en kW (convertido a W)
- **`time`**: Timestamp de la medición

## ⚠️ Migración desde v1.x

Si actualizas desde una versión anterior:

1. **Elimina la integración antigua** completamente
2. **Reinicia Home Assistant**
3. **Sigue las instrucciones de instalación** a continuación
4. **Reconfigura según tus necesidades** (ver Casos de Uso arriba)

**Cambios principales:**
- ❌ Se eliminaron sensores "General" y "Mi Porción" separados
- ✅ Ahora hay 2 sensores que aplican el factor automáticamente
- ✅ Controles en tiempo real para factor e intervalo
- ✅ Puedes añadir múltiples configuraciones para diferentes vistas

---

## 🚀 Instalación

### Método 1: HACS (Recomendado)

1. Abre HACS en Home Assistant
2. Ve a "Integraciones"
3. Click en los tres puntos (⋮) en la esquina superior derecha
4. Selecciona "Repositorios personalizados"
5. Añade la URL: `https://github.com/borja/sentinel_solar`
6. Selecciona la categoría "Integración"
7. Busca "sentinel_solar"
8. Click en "Descargar"
9. Reinicia Home Assistant

### Método 2: Instalación Manual

1. Descarga la última versión desde [Releases](https://github.com/borja/sentinel_solar/releases)
2. Copia la carpeta `custom_components/sentinel_solar` de este repositorio dentro de tu directorio `custom_components` de Home Assistant:
   ```
   <config>/custom_components/sentinel_solar/
   ```
3. Reinicia Home Assistant

## ⚙️ Configuración

### Paso 1: Añadir la integración

1. Ve a **Configuración** → **Dispositivos y servicios**
2. Click en **+ Añadir integración**
3. Busca "**sentinel_solar**"
4. Rellena los datos solicitados:

#### Parámetros de Configuración

| Campo | Descripción | Obligatorio | Por defecto |
|-------|-------------|-------------|-------------|
| **Base URL** | URL de la API de Sentinel Solar | No | `https://apiv3.sentinel-solar.com` |
| **Token** | Tu token de autenticación (X-AUTH-TOKEN) | Sí | - |
| **Asset ID** | ID del asset de la instalación general | Sí | - |
| **Minutos entre lecturas** | Frecuencia de actualización de datos | No | 60 |
| **Factor de participación** | Tu porcentaje de participación (0..1) | No | Se obtiene de la API |

### Paso 2: Obtener tus credenciales

Para obtener tu **Token** y **Asset ID**:

1. Accede al portal web de Sentinel Solar
2. Abre las herramientas de desarrollador del navegador (F12)
3. Ve a la pestaña "Red" (Network)
4. Recarga la página y busca llamadas a la API
5. Busca el header `X-AUTH-TOKEN` para obtener tu token
6. Busca el `asset_id` en las URLs de las llamadas API

### Paso 3: Configurar opciones (opcional)

Puedes modificar las opciones en cualquier momento:

1. Ve a **Configuración** → **Dispositivos y servicios**
2. Busca "sentinel_solar"
3. Click en **Opciones**
4. Modifica los valores deseados:
   - **Minutos entre lecturas**: Ajusta la frecuencia de actualización (1-1440 minutos)
   - **Factor de participación**: Ajusta tu porcentaje (acepta punto o coma como separador decimal)

## 📈 Uso en el Panel de Energía

Para añadir la energía solar al Panel de Energía de Home Assistant:

1. Ve a **Energía** en el menú principal
2. Click en **Añadir fuente de energía solar**
3. Selecciona el sensor: `sensor.energia_mi_porcion` o `sensor.energia_general`
4. Guarda los cambios

Ahora podrás ver tu producción solar en el dashboard de energía.

## 🔧 Características Avanzadas

### Reintentos Automáticos

La integración incluye reintentos automáticos con backoff exponencial para los siguientes códigos de error HTTP:
- 429 (Too Many Requests)
- 500 (Internal Server Error)
- 502 (Bad Gateway)
- 503 (Service Unavailable)
- 504 (Gateway Timeout)

Por defecto, se hacen hasta **3 intentos** con esperas de 1s, 2s y 4s entre intentos.

### Validación de Datos

La integración valida automáticamente:
- **Potencia**: Detecta valores anormalmente altos (>10 MW) o bajos (<-100 kW)
- **Timestamps**: Verifica que no sean muy antiguos (>7 días) o futuros (>1 hora)

Los valores anómalos se registran en el log y se limitan a valores razonables.

### Métricas de Rendimiento

El cliente API recopila métricas de rendimiento:
- Total de peticiones realizadas
- Peticiones exitosas/fallidas
- Número de reintentos
- Tiempo promedio de respuesta
- Tiempo de la última petición

Estas métricas se pueden consultar desde los atributos de los sensores o el log.

## 🐛 Solución de Problemas

### La integración no se conecta

**Posibles causas:**
- Token inválido o expirado
- Asset ID incorrecto
- Problemas de red o firewall

**Solución:**
1. Verifica que el token y asset ID sean correctos
2. Comprueba los logs de Home Assistant: **Configuración** → **Sistema** → **Logs**
3. Busca mensajes de error relacionados con `sentinel_solar`

### Los sensores muestran 0 W o no se actualizan

**Posibles causas:**
- API de Sentinel Solar temporalmente no disponible
- Intervalo de actualización muy alto
- La API devuelve `powerProduction: null`

**Solución:**
1. Activa los logs de depuración (ver más abajo)
2. Busca líneas con "Datos recibidos de la API" y "Datos extraídos"
3. Verifica que `powerProduction` no sea `null` en la respuesta
4. Revisa los logs para ver si hay errores de API
5. Reduce el intervalo de actualización en las opciones de la integración
6. Los reintentos automáticos intentarán reconectar automáticamente

**Ejemplo de logs correctos:**
```
DEBUG Datos recibidos de la API: {'powerProduction': 5.727, 'time': '2025-11-04T14:17:30.005Z', ...}
DEBUG Datos extraídos - Potencia: 5727.00 W, Timestamp: 2025-11-04T14:17:30.005Z
```

### El factor de participación es incorrecto

**Solución:**
1. Ve a **Opciones** de la integración
2. Introduce manualmente tu factor de participación correcto
3. Acepta formato decimal con punto (0.025) o coma (0,025)

### Los valores de energía son incorrectos

**Posibles causas:**
- El sensor se reinició recientemente
- Cambios en el intervalo de actualización

**Solución:**
- Los sensores de energía integran la potencia a lo largo del tiempo
- Si los valores parecen incorrectos, puedes resetear la integración o esperar a que se estabilicen

## 📝 Logs y Depuración

Para activar logs detallados, añade a tu `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.sentinel_solar: debug
```

Esto mostrará información detallada sobre:
- Peticiones API y tiempos de respuesta
- Reintentos automáticos
- Validaciones de datos
- Actualizaciones de sensores

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Haz fork del repositorio
2. Crea una rama para tu característica (`git checkout -b feature/NuevaCaracteristica`)
3. Commit tus cambios (`git commit -m 'Añadir nueva característica'`)
4. Push a la rama (`git push origin feature/NuevaCaracteristica`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## 🙏 Créditos

- Desarrollado por [@borja](https://github.com/borja)
- Integración para [Home Assistant](https://www.home-assistant.io/)
- API proporcionada por [Sentinel Solar](https://sentinel-solar.com)

## 📧 Soporte

Si tienes problemas o preguntas:

1. Revisa la sección [Solución de Problemas](#-solución-de-problemas)
2. Consulta los [Issues existentes](https://github.com/borja/sentinel_solar/issues)
3. Abre un [nuevo Issue](https://github.com/borja/sentinel_solar/issues/new) si es necesario

---

**⚡ Disfruta monitorizando tu energía solar con sentinel_solar en Home Assistant (proyecto no oficial de Sentinel Solar).**

