# HA · TECHO5 Dot

**Beide Echo Dot 2 laufen jetzt mit TECHO5 und sind direkt mit Home Assistant verbunden. Die technischen Prüfungen sind bestanden; Hörtests stehen noch aus.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md)

**Beide Dots laufen nach dem signierten OTA-Update vom 28. Oktober mit v1.0.39.** Bei der Migration am 28. Oktober wurden das persönliche Aktivierungsmodell erhalten, die verschlüsselte Verbindung eingerichtet, Dashboard und Musikzuordnung aktualisiert und alte EchoMuse-Einträge entfernt. Ein Software-Neustart wurde geprüft. Beide Bluetooth-Proxys liefern neue Meldungen. Sprach- und Musikhörtests sind ein eigener Prüfschritt. Siehe [Status](docs/status.md).

Das persönliche Modell wurde von ONNX nach OWW TFLite konvertiert und von openWakeWord geladen. Sein eindeutiger Einstellungsname lautet **«Привет, Мышка (personal)»**; gesprochen wird weiterhin **«Привет, Мышка»**. Bestätigt sind ein Schwellenwert von **0.5** und kein zweites Aktivierungswort. Beide Assist-Auswahlen verwenden **Local Russian Home**; BLE-Proxy und gestreamte Antworten sind aktiviert. Erkennung auf Entfernung, Fehlaktivierungen, Latenz und Musik müssen noch geprüft werden.

Vorbereitung und Cache-Reparatur sind separat dokumentiert. Alte vollständige Alexa-Sicherungen wurden bewusst gelöscht; für diesen Übergang bleibt ein begrenzter Satz von Wiederherstellungsdateien erhalten.

Ausführliche Anleitungen sind derzeit auf Englisch: [Status](docs/status.md), [Migration](docs/migration.md), [Wake Word](docs/wake-word.md), [Home Assistant](docs/home-assistant.md), [Abnahme](docs/acceptance.md).

[Update auf v1.0.35 über HA](docs/updates.md).
