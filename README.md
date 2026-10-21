# blueye.protocol.swift

Swift Protocol Buffer messages for Blueye underwater drones, exposed as the
`BlueyeProtocol` Swift Package Manager library. Requires Swift 6.2 or newer.

The schemas live in [ProtocolDefinitions](https://github.com/BluEye-Robotics/ProtocolDefinitions),
pinned here as a Git submodule. Generated Swift sources are committed in this
repository, following the same ownership model as
[blueye.protocol for Python](https://github.com/BluEye-Robotics/blueye.protocol).
Clients do not need protoc, the generator, or a submodule checkout to use the
library. This package provides messages and serialization, not a network
transport or drone connection API.

## Consume

After the first 6.5 release, add the package to your application's manifest.
The lower bound below accepts stable 6.5 releases and later compatible versions;
use an exact published version if you need a particular protocol revision.

```swift
dependencies: [
  .package(
    url: "https://github.com/BluEye-Robotics/blueye.protocol.swift.git",
    from: "6.5.0"
  )
],
targets: [
  .target(
    name: "YourApp",
    dependencies: [.product(name: "BlueyeProtocol", package: "blueye.protocol.swift")]
  )
]
```

In Xcode, add that repository URL under Package Dependencies and select the
`BlueyeProtocol` product. Before a version is released, select a commit or branch.

```swift
import BlueyeProtocol

var attitude = Blueye_Protocol_Attitude()
attitude.yaw = 90
let bytes = try attitude.serializedData()
let decoded = try Blueye_Protocol_Attitude(serializedBytes: bytes)
```

The module is `BlueyeProtocol`; generated types retain the protobuf namespace,
for example `Blueye_Protocol_Attitude`. SwiftProtobuf 1.39.0 is an exact package
dependency, matching the code generator used for these sources.

## Develop

```sh
git clone --recurse-submodules https://github.com/BluEye-Robotics/blueye.protocol.swift.git
cd blueye.protocol.swift
swift test
swift build --configuration release
```

To regenerate, install protoc 36.2 (pinned in `protobuf.version`). On macOS or
Linux x86-64, the helper installs a checksum-verified copy locally:

```sh
scripts/install-protoc.sh .build/protoc
export PATH="$PWD/.build/protoc/bin:$PATH"
scripts/generate-swift.sh
scripts/generate-swift.sh --check
swift test
```

The generator script resolves SwiftProtobuf from `Package.swift`, builds its
matching `protoc-gen-swift`, and generates public types. The `--check` mode
detects stale, missing, and removed generated files without changing them.
When upgrading tools, update `Package.swift`, `protobuf.version`, and
`protobuf.checksums` as appropriate, then regenerate and test.

CI verifies generation, tests binary fixtures, Any, timestamps, oneofs, and
unknown fields, and builds in release mode on macOS and Linux with Swift 6.2.3.

## Shared versioning and releases

NuGet, Maven, and Swift share the version calculated by the **Protocol packages**
workflow in ProtocolDefinitions. Its `version.txt` holds the Blueye App
major/minor version, currently `6.5`. Each master build publishes a stable
`6.5.<run-number>`; merging schema changes does not require a version-file edit.
Swift tags are `v<package-version>`. This repository does not assign its own
build counter or independently choose release versions. The Python package
retains its separate versioning.

After NuGet and Maven publish successfully, the upstream workflow dispatches
`protocol-update` with `client_payload.sha` and `client_payload.version`.
The **Update and release protocol** workflow:

1. Verifies that the SHA belongs to upstream master and the version matches the
   pinned revision's `version.txt`.
2. Advances the submodule to that SHA, regenerates, tests, and commits the sources.
3. Runs the full macOS/Linux CI workflow against that generated commit.
4. Creates a matching immutable version tag and GitHub Release.

Updates are serialized. An older update is ignored if the default branch has
already advanced; an existing tag is reused only for the same protocol SHA.
The receiver uses `GITHUB_TOKEN` with `contents: write`. Bot pushes do not start
another Actions run, so the receiver explicitly calls CI before releasing.

To enable upstream dispatch, configure these in ProtocolDefinitions:

- Actions variable `SWIFT_PROTOCOL_REPOSITORY` = `BluEye-Robotics/blueye.protocol.swift`.
- The existing `CI_PAT` secret must be able to dispatch events to this repository.

The receiver must first be committed on this repository's default branch.
If branch protection prevents bot pushes, adapt the workflow to use pull requests.

To retry a failed Swift update or release, manually run **Update and release
protocol** with the exact upstream SHA and version from the successful
ProtocolDefinitions package run. Do not move published tags.

## License

GNU Lesser General Public License version 3, using the same LICENSE text as
the generated Python package. See [LICENSE](LICENSE).
