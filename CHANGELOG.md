# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [2.0.1] - 2025-11-04

### 🐛 Corregido

- **Icono de la integración**: Renombrado `image.png` a `icon.png` para que Home Assistant lo muestre correctamente en la interfaz

---

## [2.0.0] - 2025-11-04

### 🎉 Cambio Mayor - Nueva Arquitectura

**⚠️ BREAKING CHANGES**: Esta versión cambia significativamente la estructura de sensores.

#### ✨ Añadido

- **Controles de configuración en tiempo real** (Number entities):
  - `number.factor_de_participacion`: Ajusta tu porcentaje de participación (0..1) sin recargar
  - `number.intervalo_de_actualizacion`: Cambia los minutos entre lecturas (1-1440) sin recargar
  
- **Soporte para múltiples configuraciones**:
  - Puedes añadir la misma integración varias veces con diferentes Asset IDs
  - Ejemplo: Asset con factor 1.0 para ver el total de la comunidad
  - Ejemplo: Asset con factor 0.025 para ver solo tu porción

#### 🔧 Cambiado

- **Simplificación de sensores** (de 4 a 2):
  - ❌ Eliminado: `sensor.potencia_general` → ✅ Ahora: `sensor.potencia`
  - ❌ Eliminado: `sensor.potencia_mi_porcion`
  - ❌ Eliminado: `sensor.energia_general` → ✅ Ahora: `sensor.energia`
  - ❌ Eliminado: `sensor.energia_mi_porcion`
  
- **Los sensores ahora aplican automáticamente el factor de participación**:
  - Si factor = 1.0 → muestra el total de la instalación
  - Si factor = 0.025 → muestra tu porción (2.5%)
  
- **Nombres más limpios**:
  - Eliminado término "General" (confundía según el contexto)
  - Los sensores se llaman simplemente "Potencia" y "Energía"

- **Atributos mejorados**:
  - `raw_power`: Potencia sin aplicar factor (W)
  - `share_factor`: Factor aplicado actual
  
#### 📝 Migración

Si actualizas desde v1.x:

1. **Elimina la integración antigua**
2. **Reinicia Home Assistant**
3. **Vuelve a añadir la integración**
4. **Configura tus assets**:
   - Para el total: Añade con factor = 1.0
   - Para tu porción: Añade con tu factor real (ej: 0.025)

#### 🎯 Beneficios

- ✅ Más flexible: añade múltiples assets sin duplicar código
- ✅ Configuración en vivo: cambia factor/intervalo sin recargar
- ✅ Menos confusión: nombres más claros según tu configuración
- ✅ Menos sensores: solo los necesarios (2 en lugar de 4)

---

## [1.0.2] - 2025-11-04

### 🐛 Corregido

- **FIX CRÍTICO**: Eliminado `last_reset` de sensores de energía
  - Los sensores con `state_class = TOTAL_INCREASING` no deben usar `last_reset`
  - Solucionado error: "Setting last_reset for entities with state_class other than 'total' is not supported"
  - Los sensores de energía ahora se crean correctamente en Home Assistant
  - Compatible con Home Assistant 2023.1+

---

## [1.0.1] - 2025-11-04

### 🐛 Corregido

- **FIX CRÍTICO**: Corrección en la extracción de datos de la API
  - Ahora busca correctamente el campo `powerProduction` (en kW) de la respuesta de la API
  - Conversión automática de kW a W (multiplicación por 1000)
  - Ahora busca el campo `time` como timestamp principal
  - Añadido logging de depuración para ver los datos recibidos y extraídos
  
### 🔧 Mejorado

- Prioridad en la búsqueda de campos: `powerProduction` → `power` → `activePower`
- Prioridad en la búsqueda de timestamp: `time` → `timestamp` → `ts` → `updatedAt`
- Validación de valores `null` en `powerProduction`

---

## [1.0.0] - 2025-11-04

### 🎉 Primera versión de producción

#### ✨ Añadido

- **Reintentos automáticos con backoff exponencial** para mejorar la fiabilidad
  - Reintentos automáticos para códigos de error 429, 500, 502, 503, 504
  - Backoff exponencial: 1s, 2s, 4s entre reintentos
  - Hasta 3 intentos por defecto
  - Logging detallado de reintentos

- **Validación de datos mejorada**
  - Detección de valores de potencia anormales (>10 MW o <-100 kW)
  - Validación de timestamps (futuros o muy antiguos)
  - Logging de advertencias cuando se detectan valores anómalos
  - Limitación automática de valores fuera de rango

- **Sistema de métricas de rendimiento**
  - Contador de peticiones totales, exitosas y fallidas
  - Contador de reintentos totales
  - Tiempo promedio de respuesta de la API
  - Tiempo de la última petición
  - Método `get_metrics()` para consultar métricas

- **Documentación completa**
  - README.md detallado con instrucciones de instalación y uso
  - Guía de solución de problemas
  - Documentación de características avanzadas
  - Ejemplos de configuración
  - Sección de contribución

- **Archivos de proyecto**
  - LICENSE (MIT)
  - .gitignore completo
  - hacs.json para compatibilidad con HACS
  - CHANGELOG.md

- **Información del dispositivo (Device Info)**
  - Todos los sensores agrupados bajo un único dispositivo
  - Información del asset (nombre, tipo, versión de firmware)
  - URL de configuración al portal de Sentinel Solar

#### 🔧 Mejorado

- **Manejo de errores robusto**
  - Mejor gestión de errores de conexión
  - Reintentos automáticos para errores temporales
  - Mensajes de error más descriptivos
  - Logging estructurado con contexto

- **Sensores de energía**
  - Compatible con el Panel de Energía de Home Assistant
  - Persistencia de estado al reiniciar Home Assistant
  - Integración rectangular mejorada con timestamps de la API
  - Atributo `last_reset` correctamente implementado

- **Cacheo de información del asset**
  - Reducción de llamadas innecesarias a la API
  - Obtención de información del asset al iniciar
  - Uso de información cacheada en todos los sensores

- **Traducciones**
  - Soporte completo para Español, Inglés y Catalán
  - Estructura de errores corregida y simplificada
  - Mensajes de error más claros

- **Manifest actualizado**
  - Versión 1.0.0 lista para producción
  - URL de documentación válida
  - integration_type definido como "hub"

#### 🐛 Corregido

- Estructura de claves de error en archivos de traducción
- Validación correcta del share_factor (acepta punto y coma como separador decimal)
- Manejo de timeouts y errores de conexión
- Detección de valores de potencia negativos (consumo)

#### 📚 Documentación

- Guía de instalación paso a paso (HACS y manual)
- Instrucciones de configuración detalladas
- Cómo obtener credenciales (Token y Asset ID)
- Uso en el Panel de Energía
- Características avanzadas explicadas
- Solución de problemas común
- Activación de logs de depuración

---

## [0.2.0] - 2025-XX-XX

### Añadido

- Sensores de energía acumulada (kWh)
- Factor de participación configurable
- Opciones de configuración (OptionsFlow)
- Obtención automática del share_factor desde la API
- Cacheo de información del asset

### Mejorado

- Config Flow con validación de datos
- Manejo de errores básico
- Estructura de sensores con clase base

---

## [0.1.0] - 2025-XX-XX

### 🎉 Versión inicial

- Sensores básicos de potencia (W)
- Config Flow para configuración inicial
- Integración con API de Sentinel Solar
- Soporte multiidioma básico

