# emOS cache filesystem recovery

**Recovery checkpoint: October 26, 2026.** The cache filesystem was repaired and passed a read-only check before installation continued. This record covers the repair only; see [pilot status](status.md) for the later successful installation and pairing, and the remaining voice acceptance.

## What stopped the pilot

The intended Dot 2 reached its existing TWRP with root ADB, and its retained system matched NS6574 build 7623. The TECHO5 preflight then stopped because cache would not mount. Userdata mounted successfully. Cache was not recognized as a valid filesystem and its primary ext4 signature was missing.

This was a damaged-filesystem case, not evidence that cache was empty or safe to format. TECHO5 needs a working ext4 cache on Dot 2: it stores its root-filesystem slots there. The reviewed installer tries to mount cache and stops on failure; it has no automatic format or repair fallback. [Installer checks](https://github.com/HuskerMinion/techo5-dot/blob/88b26703d5e1a97d5ce0fee90805e8a3dd206a95/tools/install-dot.py#L272-L290)

## Cause and upstream correction

The source for `emos-v0.10`, commit `6a7f6625ed3023a0d5a7a1990cef77a4a13081f1`, writes its boot-progress trail starting at byte 1024 of cache. That overlaps ext4's primary superblock. The offset and the write are both present in the tagged source; this is not a conclusion based only on the missing signature. [Offset](https://github.com/wilbowes/EchoMuse/blob/6a7f6625ed3023a0d5a7a1990cef77a4a13081f1/emos/init/init.c#L50) · [Boot-trail write](https://github.com/wilbowes/EchoMuse/blob/6a7f6625ed3023a0d5a7a1990cef77a4a13081f1/emos/init/init.c#L1088)

Upstream fixed the behavior in [EchoMuse PR #1036](https://github.com/wilbowes/EchoMuse/pull/1036), merged as `00c6f32dafe3a2a31bb6712dd17347449d81bba2`. The corrected raw trail stays within the first 1024 bytes, ahead of the ext4 superblock, and later progress goes into a bounded file on userdata. Upstream notes that biscuit can have a surviving backup superblock, while the smaller single-group cache on donut may not. Do not generalize this Dot 2 recovery result to other boards. [Corrected source](https://github.com/wilbowes/EchoMuse/blob/00d108b18383f73efb403886a73c88d63f7872d8/emos/init/init.c#L50-L57)

## Diagnosis and repair boundary

The sequence used for this pilot was:

1. Stay in the existing TWRP. Identify cache from the device's actual partition mapping and verify that it is unmounted.
2. Inspect the filesystem signature and run a read-only check. Preserve the diagnostic output and relevant original metadata privately. A missing primary signature does not justify creating a new filesystem.
3. Establish the surviving ext4 geometry and backup superblock from this device. Do not copy a block number or filesystem layout from another Echo.
4. Use standard `e2fsck` metadata repair with that verified backup superblock and an undo file, after reviewing the read-only assessment. Keep the undo file outside the filesystem being repaired.
5. Run a separate read-only check before allowing the installer to use cache.

The actual repair used `e2fsck` preen/forced-check mode with a backup superblock and undo enabled. It succeeded, and the following `e2fsck -fn` check returned **exit code 0**. The undo file was **48 KiB**. Cache was not blindly formatted, and userdata was not wiped.

The `e2fsck` manual documents alternate-superblock recovery, conservative automatic repairs and recording overwritten blocks in an undo file. Its results are not valid evidence of filesystem health while that filesystem is mounted. An undo file is also not protection against a power or system crash. [Upstream manual](https://man7.org/linux/man-pages/man8/e2fsck.8.html)

This document intentionally omits device paths, geometry-specific repair commands and raw partition-write recipes. If no valid backup metadata survives, or the read-only assessment reports unresolved damage, this successful case is not a reason to force the repair or bypass the installer.

## Consequences for rollback

Repairing cache does not change the old emOS boot image. **A subsequent boot of the affected emOS version can overwrite the repaired superblock again.** Keep that in mind before returning to an old image: after TECHO5 installation, cache contains TECHO5's own store as well.

Retain the original per-device boot and recovery images, boot-selection metadata, the installer's required boot-critical backups and their checksums, current configuration, and the repair evidence/undo file. Store them privately with the intended device identified in the local manifest. This is a bounded recovery set, not a new full Alexa disk archive.

For this pilot, the compressed archive contains 13 boot-critical originals and the generated TECHO5 image: 14 files, approximately 50 MiB compressed. Every archive member was independently checked against the source manifest's size and SHA-256 checksum. The Mac copy uses file mode `0600`. This validates the saved bytes; it does not make an old emOS boot safe for the repaired cache.

The installer's boot-critical backups do not preserve all cache contents. The 48 KiB undo file covers this metadata repair only; it is not a backup of a later TECHO5 root filesystem or a general rollback image. A working mount and a clean check also do not establish boot health, networking, pairing, audio quality or wake-word accuracy. Those remain part of [device acceptance](acceptance.md).

Return to [compatibility and migration](migration.md).
