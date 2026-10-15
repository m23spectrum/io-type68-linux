# HID protocol (experimental)

Observed hardware: USB `0c45:0256`, product IO Type 68 Magnetic WH, firmware 1.37; vendor interface 2, usage page `0xff68`. Discovery checks the HID uevent ID and a report descriptor beginning `06 68 ff`. `/dev/hidrawN` is resolved dynamically.

## Transport

An output packet is 64 bytes, preceded by hidraw's zero report ID (65 bytes written):

| Offset within report | Meaning |
|---|---|
| 0 | `AA` |
| 1 | command |
| 2 | payload size in this chunk, at most 56 |
| 3–4 | byte offset, little endian |
| 5 | zero |
| 6 | 1 on last chunk, otherwise 0 |
| 7 | zero |
| 8–63 | data, zero padded |

Responses start `55 command`; address is at bytes 3–4 and payload begins at byte 8. The transport checks command/address, complete response length and a two-second per-chunk timeout. Writes are followed by readback. Lighting comparison normalizes mode 20 to 128 and compares the supported mutable fields because firmware rewrites other bytes.

| Read | Write | Size | Data |
|---|---|---|---|
| `10` | — | 48 | firmware and precision information |
| `13` | `23` | 16 | lighting settings |
| `14` | `24` | 512 | 128 RGB slots: `id r g b` |
| `17` | `27` | 1024 | 128 magnetic slots, 8 bytes each |
| `11` | `21` | 56 | general settings, including dead zones |
| — | `32` | 272 | volatile frame: 68 × `id r g b` |

All commands in this table are hexadecimal. Other commands are rejected by the transport; firmware/reset commands are not exposed.

Lighting: mode byte 0; color-mode byte 8; brightness byte 9 (0–5); speed byte 10 (1–5); direction byte 11 (0–3). RGB bytes 1–3 are rewritten by firmware 1.37. Custom mode is requested as 128 and read back as 20. Writes set bytes 4/14/15 to `ff/aa/55`, matching the observed vendor sequence. Other general/magnetic bytes are preserved through read-modify-write.

Built-in mode IDs: 0 off, 1 static, 2 key-on, 3 key-off, 4 stars, 5 snow, 6 flowers, 7 breathing, 8 spectrum, 9 fountain, 10 cross waves, 11 wave, 12 mountain wave, 13 flash, 14 double wave, 15 ripple, 16 flow, 17 cascade, 18 rain, 19 pendulum; 128 custom/per-key. Names describe vendor modes and are not a separate visual characterization.

Magnetic slot: `<BBHHH` = axis/opaque byte, flags, actuation, RT press, RT release. Flag bit 0 enables RT; other bits preserved. Precision byte `info[29]`: actuation scale 1000 if 2, otherwise 100; RT scale 1000 if nonzero, otherwise 100. Firmware display derives from info bytes 8–9. General bytes 8/9 store top/bottom dead zones in hundredths of a millimeter.

Only IDs in the bundled 68-key layout are writable. Physical sensor accuracy and limits on other firmware remain unverified. Volatile frames avoid `24` table writes; this is not a claim about undocumented internal firmware storage.

## D-Bus

Session service/interface `local.io.Keyboard`, path `/local/io/Keyboard`, retained for compatibility with the original menu:

- `Snapshot() -> JSON string`: short lighting read plus cached magnetic settings.
- `RefreshKeys() -> JSON string`: full refreshed state.
- `Apply(JSON string) -> JSON string`: `{ok, state}` or `{ok:false, error}`.
- `org.freedesktop.DBus.Properties.State`: JSON string; PropertiesChanged after operations.

Example request: `{"kind":"keys","selected":[34,49,50,51],"values":{"trigger":0.2}}`.
Kinds: `lighting`, `keys`, `deadzone`, `effect`. Numeric inputs, colors, keys and fields are validated before hardware writes. Unknown operations and firmware/reset commands are not exposed. One daemon serializes HID access; CLI always calls D-Bus. A per-user runtime flock prevents two copies of this transport from writing simultaneously; third-party tools do not obey this lock.
