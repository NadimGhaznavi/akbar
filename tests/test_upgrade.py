from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.install import APPLICATION_FILES
from scripts.upgrade import remove_installed_runtime


class UpgradeBoundaryTest(unittest.TestCase):
    def test_operational_scripts_are_in_the_install_manifest(self) -> None:
        destinations = {destination for _, destination in APPLICATION_FILES}
        self.assertIn(Path("scripts/akbar-cli.py"), destinations)
        self.assertIn(Path("scripts/install.py"), destinations)
        self.assertIn(Path("scripts/upgrade.py"), destinations)

    def test_runtime_replacement_preserves_environment_and_unowned_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            install_root = Path(directory)
            runtime_file = install_root / "constants" / "stale.py"
            runtime_file.parent.mkdir()
            runtime_file.write_text("stale", encoding="utf-8")
            environment_file = install_root / ".venv" / "marker"
            environment_file.parent.mkdir()
            environment_file.write_text("preserve", encoding="utf-8")
            data_file = install_root / "data" / "marker"
            data_file.parent.mkdir()
            data_file.write_text("preserve", encoding="utf-8")

            remove_installed_runtime(install_root)

            self.assertFalse(runtime_file.exists())
            self.assertEqual(
                environment_file.read_text(encoding="utf-8"),
                "preserve",
            )
            self.assertEqual(data_file.read_text(encoding="utf-8"), "preserve")


if __name__ == "__main__":
    unittest.main()
