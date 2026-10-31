# HA · TECHO5 Dot

Las actualizaciones firmadas se describen en la [guía OTA de Myshka](docs/signed-ota.md). La nueva serie usa TECHO5 v1.0.44, una clave de firma propia y canales de este repositorio. Conserva el modelo personal de activación y la atenuación de música.

**Los dos Echo Dot 2 ejecutan TECHO5 y se conectan directamente a Home Assistant. Las comprobaciones técnicas se han completado; quedan las pruebas de escucha.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md)

**Ambos Dot ejecutan v1.0.44-beta.202_myshka2**, instalada mediante Firmware en Home Assistant desde nuestro canal firmado **myshka-beta**. El sistema completo incorpora la corrección de AirPlay IPv6 de TECHO5 v1.0.44 y conserva el modelo personal de activación, los anuncios y la atenuación de música. La instalación automática sigue desactivada. Consulte [OTA y recuperación](docs/signed-ota.md) y los [resultados](docs/status.md).

El modelo personal se convirtió de ONNX a OWW TFLite y se cargó en openWakeWord. Su nombre único en los ajustes es **«Привет, Мышка (personal)»**; la frase hablada sigue siendo **«Привет, Мышка»**. El umbral verificado es **0.5**, sin una segunda palabra de activación. Ambos selectores de Assist usan **Local Russian Home**; el proxy BLE y las respuestas en streaming están activados. Aún hay que evaluar distancia, falsas activaciones, latencia y música.

La preparación y la reparación de cache tienen su propio registro. Las antiguas copias completas de Alexa se eliminaron deliberadamente; se conserva un conjunto limitado de archivos de recuperación para esta transición.

Guías detalladas, actualmente en inglés: [estado](docs/status.md), [migración](docs/migration.md), [palabra de activación](docs/wake-word.md), [Home Assistant](docs/home-assistant.md), [aceptación](docs/acceptance.md).

[Actualización a v1.0.35 mediante HA](docs/updates.md).

Consulta la [auditoría de funciones y el plan de ampliación](docs/capabilities.md), con catálogo de acciones y tarjeta de diagnóstico (en inglés).
[Funciones adicionales de HA](docs/capability-package.md): anillo, temporizadores,
alarmas, recordatorios, anuncios y diagnóstico. [Acceso y medios](docs/capability-access.md)
e [informe de implementación](docs/capability-deployment.md), en inglés.

[Teléfono SIP con una centralita propia](docs/phone.md): configuración y comprobación separada de llamadas (en inglés).
