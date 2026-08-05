"""Controlled GitHub Release updater for EZ FAIR.

The updater only consumes published release assets, verifies the installer
against the release manifest, and can enforce an Authenticode publisher once a
code-signing certificate is configured.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from app_version import APP_VERSION

LATEST_RELEASE_API = "https://api.github.com/repos/danieloculus0-bot/EZ-FAIR/releases/latest"
MANIFEST_NAME = "EZ-FAIR-release-manifest.json"
INSTALLER_SUFFIXES = ("-Setup-x64.exe", "-x64.msi")
EXPECTED_PUBLISHER = os.environ.get("EZ_FAIR_EXPECTED_PUBLISHER", "").strip()


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    release_name: str
    notes: str
    download_url: str | None
    release_url: str
    installer_name: str | None = None
    installer_sha256: str | None = None

    @property
    def available(self) -> bool:
        return _version_tuple(self.latest_version) > _version_tuple(self.current_version)


def _version_tuple(value: str) -> tuple[int, ...]:
    clean = value.strip().lower().lstrip("v").split("-", 1)[0]
    parts: list[int] = []
    for token in clean.split("."):
        try:
            parts.append(int(token))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _request_json(url: str, timeout: int) -> dict:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": f"EZ-FAIR/{APP_VERSION}"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def check_for_updates(timeout: int = 8) -> UpdateInfo:
    payload = _request_json(LATEST_RELEASE_API, timeout)
    assets = {str(asset.get("name", "")): asset for asset in payload.get("assets", [])}

    manifest: dict = {}
    manifest_asset = assets.get(MANIFEST_NAME)
    if manifest_asset and manifest_asset.get("browser_download_url"):
        manifest = _request_json(str(manifest_asset["browser_download_url"]), timeout)

    installer_name = str(manifest.get("installer", {}).get("name") or "") or None
    installer_sha256 = str(manifest.get("installer", {}).get("sha256") or "") or None

    if not installer_name:
        for name in assets:
            if name.endswith(INSTALLER_SUFFIXES):
                installer_name = name
                break

    asset_url: str | None = None
    if installer_name and installer_name in assets:
        asset_url = str(assets[installer_name].get("browser_download_url") or "") or None

    return UpdateInfo(
        current_version=APP_VERSION,
        latest_version=str(payload.get("tag_name", "0.0.0")).lstrip("v"),
        release_name=str(payload.get("name") or payload.get("tag_name") or "EZ FAIR update"),
        notes=str(payload.get("body") or ""),
        download_url=asset_url,
        release_url=str(payload.get("html_url") or "https://github.com/danieloculus0-bot/EZ-FAIR/releases"),
        installer_name=installer_name,
        installer_sha256=installer_sha256,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def _verify_authenticode(path: Path) -> None:
    if not EXPECTED_PUBLISHER:
        return
    command = (
        "$s=Get-AuthenticodeSignature -LiteralPath $args[0];"
        "if($s.Status -ne 'Valid'){exit 2};"
        "$subject=$s.SignerCertificate.Subject;"
        "if($subject -notlike ('*'+$args[1]+'*')){exit 3};"
        "Write-Output $subject"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command, str(path), EXPECTED_PUBLISHER],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 2:
        raise RuntimeError("The downloaded EZ FAIR installer does not have a valid digital signature.")
    if result.returncode == 3:
        raise RuntimeError("The downloaded installer was not signed by the approved EZ FAIR publisher.")
    if result.returncode != 0:
        raise RuntimeError("Windows could not verify the installer signature.")


def download_and_launch_installer(info: UpdateInfo) -> Path:
    if not info.available:
        raise ValueError("No newer EZ FAIR release is available.")
    if not info.download_url or not info.installer_name:
        raise RuntimeError("The latest release does not contain an approved Windows installer.")
    if not info.installer_sha256:
        raise RuntimeError("The release is missing its integrity manifest. Update was blocked.")

    target = Path(tempfile.gettempdir()) / info.installer_name
    request = urllib.request.Request(info.download_url, headers={"User-Agent": f"EZ-FAIR/{APP_VERSION}"})
    with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as output:
        for chunk in iter(lambda: response.read(1024 * 1024), b""):
            output.write(chunk)

    actual_hash = _sha256(target)
    if actual_hash != info.installer_sha256.lower():
        target.unlink(missing_ok=True)
        raise RuntimeError("The downloaded installer failed SHA-256 verification. Update was blocked.")

    if os.name != "nt":
        raise RuntimeError("Installer launch is supported only on Windows.")
    _verify_authenticode(target)

    if target.suffix.lower() == ".msi":
        subprocess.Popen(["msiexec.exe", "/i", str(target)], close_fds=True)
    else:
        subprocess.Popen([str(target)], close_fds=True)
    return target
