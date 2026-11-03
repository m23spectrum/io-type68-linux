# Changelog

## 0.2.0 — 2026-11-04

- Add a percentage brightness slider for per-key static colors in the Plasma widget.
- Scale each saved key color through volatile frames without rewriting the per-key color table during dragging.
- Keep the hardware's six brightness levels for built-in effects and host effects.
- Cover per-key scaling, validation, hardware brightness and the D-Bus API with simulated-device tests.

Smooth brightness is experimental and requires the daemon and per-key color mode. Its intermediate level is not saved; activating it sets the keyboard's hardware brightness to maximum. The saved per-key colors remain unchanged. Built-in and host effects continue to use the hardware brightness levels.

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
