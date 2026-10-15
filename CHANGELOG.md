# Changelog

## 0.1.0 — 2026-10-15

Initial experimental release for IO by Red Square Type 68 Magnetic, USB 0c45:0256, firmware 1.37.

- Userspace HID transport, validated settings and readback verification.
- Keyboard brightness, whole/per-key RGB, built-in modes, speed and direction.
- Actuation, separate Rapid Trigger thresholds and top/bottom dead zones.
- Aurora, breathing, comet and rainbow host effects via volatile frames.
- CLI, session D-Bus daemon and Plasma 6 keyboard controls.
- One-command per-user installer and manifest-based uninstaller.
- Protocol tests, isolated D-Bus tests and installer tests.

Support is experimental. The standalone panel wrapper and root installation paths still need fresh-machine validation; physical actuation depth and optical animation rate have not been measured.
