# Testing

## Compatibility

- Keyboard: IO Type 68 Magnetic WH, USB `0c45:0256`.
- Verified firmware: **1.37**.
- KDE widget: visually checked on Plasma **6.7.5**.

Other firmware versions and desktop releases require additional verification.

## Automated tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src dbus-run-session -- python3 tests/daemon_integration.py
```

The unit tests cover USB packet chunking, request validation, preservation of unrelated settings, volatile effect frames, key selection, staged installation, upgrades, uninstall, conflict handling and rollback.

The isolated D-Bus test covers state reads, settings updates, errors, effect start/stop, palette updates and properties using simulated HID hardware. These tests do not write to a connected keyboard.

GitHub Actions runs unit tests on Python 3.10, 3.12 and 3.14, plus isolated D-Bus integration.

## Hardware verification

The protocol implementation has been checked for brightness, RGB, actuation depth, Rapid Trigger and dead-zone readback on firmware 1.37. New daemon write paths and privileged installation still require independent end-to-end hardware validation.

Readback checks do not measure physical actuation accuracy. The 30 fps animation target is a software scheduling limit, not an optical measurement.
