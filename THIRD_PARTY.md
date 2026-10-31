# Third-party sources

- [HuskerMinion/techo5-dot](https://github.com/HuskerMinion/techo5-dot): platform
  support, installation documentation and official release assets.
- [HuskerMinion/techo5](https://github.com/HuskerMinion/techo5): shared daemon,
  voice, audio and HA integration.
- [wilbowes/EchoMuse](https://github.com/wilbowes/EchoMuse): installed baseline.
- [ha-homelab/ha-echomuse](https://github.com/ha-homelab/ha-echomuse): deployment
  documentation and MIT-licensed public-data checker adapted here.
- [venus-os-ci-toolkit](https://github.com/victron-venus/venus-os-ci-toolkit):
  pinned shared CI and review workflows.

No affiliation or endorsement is implied. Downloaded assets and upstream code
retain their original licenses. This repository does not redistribute Amazon
firmware, owner recordings or personalized wake weights.

## Guarded announcement source overlay

`integrations/guarded-announcement/guarded-announcement.patch` contains source
context and modifications of TECHO5's shared daemon at commit
`892cdef6663acbb6ee963ed5862e363d61aff253`, Copyright (c) 2026 TECHO5 contributors.
The [upstream MIT license](integrations/guarded-announcement/TECHO5-MIT.txt) is
preserved. Added guarded announcement logic and the patch clearly identify the
local changes; this is not an official upstream release.

The build helper fetches upstream source and dependencies without copying them
into this repository. Their individual terms still apply to compiled artifacts;
the upstream `NOTICE` describes inherited EchoLocal code and other components.

## Signed Dot 2 distribution

The signed OTA line derives the exact TECHO5 Dot v1.0.44 rootfs and applies the
downstream daemon built from shared commit `b6a070fc6e62ec0e2636726619003e8c6505c4f8`.
See the [locked inputs](integrations/signed-ota/upstream-lock.json) and
[source collection instructions](integrations/signed-ota/README.md). Each release
ships an authenticated corresponding-source archive: exact project/daemon/platform
sources, upstream special media sources, Alpine recipes and original distfiles,
custom bluealsa patches, imported Go modules and their license notices.

These remain separate licensed components; this project's license does not
relicense them. The source inventory records five historical Alpine APK metadata
limitations explicitly. No kernel, OEM image, personal wake weights or device
configuration is distributed in the rootfs.
