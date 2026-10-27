# HA · TECHO5 Dot

**Un Echo Dot 2 ya ejecuta TECHO5 y está conectado directamente con Home Assistant. Las pruebas de voz y música siguen pendientes.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md)

El dispositivo piloto ejecuta **TECHO5 Dot v1.0.35, ranura b**. El instalador confirmó un arranque correcto; la API responde y el emparejamiento cifrado con HA se completó. El segundo Dot está desconectado y sin cambios. Un reinicio por software confirmó el arranque correcto y conservó el emparejamiento y los ajustes del modelo personal. Las pruebas prácticas de voz y música siguen pendientes.

El modelo personal se convirtió de ONNX a OWW TFLite y se cargó en openWakeWord. Su nombre único en los ajustes es **«Привет, Мышка (personal)»**; la frase hablada sigue siendo **«Привет, Мышка»**. El umbral verificado es **0.5**, sin una segunda palabra de activación. Ambos selectores de Assist usan **Local Russian Home**; el proxy BLE y las respuestas en streaming están activados. Aún hay que evaluar distancia, falsas activaciones, latencia y música.

La preparación y la reparación de cache tienen su propio registro. Las antiguas copias completas de Alexa se eliminaron deliberadamente; se conserva un conjunto limitado de archivos de recuperación para esta transición.

Guías detalladas, actualmente en inglés: [estado](docs/status.md), [migración](docs/migration.md), [palabra de activación](docs/wake-word.md), [Home Assistant](docs/home-assistant.md), [aceptación](docs/acceptance.md).

[Actualización a v1.0.35 mediante HA](docs/updates.md).
