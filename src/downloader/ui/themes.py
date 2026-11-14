"""Paletas de la interfaz: claro, oscuro y cálido (RN-038, versión rápida)."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Palette:
    name: str
    background: str
    surface: str
    foreground: str
    muted: str
    accent: str
    accent_text: str
    border: str
    success: str
    error: str
    selection: str


LIGHT = Palette(
    name="Claro",
    background="#F6F7F9",
    surface="#FFFFFF",
    foreground="#1F2328",
    muted="#5B6573",
    accent="#2563EB",
    accent_text="#FFFFFF",
    border="#D5DAE1",
    success="#1A7F37",
    error="#CF222E",
    selection="#DCE7FD",
)
DARK = Palette(
    name="Oscuro",
    background="#15171C",
    surface="#1E2128",
    foreground="#E6EAF0",
    muted="#9AA4B2",
    accent="#5B9BFF",
    accent_text="#0B1220",
    border="#323844",
    success="#4CC38A",
    error="#FF7B72",
    selection="#2B3A57",
)
WARM = Palette(
    name="Cálido",
    background="#FBF4E9",
    surface="#FFFCF6",
    foreground="#3A2E27",
    muted="#7D6A5B",
    accent="#B4531A",
    accent_text="#FFFFFF",
    border="#E5D6BF",
    success="#2F7D3B",
    error="#B3261E",
    selection="#F3DFC2",
)

PALETTES: dict[str, Palette] = {palette.name: palette for palette in (LIGHT, DARK, WARM)}
DEFAULT_THEME = LIGHT.name
