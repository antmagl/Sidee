"""Reject incomplete or incorrectly targeted Linux distribution bundles."""
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from tools import build_linux_release as packaging


class TestLinuxBundleValidation(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        for name in ("README.md", "LICENSE"):
            (self.root / name).write_text("fixture", encoding="utf-8")
        self.bundle = self.root / "dist" / "Sidee"
        self.executable = self.bundle / "sidee"
        self.executable.parent.mkdir(parents=True)
        self.executable.write_bytes(b"\x7fELF" + b"fixture")
        self.executable.chmod(0o755)
        for relative in packaging.RESOURCES:
            destination = self.bundle / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("fixture", encoding="utf-8")

    def test_complete_bundle_is_verified_without_running_a_tv_operation(self):
        self.assertEqual(packaging.verify_bundle(self.bundle), self.executable)

    def test_pyinstaller_internal_data_folder_is_accepted(self):
        internal = self.bundle / "_internal"
        for relative in packaging.RESOURCES:
            source = self.bundle / relative
            destination = internal / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.replace(destination)
        self.assertEqual(packaging.verify_bundle(self.bundle), self.executable)

    def test_missing_connection_identity_is_rejected(self):
        (self.bundle / "core" / "tv-client.bundle").unlink()
        with self.assertRaisesRegex(RuntimeError, "tv-client.bundle"):
            packaging.verify_bundle(self.bundle)

    def test_non_elf_executable_is_rejected(self):
        self.executable.write_bytes(b"#!/bin/sh\n")
        with self.assertRaisesRegex(RuntimeError, "ELF"):
            packaging.verify_bundle(self.bundle)

    def test_tarball_has_one_predictable_top_level_folder(self):
        with patch.object(packaging, "ROOT", self.root):
            archive = packaging.package_bundle(self.bundle, "x86_64")
        self.assertEqual(archive, self.root / "dist" / "Sidee-linux-x86_64.tar.gz")
        with tarfile.open(archive) as downloaded:
            names = downloaded.getnames()
        self.assertIn("Sidee", names)
        self.assertIn("Sidee/sidee", names)
        self.assertIn("Sidee/core/tv-client.bundle", names)
        self.assertFalse(any(name.startswith(("Sidee-", "/")) for name in names))

    def test_cross_compilation_is_rejected(self):
        with patch.object(packaging.sys, "platform", "win32"):
            with self.assertRaisesRegex(RuntimeError, "must be built on Linux"):
                packaging.build("x86_64")

    def test_architecture_aliases_and_versions_are_normalized(self):
        self.assertEqual(packaging.normalized_architecture("AMD64"), "x86_64")
        self.assertEqual(packaging.normalized_architecture("arm64"), "aarch64")
        self.assertEqual(packaging.validate_version("v0.1.4.1"), "0.1.4.1")
        for value in ("v1", "1.2.3-preview", "1.2.3/../other", "1.2.3\n"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                packaging.validate_version(value)


if __name__ == "__main__":
    unittest.main()
