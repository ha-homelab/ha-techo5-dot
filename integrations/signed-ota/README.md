# Signed Myshka Dot 2 rootfs releases

The builder and packager create a complete A/B rootfs update for already
converted Echo Dot 2 devices. They do not unlock devices, redistribute factory
firmware, flash boot partitions or contact Home Assistant. The separate
`publish.py` tool verifies and publishes signed assets when explicitly invoked. The installation and publication process is described in
[the signed OTA guide](../../docs/signed-ota.md).

## What is reproduced

`pack.py` derives a rootfs from the exact, signed public TECHO5 v1.0.44 release in
[`upstream-lock.json`](upstream-lock.json). It verifies the upstream manifest's
Ed25519 signature, its pinned SHA-256, and the rootfs size and SHA-256. The separate
upstream source bundle is pinned by SHA-256 and size; it is not covered by that
upstream manifest's signature.

The package keeps the upstream init, slot manager, operating-system files,
Bluetooth helpers, and media programs. It changes only these file contents:

- `usr/local/bin/echod`: our ARMv7 daemon with both reviewed patches applied.
- `etc/techo5-release`: the downstream version and project commit.
- `usr/share/myshka/provenance.json`: build and source input hashes.
- `usr/share/licenses/myshka/LICENSE`: this project's license.

Parent directories are added as needed. File modes and symbolic link targets are
preserved; archive ordering, owners, timestamps, and gzip headers are normalized.
The packager reads tar members without extracting them onto the host. It rejects
path traversal, duplicate names, hard links, device nodes, symlink children,
excessive expansion, and device-state paths.

This is a reproducible **derivation of a verified binary rootfs**, not a claim that
every upstream system binary has been rebuilt reproducibly. Two runs with identical
inputs, project commit, timestamps, Python version, and zlib version produce the
same output. Those runtime versions are recorded because gzip output can change
between zlib implementations. Python 3.11 or newer, Git, and OpenSSL 3 are required;
there are no third-party Python packages.

## Build and collect inputs

1. Download the locked upstream `manifest.json`, `manifest.json.sig`, rootfs, and
   `techo5-third-party-sources.tar.gz` into one local input directory. The packager
   performs verification; a file name alone is never trusted.
2. Keep Git checkouts containing the exact daemon and platform commits in the lock.
   The daemon is based on `b6a070fc6e62ec0e2636726619003e8c6505c4f8`; the platform is
   `7f91b238b91956f9da64bbc7ec3c1501ea3e7fe4`.
3. Run the builder, which applies the guarded-announcement patch and then
   [`native.patch`](native.patch), and retains a machine-readable `build.json`:

   ```sh
   python3 integrations/signed-ota/build.py \
     --work-dir private/myshka-ota-build \
     --source-cache private/upstream-techo5 \
     --version v1.0.44-beta.202_myshka2
   ```

4. Collect the corresponding sources described below. Do not substitute a list of
   download URLs for the actual source archives.
5. Commit the public patches and packaging instructions. The packager checks that
   this commit's two patches match the daemon's build record. Uncommitted patches
   cannot silently become an untraceable public binary.

`v1.0.44-beta.201_myshka2` is the bridge build and
`v1.0.44-beta.202_myshka2` is the first full OTA target.
`v1.0.44_myshka2` is the stable version shape. Home Assistant strips the underscore
suffix before comparing versions; the beta counter therefore belongs before it.
Increment that counter for another beta of the same upstream version. Do not
reuse a released version or change only the suffix to advertise an update.

## Package and sign offline

Use an existing Ed25519 seed file containing base64 of exactly 32 raw bytes. It
must be owned by the current user, a regular file with mode `0600`, and not a
symbolic link. The seed must correspond to the public key compiled into the
daemon. Never pass a seed value on the command line or commit it.

The example's timestamp variables and commit must be explicit release inputs.
The normal manifest lifetime is 180 days; the native safety limit is 366 days.

```sh
python3 integrations/signed-ota/pack.py \
  --upstream-dir private/upstream-release-v1.0.44 \
  --daemon private/myshka-ota-build/echod-arm-dot \
  --build-record private/myshka-ota-build/build.json \
  --release v1.0.44-beta.202_myshka2 \
  --channel beta \
  --published-at "$RELEASE_PUBLISHED_AT" \
  --expires-at "$RELEASE_EXPIRES_AT" \
  --source-date-epoch "$RELEASE_SOURCE_DATE_EPOCH" \
  --seed-file private/myshka-release-seed \
  --public-key 'VE1OZ3bqYzfSexvgIBbi6lGMkZW1VV22jnTTbogJBNw=' \
  --project-repo . \
  --project-commit "$RELEASE_PROJECT_COMMIT" \
  --daemon-repo private/upstream-techo5 \
  --platform-repo private/upstream-techo5-dot \
  --source-extra private/alpine-corresponding-sources.tar.gz \
  --source-extra private/bluealsa-corresponding-sources.tar.gz \
  --source-extra private/go-corresponding-sources.tar.gz \
  --out-dir private/myshka-release-v1.0.44-beta.202_myshka2
```

The output directory must not exist. A complete, verified release is staged in a
sibling temporary directory and moved into place only after successful signing.
Outputs are:

- `echod-arm-dot`
- `myshka-dot2-rootfs-<version>.tar.gz`
- `myshka-corresponding-sources-<version>.tar.gz`
- `release-provenance.json`
- `manifest.json` and `manifest.json.sig`
- `SHA256SUMS`

The signature covers the exact manifest bytes. The manifest binds distribution
`myshka-dot2`, schema 1, beta/stable channel, lifetime, and exactly one `arm-dot`
binary and rootfs. Their URLs point to immutable versioned assets in
`ha-homelab/ha-techo5-dot`. Source attachments are not firmware install targets and
do not appear in the manifest's firmware asset map. The separate signed
`release_artifacts` map binds the complete corresponding-source archive and
`release-provenance.json` by immutable URL, size, and SHA-256. The publisher checks
those signed records, not an untrusted replacement of `SHA256SUMS`. Individual
input archive hashes are also recorded inside the signed rootfs's provenance.

Publish complete immutable version assets before updating the separately signed
`myshka-beta` or `myshka-stable` channel pointer. The publisher must verify remote
bytes and refuse replacement of immutable assets. A channel's manifest/signature
pair is not an atomic two-file operation; mismatched pairs temporarily fail
signature verification instead of authorizing an unverified install. An expired
feed must be deliberately renewed by the maintainer.

## Corresponding sources and license scope

The source bundle contains Git archives of the exact project, upstream daemon,
and platform commits, the locked upstream third-party source archive, and every
`--source-extra` archive. The project retains its own license; packaged components
retain their respective licenses and notices. The kernel and factory firmware
are not included in this rootfs release.

The upstream source bundle covers its special media components, but **does not by
itself cover the Alpine rootfs and custom bluealsa**. A release source audit must
also collect:

- Alpine package origins, exact aports commits, `APKBUILD` recipes, referenced
  patches, and matching upstream source tarballs, checked against their SHA-512
  entries. Include the base rootfs, unpacked overlay packages, and static BusyBox.
- Custom bluealsa 4.3.1 source, the pinned platform build script, and its FDK-AAC
  crash-fix patch. The script records its source hash and compiler options.
- The daemon's Go dependency source ZIPs, resolved replacements, licenses and
  notices, plus the Go runtime license. Collect the modules actually imported by
  `GOOS=linux GOARCH=arm GOARM=7 CGO_ENABLED=0 go list -tags dot -deps -json
  ./cmd/echod`, verifying each ZIP's Go `h1` content checksum against `go.sum`.
  The vendored local microWakeWord replacement is already in the daemon source.
- An inventory connecting those source inputs to the actual binaries in the
  locked rootfs, including any discrepancy between package lists and payloads.

The base APK database alone is incomplete: upstream unpacks some packages without
adding them to that database. Its download helper can select a newer mirror
package when an old listed version is unavailable. Therefore package lists alone
are not proof of which source version corresponds to a binary. Preserve exact
payload comparisons and record unresolved coverage before publishing.

`pack.py` validates archive structure, rejects obvious secret paths and private-key
headers in supplemental archive wrappers, and records hashes; it cannot determine
license compliance or prove that a manually supplied supplement covers every
binary. Source coverage review is a release prerequisite, not a claim inferred
from the presence of a tar file. Retain source attachments for every distributed
binary release, rather than relying on an unrelated project's future availability.

## Verification

```sh
python3 -m unittest discover -s integrations/signed-ota -p 'test_*.py' -v
```

Packaging tests cover deterministic complete output, exact manifest signatures,
tampering, seed permissions, architecture checks, version/channel/lifetime
mismatches, uncommitted patch mismatch, private source paths, and hostile archives.
They use a deterministic disposable test key and small synthetic binaries; they
do not touch production credentials, devices, or Home Assistant. Production
release verification additionally checks the real locked upstream inputs, native
updater tests, and the downloaded published artifacts before installation.
