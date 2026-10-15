# Verification scope

## Original hardware implementation

Developed against one IO Type 68 Magnetic WH, `0c45:0256`, firmware 1.37. The original installed bridge received successful device replies and readback for brightness, RGB table, one-key actuation, Rapid Trigger and dead zones. Tests of magnetic settings checked preservation of other slots and restored pre-test values. The user visually confirmed alternating red/blue volatile frames. This does not measure physical sensor actuation or end-to-end input latency.

Persistent HID connection reuse removed repeated open overhead. The updated original bridge's animation scheduler measured about 29.9 fps at the software frame-completion boundary; an earlier implementation ran about 19–20 fps. Neither figure is an optical measurement or a performance guarantee for another machine/firmware.

The protocol and frame generators in this release derive from that implementation. The release adds strict whole-request validation, an explicit command allowlist, short-write detection and a runtime flock.

## Release verification on the development desktop

- Eight protocol unit tests passed: 19-chunk transfer for a 1024-byte read, report ID/header/final marker, rejection of unsupported command, rejection of invalid mixed requests without side effects, magnetic record/flag preservation, RGB slot preservation, dead-zone byte preservation, four volatile effect generators and CLI key selection.
- Separate daemon passed an isolated real D-Bus test using an in-memory HID device: snapshot, magnetic write, error result, running effect, palette change while animating, stop/restore and Properties.Get.
- The new CLI read the **existing installed bridge** and received connected=true, firmware=1.37. This confirms CLI/API interoperability, not an independent end-to-end hardware-write test of the new daemon.
- `IOKeyboardControls.qml` instantiated using the host PySide6/Qt QML engine and installed KDE modules, offscreen, without QML errors. The standalone panel wrapper was subsequently installed on a real Plasma 6.7.5 panel and visually checked with the existing bridge. Lighting, the 68-key layout, WASD selection, actuation, RT and dead-zone controls were visible; no persistent keyboard writes were made during screenshot capture. The default popup was enlarged and padded to fit the advanced controls. The screenshot in docs/images is an actual capture of this widget only.
- Five installer tests passed: staged install/upgrade/uninstall, conflict preservation, modified-file preservation, failure rollback and manifest path rejection.
- Per-user installer staged files in a scratch directory; staged CLI `--help` ran successfully. Current desktop installation and panel were not replaced.
- A wheel built successfully. CI definitions are included; current GitHub checks are visible in the repository Actions tab. Local checks do not substitute for hosted CI.

No new persistent hardware settings were written during release packaging. The existing all-in-one bridge remains installed. No proprietary vendor bundle, device-state backup, serial number or private desktop configuration is included.

## Remaining release checks

Test the standalone widget on another Plasma 6 session, install/uninstall on another machine with compatible hardware, and repeat readback checks for any new firmware before advertising support. A firmware version readout alone does not prove the same settings/protocol semantics.

The updated one-command installer was additionally checked against the current desktop: it correctly refused the existing original bridge before any changes. Root package/udev operations were not executed during packaging. Those paths require a fresh-machine check.
