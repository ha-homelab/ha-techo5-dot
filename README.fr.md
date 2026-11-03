# HA · TECHO5 Dot

La version bêta visée est **v1.0.49-beta.203_myshka2**, basée sur TECHO5 Dot v1.0.49. Elle conserve notre clé de signature, les canaux du dépôt, la prise en charge du modèle personnel de réveil et l’atténuation musicale pendant les annonces. Voir les [changements et limites](docs/upstream-1.0.49.md) et le [guide OTA Myshka](docs/signed-ota.md). Préparer ou publier cette bêta ne l’installe pas sur les appareils.

**Les deux Echo Dot 2 fonctionnent sous TECHO5 et se connectent directement à Home Assistant. Les vérifications techniques sont terminées ; les essais d’écoute restent distincts.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md)

**La dernière installation vérifiée sur les deux Dot (31 octobre) est v1.0.44-beta.202_myshka2**, installée via Firmware dans Home Assistant depuis notre canal signé **myshka-beta**. Le système complet intègre la correction AirPlay IPv6 de TECHO5 v1.0.44 et conserve le modèle personnel de réveil, les annonces et l’atténuation musicale. L’installation automatique reste désactivée. Voir [OTA et récupération](docs/signed-ota.md) et les [résultats](docs/status.md).

Le modèle personnel a été converti d'ONNX en OWW TFLite et chargé par openWakeWord. Son libellé unique dans les réglages est **«Привет, Мышка (personal)»** ; la phrase prononcée reste **«Привет, Мышка»**. Le seuil vérifié est **0.5**, sans second mot d'activation. Les deux sélecteurs Assist utilisent **Local Russian Home** ; le proxy BLE et les réponses en streaming sont activés. La portée, les faux déclenchements, la latence et la musique restent à vérifier.

La préparation et la réparation de cache sont consignées séparément. Les anciennes sauvegardes complètes d'Alexa ont été supprimées volontairement ; un ensemble limité de fichiers de récupération est conservé pour cette transition.

Guides détaillés, actuellement en anglais : [état](docs/status.md), [migration](docs/migration.md), [mot d'activation](docs/wake-word.md), [Home Assistant](docs/home-assistant.md), [validation](docs/acceptance.md).

[Mise à jour vers v1.0.35 via HA](docs/updates.md).

Consultez [l’audit des fonctions et le plan d’extension](docs/capabilities.md), avec catalogue des actions et carte de diagnostic (en anglais).
[Fonctions HA supplémentaires](docs/capability-package.md) : anneau lumineux,
minuteurs, alarmes, rappels, annonces et diagnostic. [Accès et médias](docs/capability-access.md)
et [rapport de déploiement](docs/capability-deployment.md), en anglais.

[Téléphone SIP avec votre propre PBX](docs/phone.md) : configuration et vérification distincte des appels (en anglais).
