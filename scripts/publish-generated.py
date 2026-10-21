#!/usr/bin/env python3
"""Publish a generated Swift commit without moving the default branch backward."""

import os
from pathlib import Path
import subprocess


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def is_ancestor(repo: Path, older: str, newer: str) -> bool:
    result = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", older, newer])
    if result.returncode not in (0, 1):
        result.check_returncode()
    return result.returncode == 0


def publish_generated(repo: Path, env: dict[str, str]) -> dict[str, str]:
    protocol = git(repo / "ProtocolDefinitions", "rev-parse", "HEAD")
    if protocol != env["PROTOCOL_SHA"]:
        raise ValueError("The checked-out protocol does not match the requested revision")

    current = git(repo, "rev-parse", "HEAD:ProtocolDefinitions")
    historical = protocol != current and is_ancestor(repo / "ProtocolDefinitions", protocol, current)
    if protocol != current and not historical and not is_ancestor(repo / "ProtocolDefinitions", current, protocol):
        raise ValueError("The requested and current protocol revisions have diverged")

    existing = env.get("EXISTING_COMMIT", "")
    if existing:
        if git(repo, "rev-parse", f"{existing}:ProtocolDefinitions") != protocol:
            raise ValueError("The existing tag refers to a different protocol revision")
        return {"sha": git(repo, "rev-parse", f"{existing}^{{commit}}"),
                "historical": str(historical).lower(), "temporary_branch": ""}

    temporary_branch = ""
    destination = env["DEFAULT_BRANCH"]
    if historical:
        # Keep the commit reachable for CI without publishing an unverified tag.
        # Unique attempt refs allow retries after a failed generation/CI/release.
        temporary_branch = f"protocol-releases/{env['RELEASE_TAG']}-{env['GITHUB_RUN_ID']}-{env['GITHUB_RUN_ATTEMPT']}"
        destination = temporary_branch
    git(repo, "check-ref-format", f"refs/heads/{destination}")

    git(repo, "add", "--", "Sources/BlueyeProtocol", "ProtocolDefinitions")
    changed = subprocess.run(["git", "-C", str(repo), "diff", "--cached", "--quiet"])
    if changed.returncode not in (0, 1):
        changed.check_returncode()
    if changed.returncode == 1:
        git(repo, "config", "user.name", "github-actions[bot]")
        git(repo, "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
        git(repo, "commit", "--quiet", "-m", f"Update protocol to {protocol[:12]}")

    # A concurrent human push is rejected; never force-update the default branch.
    git(repo, "push", "--quiet", "origin", f"HEAD:refs/heads/{destination}")
    return {"sha": git(repo, "rev-parse", "HEAD"),
            "historical": str(historical).lower(), "temporary_branch": temporary_branch}


if __name__ == "__main__":
    outputs = publish_generated(Path.cwd(), dict(os.environ))
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        for key, value in outputs.items():
            output.write(f"{key}={value}\n")
