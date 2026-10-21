#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 1 ]]; then
  echo "Usage: $0 <installation-directory>" >&2
  exit 2
fi
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VERSION=$(cat "$ROOT/protobuf.version")
case "$(uname -s)-$(uname -m)" in
  Darwin-*) PLATFORM=osx-universal_binary ;;
  Linux-x86_64) PLATFORM=linux-x86_64 ;;
  *) echo "Install protoc $VERSION manually on this platform." >&2; exit 1 ;;
esac
FILENAME="protoc-$VERSION-$PLATFORM.zip"
CHECKSUM=$(awk -v name="$FILENAME" '$2 == name {print $1}' "$ROOT/protobuf.checksums")
if [[ -z "$CHECKSUM" ]]; then
  echo "Missing checksum for $FILENAME; update protobuf.checksums." >&2
  exit 1
fi
ARCHIVE=$(mktemp)
trap 'rm -f "$ARCHIVE"' EXIT
curl --fail --location --retry 3 \
  "https://github.com/protocolbuffers/protobuf/releases/download/v$VERSION/$FILENAME" \
  --output "$ARCHIVE"
echo "$CHECKSUM  $ARCHIVE" | shasum -a 256 --check
mkdir -p "$1"
unzip -qo "$ARCHIVE" -d "$1"
