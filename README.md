# IO Type 68 Magnetic — Linux driver

[![Tests](https://github.com/m23spectrum/io-type68-linux/actions/workflows/test.yml/badge.svg)](https://github.com/m23spectrum/io-type68-linux/actions/workflows/test.yml) ![License: GPL v3+](https://img.shields.io/badge/license-GPLv3%2B-blue) ![Platform: Linux](https://img.shields.io/badge/platform-Linux-blue)

Linux driver and KDE Plasma 6 widget for **IO by Red Square Type 68 Magnetic**.

[Русский](docs/README.ru.md) · [Protocol](docs/protocol.md) · [Tests](docs/verification.md) · [KDE integration](docs/kde.md)

![IO Type 68 Magnetic KDE widget](docs/images/kde-widget.png)

## Features

- Keyboard brightness and lighting off.
- Whole-keyboard and per-key RGB.
- Built-in effects, speed and direction.
- Aurora, breathing, comet and rainbow host effects, targeting up to 30 fps.
- Actuation depth **0.10–3.20 mm** for all keys, WASD or individual keys.
- Rapid Trigger with separate press/release thresholds.
- Top and bottom dead zones, **0–0.50 mm**.
- KDE widget and command-line control.

## Compatibility

Linux, Python 3.10+, `dbus-python`, PyGObject/GLib and a desktop session bus. The widget requires KDE Plasma 6, Kirigami and `org.kde.plasma.workspace.dbus`.

Supported device: USB `0c45:0256`, firmware **1.37**. Support is experimental; other firmware versions are unverified.

## Install

```sh
git clone https://github.com/m23spectrum/io-type68-linux.git
cd io-type68-linux
python3 install.py
```

Run as your desktop user, **without sudo**. The installer requests sudo for missing dependencies and the USB-access rule, installs the driver and widget, then starts the service. On immutable distributions, missing host dependencies must be installed through the distribution's package workflow.

Add **IO Type 68 Magnetic** through KDE's “Add Widgets”. Reconnect the keyboard if USB access is not available yet.

Installer options:

```sh
python3 install.py --check          # Check dependencies and conflicts
python3 install.py --no-udev        # Skip the USB-access rule
python3 install.py --no-activate    # Do not start the service
python3 install.py --destdir /tmp/io-type68-staging  # Stage files only
python3 install.py --uninstall
```

The installer refuses conflicting or locally modified files. Panel layout is configured through KDE. Close other keyboard configuration tools before changing device settings.

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

Key selection accepts `all`, `wasd`, DOM-style names (`KeyW`, `Escape`), display names or comma-separated names/slot IDs. Lighting mode IDs are listed in [protocol.md](docs/protocol.md).

Settings are written immediately and checked by readback. `io-type68 refresh` returns the current settings as diagnostic JSON; it is not an importable backup.

## Limitations

- Choosing RGB selects custom/static lighting. Arbitrary colors for built-in animations are not supported.
- Host effects require the service and must be selected again after a restart. Stopping an effect restores the previous built-in lighting mode.
- Macros, remapping, SOCD/DKS, calibration and firmware updates are not implemented.

## Remove

```sh
python3 install.py --uninstall
```

The uninstaller removes unmodified files owned by the package and its USB rule. Remove the widget from the panel through KDE. Saved keyboard settings remain on the device.

## Development

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src dbus-run-session -- python3 tests/daemon_integration.py
python3 -m pip wheel --no-deps .
```

The wheel contains the Python package; use the source installer for KDE and system integration. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

GPL-3.0-or-later. Independent project; not an official manufacturer driver.
