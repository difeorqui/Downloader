"""Las tablas normativas de ``lists.py`` coinciden con el glosario 2.1 y 2.2 (T-05)."""

from __future__ import annotations

from downloader.domain.addresses import lists


def test_table_sizes_match_the_glossary() -> None:
    assert len(lists.INTERNAL_IPV4_NETWORKS) == 5
    assert len(lists.INTERNAL_IPV6_NETWORKS) == 2  # ::1 y fc00::/7
    assert len(lists.BLOCKED_IPV4_NETWORKS) == 10
    assert len(lists.BLOCKED_IPV6_NETWORKS) == 9
    assert len(lists.EMBEDDED_IPV4_NETWORKS) == 2
    assert len(lists.INTERNAL_NAME_SUFFIXES) == 7  # .localhost + los 6 sufijos
    assert {"localhost"} == lists.INTERNAL_EXACT_NAMES


def test_ipv4_internal_and_blocked_do_not_overlap() -> None:
    for internal in lists.INTERNAL_IPV4_NETWORKS:
        for blocked in lists.BLOCKED_IPV4_NETWORKS:
            assert not internal.overlaps(blocked), (internal, blocked)


def test_only_known_ipv6_overlaps_between_internal_and_blocked() -> None:
    """Los únicos solapes son los que el glosario resuelve a mano: ``::1`` y ``fd00:ec2::254``."""
    overlaps = {
        (str(internal), str(blocked))
        for internal in lists.INTERNAL_IPV6_NETWORKS
        for blocked in lists.BLOCKED_IPV6_NETWORKS
        if internal.overlaps(blocked)
    }
    assert overlaps == {("::1/128", "::/96"), ("fc00::/7", "fd00:ec2::254/128")}


def test_suffixes_start_with_a_dot_and_are_lowercase() -> None:
    for suffix in lists.INTERNAL_NAME_SUFFIXES:
        assert suffix.startswith(".")
        assert suffix == suffix.lower()
