import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("publish_generated", Path(__file__).with_name("publish-generated.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def git(repo, *args):
    return subprocess.check_output(
        ["git", "-c", "protocol.file.allow=always", "-C", str(repo), *args],
        text=True, stderr=subprocess.PIPE,
    ).strip()


class PublishGeneratedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="swift-release-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.upstream = self.root / "upstream"
        self.upstream.mkdir()
        git(self.upstream, "init", "--quiet", "-b", "master")
        git(self.upstream, "config", "user.name", "Test")
        git(self.upstream, "config", "user.email", "test@example.invalid")
        self.protocol = []
        for index in range(4):
            (self.upstream / "schema.txt").write_text(f"revision {index}\n")
            git(self.upstream, "add", "schema.txt")
            git(self.upstream, "commit", "--quiet", "-m", f"Protocol {index}")
            self.protocol.append(git(self.upstream, "rev-parse", "HEAD"))

        self.remote = self.root / "swift.git"
        self.remote.mkdir()
        git(self.remote, "init", "--quiet", "--bare", "--initial-branch=master")
        seed = self.root / "seed"
        seed.mkdir()
        git(seed, "init", "--quiet", "-b", "master")
        git(seed, "config", "user.name", "Test")
        git(seed, "config", "user.email", "test@example.invalid")
        git(seed, "submodule", "add", "--quiet", str(self.upstream), "ProtocolDefinitions")
        git(seed / "ProtocolDefinitions", "checkout", "--quiet", self.protocol[0])
        source = seed / "Sources/BlueyeProtocol/fixture.pb.swift"
        source.parent.mkdir(parents=True)
        source.write_text(self.protocol[0])
        git(seed, "add", ".")
        git(seed, "commit", "--quiet", "-m", "Initial Swift fixture")
        git(seed, "remote", "add", "origin", str(self.remote))
        git(seed, "push", "--quiet", "origin", "master")
        self.attempt = 0

    def checkout(self, index, version, existing=""):
        self.attempt += 1
        repo = self.root / f"run-{self.attempt}"
        git(self.root, "clone", "--quiet", "--recurse-submodules", str(self.remote), str(repo))
        git(repo / "ProtocolDefinitions", "checkout", "--quiet", self.protocol[index])
        (repo / "Sources/BlueyeProtocol/fixture.pb.swift").write_text(self.protocol[index])
        env = {
            "PROTOCOL_SHA": self.protocol[index],
            "DEFAULT_BRANCH": "master",
            "RELEASE_TAG": f"v{version}",
            "GITHUB_RUN_ID": str(1000 + self.attempt),
            "GITHUB_RUN_ATTEMPT": "1",
            "EXISTING_COMMIT": existing,
        }
        return repo, env

    def publish_and_tag(self, index, version):
        repo, env = self.checkout(index, version)
        outputs = module.publish_generated(repo, env)
        # CI verifies this exact generated tree before the release creates its tag.
        self.assertEqual(git(repo, "show", f"{outputs['sha']}:Sources/BlueyeProtocol/fixture.pb.swift"), self.protocol[index])
        git(repo, "tag", env["RELEASE_TAG"], outputs["sha"])
        git(repo, "push", "--quiet", "origin", f"refs/tags/{env['RELEASE_TAG']}")
        if outputs["temporary_branch"]:
            git(repo, "push", "--quiet",
                f"--force-with-lease=refs/heads/{outputs['temporary_branch']}:{outputs['sha']}",
                "origin", f":refs/heads/{outputs['temporary_branch']}")
        return outputs

    def test_newer_then_older_releases_all_get_matching_tags_without_rollback(self):
        newest = self.publish_and_tag(3, "6.5.803")
        self.assertEqual(newest["historical"], "false")
        for index in (1, 2):
            with self.subTest(index=index):
                older = self.publish_and_tag(index, f"6.5.{800 + index}")
                self.assertEqual(older["historical"], "true")
                self.assertEqual(git(self.remote, "rev-parse", "master"), newest["sha"])
        for index in (1, 2, 3):
            self.assertEqual(git(self.remote, "rev-parse", f"v6.5.{800 + index}:ProtocolDefinitions"), self.protocol[index])
        self.assertEqual(git(self.remote, "for-each-ref", "--format=%(refname)", "refs/heads"), "refs/heads/master")

    def test_ordered_releases_advance_the_default_branch(self):
        for index in (1, 2, 3):
            outputs = self.publish_and_tag(index, f"6.5.{800 + index}")
            self.assertEqual(outputs["historical"], "false")
            self.assertEqual(outputs["temporary_branch"], "")
            self.assertEqual(git(self.remote, "rev-parse", "master:ProtocolDefinitions"), self.protocol[index])

    def test_retry_of_historical_tag_reuses_the_same_commit(self):
        newer = self.publish_and_tag(3, "6.5.803")
        older = self.publish_and_tag(1, "6.5.801")
        repo, env = self.checkout(1, "6.5.801", existing=older["sha"])
        outputs = module.publish_generated(repo, env)
        self.assertEqual(outputs["sha"], older["sha"])
        self.assertEqual(outputs["historical"], "true")
        self.assertEqual(outputs["temporary_branch"], "")
        self.assertEqual(git(self.remote, "rev-parse", "master"), newer["sha"])

    def test_failed_historical_attempt_can_retry_on_a_fresh_temporary_branch(self):
        newer = self.publish_and_tag(3, "6.5.803")
        first_repo, first_env = self.checkout(1, "6.5.801")
        first = module.publish_generated(first_repo, first_env)
        # Simulate CI failing before a tag is created, then a workflow rerun.
        second_repo, second_env = self.checkout(1, "6.5.801")
        second_env["GITHUB_RUN_ID"] = first_env["GITHUB_RUN_ID"]
        second_env["GITHUB_RUN_ATTEMPT"] = "2"
        second = module.publish_generated(second_repo, second_env)
        self.assertNotEqual(first["temporary_branch"], second["temporary_branch"])
        self.assertEqual(git(self.remote, "rev-parse", "master"), newer["sha"])
        self.assertEqual(git(self.remote, "rev-parse", f"{second['temporary_branch']}:ProtocolDefinitions"), self.protocol[1])

    def test_repeated_protocol_revision_can_receive_another_version_tag(self):
        first = self.publish_and_tag(1, "6.5.801")
        second = self.publish_and_tag(1, "6.5.802")
        self.assertEqual(first["sha"], second["sha"])
        self.assertEqual(git(self.remote, "rev-parse", "v6.5.802:ProtocolDefinitions"), self.protocol[1])

    def test_concurrent_default_branch_update_rejects_stale_push(self):
        stale_repo, stale_env = self.checkout(1, "6.5.801")
        newer = self.publish_and_tag(3, "6.5.803")
        with self.assertRaises(subprocess.CalledProcessError):
            module.publish_generated(stale_repo, stale_env)
        self.assertEqual(git(self.remote, "rev-parse", "master"), newer["sha"])

    def test_mismatched_existing_tag_is_rejected(self):
        newer = self.publish_and_tag(3, "6.5.803")
        repo, env = self.checkout(1, "6.5.801", existing=newer["sha"])
        with self.assertRaisesRegex(ValueError, "different protocol revision"):
            module.publish_generated(repo, env)
        self.assertEqual(git(self.remote, "rev-parse", "master"), newer["sha"])


if __name__ == "__main__":
    unittest.main()
