# Compatibility and migration

## Supported hardware

Our pilot targets **Echo Dot 2, RS03QR / biscuit**. Upstream also supports **Echo 2, XC56PY / radar**, and **2018 Dot 3, D9N29T / donut**. Dot 3's **2019 C78MP8 / crumpet** and clock variant **doebrite** are excluded. Our full-size **SK705DI** is not an established target. [Dot 3 identification](https://github.com/HuskerMinion/techo5-dot/blob/88b26703d5e1a97d5ce0fee90805e8a3dd206a95/docs/hardware-donut.md#L10-L21) · [Echo 2 identification](https://github.com/HuskerMinion/techo5-dot/blob/88b26703d5e1a97d5ce0fee90805e8a3dd206a95/docs/hardware-radar.md#L32-L48)

## Starting from emOS

The current device provides an authenticated EchoMuse console and a USB serial console. It does not provide the USB ADB interface expected by the TECHO5 installer. The documented installer starts from a supported Fire OS 6/recovery environment; its tested baseline is Fire OS 6574.1. A direct emOS filesystem replacement is not documented. [Upstream requirements](https://github.com/HuskerMinion/techo5-dot/blob/88b26703d5e1a97d5ce0fee90805e8a3dd206a95/README.md#L133-L180)

Proceed only after identifying a supported route for the actual device. Existing recovery and retained system material must be verified; historical installation records alone do not prove their present condition. This repository provides no unlocking, boot-verification bypass or improvised partition-writing procedure.

## Recovery boundary

Preserve configuration and the exact minimal recovery material required by the verified method. Do not recreate indiscriminate full-disk archives: earlier full Alexa backups were intentionally deleted. Configuration alone is not OS rollback.

TECHO5's signed A/B updates protect later TECHO5 root-filesystem updates. They do not establish a return path to emOS or guarantee recovery from every initial-installation/kernel failure. The upstream SSH boot updater is for devices **already running TECHO5**. [Updater scope](https://github.com/HuskerMinion/techo5-dot/blob/88b26703d5e1a97d5ce0fee90805e8a3dd206a95/tools/update-boot.py#L1-L24)
