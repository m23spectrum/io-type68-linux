# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('installer',ROOT/'install.py')
installer=importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)

def args(home):
    return SimpleNamespace(destdir=home,no_udev=False,no_activate=False)

class InstallerTests(unittest.TestCase):
    def test_staged_install_upgrade_uninstall(self):
        with tempfile.TemporaryDirectory(prefix='type68 with spaces ') as temp:
            home=Path(temp)
            installer.install(args(home),home)
            self.assertTrue((home/'etc/udev/rules.d/70-io-type68.rules').is_file())
            self.assertTrue(json.loads(installer.manifest_path(home).read_text())['files'])
            help_result=subprocess.run([str(home/'.local/bin/io-type68'),'--help'],capture_output=True,text=True)
            self.assertEqual(help_result.returncode,0,help_result.stderr)
            installer.install(args(home),home)
            unrelated=home/'.local/share/io-type68/my-note.txt'; unrelated.write_text('keep')
            installer.uninstall(args(home),home)
            self.assertTrue(unrelated.exists()); self.assertFalse((home/'.local/bin/io-type68').exists())
            self.assertFalse(installer.manifest_path(home).exists())
    def test_existing_bridge_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp); target=home/'.local/share/dbus-1/services/local.io.Keyboard.service'
            target.parent.mkdir(parents=True); target.write_text('original bridge')
            with self.assertRaises(RuntimeError): installer.install(args(home),home)
            self.assertEqual(target.read_text(),'original bridge')
            self.assertFalse((home/'.local/bin/io-type68').exists())
    def test_modified_file_not_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp); installer.install(args(home),home)
            target=home/'.local/bin/io-type68'; target.write_text('modified')
            with self.assertRaises(RuntimeError): installer.uninstall(args(home),home)
            self.assertEqual(target.read_text(),'modified')
            self.assertTrue(installer.manifest_path(home).exists())
    def test_failure_restores_user_files(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp)
            with patch.object(installer.shutil,'copyfile',side_effect=OSError('simulated udev failure')):
                with self.assertRaises(OSError): installer.install(args(home),home)
            self.assertFalse((home/'.local/bin/io-type68').exists())
            self.assertFalse(installer.manifest_path(home).exists())
    def test_manifest_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp); p=installer.manifest_path(home); p.parent.mkdir(parents=True)
            p.write_text(json.dumps({'package':'io-type68-driver','files':{'../../outside':'x'}}))
            with self.assertRaises(RuntimeError): installer.uninstall(args(home),home)

if __name__=='__main__': unittest.main()
