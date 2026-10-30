# HA · TECHO5 Dot

**Les deux Echo Dot 2 fonctionnent sous TECHO5 et se connectent directement à Home Assistant. Les vérifications techniques sont terminées ; les essais d’écoute restent distincts.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md)

**Les deux Dot utilisent v1.0.40 après la mise à jour OTA signée du 29 octobre.** La migration du 28 octobre a conservé le modèle personnel, configuré la connexion chiffrée, actualisé le tableau de bord et les destinations musicales, puis supprimé les anciens enregistrements EchoMuse. Un redémarrage logiciel a été vérifié. Les deux proxies Bluetooth transmettent de nouvelles annonces. Les essais vocaux et musicaux restent une étape distincte. Voir le [statut](docs/status.md).

Le modèle personnel a été converti d'ONNX en OWW TFLite et chargé par openWakeWord. Son libellé unique dans les réglages est **«Привет, Мышка (personal)»** ; la phrase prononcée reste **«Привет, Мышка»**. Le seuil vérifié est **0.5**, sans second mot d'activation. Les deux sélecteurs Assist utilisent **Local Russian Home** ; le proxy BLE et les réponses en streaming sont activés. La portée, les faux déclenchements, la latence et la musique restent à vérifier.

La préparation et la réparation de cache sont consignées séparément. Les anciennes sauvegardes complètes d'Alexa ont été supprimées volontairement ; un ensemble limité de fichiers de récupération est conservé pour cette transition.

Guides détaillés, actuellement en anglais : [état](docs/status.md), [migration](docs/migration.md), [mot d'activation](docs/wake-word.md), [Home Assistant](docs/home-assistant.md), [validation](docs/acceptance.md).

[Mise à jour vers v1.0.35 via HA](docs/updates.md).

Consultez [l’audit des fonctions et le plan d’extension](docs/capabilities.md), avec catalogue des actions et carte de diagnostic (en anglais).
[Fonctions HA supplémentaires](docs/capability-package.md) : anneau lumineux,
minuteurs, alarmes, rappels, annonces et diagnostic. [Accès et médias](docs/capability-access.md)
et [rapport de déploiement](docs/capability-deployment.md), en anglais.

[Téléphone SIP avec votre propre PBX](docs/phone.md) : configuration et vérification distincte des appels (en anglais).
