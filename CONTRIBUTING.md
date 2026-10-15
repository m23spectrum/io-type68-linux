# Contributing

Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`. Tests must not need USB access. Include firmware version, USB ID, desktop version and sanitized error output with hardware reports. Never include passwords, serial numbers, full personal Steam/KDE configs or raw private session logs.

Changes to persistent writes need tests demonstrating preservation of unrelated bytes, validation before side effects and readback behavior. Do not add firmware/reset/calibration writes without separate protocol evidence and a recovery procedure. Prefer small patches; no speculative support based only on a matching VID/PID.

Run host effects using volatile frames, not persistent RGB-table writes per frame. Do not remove the transport lock or make the CLI open its own competing HID connection.
