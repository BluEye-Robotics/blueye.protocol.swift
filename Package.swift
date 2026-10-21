// swift-tools-version: 6.2

import PackageDescription

let package = Package(
  name: "BlueyeProtocol",
  products: [
    .library(name: "BlueyeProtocol", targets: ["BlueyeProtocol"])
  ],
  dependencies: [
    // The generation script builds protoc-gen-swift from this same dependency.
    .package(url: "https://github.com/apple/swift-protobuf.git", exact: "1.39.0")
  ],
  targets: [
    .target(
      name: "BlueyeProtocol",
      dependencies: [.product(name: "SwiftProtobuf", package: "swift-protobuf")],
      path: "Sources/BlueyeProtocol"
    ),
    .testTarget(
      name: "BlueyeProtocolTests",
      dependencies: [
        "BlueyeProtocol",
        .product(name: "SwiftProtobuf", package: "swift-protobuf")
      ],
      path: "Tests/BlueyeProtocolTests"
    )
  ]
)
