# sentinel_solar

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2023.1+-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

Integración personalizada para Home Assistant que creé para integrar los consumos y la producción de mi comunidad solar. Gracias a **Km0 Energy** por impulsar y mantener la comunidad que inspiró este proyecto. Este componente no es oficial de Sentinel Solar.

## Qué aporta

- Monitoriza potencia y energía en tiempo real desde la API de Sentinel Solar.
- Ajusta al vuelo el intervalo de actualización y el factor de participación.
- Permite múltiples configuraciones para combinar comunidad y consumo propio.
- Usa `sensor.energia` para el Panel de Energía de Home Assistant sin pasos extra.
- Disponible en español, inglés y catalán, con configuración guiada (config flow).

## Instalación

### HACS (recomendado)
1. HACS → Integraciones → menú (⋮) → Repositorios personalizados.
2. Añade `https://github.com/borja/sentinel_solar` como categoría *Integración*.
3. Busca `sentinel_solar`, instala y reinicia Home Assistant.

### Manual
1. Descarga la última release.
2. Copia `custom_components/sentinel_solar/` dentro de `<config>/custom_components/`.
3. Reinicia Home Assistant.

## Configuración básica

- **Base URL** (opcional, por defecto `https://apiv3.sentinel-solar.com`).
- **Token** y **Asset ID** se obtienen desde el portal de Sentinel Solar (inspecciona las llamadas de red del navegador).
- **Minutos entre lecturas** y **Factor de participación** pueden ajustarse en Opciones tras la instalación.

> En muchos assets particulares el factor de participación ya viene aplicado, así que introduce **Factor de participación = 1** para que los valores coincidan con tu producción real.

## Entidades creadas

- `sensor.potencia`: potencia instantánea en W, con atributos de potencia bruta y factor aplicado.
- `sensor.energia`: energía acumulada en kWh; añádelo directamente al Panel de Energía.
- `number.factor_de_participacion`: factor configurable (0..1).
- `number.intervalo_de_actualizacion`: intervalo entre lecturas (1-1440 minutos).

## Agradecimientos

- Km0 Energy, por la comunidad solar que motivó este desarrollo.
- La comunidad de Home Assistant, por la inspiración y soporte continuo.

¡Disfruta monitorizando tus datos solares con `sentinel_solar`! Las contribuciones y sugerencias son bienvenidas.

