"""Validación previa del lote (RN-004 a RN-006, RN-012 b, RN-017 a; CA-001-35 a 43; S-001-09)."""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from hypothesis import given
from hypothesis import strategies as st

from downloader.domain.addresses import AddressClass
from downloader.domain.batch.file_decoder import DecodedBatch, decode_batch_file
from downloader.domain.batch.source import SourceLine
from downloader.domain.batch.validator import (
    BatchValidation,
    InternalHost,
    validate_batch,
)
from downloader.domain.catalog import InvalidReason

CANARY = "CANARIO-2b8e"


def lines(*texts: str) -> list[SourceLine]:
    return [SourceLine(number, text) for number, text in enumerate(texts, start=1)]


def validate(*texts: str) -> BatchValidation:
    return validate_batch(lines(*texts))


def urls(result: BatchValidation) -> list[str]:
    return [item.url.processed() for item in result.items]


# --- CA-001-36 a 40: duplicados ---------------------------------------------------------------


def test_ca_001_36_fragment_and_host_case_make_duplicates() -> None:
    result = validate(
        "https://sitio.com/a.pdf", "https://sitio.com/a.pdf#parte2", "https://SITIO.com/a.pdf"
    )
    assert urls(result) == ["https://sitio.com/a.pdf"]
    assert result.items[0].line == 1  # se conserva la primera aparición
    assert result.duplicates == 2


def test_ca_001_37_standard_port_is_a_duplicate_but_the_other_scheme_port_is_not() -> None:
    assert validate("https://a.com:443/x", "https://a.com/x").duplicates == 1
    result = validate("http://a.com:443/x", "http://a.com/x")
    assert result.duplicates == 0
    assert len(result.items) == 2


def test_ca_001_38_scheme_case_and_idn_forms() -> None:
    assert validate("HTTPS://a.com/x", "https://a.com/x").duplicates == 1
    assert validate("https://bogotá.com/x", "https://xn--bogot-1qa.com/x").duplicates == 1


def test_ca_001_39_paths_are_case_sensitive() -> None:
    result = validate("https://sitio.com/x/A.pdf", "https://sitio.com/x/a.pdf")
    assert len(result.items) == 2
    assert result.duplicates == 0


def test_ca_001_40_parameters_count_and_encoding_is_applied_first() -> None:
    assert len(validate("https://s.com/a.pdf?v=1", "https://s.com/a.pdf?v=2").items) == 2
    assert validate("https://sitio.com/a b.pdf", "https://sitio.com/a%20b.pdf").duplicates == 1


def test_a_missing_scheme_equals_the_corrected_url() -> None:
    assert validate("sitio.com/a.pdf", "https://sitio.com/a.pdf").duplicates == 1


# --- Corregidas (CA-001-41) ---------------------------------------------------------------------


def test_ca_001_41_scheme_and_encoding_count_once_and_appear_in_both() -> None:
    result = validate(
        "sitio.com/a b.pdf",  # sin esquema y codificada
        "otro.com/x.pdf",  # solo sin esquema
        "https://c.com/ñ.pdf",  # solo codificada
        "https://d.com/limpia.pdf",
    )
    assert result.corrected == 3
    assert result.corrected_no_scheme == 2
    assert result.corrected_encoded == 2


def test_duplicates_are_not_counted_as_corrected() -> None:
    result = validate("https://a.com/x", "a.com/x", "a.com/x")
    assert len(result.items) == 1
    assert result.duplicates == 2
    assert result.corrected == 0  # la primera aparición no estaba corregida


def test_case_alone_is_not_a_correction() -> None:
    assert validate("HTTPS://Sitio.COM/a.pdf").corrected == 0


# --- Dominios internos (CA-001-42; ejemplos 27 y 44) --------------------------------------------


def test_ca_001_42_internal_hosts_are_listed_once_with_their_count() -> None:
    result = validate(
        "http://intranet/a",
        "https://publico.com/a",
        "http://intranet/b",
        "http://10.0.0.1/a",
        "http://intranet/c",
    )
    assert result.internal_hosts == (InternalHost("intranet", 3), InternalHost("10.0.0.1", 1))
    assert [item.address_class for item in result.items] == [
        AddressClass.INTERNAL,
        AddressClass.PUBLIC,
        AddressClass.INTERNAL,
        AddressClass.INTERNAL,
        AddressClass.INTERNAL,
    ]


def test_example_27_decimal_ip_is_internal() -> None:
    result = validate("https://2130706433/a.pdf")
    assert result.items[0].address_class is AddressClass.INTERNAL
    assert result.internal_hosts == (InternalHost("2130706433", 1),)


def test_example_44_trailing_dot_is_removed_before_classifying() -> None:
    result = validate("https://localhost./a.pdf")
    assert result.items[0].address_class is AddressClass.INTERNAL
    assert result.internal_hosts == (InternalHost("localhost", 1),)


def test_ipv6_loopback_is_internal() -> None:
    result = validate("https://[::1]:8443/a.pdf")
    assert result.internal_hosts == (InternalHost("[::1]", 1),)


def test_example_48_a_public_name_pointing_inside_is_not_detectable_here() -> None:
    result = validate("https://archivos.miempresa.com/a.pdf")
    assert result.items[0].address_class is AddressClass.PUBLIC
    assert result.internal_hosts == ()


def test_internal_hosts_only_count_unique_valid_elements() -> None:
    result = validate("http://intranet/a", "http://intranet/a", "http://INTRANET/a#f")
    assert result.internal_hosts == (InternalHost("intranet", 1),)
    assert result.duplicates == 2


# --- Bloqueadas: I-06 (ejemplos 28 y 45) ----------------------------------------------------------


def test_example_28_metadata_service_is_i06() -> None:
    result = validate("https://169.254.169.254/latest/meta-data")
    assert result.items == ()
    assert [(i.line, i.reason) for i in result.invalid] == [(1, InvalidReason.I06)]
    assert not result.can_start


def test_example_45_blocked_ipv6_is_i06() -> None:
    result = validate("https://[2002:7f00:1::]/a.pdf")
    assert result.invalid[0].reason is InvalidReason.I06


@pytest.mark.parametrize(
    "text",
    [
        "https://0.0.0.1/a",
        "https://0x7f.1/a",  # interna: la notación alternativa no la hace pública
        "https://4294967295/a",  # 255.255.255.255
        "https://[fe80::1]/a",
        "https://[fd00:ec2::254]/a",
        "https://[::ffff:169.254.169.254]/a",
        "https://224.0.0.1/a",
    ],
)
def test_blocked_addresses_in_any_notation(text: str) -> None:
    result = validate(text)
    blocked = text != "https://0x7f.1/a"
    assert bool(result.invalid) is blocked
    if blocked:
        assert result.invalid[0].reason is InvalidReason.I06


def test_i06_masks_the_parameters_like_a_valid_url() -> None:
    result = validate(f"https://169.254.169.254/x?k={CANARY}#{CANARY}")
    assert result.invalid[0].masked_text == "https://169.254.169.254/x?k=***#***"


def test_ca_001_44_port_error_wins_over_the_blocked_address() -> None:
    result = validate("https://169.254.169.254:99999/")
    assert result.invalid[0].reason is InvalidReason.I07


def test_a_repeated_blocked_url_is_invalid_each_time() -> None:
    """S-001-09: una inválida repetida cuenta como inválida cada vez, no como duplicada."""
    result = validate("https://169.254.169.254/x", "https://169.254.169.254/x")
    assert len(result.invalid) == 2
    assert result.duplicates == 0


def test_a_blocked_url_does_not_hide_a_later_valid_duplicate_logic() -> None:
    result = validate("https://169.254.169.254/x", "https://a.com/x", "https://a.com/x")
    assert len(result.items) == 1
    assert result.duplicates == 1
    assert len(result.invalid) == 1


# --- Inválidas: motivo, línea y texto enmascarado -------------------------------------------------


def test_invalid_lines_keep_their_line_number_and_masked_text() -> None:
    result = validate_batch(
        [
            SourceLine(3, "https://a.com/ok"),
            SourceLine(7, f"ftp://u:{CANARY}@x.com/a?t={CANARY}"),
            SourceLine(9, f"https://u:{CANARY}@b.com/y#{CANARY}"),
            SourceLine(12, "C:\\temp\\a.pdf"),
        ],
        total_lines=12,
    )
    assert [(i.line, i.reason) for i in result.invalid] == [
        (7, InvalidReason.I01),
        (9, InvalidReason.I05),
        (12, InvalidReason.I02),
    ]
    assert result.invalid[0].masked_text == "ftp://***@x.com/a?***"
    assert result.invalid[1].masked_text == "https://***@b.com/y#***"
    assert result.total_lines == 12
    for invalid in result.invalid:
        assert CANARY not in invalid.masked_text
        assert CANARY not in repr(invalid)


def test_a_repeated_invalid_line_counts_each_time() -> None:
    result = validate("ftp://x", "ftp://x", "ftp://x")
    assert len(result.invalid) == 3
    assert result.duplicates == 0


def test_every_invalid_reason_of_the_pipeline_is_reachable() -> None:
    result = validate(
        "ftp://x.com/a",  # I-01
        "C:\\a",  # I-02
        "https://a.com\\b",  # I-03
        "https://a.com/" + "x" * 2100,  # I-04
        "https://u@a.com/a",  # I-05
        "https://169.254.169.254/a",  # I-06
        "https://a.com:0/a",  # I-07
        "https://a.com/x https://b.com/y",  # I-09
    )
    assert [i.reason for i in result.invalid] == [
        InvalidReason.I01,
        InvalidReason.I02,
        InvalidReason.I03,
        InvalidReason.I04,
        InvalidReason.I05,
        InvalidReason.I06,
        InvalidReason.I07,
        InvalidReason.I09,
    ]
    assert result.items == ()


# --- CA-001-43 y invariantes (CA-001-35, S-001-09) ------------------------------------------------


def test_ca_001_43_a_batch_without_valid_urls_cannot_start() -> None:
    assert not validate("ftp://x", "ba sura", "", "https://").can_start
    assert not validate().can_start
    assert validate("https://a.com/x").can_start


def test_ca_001_35_invariants_with_a_mixed_batch() -> None:
    result = validate(
        "https://a.com/1",
        "https://a.com/1",
        "a.com/2",
        "ftp://x",
        "https://169.254.169.254/",
        "http://intranet/",
        "https://a.com/1#otra",
    )
    assert len(result.items) + result.duplicates + len(result.invalid) == 7
    assert result.duplicates == 2
    assert len(result.invalid) == 2
    assert {host.host for host in result.internal_hosts} <= {item.url.host for item in result.items}
    assert result.corrected <= len(result.items)
    assert result.corrected_no_scheme <= len(result.items)


def test_items_keep_the_order_of_the_batch_and_have_consecutive_indexes() -> None:
    result = validate("https://c.com/1", "ftp://x", "https://a.com/2", "https://b.com/3")
    assert [item.url.host for item in result.items] == ["c.com", "a.com", "b.com"]
    assert [item.index for item in result.items] == [0, 1, 2]
    assert [item.line for item in result.items] == [1, 3, 4]


def test_total_lines_comes_from_the_file_not_from_the_content_lines() -> None:
    decoded = decode_batch_file("a.txt", b"# c\n\nhttps://a.com/x\n  \nftp://y\n")
    assert isinstance(decoded, DecodedBatch)
    result = validate_batch(decoded.lines, decoded.total_lines)
    assert result.total_lines == 5
    assert len(result.items) + len(result.invalid) + result.duplicates == len(decoded.lines) == 2


# --- Carpetas requeridas (RN-012 b) ---------------------------------------------------------------


def test_required_folders_include_every_ancestor_folded() -> None:
    result = validate("https://Sitio.com/Docs/2024/a.pdf", "https://sitio.com:8443/x/y.pdf")
    assert result.required_folders == frozenset(
        {
            "SITIO.COM",
            "SITIO.COM\\DOCS",
            "SITIO.COM\\DOCS\\2024",
            "SITIO.COM_8443",
            "SITIO.COM_8443\\X",
        }
    )


def test_required_folders_ignore_invalid_and_duplicate_lines() -> None:
    result = validate(
        "https://a.com/x/f.pdf", "https://a.com/x/f.pdf", "ftp://z.com/q/f", "https://b.com/y"
    )
    assert result.required_folders == frozenset({"A.COM", "A.COM\\X", "B.COM"})


def test_required_folders_for_a_url_without_path() -> None:
    assert validate("https://a.com").required_folders == frozenset({"A.COM"})


def test_folder_names_are_compared_without_distinguishing_case() -> None:
    result = validate("https://a.com/Docs/x.pdf", "https://a.com/DOCS/y.pdf")
    assert result.required_folders == frozenset({"A.COM", "A.COM\\DOCS"})


def test_example_42_a_file_name_that_is_also_a_needed_folder() -> None:
    result = validate("https://sitio.com/docs", "https://sitio.com/docs/x.pdf")
    assert "SITIO.COM\\DOCS" in result.required_folders
    assert len(result.items) == 2


# --- Propiedades ----------------------------------------------------------------------------------

PIECES = st.sampled_from(
    ["https://a.com/", "http://b.org/", "ftp://c.net/", "sitio.com/", "10.0.0.1/", "localhost/",
     "169.254.169.254/", "[::1]/", "x", "y.pdf", "?t=1", "#f", " ", "..", "%2e", "ñ", "@", "\\"]
)  # fmt: skip
TEXTS = st.lists(PIECES, max_size=8).map("".join)


@given(st.lists(TEXTS, max_size=25))
def test_the_summary_invariants_hold_for_any_batch(texts: list[str]) -> None:
    source: Sequence[SourceLine] = lines(*texts)
    result = validate_batch(source)
    assert len(result.items) + result.duplicates + len(result.invalid) == len(source)
    assert {host.host for host in result.internal_hosts} <= {item.url.host for item in result.items}
    assert sum(host.count for host in result.internal_hosts) == sum(
        1 for item in result.items if item.address_class is AddressClass.INTERNAL
    )
    assert result.corrected <= len(result.items)
    assert result.can_start is bool(result.items)
    assert all(item.address_class is not AddressClass.BLOCKED for item in result.items)
    assert len({item.url.processed() for item in result.items}) == len(result.items)


@given(st.lists(TEXTS, max_size=15))
def test_validation_is_deterministic(texts: list[str]) -> None:
    assert validate_batch(lines(*texts)) == validate_batch(lines(*texts))
