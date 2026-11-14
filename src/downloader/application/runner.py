"""Ejecución de un lote: descarga en paralelo, avance y cancelación (versión rápida, specs 002/003).

Cada elemento: conexión comprobada (``open_url``) → nombre y ruta con el dominio
(``compute_target_path``, bajo un cerrojo porque las reservas no son seguras entre hilos) →
archivo temporal ``~descargador-<32>.parcial`` → renombrado al final solo si está completo. Nada
se sobrescribe y un fallo o una cancelación no dejan temporales.

Cancelar cierra los sockets abiertos, de modo que los hilos que esperan datos salen enseguida.
"""

import contextlib
import errno
import http.client
import os
import threading
import time
import uuid
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Final

from downloader.application.events import (
    AllDone,
    Cancelled,
    Event,
    Failed,
    Finished,
    Progress,
    Started,
)
from downloader.domain.batch.validator import BatchItem
from downloader.domain.paths.collisions import PathReservations
from downloader.domain.paths.failure import PathFailure
from downloader.domain.paths.length import PathLimits
from downloader.domain.paths.response import ServerResponse
from downloader.domain.paths.target import PathEnvironment, compute_target_path
from downloader.infrastructure.disk import FilesystemEntries
from downloader.infrastructure.net import (
    DownloadError,
    Opened,
    open_url,
    suggested_names,
)

CHUNK_BYTES: Final = 64 * 1024
MAX_FILE_BYTES: Final = 10 * 1024**3  # tope por archivo (RN-024)
PROGRESS_INTERVAL: Final = 0.1
DEFAULT_WORKERS: Final = 3


@dataclass(frozen=True, slots=True)
class RunConfig:
    """Parámetros fijos de un lote."""

    destination: str
    required_folders: frozenset[str]  # de ``BatchValidation.required_folders``
    authorized_hosts: frozenset[str] = frozenset()  # dominios internos que el usuario permitió
    long_paths_enabled: bool = False
    workers: int = DEFAULT_WORKERS


class BatchRunner:
    """Descarga los elementos de un lote validado. ``run`` bloquea: se llama desde un hilo."""

    def __init__(
        self, config: RunConfig, items: Sequence[BatchItem], emit: Callable[[Event], None]
    ) -> None:
        self._destination = config.destination
        self._items = list(items)
        self._authorized = config.authorized_hosts
        self._emit = emit
        self._workers = config.workers
        self._cancel = threading.Event()
        self._lock = threading.Lock()  # reservas de nombres y conexiones activas
        self._active: set[http.client.HTTPConnection] = set()
        self._counts = {"completed": 0, "failed": 0, "cancelled": 0}
        self._env = PathEnvironment(
            FilesystemEntries(config.destination),
            PathReservations(config.required_folders),
            PathLimits(config.long_paths_enabled),
        )

    def cancel(self) -> None:
        """Pide cancelar: los hilos que esperan datos salen al cerrarse sus conexiones."""
        self._cancel.set()
        with self._lock:
            connections = list(self._active)
        for connection in connections:
            with contextlib.suppress(OSError):
                connection.close()

    def run(self) -> None:
        with ThreadPoolExecutor(max_workers=self._workers) as pool:
            for item in self._items:
                pool.submit(self._download, item)
        self._emit(AllDone(**self._counts))

    # --- un elemento ---------------------------------------------------------------------------

    def _download(self, item: BatchItem) -> None:
        index = item.index
        if self._cancel.is_set():
            self._finish_cancelled(index)
            return
        self._emit(Started(index))
        temp_path: str | None = None
        opened: Opened | None = None
        try:
            opened = open_url(item.url, self._authorized)
            with self._lock:
                self._active.add(opened.connection)
            target, temp_path, warnings = self._prepare(item, opened)
            self._stream(index, opened, temp_path)
            self._publish(temp_path, target)
            temp_path = None
            self._count("completed")
            self._emit(Finished(index, target, warnings))
        except DownloadError as error:
            self._fail_or_cancel(index, str(error))
        except (OSError, http.client.HTTPException) as error:
            self._fail_or_cancel(index, self._describe(error))
        finally:
            if opened is not None:
                with self._lock:
                    self._active.discard(opened.connection)
                with contextlib.suppress(OSError):
                    opened.close()
            if temp_path is not None:
                with contextlib.suppress(OSError):
                    os.remove(temp_path)

    def _prepare(self, item: BatchItem, opened: Opened) -> tuple[str, str, tuple[str, ...]]:
        response = opened.response
        simple, extended = suggested_names(response.getheader("Content-Disposition"))
        server = ServerResponse(
            filename=simple,
            filename_ext=extended,
            content_type=response.getheader("Content-Type"),
            final_url=opened.final_url,
        )
        with self._lock:
            result = compute_target_path(self._destination, item.url, server, self._env)
        if isinstance(result, PathFailure):
            raise DownloadError(result.code.message)
        length = response.getheader("Content-Length")
        if length is not None and length.isdigit() and int(length) > MAX_FILE_BYTES:
            raise DownloadError("El archivo supera el tamaño máximo permitido")
        folder = os.path.dirname(result.full_path)
        os.makedirs(folder, exist_ok=True)
        temp_path = os.path.join(folder, f"~descargador-{uuid.uuid4().hex}.parcial")
        return result.full_path, temp_path, tuple(w.message for w in sorted(result.warnings))

    def _stream(self, index: int, opened: Opened, temp_path: str) -> None:
        response = opened.response
        length = response.getheader("Content-Length")
        total = int(length) if length is not None and length.isdigit() else None
        done = 0
        last_report = 0.0
        with open(temp_path, "xb") as out:
            while chunk := response.read(CHUNK_BYTES):
                if self._cancel.is_set():
                    raise DownloadError("cancelado")
                out.write(chunk)
                done += len(chunk)
                if done > MAX_FILE_BYTES:
                    raise DownloadError("El archivo supera el tamaño máximo permitido")
                now = time.monotonic()
                if now - last_report >= PROGRESS_INTERVAL:
                    last_report = now
                    self._emit(Progress(index, done, total))
        if self._cancel.is_set():
            raise DownloadError("cancelado")
        if total is not None and done != total:
            raise DownloadError("La descarga quedó incompleta")
        self._emit(Progress(index, done, total))

    @staticmethod
    def _publish(temp_path: str, target: str) -> None:
        try:
            os.rename(temp_path, target)  # en Windows falla si el destino ya existe: no sobrescribe
        except FileExistsError as error:
            raise DownloadError("El archivo ya existe") from error

    # --- cuentas -------------------------------------------------------------------------------

    def _count(self, key: str) -> None:
        with self._lock:
            self._counts[key] += 1

    def _finish_cancelled(self, index: int) -> None:
        self._count("cancelled")
        self._emit(Cancelled(index))

    def _fail_or_cancel(self, index: int, message: str) -> None:
        if self._cancel.is_set():
            self._finish_cancelled(index)
            return
        self._count("failed")
        self._emit(Failed(index, message))

    @staticmethod
    def _describe(error: Exception) -> str:
        if isinstance(error, TimeoutError):
            return "Se agotó el tiempo de espera del servidor"
        if isinstance(error, PermissionError):
            return "No hay permiso para escribir en la carpeta destino"
        if isinstance(error, OSError) and error.errno == errno.ENOSPC:
            return "No hay espacio suficiente en el disco"
        return "La conexión se interrumpió"
