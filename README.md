# IO Type 68 Magnetic — Linux driver

[![Tests](https://github.com/m23spectrum/io-type68-linux/actions/workflows/test.yml/badge.svg)](https://github.com/m23spectrum/io-type68-linux/actions/workflows/test.yml) ![License: GPL v3+](https://img.shields.io/badge/license-GPLv3%2B-blue) ![Platform: Linux](https://img.shields.io/badge/platform-Linux-blue)

Open-source userspace HID driver for **IO by Red Square Type 68 Magnetic**, with a CLI, a session D-Bus service and a KDE Plasma 6 widget. No kernel module or firmware modification is required.

**Status: experimental, v0.1.0.** Protocol developed and checked on one `0c45:0256` keyboard with firmware **1.37**. Other firmware revisions and lookalike keyboards have not been verified. This is an independent project, not an official IO/Red Square driver.

[Русское описание](docs/README.ru.md) · [Protocol](docs/protocol.md) · [Verification](docs/verification.md) · [KDE integration](docs/kde.md)

## Features

- Keyboard brightness, 0–5, and lighting off.
- Whole-keyboard and per-key RGB, built-in effect selection, speed and direction.
- Actuation depth **0.10–3.20 mm**; all keys, WASD or named individual keys.
- Rapid Trigger with separate press/release sensitivities, independently of actuation depth.
- Top and bottom dead zones, 0–0.50 mm.
- Four host-generated effects: **aurora, breathing, comet and rainbow**, targeting up to **30 fps** through volatile frames. No RGB-table writes per animation frame.
- Readback verification of persistent writes; USB reconnect detection and an exclusive per-user transport lock.

Actuation depth is not spring force: software cannot change the mechanical force required to press a key.

On firmware 1.37, choosing RGB selects custom/static mode. Arbitrary base colors for built-in animations are not confirmed. Macro/remap, SOCD, DKS, calibration, firmware flashing and factory reset are not implemented. PC motherboard/RAM RGB and monitor brightness are outside this keyboard package.

## Requirements

Linux, Python 3.10+, `dbus-python`, PyGObject/GLib and a desktop session bus. KDE integration additionally needs Plasma 6, Kirigami and `org.kde.plasma.workspace.dbus` (the original integration was tested on Plasma 6.7.5).

Fedora packages: `python3-dbus python3-gobject`; Debian/Ubuntu: `python3-dbus python3-gi`. Install these through your distribution's supported method. On immutable systems such as Bazzite, use the available host packages; a container without the host session bus and HID access is insufficient.

## Install

```sh
git clone https://github.com/m23spectrum/io-type68-linux.git
cd io-type68-linux
python3 install.py
```

Run this as your normal desktop user, **without sudo**. The installer checks for existing/conflicting files first, checks host Python dependencies, and on standard Debian/Ubuntu, Fedora and Arch installs missing Python dependencies through the package manager. Only package installation and the udev USB rule request sudo. It then reloads USB rules, triggers HID permissions, starts the user service and checks keyboard connectivity. Reconnecting the keyboard may still be needed for your session's access rules.

On immutable systems such as Bazzite, missing host dependencies require the distribution's host-package workflow; the installer explains this and stops instead of modifying an immutable base or silently switching to a container.

Available modes:

```sh
python3 install.py --check           # Read-only dependency/conflict check
python3 install.py --no-udev         # USB permissions already managed separately
python3 install.py --no-activate     # Install files without starting the service
python3 install.py --destdir /tmp/io-type68-staging  # Fully staged, including the rule
python3 install.py --uninstall       # Remove only manifest-owned, unmodified files
```

Installation records file hashes in a per-user ownership manifest. Conflicting or locally modified files are not overwritten or removed. Failed installation restores user files and attempts to remove a newly added USB rule. System packages installed as dependencies are not automatically removed. KDE panel contents are never rewritten.

The daemon runs as your desktop user and is activated on demand over D-Bus. The udev rule grants the active local user access only to this USB VID/PID's hidraw nodes; the driver additionally selects usage page `0xff68`. Do not run the daemon as root. Do not operate the vendor web configurator or another HID tool simultaneously.

The installer never edits your KDE panel or replaces an existing IO keyboard D-Bus bridge. If the original all-in-one brightness integration is already installed, the installer refuses to overwrite it. The CLI can already talk to that bridge without installation using `PYTHONPATH=src python3 -m io_type68.cli status`. Migrate only after backing up the original integration; the keyboard-only service does not implement its PC RGB/monitor methods.

Add **IO Type 68 Magnetic** through KDE's “Add Widgets”. To embed the controls in a brightness menu instead, see [KDE integration](docs/kde.md).

For a Python wheel: `python3 -m pip wheel --no-deps .`. This packages the Python driver and key layout; the source installer supplies KDE and D-Bus/systemd integration.

## CLI examples

```sh
io-type68 status
io-type68 lighting --brightness 3
io-type68 lighting --mode 0
io-type68 lighting --color '#800020'
io-type68 lighting --keys wasd --color '#ff6600'
io-type68 lighting --mode 11 --speed 3 --direction 1
io-type68 keys --keys wasd --trigger 0.20
io-type68 keys --keys KeyW --rapid on --press 0.10 --release 0.15
io-type68 keys --keys all --rapid off
io-type68 deadzone --top 0.10 --bottom 0.10
io-type68 effect aurora --color '#800020' --speed 3
io-type68 effect none
```

Key selection accepts `all`, `wasd`, DOM-style names (`KeyW`, `Escape`), display names or comma-separated names/slot IDs. Lighting mode numbers are documented in [protocol.md](docs/protocol.md).

Persistent keyboard settings are written immediately and checked by readback. There is no automatic rollback of arbitrary setting changes; save `io-type68 refresh` output before experimenting. That JSON is diagnostic, not an importable raw backup. Effects are temporary, stop on service termination, and restore the previous built-in lighting mode; selecting a built-in mode exits a host effect. Host effects must be selected again after a restart.

## Development and publishing

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 install.py --destdir /tmp/io-type68-staging
```

Tests use simulated devices and do not change hardware. CI runs protocol tests on Python 3.10, 3.12 and 3.14. See [CONTRIBUTING.md](CONTRIBUTING.md) and [publishing checklist](docs/publishing.md).

## Remove

Use the same source release to remove its installation:

```sh
python3 install.py --uninstall
```

The uninstaller stops the user service, removes files listed in its ownership manifest and its USB-access rule, and reloads user units/rules. It refuses to delete modified or unrelated files. With `--no-udev`, a previously installed USB rule is deliberately left in place. Remove the widget from your panel through KDE. Saved keyboard settings remain on the device.

## License and provenance

GPL-3.0-or-later. The source is based on our Linux HID implementation and original keyboard controls, informed by analysis of the vendor web configurator and verified device replies. Proprietary JavaScript, firmware images and binary evidence dumps are **not distributed**. The standalone widget contains no extracted KDE brightness-widget code. KDE and IO/Red Square trademarks belong to their respective owners.
