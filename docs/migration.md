# Compatibility and migration

## Supported hardware

Our pilot targets **Echo Dot 2, RS03QR / biscuit**. Upstream also supports **Echo 2, XC56PY / radar**, and **2018 Dot 3, D9N29T / donut**. Dot 3's **2019 C78MP8 / crumpet** and clock variant **doebrite** are excluded. Our full-size **SK705DI** is not an established target. [Dot 3 identification](https://github.com/HuskerMinion/techo5-dot/blob/88b26703d5e1a97d5ce0fee90805e8a3dd206a95/docs/hardware-donut.md#L10-L21) · [Echo 2 identification](https://github.com/HuskerMinion/techo5-dot/blob/88b26703d5e1a97d5ce0fee90805e8a3dd206a95/docs/hardware-radar.md#L32-L48)

## Starting from emOS

emOS exposes a USB serial console rather than the USB ADB interface expected by the TECHO5 installer. On a device that already has working TWRP, emOS provides a normal administrator control to reboot into that recovery: `/init recovery`. Upstream documents this route from emOS 0.4 onward. Confirm the intended device then appears in ADB as `recovery`; a ring color alone does not establish which environment is running. [Official emOS recovery control](https://github.com/wilbowes/EchoMuse/blob/00d108b18383f73efb403886a73c88d63f7872d8/emos/README.md#getting-to-twrp-init-recovery)

The TECHO5 installer accepts an already-unlocked Dot 2 running TWRP or Fire OS with root ADB. Its documented retained-system requirement is **Fire OS 6574.1, NS6574 build 7623**, which supplies drivers matching the Dot 2 kernel. The installer checks for the broader string `Fire OS 6`, so verify the exact build independently. Our October 26 pilot confirmed that build and existing TWRP before proceeding. A direct emOS filesystem replacement or an EchoMuse OTA carrying TECHO5 is not a documented migration route. [Upstream requirements](https://github.com/HuskerMinion/techo5-dot/blob/88b26703d5e1a97d5ce0fee90805e8a3dd206a95/tools/install-dot.py#L16-L31) · [Exact build and TWRP support](https://github.com/HuskerMinion/techo5/blob/main/docs/getting-started.md#echo-dot-2nd-gen)

Use reviewed installer source and an explicit release tag. [upstream-lock.json](../upstream-lock.json) preserves the original v1.0.34 pilot baseline; the dated [deployment status](status.md) records the v1.0.38 source pin used for the remaining Dot on October 28. The upstream default selects the latest release, which may differ from the reviewed pilot. Its `--dry-run` mode creates local backups, downloads and a per-device image, and may create a private HA key; it also mounts filesystems in recovery. That mode skips the final installation but is not a forensic read-only operation. Keep its output and generated material private.

The normal migration sequence is:

1. Confirm the board, active device identity, USB connection and current configuration.
2. Use the existing emOS administrator control to enter the already-installed TWRP; verify recovery and root ADB.
3. Verify the retained system build and the health of the filesystems the installer needs. Resolve an unmountable cache before running installation; see [the emOS cache recovery record](emOS-cache-recovery.md).
4. Preserve and verify the bounded, per-device rollback material described below, then review the pinned installer's preflight results.
5. Install through the supported recovery route, then require a healthy boot and a reachable Home Assistant API.
6. Review the HA identity and pairing deliberately. Automatic preservation reads old EchoLocal settings, which may differ from the active EchoMuse Controller identity. Follow [Home Assistant integration](home-assistant.md) and complete [device acceptance](acceptance.md).

These steps assume the existing administrative access and recovery are already functional. This repository provides no unlocking, boot-verification bypass or improvised partition-writing procedure.

## Recovery boundary

Preserve configuration and the exact minimal recovery material required by the verified method: the current per-device boot image, its working recovery image and boot-selection metadata, the installer's required boot-critical backups and checksums, and any filesystem-repair evidence and undo file. Keep personal models, pairing keys and configuration private. Do not recreate indiscriminate full-disk archives: earlier full Alexa backups were intentionally deleted. Configuration alone is not OS rollback.

The October 26 pilot encountered an unmountable cache caused by the emOS 0.10 boot-trail behavior. Standard metadata repair using a surviving backup superblock and an undo file succeeded; a subsequent read-only filesystem check returned exit code 0. This cleared a filesystem prerequisite. The later successful installation and remaining voice acceptance are recorded in [pilot status](status.md). **Booting the old emOS image again can corrupt the repaired cache again**, including a TECHO5 store placed there. See the [cause, repair result and rollback limits](emOS-cache-recovery.md).

TECHO5's signed A/B updates protect later TECHO5 root-filesystem updates. They do not establish a return path to emOS or guarantee recovery from every initial-installation/kernel failure. The upstream SSH boot updater is for devices **already running TECHO5**. [Updater scope](https://github.com/HuskerMinion/techo5-dot/blob/88b26703d5e1a97d5ce0fee90805e8a3dd206a95/tools/update-boot.py#L1-L24)

Upstream's return-to-Fire-OS description assumes a Fire OS boot image was present before installation. This pilot starts from emOS, so the actual saved images and boot settings determine the return path; do not infer it from that label.
