# HA · TECHO5 Dot

Signierte Firmware-Updates sind im [Myshka-OTA-Leitfaden](docs/signed-ota.md) beschrieben. Die neue Build-Reihe verwendet TECHO5 v1.0.44, einen eigenen Signaturschlüssel und Repository-Kanäle. Das persönliche Aktivierungsmodell und die Musikabsenkung bleiben erhalten.

**Beide Echo Dot 2 laufen jetzt mit TECHO5 und sind direkt mit Home Assistant verbunden. Die technischen Prüfungen sind bestanden; Hörtests stehen noch aus.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md)

**Beide Dots verwenden v1.0.44-beta.202_myshka2**, über die Firmware-Aktion in Home Assistant aus unserem signierten Kanal **myshka-beta** installiert. Das vollständige System enthält die AirPlay-IPv6-Korrektur von TECHO5 v1.0.44 und behält das persönliche Aktivierungsmodell, Ansagen und Musikabsenkung bei. Die automatische Installation bleibt ausgeschaltet. Siehe [OTA und Wiederherstellung](docs/signed-ota.md) und [Prüfergebnisse](docs/status.md).

Das persönliche Modell wurde von ONNX nach OWW TFLite konvertiert und von openWakeWord geladen. Sein eindeutiger Einstellungsname lautet **«Привет, Мышка (personal)»**; gesprochen wird weiterhin **«Привет, Мышка»**. Bestätigt sind ein Schwellenwert von **0.5** und kein zweites Aktivierungswort. Beide Assist-Auswahlen verwenden **Local Russian Home**; BLE-Proxy und gestreamte Antworten sind aktiviert. Erkennung auf Entfernung, Fehlaktivierungen, Latenz und Musik müssen noch geprüft werden.

Vorbereitung und Cache-Reparatur sind separat dokumentiert. Alte vollständige Alexa-Sicherungen wurden bewusst gelöscht; für diesen Übergang bleibt ein begrenzter Satz von Wiederherstellungsdateien erhalten.

Ausführliche Anleitungen sind derzeit auf Englisch: [Status](docs/status.md), [Migration](docs/migration.md), [Wake Word](docs/wake-word.md), [Home Assistant](docs/home-assistant.md), [Abnahme](docs/acceptance.md).

[Update auf v1.0.35 über HA](docs/updates.md).

Siehe [Funktionsübersicht und Erweiterungsplan](docs/capabilities.md) mit Aktionskatalog und Diagnosekarte (auf Englisch).
[Zusätzliche HA-Funktionen](docs/capability-package.md): Lichtring, Timer,
Wecker, Erinnerungen, Ansagen und Diagnose. [Zugriff und Medien](docs/capability-access.md)
und [Bereitstellungsbericht](docs/capability-deployment.md) sind auf Englisch.

[SIP-Telefon an der eigenen Telefonanlage](docs/phone.md): Einrichtung und separate Anrufprüfung (Englisch).
