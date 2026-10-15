# Publishing releases

Repository: https://github.com/m23spectrum/io-type68-linux

1. Run the unit and isolated D-Bus tests, build a wheel, and review the exact release commit.
2. Confirm the GitHub Actions checks are green. Keep hardware and UI validation limits in the release notes.
3. Tag the reviewed commit and create a GitHub release. Attach a source archive, wheel and SHA256 checksums if desired.
4. Never include private settings, vendor firmware/JavaScript, session logs or credentials.

Experimental v0.1.0 supports one verified device/firmware combination; it is not an official IO/Red Square driver. New firmware requires new hardware verification before support is advertised.
