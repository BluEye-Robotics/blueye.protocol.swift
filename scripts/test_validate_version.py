import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location("validate_version", Path(__file__).with_name("validate-version.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReleaseVersionTests(unittest.TestCase):
    def test_accepts_shared_release_and_branch_versions(self):
        for version in ("6.5.815", "6.5.816", "6.5.817-branch-feature", "6.5.818-rc.1"):
            with self.subTest(version=version):
                module.validate_version(version, "6.5")

    def test_rejects_different_app_version_and_invalid_semver(self):
        for version in ("1.0.0", "6.4.815", "6.5", "6.5.0815", "v6.5.815", "6.5.815+meta", "6.5.815-01"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                module.validate_version(version, "6.5")

    def test_rejects_invalid_upstream_base(self):
        for base in ("6.5.0", "v6.5", "06.5"):
            with self.subTest(base=base), self.assertRaises(ValueError):
                module.validate_version("6.5.815", base)


if __name__ == "__main__":
    unittest.main()
