#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""One-command per-user installer. System privileges are limited to udev/packages."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
MARKER = 'io-type68-driver'
RULE = Path('/etc/udev/rules.d/70-io-type68.rules')
PYTHON = '/usr/bin/python3'


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dependencies():
    result = subprocess.run([PYTHON, '-c', 'import dbus; from gi.repository import GLib'], capture_output=True, text=True)
    return result.returncode == 0, result.stderr.strip()


def ensure_dependencies():
    ok, error = dependencies()
    if ok: return
    if Path('/run/ostree-booted').exists():
        raise RuntimeError('Host Python dependencies are missing on an immutable system. Install python3-dbus and python3-gobject using your distribution\'s supported host-package method, reboot if required, then rerun. Details: '+error)
    if shutil.which('apt-get'):
        run(['sudo', 'apt-get', 'update'])
        run(['sudo', 'apt-get', 'install', '-y', 'python3-dbus', 'python3-gi'])
    elif shutil.which('dnf'):
        run(['sudo', 'dnf', 'install', '-y', 'python3-dbus', 'python3-gobject'])
    elif shutil.which('pacman'):
        # No partial system upgrade: install from the currently synchronized repositories.
        run(['sudo', 'pacman', '-S', '--needed', '--noconfirm', 'python-dbus', 'python-gobject'])
    else:
        raise RuntimeError('Install dbus-python and PyGObject for /usr/bin/python3, then rerun. '+error)
    if not dependencies()[0]: raise RuntimeError('Dependencies still unavailable to '+PYTHON)


def assets(home):
    data = home/'.local/share/io-type68'
    files = {}
    for source in (ROOT/'src/io_type68').rglob('*'):
        if source.is_file() and '__pycache__' not in source.parts and source.suffix != '.pyc':
            files[data/'io_type68'/source.relative_to(ROOT/'src/io_type68')] = (source.read_bytes(), 0o644)
    for name, module in [('io-type68', 'cli'), ('io-type68d', 'daemon')]:
        content = '#!'+PYTHON+'\nimport sys\nsys.path.insert(0, '+repr(str(data))+')\nfrom io_type68.'+module+' import main\nsys.exit(main())\n'
        files[home/'.local/bin'/name] = (content.encode(), 0o755)
    exe = str(home/'.local/bin/io-type68d')
    # systemd expands percent specifiers; D-Bus desktop Exec does not.
    quote = lambda text: '"'+text.replace('\\','\\\\').replace('"','\\"')+'"'
    unit = '[Unit]\nDescription=IO Type 68 Magnetic HID driver\n\n[Service]\nType=dbus\nBusName=local.io.Keyboard\nExecStart='+quote(exe.replace('%','%%'))+'\nRestart=on-failure\nRestartSec=2\nTimeoutStopSec=15\n'
    service = '[D-BUS Service]\nName=local.io.Keyboard\nExec='+quote(exe)+'\nSystemdService=io-type68.service\n'
    files[home/'.config/systemd/user/io-type68.service'] = (unit.encode(), 0o644)
    files[home/'.local/share/dbus-1/services/local.io.Keyboard.service'] = (service.encode(), 0o644)
    for source in (ROOT/'plasmoid').rglob('*'):
        if source.is_file(): files[home/'.local/share/plasma/plasmoids/io.github.io-type68.keyboard'/source.relative_to(ROOT/'plasmoid')] = (source.read_bytes(), 0o644)
    return files


def manifest_path(home):
    return home/'.local/share/io-type68/install-manifest.json'


def load_manifest(home):
    path = manifest_path(home)
    if not path.exists(): return {}
    data = json.loads(path.read_text())
    if data.get('package') != MARKER: raise RuntimeError('Unrecognized installation manifest')
    # Validate against explicit package paths before removal or replacement.
    allowed = set(str(p.relative_to(home)) for p in assets(home))
    if set(data['files']) - allowed: raise RuntimeError('Manifest contains unexpected paths')
    return data


def preflight(home, files, previous):
    for path, (content, _) in files.items():
        if path.is_symlink(): raise RuntimeError('Refusing symlink destination: '+str(path))
        rel = str(path.relative_to(home))
        if path.exists():
            existing = path.read_bytes()
            if rel not in previous.get('files', {}) and existing != content:
                raise RuntimeError('Existing file belongs to another installation: '+str(path)+'. Your original bridge was not changed.')
            if rel in previous.get('files', {}) and digest(existing) != previous['files'][rel]:
                raise RuntimeError('Locally modified file; back it up and resolve before upgrade: '+str(path))


def udev_path(args, home):
    return home/'etc/udev/rules.d/70-io-type68.rules' if args.destdir else RULE


def check_rule(path):
    if path.is_symlink(): raise RuntimeError('Refusing symlink udev rule: '+str(path))
    if path.exists() and path.read_bytes() != (ROOT/'packaging/70-io-type68.rules').read_bytes():
        raise RuntimeError('A different udev rule already exists: '+str(path))


def install(args, home):
    files = assets(home); previous = load_manifest(home)
    preflight(home, files, previous)
    rule = udev_path(args, home)
    if not args.no_udev: check_rule(rule)
    if not args.destdir:
        ensure_dependencies()
        if not args.no_activate and not shutil.which('systemctl'): raise RuntimeError('systemctl is required; use --no-activate for manual setup')
        if not args.no_udev and (not shutil.which('sudo') or not shutil.which('udevadm')): raise RuntimeError('sudo and udevadm are required; use --no-udev for manual USB permissions')
        if not args.no_activate:
            run(['systemctl', '--user', 'show-environment'], stdout=subprocess.DEVNULL)
            run(['systemctl', '--user', 'stop', 'io-type68.service'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) if previous else None
    manifest = manifest_path(home)
    rule_existed = rule.exists()
    created_rule = False
    backups = {p: (p.read_bytes(), p.stat().st_mode & 0o777) if p.exists() else None for p in (*files, manifest)}
    try:
        for path, (content, mode) in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
                tmp.write(content); temporary = Path(tmp.name)
            temporary.chmod(mode); temporary.replace(path)
        rule_installed = previous.get('udev', False)
        if not args.no_udev:
            if args.destdir:
                rule.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(ROOT/'packaging/70-io-type68.rules', rule)
                created_rule = not rule_existed
            else:
                run(['sudo','install','-m','0644',str(ROOT/'packaging/70-io-type68.rules'),str(rule)])
                created_rule = not rule_existed
                run(['sudo','udevadm','control','--reload-rules'])
                run(['sudo','udevadm','trigger','--action=add','--subsystem-match=hidraw'])
                run(['udevadm','settle','--timeout=10'])
            rule_installed = True
        manifest.write_text(json.dumps({'package':MARKER,'files':{str(p.relative_to(home)):digest(v[0]) for p,v in files.items()},'udev':rule_installed}, indent=2)+'\n')
        if not args.destdir and not args.no_activate:
            run(['systemctl','--user','daemon-reload'])
            run(['systemctl','--user','restart','io-type68.service'])
    except BaseException:
        # Restore only files owned by this transaction; don't delete a previously installed udev rule.
        for path, old in backups.items():
            if old is None: path.unlink(missing_ok=True)
            else: path.write_bytes(old[0]); path.chmod(old[1])
        if not args.destdir and not args.no_activate:
            subprocess.run(['systemctl','--user','daemon-reload'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if previous: subprocess.run(['systemctl','--user','restart','io-type68.service'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if created_rule:
            if args.destdir: rule.unlink(missing_ok=True)
            else:
                cleanup = subprocess.run(['sudo','rm','--',str(rule)], check=False)
                subprocess.run(['sudo','udevadm','control','--reload-rules'], check=False)
                if cleanup.returncode: print('Could not remove the new USB rule: '+str(rule), file=sys.stderr)
        print('User files restored after failed installation.', file=sys.stderr)
        raise
    print('Installed driver, D-Bus service and KDE widget. Panel configuration was not changed.')
    if args.destdir: print('Staged only; no system service or USB permissions were changed.'); return
    if not args.no_activate:
        result = subprocess.run([str(home/'.local/bin/io-type68'), 'status'], capture_output=True, text=True)
        if result.returncode == 0: print('Keyboard connection: OK')
        else: print('Service installed; keyboard unavailable. Reconnect it and run ~/.local/bin/io-type68 status.\n'+result.stdout+result.stderr)
    if args.no_udev: print('USB permissions were skipped; configure packaging/70-io-type68.rules manually if needed.')
    if not shutil.which('plasmashell'):
        print('KDE Plasma was not detected. The CLI/service are installed; the widget requires Plasma 6, Kirigami and its workspace D-Bus QML module.')
    print('KDE: Add Widgets → IO Type 68 Magnetic. CLI: ~/.local/bin/io-type68')


def uninstall(args, home):
    previous = load_manifest(home)
    if not previous: raise RuntimeError('No installation manifest; refusing to remove unowned files')
    files = {home/rel: (b'',0) for rel in previous['files']}
    for path in files:
        if path.exists() and (path.is_symlink() or digest(path.read_bytes()) != previous['files'][str(path.relative_to(home))]):
            raise RuntimeError('Modified file will not be deleted: '+str(path))
    rule = udev_path(args, home)
    if previous.get('udev') and not args.no_udev: check_rule(rule)
    if not args.destdir and not args.no_activate:
        run(['systemctl','--user','stop','io-type68.service'])
    if previous.get('udev') and not args.no_udev and rule.exists():
        if args.destdir: rule.unlink()
        else:
            run(['sudo','rm','--',str(rule)])
            run(['sudo','udevadm','control','--reload-rules'])
    for path in files: path.unlink(missing_ok=True)
    manifest_path(home).unlink()
    if not args.destdir and not args.no_activate: run(['systemctl','--user','daemon-reload'])
    print('Removed package-owned files. Keyboard settings and KDE panel configuration were preserved.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destdir',type=Path,help='Stage under a directory without touching the running system')
    parser.add_argument('--no-activate',action='store_true',help='Do not reload/start user services')
    parser.add_argument('--no-udev',action='store_true',help='Skip system USB-access rule')
    parser.add_argument('--activate',action='store_true',help=argparse.SUPPRESS)  # Old invocation remains accepted.
    parser.add_argument('--uninstall',action='store_true',help='Remove this installation using its ownership manifest')
    parser.add_argument('--check',action='store_true',help='Read-only dependency and conflict check')
    args=parser.parse_args()
    if sys.version_info < (3,10): parser.error('Python 3.10 or newer is required')
    if os.geteuid()==0 and not args.destdir: parser.error('Run as your desktop user, without sudo; only system operations request sudo')
    home=args.destdir.resolve() if args.destdir else Path.home()
    try:
        if args.check:
            preflight(home,assets(home),load_manifest(home))
            if not args.no_udev: check_rule(udev_path(args,home))
            ok,error=dependencies()
            print('Host Python dependencies: '+('OK' if ok else error))
            return 0 if ok else 1
        (uninstall if args.uninstall else install)(args,home)
        return 0
    except (OSError,RuntimeError,ValueError,subprocess.CalledProcessError) as exc:
        print('Installer: '+str(exc),file=sys.stderr); return 1

if __name__=='__main__': sys.exit(main())
