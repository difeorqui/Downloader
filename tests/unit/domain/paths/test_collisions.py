"""Colisiones y reservas (RN-012 a-c, RN-013 b, D-12; CA-001-86 a 91; ejemplos del anexo 1)."""

from __future__ import annotations

import itertools
import random

import pytest
from hypothesis import given
from hypothesis import strategies as st

from downloader.domain.catalog import FailureCode
from downloader.domain.paths.collisions import (
    EntryKind,
    InMemoryDiskEntries,
    PathReservations,
    add_suffix,
    first_folder_problem,
    has_extension_for_suffix,
)

FILE = EntryKind.FILE
DIRECTORY = EntryKind.DIRECTORY
LINK = EntryKind.REPARSE_POINT
SITE = ("sitio.com",)
EMPTY_DISK = InMemoryDiskEntries()


def reserve(
    reservations: PathReservations,
    folder_parts: tuple[str, ...],
    name: str,
    disk: InMemoryDiskEntries = EMPTY_DISK,
) -> str:
    """Pide y confirma un nombre, como hará ``compute_target_path``."""
    candidate = reservations.find_name(folder_parts, name, disk)
    reservations.commit(candidate)
    return candidate.file_name


def fresh(required: frozenset[str] = frozenset()) -> PathReservations:
    return PathReservations(required)


# --- Posición del sufijo (CA-001-86, 87; S-001-12) -----------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("informe.pdf", "informe (1).pdf"),
        ("informe.final.pdf", "informe.final (1).pdf"),  # CA-001-87
        ("docs", "docs (1)"),  # CA-001-87
        ("x", "x (1)"),
        (".htaccess", ".htaccess (1)"),  # CA-001-86: el punto inicial no abre una extensión
        (".gitignore", ".gitignore (1)"),
        ("v1.2", "v1 (1).2"),  # CA-001-86
        ("a.b", "a (1).b"),
        ("a.tar.gz", "a.tar (1).gz"),
        ("a. b", "a (1). b"),
        ("index", "index (1)"),
        ("a (1).pdf", "a (1) (1).pdf"),
    ],
)
def test_suffix_goes_before_the_last_extension(name: str, expected: str) -> None:
    assert add_suffix(name, 1) == expected


def test_suffix_number_is_used_as_given() -> None:
    assert add_suffix("a.pdf", 12) == "a (12).pdf"


def test_trailing_dot_names_do_not_reach_here_but_are_still_handled() -> None:
    """``x.`` y ``a.b.`` se sanean antes (RN-014 c); aquí el punto final no abre extensión."""
    assert has_extension_for_suffix("a.b.") is False
    assert add_suffix("x.", 1) == "x. (1)"
    assert add_suffix("a.b.", 1) == "a.b. (1)"


# --- Existe en disco (CA-001-88, ejemplo 18) -----------------------------------------------------


def test_example_18_existing_file_gets_suffix_1() -> None:
    disk = InMemoryDiskEntries({("sitio.com", "a.pdf"): FILE})
    assert reserve(fresh(), SITE, "a.pdf", disk) == "a (1).pdf"


def test_ca_001_88_existing_as_a_folder_also_counts() -> None:
    disk = InMemoryDiskEntries({("sitio.com", "a.pdf"): DIRECTORY})
    assert reserve(fresh(), SITE, "a.pdf", disk) == "a (1).pdf"


def test_ca_001_88_existing_as_a_link_also_counts() -> None:
    disk = InMemoryDiskEntries({("sitio.com", "a.pdf"): LINK})
    assert reserve(fresh(), SITE, "a.pdf", disk) == "a (1).pdf"


def test_ca_001_88_case_is_ignored_like_windows() -> None:
    disk = InMemoryDiskEntries({("SITIO.COM", "A.PDF"): FILE})
    assert reserve(fresh(), SITE, "a.pdf", disk) == "a (1).pdf"
    disk = InMemoryDiskEntries({("sitio.com", "Á.pdf"): FILE})  # Á
    assert reserve(fresh(), SITE, "á.pdf", disk) == "á (1).pdf"


def test_ca_001_88_the_suffix_skips_numbers_that_are_also_taken() -> None:
    disk = InMemoryDiskEntries(
        {
            ("sitio.com", "a.pdf"): FILE,
            ("sitio.com", "a (1).pdf"): FILE,
            ("sitio.com", "a (2).pdf"): DIRECTORY,
        }
    )
    assert reserve(fresh(), SITE, "a.pdf", disk) == "a (3).pdf"


def test_a_free_name_is_kept() -> None:
    assert reserve(fresh(), SITE, "a.pdf") == "a.pdf"


def test_names_in_other_folders_do_not_collide() -> None:
    disk = InMemoryDiskEntries({("otro.com", "a.pdf"): FILE, ("sitio.com", "sub", "a.pdf"): FILE})
    assert reserve(fresh(), SITE, "a.pdf", disk) == "a.pdf"


# --- Reservado por otro elemento del lote (CA-001-89, ejemplo 19) --------------------------------


def test_example_19_second_request_for_the_same_name_gets_a_suffix() -> None:
    reservations = fresh()
    folder = ("sitio.com", "x")
    assert reserve(reservations, folder, "A.pdf") == "A.pdf"
    assert reserve(reservations, folder, "a.pdf") == "a (1).pdf"


def test_ca_001_89_the_first_call_keeps_the_name_and_the_result_depends_on_order() -> None:
    folder = ("sitio.com", "x")
    forward = fresh()
    assert [reserve(forward, folder, n) for n in ("A.pdf", "a.pdf")] == ["A.pdf", "a (1).pdf"]
    backward = fresh()
    assert [reserve(backward, folder, n) for n in ("a.pdf", "A.pdf")] == ["a.pdf", "A (1).pdf"]


def test_three_equal_names_get_consecutive_suffixes() -> None:
    reservations = fresh()
    names = [reserve(reservations, SITE, "a.pdf") for _ in range(4)]
    assert names == ["a.pdf", "a (1).pdf", "a (2).pdf", "a (3).pdf"]


def test_finding_a_name_does_not_reserve_it() -> None:
    reservations = fresh()
    first = reservations.find_name(SITE, "a.pdf", EMPTY_DISK)
    second = reservations.find_name(SITE, "a.pdf", EMPTY_DISK)
    assert first == second
    assert not reservations.is_reserved(SITE, "a.pdf")
    reservations.commit(first)
    assert reservations.is_reserved(SITE, "a.pdf")
    assert reservations.find_name(SITE, "a.pdf", EMPTY_DISK).file_name == "a (1).pdf"


def test_an_uncommitted_candidate_does_not_advance_the_counter() -> None:
    """Si el elemento acaba fallando (F-25...), el sufijo que iba a usar queda libre."""
    reservations = fresh()
    reserve(reservations, SITE, "a.pdf")
    abandoned = reservations.find_name(SITE, "a.pdf", EMPTY_DISK)
    assert abandoned.file_name == "a (1).pdf"
    assert reserve(reservations, SITE, "a.pdf") == "a (1).pdf"


def test_a_requested_name_that_looks_like_a_suffix_is_respected() -> None:
    reservations = fresh()
    assert reserve(reservations, SITE, "a (1).pdf") == "a (1).pdf"
    assert reserve(reservations, SITE, "a.pdf") == "a.pdf"
    assert reserve(reservations, SITE, "a.pdf") == "a (2).pdf"  # (1) ya está reservado


# --- Prevalecen las carpetas (CA-001-90, ejemplo 42) ---------------------------------------------

REQUIRED_DOCS = frozenset({"SITIO.COM", "SITIO.COM\\DOCS"})


def test_example_42_file_named_like_a_needed_folder_gets_a_suffix() -> None:
    reservations = fresh(REQUIRED_DOCS)
    assert reserve(reservations, SITE, "docs") == "docs (1)"


@pytest.mark.parametrize("order", list(itertools.permutations(["docs", "x.pdf"])))
def test_ca_001_90_the_folder_wins_in_any_order(order: tuple[str, ...]) -> None:
    reservations = fresh(REQUIRED_DOCS)
    results = {}
    for name in order:
        folder = SITE if name == "docs" else ("sitio.com", "docs")
        results[name] = reserve(reservations, folder, name)
    assert results == {"docs": "docs (1)", "x.pdf": "x.pdf"}


def test_ca_001_90_case_is_ignored_for_the_folder_too() -> None:
    reservations = fresh(REQUIRED_DOCS)
    assert reserve(reservations, SITE, "DOCS") == "DOCS (1)"
    assert reserve(reservations, SITE, "Docs") == "Docs (2)"


def test_the_suffixed_name_must_not_be_a_needed_folder_either() -> None:
    required = frozenset({"SITIO.COM", "SITIO.COM\\DOCS", "SITIO.COM\\DOCS (1)"})
    assert reserve(fresh(required), SITE, "docs") == "docs (2)"


def test_a_needed_folder_in_another_branch_does_not_matter() -> None:
    required = frozenset({"SITIO.COM", "SITIO.COM\\DOCS"})
    assert reserve(fresh(required), ("sitio.com", "sub"), "docs") == "docs"


# --- F-27 y F-24 (ejemplos 25 y 26; CA-001-91, 52) -----------------------------------------------


def test_example_25_a_file_where_a_folder_is_needed_is_f27() -> None:
    disk = InMemoryDiskEntries({("sitio.com", "docs"): FILE})
    assert first_folder_problem(("sitio.com", "docs"), disk) is FailureCode.F27


def test_ca_001_91_the_file_may_be_at_any_depth() -> None:
    disk = InMemoryDiskEntries({("sitio.com",): FILE})
    assert first_folder_problem(("sitio.com", "a", "b"), disk) is FailureCode.F27


def test_example_26_a_link_in_an_intermediate_folder_is_f24() -> None:
    disk = InMemoryDiskEntries({("sitio.com", "x"): LINK})
    assert first_folder_problem(("sitio.com", "x"), disk) is FailureCode.F24


def test_a_link_is_f24_wherever_it_points() -> None:
    """RN-013 b: no importa a dónde apunte; el dominio ni siquiera lo sabe."""
    disk = InMemoryDiskEntries({("sitio.com",): LINK})
    assert first_folder_problem(("sitio.com", "x", "y"), disk) is FailureCode.F24


def test_ca_001_52_the_first_problem_from_the_root_decides() -> None:
    disk = InMemoryDiskEntries({("sitio.com", "a"): LINK, ("sitio.com", "a", "b"): FILE})
    assert first_folder_problem(("sitio.com", "a", "b"), disk) is FailureCode.F24
    disk = InMemoryDiskEntries({("sitio.com", "a"): FILE, ("sitio.com", "a", "b"): LINK})
    assert first_folder_problem(("sitio.com", "a", "b"), disk) is FailureCode.F27


def test_existing_real_folders_and_missing_ones_are_fine() -> None:
    disk = InMemoryDiskEntries({("sitio.com",): DIRECTORY, ("sitio.com", "a"): DIRECTORY})
    assert first_folder_problem(("sitio.com", "a", "b"), disk) is None
    assert first_folder_problem(("nuevo.com", "a"), disk) is None
    assert first_folder_problem((), disk) is None


def test_the_destination_folder_itself_is_not_evaluated() -> None:
    """RN-013 b: la carpeta destino puede ser un enlace; la 002 la deja fuera de ``disk``."""
    assert first_folder_problem((), InMemoryDiskEntries({(): LINK})) is None


def test_folder_problems_ignore_case() -> None:
    disk = InMemoryDiskEntries({("SITIO.COM", "DOCS"): FILE})
    assert first_folder_problem(("sitio.com", "docs"), disk) is FailureCode.F27


# --- Coste (D-12) y determinismo -----------------------------------------------------------------


class CountingDisk(InMemoryDiskEntries):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def kind_of(self, relative_parts: tuple[str, ...]) -> EntryKind | None:
        self.calls += 1
        return super().kind_of(relative_parts)


def test_d12_ten_thousand_equal_names_cost_linear_lookups() -> None:
    disk = CountingDisk()
    reservations = fresh()
    names = [reserve(reservations, SITE, "a.pdf", disk) for _ in range(10_000)]
    assert names[0] == "a.pdf"
    assert names[1] == "a (1).pdf"
    assert names[-1] == "a (9999).pdf"
    assert len(set(names)) == 10_000
    assert disk.calls <= 2 * 10_000 + 10  # sin contador por nombre serían ~50 millones


def test_the_counter_is_per_requested_name() -> None:
    reservations = fresh()
    assert [reserve(reservations, SITE, n) for n in ("a.pdf", "b.pdf", "a.pdf", "b.pdf")] == [
        "a.pdf",
        "b.pdf",
        "a (1).pdf",
        "b (1).pdf",
    ]


@given(
    st.lists(
        st.sampled_from(["a.pdf", "A.PDF", "b", "B", "a (1).pdf", ".x", "c.tar.gz"]), max_size=30
    )
)
def test_every_reserved_name_is_unique_ignoring_case(requests: list[str]) -> None:
    reservations = fresh()
    folded = [reserve(reservations, SITE, name).upper() for name in requests]
    assert len(folded) == len(set(folded))


@given(
    st.lists(st.sampled_from(["a.pdf", "A.PDF", "b", "docs", "DOCS"]), min_size=1, max_size=12),
    st.randoms(),
)
def test_with_needed_folders_the_final_set_of_names_does_not_depend_on_the_order(
    requests: list[str], rng: random.Random
) -> None:
    """RN-012 b: una carpeta necesaria nunca se pierde, sin importar el orden de llamadas."""
    required = frozenset({"SITIO.COM", "SITIO.COM\\DOCS"})
    shuffled = list(requests)
    rng.shuffle(shuffled)
    for order in (requests, shuffled):
        reservations = fresh(required)
        names = [reserve(reservations, SITE, name) for name in order]
        assert all(name.upper() != "DOCS" for name in names)
