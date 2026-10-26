# HA · TECHO5 Dot

**Ein Echo Dot 2 läuft jetzt mit TECHO5 und ist direkt mit Home Assistant gekoppelt. Sprach- und Musiktests stehen noch aus.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md)

Auf dem Pilotgerät läuft **TECHO5 Dot v1.0.35, Slot b**. Der Installer bestätigte einen erfolgreichen Start; die API antwortet und die verschlüsselte Kopplung mit HA ist abgeschlossen. Der zweite Dot ist offline und unverändert. Ein softwaregesteuerter Neustart bestätigte den gesunden Startzustand und den Erhalt der Kopplung und persönlichen Modelleinstellungen. Praktische Sprach- und Musiktests sind noch offen.

Das persönliche Modell wurde von ONNX nach OWW TFLite konvertiert und von openWakeWord geladen. Sein eindeutiger Einstellungsname lautet **«Привет, Мышка (personal)»**; gesprochen wird weiterhin **«Привет, Мышка»**. Bestätigt sind ein Schwellenwert von **0.5** und kein zweites Aktivierungswort. Beide Assist-Auswahlen verwenden **Local Russian Home**; BLE-Proxy und gestreamte Antworten sind aktiviert. Erkennung auf Entfernung, Fehlaktivierungen, Latenz und Musik müssen noch geprüft werden.

Vorbereitung und Cache-Reparatur sind separat dokumentiert. Alte vollständige Alexa-Sicherungen wurden bewusst gelöscht; für diesen Übergang bleibt ein begrenzter Satz von Wiederherstellungsdateien erhalten.

Ausführliche Anleitungen sind derzeit auf Englisch: [Status](docs/status.md), [Migration](docs/migration.md), [Wake Word](docs/wake-word.md), [Home Assistant](docs/home-assistant.md), [Abnahme](docs/acceptance.md).

[Update auf v1.0.35 über HA](docs/updates.md).
