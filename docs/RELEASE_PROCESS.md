# EZ-FAIR beta release checklist

The `main` branch is under active development. A Windows archive installer
must not fetch a moving `main.zip`. The Windows scripts now target the
`v0.2.0b1` tag and will remain unavailable until the tag is published.

Before tagging:

1. Review branch diff for confidential information per `AGENTS.md`; no
   employer/customer drawings, names, records or outputs are publishable.
2. Require green Linux + Windows CI and check the installed Python entrypoint.
3. Run installer and updater on an actual Windows machine, preferably a clean
   VM, with a vector PDF and a synthetic scanned PDF. Confirm Tesseract and
   English trained data, desktop shortcut, launch, output and preservation of
   `local_inputs` / `local_outputs`.
4. Validate a frozen, independently labeled, cleared drawing benchmark.
   Synthetic CI is a tool test and does not establish production accuracy.
5. Have the owner choose and explicitly approve a distribution license before
   authorizing distribution. Until then code is publicly readable, not
   automatically licensed for redistribution.
6. Publish the immutable release tag only after review. Never move or
   overwrite a previously published tag.
7. Download the GitHub source archive for the tag, calculate SHA-256 using
   `Get-FileHash -Algorithm SHA256 .\EZ-FAIR-v0.2.0b1.zip`, and publish the
   digest independently. Run the installer/updater with
   `-ExpectedSha256 <approved-digest>`. Without this optional parameter the
   installer warns that independent archive checksum verification was skipped.

Even after a tagged beta release, do **not** represent it as an authenticated,
unattended or customer-approved inspection system. The extraction result is a
proposal requiring engineering review. Updating version requires updating
`pyproject.toml`, `package_python_beta.ps1`, and the Windows scripts together.
