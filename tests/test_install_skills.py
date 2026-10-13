from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("install_skills", ROOT / "install_skills.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source" / "ace-skill"
        self.source.mkdir(parents=True)
        (self.source / "SKILL.md").write_text("---\nname: ace-skill\n---\n", encoding="utf-8")
        (self.source / "data.txt").write_text("v1\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_targets_are_loaded_from_agents_configuration(self):
        self.assertIn("opencode", MODULE.TARGETS)
        self.assertEqual(Path(".config/opencode/skills"), MODULE.TARGETS["opencode"].relative_path)
        self.assertEqual("supported", MODULE.TARGETS["opencode"].status)

    def test_invalid_agent_configuration_is_rejected(self):
        config = self.root / "invalid-agents.yaml"
        config.write_text(
            '{"agents": {"bad": {"relative_path": "../outside", "executables": "bad"}}}',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(RuntimeError, "ruta relativa inválida"):
            MODULE.load_targets(config)

        config.write_text(
            '{"agents": {"bad": {"relative_path": ".bad", "executables": "bad"}}}',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(RuntimeError, "executables inválido"):
            MODULE.load_targets(config)

    def test_doctor_is_read_only_and_reports_environment(self):
        home = self.root / "home"
        with patch.object(MODULE, "command_version", return_value="test-version"):
            report = MODULE.doctor_report(home)
        self.assertEqual("factory-ai-skills-installer", report["installer"])
        self.assertEqual("test-version", report["git"])
        self.assertEqual(len(MODULE.TARGETS), len(report["agents"]))
        self.assertFalse(home.exists())

    def test_installs_skill_and_receipt(self):
        destination = self.root / "home" / ".agents" / "skills" / "ace-skill"
        status = MODULE.install_skill(self.source, destination, update=False, dry_run=False)
        self.assertEqual("installed-verified", status)
        self.assertTrue((destination / "SKILL.md").is_file())
        self.assertTrue((destination / ".factory-skill-install.json").is_file())

    def test_receipt_records_provenance(self):
        destination = self.root / "destination" / "ace-skill"
        provenance = {
            "source": "git",
            "repository": "https://example.test/repo",
            "branch": "feature/test",
            "commit": "abc123",
            "skill_path": "skills/ace-skill",
        }
        MODULE.install_skill(
            self.source,
            destination,
            update=False,
            dry_run=False,
            provenance=provenance,
        )
        receipt = json.loads((destination / MODULE.RECEIPT_NAME).read_text(encoding="utf-8"))
        self.assertEqual("abc123", receipt["commit"])
        self.assertEqual("feature/test", receipt["branch"])

    def test_outdated_skill_is_not_modified(self):
        destination = self.root / "destination" / "ace-skill"
        destination.mkdir(parents=True)
        skill = destination / "SKILL.md"
        skill.write_text("existing\n", encoding="utf-8")
        status = MODULE.install_skill(self.source, destination, update=False, dry_run=False)
        self.assertEqual("outdated", status)
        self.assertEqual("existing\n", skill.read_text(encoding="utf-8"))

    def test_identical_existing_skill_is_verified_without_changes(self):
        destination = self.root / "destination" / "ace-skill"
        MODULE.install_skill(self.source, destination, update=False, dry_run=False)
        receipt = destination / MODULE.RECEIPT_NAME
        installed_at = receipt.read_text(encoding="utf-8")
        status = MODULE.install_skill(self.source, destination, update=False, dry_run=False)
        self.assertEqual("exists-verified", status)
        self.assertEqual(installed_at, receipt.read_text(encoding="utf-8"))

    def test_update_replaces_existing_skill(self):
        destination = self.root / "destination" / "ace-skill"
        destination.mkdir(parents=True)
        (destination / "SKILL.md").write_text("old\n", encoding="utf-8")
        status = MODULE.install_skill(self.source, destination, update=True, dry_run=False)
        self.assertEqual("updated-verified", status)
        self.assertIn("name: ace-skill", (destination / "SKILL.md").read_text(encoding="utf-8"))

    def test_dry_run_does_not_write(self):
        destination = self.root / "destination" / "ace-skill"
        status = MODULE.install_skill(self.source, destination, update=False, dry_run=True)
        self.assertEqual("would-install", status)
        self.assertFalse(destination.exists())

    def test_ignores_cache_files(self):
        cache = self.source / "__pycache__"
        cache.mkdir()
        (cache / "module.pyc").write_bytes(b"cache")
        destination = self.root / "destination" / "ace-skill"
        MODULE.install_skill(self.source, destination, update=False, dry_run=False)
        self.assertFalse((destination / "__pycache__").exists())

    def test_repository_access_failure_is_explained(self):
        failed = MODULE.subprocess.CompletedProcess(
            args=["git"], returncode=128, stdout="", stderr="Authentication failed"
        )
        with patch.object(MODULE.shutil, "which", return_value="/usr/bin/git"), patch.object(
            MODULE, "run_git", return_value=failed
        ):
            with self.assertRaisesRegex(RuntimeError, "VPN, red y credenciales"):
                MODULE.download_skill(
                    "https://example.invalid/repo",
                    "feature/test",
                    "skills/ace-skill",
                    self.root / "download",
                )

    def test_missing_git_is_explained(self):
        with patch.object(MODULE.shutil, "which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "Git no está instalado"):
                MODULE.download_skill(
                    "https://example.invalid/repo",
                    "feature/test",
                    "skills/ace-skill",
                    self.root / "download",
                )


if __name__ == "__main__":
    unittest.main()
