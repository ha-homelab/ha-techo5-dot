# HA · TECHO5 Dot

**Los dos Echo Dot 2 ejecutan TECHO5 y se conectan directamente a Home Assistant. Las comprobaciones técnicas se han completado; quedan las pruebas de escucha.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md)

**Ambos Dot ejecutan la versión experimental v1.0.40-myshka.1.beta.1.** `duck_music` permite anuncios sobre música atenuada; `skip` sigue siendo el valor predeterminado. La instalación y la verificación de hashes finalizaron en ambos dispositivos. Es una compilación independiente del daemon, no una actualización OTA firmada. Consulte las [pruebas y limitaciones](docs/guarded-announcement-ducking.md).

El modelo personal se convirtió de ONNX a OWW TFLite y se cargó en openWakeWord. Su nombre único en los ajustes es **«Привет, Мышка (personal)»**; la frase hablada sigue siendo **«Привет, Мышка»**. El umbral verificado es **0.5**, sin una segunda palabra de activación. Ambos selectores de Assist usan **Local Russian Home**; el proxy BLE y las respuestas en streaming están activados. Aún hay que evaluar distancia, falsas activaciones, latencia y música.

La preparación y la reparación de cache tienen su propio registro. Las antiguas copias completas de Alexa se eliminaron deliberadamente; se conserva un conjunto limitado de archivos de recuperación para esta transición.

Guías detalladas, actualmente en inglés: [estado](docs/status.md), [migración](docs/migration.md), [palabra de activación](docs/wake-word.md), [Home Assistant](docs/home-assistant.md), [aceptación](docs/acceptance.md).

[Actualización a v1.0.35 mediante HA](docs/updates.md).
