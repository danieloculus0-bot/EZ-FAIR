# EZ FAIR deployment and firewall approval packet

## Purpose
EZ FAIR is a local Windows desktop application used to extract inspection characteristics from engineering drawings, review them, create ballooned PDFs, and generate first article inspection records.

## Installation model
- Machine-wide Windows application
- Default installation path: `C:\Program Files\EZ FAIR`
- Listed in Windows Apps and Features
- No browser extension
- No kernel driver
- No Windows service
- No inbound listener
- No scheduled task required
- No database server
- No administrative access required after installation except when Windows Installer performs an approved upgrade

## Local data
User settings and cache files are stored outside the installation directory under the current Windows user profile. Drawings and generated inspection records remain local or in user-selected company storage. EZ FAIR does not upload drawings, inspection data, or customer records.

## Required outbound firewall allowlist
HTTPS TCP 443 only. No inbound rule is required.

Required for update checks:
- `api.github.com`

Required for release pages and release asset redirects/downloads:
- `github.com`
- `objects.githubusercontent.com`
- `release-assets.githubusercontent.com`

GitHub may use additional addresses behind these hostnames. The rule should therefore be hostname/FQDN based rather than fixed-IP based.

## Exact update API
`https://api.github.com/repos/danieloculus0-bot/EZ-FAIR/releases/latest`

The application does not browse arbitrary GitHub content. It requests the latest public release metadata, retrieves the published `EZ-FAIR-release-manifest.json`, and downloads only the installer named by that manifest.

## Update security controls
1. The installed application compares semantic versions.
2. The release manifest identifies the approved installer filename.
3. The downloaded installer is verified against the manifest SHA-256 hash.
4. A failed or missing hash blocks installation.
5. When the publisher certificate is configured, Windows Authenticode validation must report `Valid` and the signer subject must match the approved publisher.
6. Windows elevation occurs through the normal installer/UAC process.
7. The application does not directly overwrite files under Program Files.

## Release artifacts
Each release includes:
- Machine-wide Windows installer
- Portable package for testing only
- CycloneDX software bill of materials
- Release integrity manifest with SHA-256 values
- GitHub-generated release notes

## Silent deployment
Current installer command:

```powershell
EZ-FAIR-<version>-Setup-x64.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

Uninstall is registered in Apps and Features. STR may deploy the installer through its normal RMM or endpoint-management platform.

## Publisher allowlisting
After a code-signing certificate is configured, the recommended policy is to allow machine-wide installation and upgrades for packages whose Authenticode signer matches the approved EZ FAIR publisher. This avoids per-version executable hash exceptions while preserving publisher-based control.

## Network behavior summary
- Outbound HTTPS update check only
- No telemetry
- No advertising
- No remote-control capability
- No customer drawing upload
- No automatic background installer execution
- Update is initiated by the user through **Check for Updates**

## Rollback
- Uninstall the current release through Apps and Features.
- Install the previously approved signed release.
- User settings and project files are stored separately from application binaries and are not intentionally removed during an application rollback.

## Initial STR actions requested
1. Approve the EZ FAIR installer for machine-wide deployment.
2. Allow outbound HTTPS to the four FQDNs listed above.
3. After signing is enabled, allow the approved EZ FAIR publisher certificate.
4. Optionally deploy subsequent releases through STR's normal endpoint-management platform. No application-specific technical assistance is expected from STR.
