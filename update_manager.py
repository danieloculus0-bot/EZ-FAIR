"""GitHub Release based updater for EZ FAIR."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from app_version import APP_VERSION

LATEST_RELEASE_API = "https://api.github.com/repos/danieloculus0-bot/EZ-FAIR/releases/latest"
INSTALLER_SUFFIXES = ("-Setup-x64.exe", "-Windows-x64.exe")


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    release_name: str
    notes: str
    download_url: str | None
    release_url: str

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


def check_for_updates(timeout: int = 8) -> UpdateInfo:
    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": f"EZ-FAIR/{APP_VERSION}"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)

    asset_url: str | None = None
    for asset in payload.get("assets", []):
        name = str(asset.get("name", ""))
        if name.endswith(INSTALLER_SUFFIXES):
            asset_url = str(asset.get("browser_download_url"))
            break

    return UpdateInfo(
        current_version=APP_VERSION,
        latest_version=str(payload.get("tag_name", "0.0.0")).lstrip("v"),
        release_name=str(payload.get("name") or payload.get("tag_name") or "EZ FAIR update"),
        notes=str(payload.get("body") or ""),
        download_url=asset_url,
        release_url=str(payload.get("html_url") or "https://github.com/danieloculus0-bot/EZ-FAIR/releases"),
    )


def download_and_launch_installer(info: UpdateInfo) -> Path:
    if not info.available:
        raise ValueError("No newer EZ FAIR release is available.")
    if not info.download_url:
        raise RuntimeError("The latest release does not contain a Windows installer.")

    target = Path(tempfile.gettempdir()) / f"EZ-FAIR-{info.latest_version}-Setup-x64.exe"
    request = urllib.request.Request(info.download_url, headers={"User-Agent": f"EZ-FAIR/{APP_VERSION}"})
    with urllib.request.urlopen(request, timeout=60) as response, target.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)

    if os.name != "nt":
        raise RuntimeError("Installer launch is supported only on Windows.")
    subprocess.Popen([str(target)], close_fds=True)
    return target
