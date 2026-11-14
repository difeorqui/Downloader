"""Integración del ejecutor del lote contra un servidor HTTP local (127.0.0.1).

El servidor de pruebas vive solo en el equipo de pruebas y el dominio interno ``127.0.0.1`` se
autoriza explícitamente, como haría el usuario en el diálogo de confirmación.
"""

from __future__ import annotations

import http.server
import os
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from downloader.application.events import (
    AllDone,
    Cancelled,
    Event,
    Failed,
    Finished,
    Progress,
)
from downloader.application.runner import BatchRunner, RunConfig
from downloader.domain.batch.source import SourceLine
from downloader.domain.batch.validator import BatchValidation, validate_batch

BODY = bytes(range(256)) * 1200  # ~300 KB
SLOW_CHUNKS = 400
EXTENDED_DISPOSITION = "attachment; filename=\"x.txt\"; filename*=UTF-8''informe%20a%C3%B1o.txt"


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path == "/a.pdf":
            self._send(BODY, "application/pdf")
        elif path == "/named":
            self._send(
                BODY[:1000],
                "application/pdf",
                disposition='attachment; filename="reporte final.pdf"',
            )
        elif path == "/extended":
            self._send(
                b"x" * 10,
                "text/plain",
                disposition=EXTENDED_DISPOSITION,
            )
        elif path == "/malo":
            self._send(b"x", "text/plain", disposition='attachment; filename="..\\..\\malo.exe"')
        elif path == "/noext":
            self._send(b"<html></html>", "text/html")
        elif path == "/redir":
            self._redirect("/a.pdf")
        elif path == "/to-blocked":
            self._redirect("http://169.254.169.254/latest/meta-data")
        elif path == "/loop":
            self._redirect("/loop")
        elif path == "/slow":
            self._send_slow()
        elif path == "/short":
            self.send_response(200)
            self.send_header("Content-Length", "1000")
            self.end_headers()
            self.wfile.write(b"solo esto")
        else:
            self.send_error(404)

    def _send(self, body: bytes, content_type: str, disposition: str | None = None) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if disposition:
            self.send_header("Content-Disposition", disposition)
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str) -> None:
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_slow(self) -> None:
        self.send_response(200)
        self.send_header("Content-Length", str(SLOW_CHUNKS * 1024))
        self.end_headers()
        try:
            for _ in range(SLOW_CHUNKS):
                self.wfile.write(b"z" * 1024)
                self.wfile.flush()
                time.sleep(0.02)
        except OSError:
            return


@pytest.fixture(scope="module")
def base_url() -> Iterator[str]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def run_batch(
    urls: list[str],
    destination: Path,
    *,
    authorized: frozenset[str] = frozenset({"127.0.0.1"}),
    on_event: Callable[[Event, BatchRunner], None] | None = None,
    workers: int = 3,
) -> tuple[BatchValidation, list[Event]]:
    validation = validate_batch([SourceLine(n, url) for n, url in enumerate(urls, 1)])
    events: list[Event] = []

    def emit(event: Event) -> None:
        events.append(event)
        if on_event is not None:
            on_event(event, runner)

    config = RunConfig(
        destination=str(destination),
        required_folders=validation.required_folders,
        authorized_hosts=authorized,
        workers=workers,
    )
    runner = BatchRunner(config, validation.items, emit)
    runner.run()
    return validation, events


def only(events: list[Event], kind: type) -> list[Event]:
    return [event for event in events if isinstance(event, kind)]


def files_under(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())


def test_downloads_into_the_folders_of_the_url(base_url: str, tmp_path: Path) -> None:
    _, events = run_batch([f"{base_url}/a.pdf"], tmp_path)
    assert files_under(tmp_path) == ["127.0.0.1_" + base_url.rsplit(":", 1)[1] + "\\a.pdf"]
    saved = next(tmp_path.rglob("a.pdf"))
    assert saved.read_bytes() == BODY
    finished = only(events, Finished)
    assert len(finished) == 1
    assert isinstance(events[-1], AllDone)
    assert (events[-1].completed, events[-1].failed, events[-1].cancelled) == (1, 0, 0)


def test_progress_reaches_the_total(base_url: str, tmp_path: Path) -> None:
    _, events = run_batch([f"{base_url}/a.pdf"], tmp_path)
    progress = [e for e in events if isinstance(e, Progress)]
    assert progress
    assert progress[-1].downloaded == len(BODY)
    assert progress[-1].total == len(BODY)


def test_two_equal_names_never_overwrite_each_other(base_url: str, tmp_path: Path) -> None:
    run_batch([f"{base_url}/a.pdf?v=1", f"{base_url}/a.pdf?v=2"], tmp_path, workers=2)
    names = sorted(p.name for p in tmp_path.rglob("*.pdf"))
    assert names == ["a (1).pdf", "a.pdf"]


def test_an_existing_file_is_not_overwritten(base_url: str, tmp_path: Path) -> None:
    folder = tmp_path / ("127.0.0.1_" + base_url.rsplit(":", 1)[1])
    folder.mkdir()
    (folder / "a.pdf").write_bytes(b"original")
    run_batch([f"{base_url}/a.pdf"], tmp_path)
    assert (folder / "a.pdf").read_bytes() == b"original"
    assert (folder / "a (1).pdf").read_bytes() == BODY


def test_the_server_name_is_used_and_sanitized(base_url: str, tmp_path: Path) -> None:
    run_batch(
        [f"{base_url}/named", f"{base_url}/extended", f"{base_url}/malo"], tmp_path, workers=1
    )
    names = sorted(p.name for p in tmp_path.rglob("*") if p.is_file())
    assert names == ["informe año.txt", "malo.exe", "reporte final.pdf"]


def test_a_name_without_extension_gets_the_one_of_the_type(base_url: str, tmp_path: Path) -> None:
    run_batch([f"{base_url}/noext"], tmp_path)
    assert [p.name for p in tmp_path.rglob("*") if p.is_file()] == ["noext.html"]


def test_a_redirect_is_followed(base_url: str, tmp_path: Path) -> None:
    run_batch([f"{base_url}/redir"], tmp_path)
    saved = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert [p.name for p in saved] == [
        "redir.pdf"
    ]  # la carpeta y el nombre salen de la URL original
    assert saved[0].read_bytes() == BODY


def test_a_redirect_to_a_blocked_address_is_refused(base_url: str, tmp_path: Path) -> None:
    _, events = run_batch([f"{base_url}/to-blocked"], tmp_path)
    failed = only(events, Failed)
    assert [e.message for e in failed if isinstance(e, Failed)] == ["Dirección no permitida"]
    assert files_under(tmp_path) == []


def test_an_internal_address_not_authorized_is_refused(base_url: str, tmp_path: Path) -> None:
    _, events = run_batch([f"{base_url}/a.pdf"], tmp_path, authorized=frozenset())
    failed = [e for e in events if isinstance(e, Failed)]
    assert [e.message for e in failed] == ["Dirección interna no autorizada"]
    assert files_under(tmp_path) == []


def test_redirect_loops_stop(base_url: str, tmp_path: Path) -> None:
    _, events = run_batch([f"{base_url}/loop"], tmp_path)
    assert [e.message for e in events if isinstance(e, Failed)] == ["Demasiadas redirecciones"]


def test_http_errors_are_reported(base_url: str, tmp_path: Path) -> None:
    _, events = run_batch([f"{base_url}/nada"], tmp_path)
    assert [e.message for e in events if isinstance(e, Failed)] == ["El servidor respondió 404"]
    assert files_under(tmp_path) == []


def test_an_incomplete_download_leaves_nothing_behind(base_url: str, tmp_path: Path) -> None:
    _, events = run_batch([f"{base_url}/short"], tmp_path)
    assert len(only(events, Failed)) == 1
    assert files_under(tmp_path) == []  # ni el archivo ni el temporal


def test_cancelling_stops_the_download_and_removes_the_partial_file(
    base_url: str, tmp_path: Path
) -> None:
    def cancel_on_first_progress(event: Event, runner: BatchRunner) -> None:
        if isinstance(event, Progress) and event.downloaded > 0:
            runner.cancel()

    start = time.monotonic()
    _, events = run_batch([f"{base_url}/slow"], tmp_path, on_event=cancel_on_first_progress)
    assert time.monotonic() - start < SLOW_CHUNKS * 0.02  # no esperó a que terminara
    assert len(only(events, Cancelled)) == 1
    assert not only(events, Finished)
    assert files_under(tmp_path) == []
    last = events[-1]
    assert isinstance(last, AllDone)
    assert last.cancelled == 1


def test_cancelling_marks_the_pending_items_as_cancelled(base_url: str, tmp_path: Path) -> None:
    def cancel_on_first_progress(event: Event, runner: BatchRunner) -> None:
        if isinstance(event, Progress):
            runner.cancel()

    urls = [f"{base_url}/slow?n={n}" for n in range(8)]
    _, events = run_batch(urls, tmp_path, on_event=cancel_on_first_progress, workers=1)
    last = events[-1]
    assert isinstance(last, AllDone)
    assert last.completed == 0
    assert last.cancelled == 8
    assert files_under(tmp_path) == []


def test_temp_files_follow_the_documented_pattern_while_downloading(
    base_url: str, tmp_path: Path
) -> None:
    seen: list[str] = []

    def spy(event: Event, runner: BatchRunner) -> None:
        if isinstance(event, Progress) and not seen:
            seen.extend(
                name
                for _, _, names in os.walk(tmp_path)
                for name in names
                if name.endswith(".parcial")
            )
            runner.cancel()

    run_batch([f"{base_url}/slow"], tmp_path, on_event=spy)
    assert seen
    assert seen[0].startswith("~descargador-")
    assert len(seen[0]) == 53
