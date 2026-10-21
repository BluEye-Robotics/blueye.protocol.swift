#!/usr/bin/env python3
"""Validate the version supplied by ProtocolDefinitions against its pinned base."""

from pathlib import Path
import re
import sys


def validate_version(version: str, base: str) -> None:
    number = r"(?:0|[1-9][0-9]*)"
    identifier = r"(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
    if not re.fullmatch(rf"{number}\.{number}", base):
        raise ValueError("ProtocolDefinitions/version.txt must contain major.minor")
    if not re.fullmatch(rf"{re.escape(base)}\.{number}(?:-{identifier}(?:\.{identifier})*)?", version):
        raise ValueError(f"Expected {base}.<run-number>, optionally followed by a prerelease suffix")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: validate-version.py <package-version>")
    version = sys.argv[1]
    version_file = Path(__file__).resolve().parents[1] / "ProtocolDefinitions/version.txt"
    try:
        validate_version(version, version_file.read_text().strip())
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
    print(f"tag=v{version}")
    print(f"prerelease={str('-' in version).lower()}")
