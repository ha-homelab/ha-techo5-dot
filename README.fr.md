# HA · TECHO5 Dot

**Un Echo Dot 2 fonctionne maintenant sous TECHO5 et est directement associé à Home Assistant. Les essais vocaux et musicaux restent à effectuer.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md)

Le pilote fonctionne sous **TECHO5 Dot v1.0.35, emplacement b**. L'installateur a confirmé un démarrage sain ; l'API répond et l'association chiffrée avec HA est terminée. Le second Dot est hors ligne et inchangé. Un redémarrage logiciel a confirmé le bon démarrage et la conservation de l’association et des réglages du modèle personnel. Les essais pratiques de voix et de musique restent à faire.

Le modèle personnel a été converti d'ONNX en OWW TFLite et chargé par openWakeWord. Son libellé unique dans les réglages est **«Привет, Мышка (personal)»** ; la phrase prononcée reste **«Привет, Мышка»**. Le seuil vérifié est **0.5**, sans second mot d'activation. Les deux sélecteurs Assist utilisent **Local Russian Home** ; le proxy BLE et les réponses en streaming sont activés. La portée, les faux déclenchements, la latence et la musique restent à vérifier.

La préparation et la réparation de cache sont consignées séparément. Les anciennes sauvegardes complètes d'Alexa ont été supprimées volontairement ; un ensemble limité de fichiers de récupération est conservé pour cette transition.

Guides détaillés, actuellement en anglais : [état](docs/status.md), [migration](docs/migration.md), [mot d'activation](docs/wake-word.md), [Home Assistant](docs/home-assistant.md), [validation](docs/acceptance.md).

[Mise à jour vers v1.0.35 via HA](docs/updates.md).
