"""Disco real: puerto ``KnownDiskEntries`` del dominio y ubicaciones del sistema."""

import os

from downloader.domain.paths.collisions import EntryKind
from downloader.domain.paths.destination import SystemFolders


class FilesystemEntries:
    """Qué existe de verdad bajo la carpeta destino. Solo lee: nunca crea ni sigue enlaces."""

    def __init__(self, root: str) -> None:
        self._root = root

    def kind_of(self, relative_parts: tuple[str, ...]) -> EntryKind | None:
        path = os.path.join(self._root, *relative_parts)
        if os.path.islink(path) or os.path.isjunction(path):
            return EntryKind.REPARSE_POINT
        if os.path.isdir(path):
            return EntryKind.DIRECTORY
        if os.path.lexists(path):
            return EntryKind.FILE
        return None


def system_folders(app_data: str) -> SystemFolders:
    """Ubicaciones del sistema (RN-007 c) tomadas de las variables de entorno de Windows."""
    drive = os.environ.get("SYSTEMDRIVE", "C:")
    return SystemFolders(
        windows=os.environ.get("SYSTEMROOT", f"{drive}\\Windows"),
        program_files=os.environ.get("PROGRAMFILES", f"{drive}\\Program Files"),
        program_files_x86=os.environ.get("PROGRAMFILES(X86)", f"{drive}\\Program Files (x86)"),
        program_data=os.environ.get("PROGRAMDATA", f"{drive}\\ProgramData"),
        app_data=app_data,
        system_drive_root=f"{drive}\\",
    )


def is_writable_folder(path: str) -> bool:
    """RN-007 b: se puede escribir si se logra crear y borrar un archivo temporal."""
    probe = os.path.join(path, f"~descargador-prueba-{os.getpid()}.tmp")
    try:
        with open(probe, "xb"):
            pass
        os.remove(probe)
    except OSError:
        return False
    return True
