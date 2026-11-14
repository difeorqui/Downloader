"""Preferencias del usuario (tema y última carpeta destino) en ``%APPDATA%\\Descargador``."""

import json
import os
from dataclasses import dataclass, replace

from downloader.ui.themes import DEFAULT_THEME, PALETTES


def settings_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Descargador")


@dataclass(frozen=True, slots=True)
class Settings:
    theme: str = DEFAULT_THEME
    destination: str = ""

    def with_theme(self, theme: str) -> "Settings":
        return replace(self, theme=theme)

    def with_destination(self, destination: str) -> "Settings":
        return replace(self, destination=destination)


def load(directory: str | None = None) -> Settings:
    """Lee las preferencias; ante cualquier problema devuelve las predeterminadas."""
    path = os.path.join(directory or settings_dir(), "preferencias.json")
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, ValueError):
        return Settings()
    if not isinstance(data, dict):
        return Settings()
    theme = data.get("theme")
    destination = data.get("destination")
    return Settings(
        theme=theme if isinstance(theme, str) and theme in PALETTES else DEFAULT_THEME,
        destination=destination if isinstance(destination, str) else "",
    )


def save(settings: Settings, directory: str | None = None) -> None:
    """Guarda las preferencias; si no se puede escribir, se ignora (no es crítico)."""
    folder = directory or settings_dir()
    try:
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "preferencias.json"), "w", encoding="utf-8") as file:
            json.dump({"theme": settings.theme, "destination": settings.destination}, file)
    except OSError:
        return
