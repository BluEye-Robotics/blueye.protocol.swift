#!/usr/bin/env bash
set -euo pipefail

if [[ $# -gt 1 || ( $# -eq 1 && "$1" != "--check" ) ]]; then
  echo "Usage: $0 [--check]" >&2
  exit 2
fi

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PROTOC_VERSION=$(cat "$ROOT/protobuf.version")
if [[ "$(protoc --version)" != "libprotoc $PROTOC_VERSION" ]]; then
  echo "Install protoc $PROTOC_VERSION before generating Swift sources." >&2
  exit 1
fi

# Resolve the exact runtime version in Package.swift, then build its generator.
# Consumers only compile the checked-in sources and never run this script.
swift package --package-path "$ROOT" resolve
GENERATOR_PACKAGE="$ROOT/.build/checkouts/swift-protobuf"
GENERATOR_BUILD="$ROOT/.build/swift-protobuf-generator"
swift build --package-path "$GENERATOR_PACKAGE" --scratch-path "$GENERATOR_BUILD" \
  --configuration release --product protoc-gen-swift
GENERATOR_BIN=$(swift build --package-path "$GENERATOR_PACKAGE" \
  --scratch-path "$GENERATOR_BUILD" --configuration release --show-bin-path)

GENERATED=$(mktemp -d)
trap 'rm -rf "$GENERATED"' EXIT
protoc \
  --proto_path="$ROOT/ProtocolDefinitions/protobuf_definitions" \
  --plugin="protoc-gen-swift=$GENERATOR_BIN/protoc-gen-swift" \
  --swift_opt=Visibility=Public \
  --swift_out="$GENERATED" \
  "$ROOT"/ProtocolDefinitions/protobuf_definitions/*.proto

DESTINATION="$ROOT/Sources/BlueyeProtocol"
if [[ "${1:-}" == "--check" ]]; then
  # Directory comparison also detects added and removed proto files.
  diff -ru "$DESTINATION" "$GENERATED"
else
  mkdir -p "$DESTINATION"
  rm -f "$DESTINATION"/*.pb.swift
  cp "$GENERATED"/*.pb.swift "$DESTINATION/"
fi
