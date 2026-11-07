"""Resultado explicito Ok/Err (PA-04)."""

from __future__ import annotations

import dataclasses

import pytest

from downloader.domain.result import Err, Ok, Result


def test_ok_and_err_hold_their_values() -> None:
    assert Ok(3).value == 3
    assert Err("I-01").error == "I-01"


def test_value_equality_and_hash() -> None:
    assert Ok(1) == Ok(1)
    assert Ok(1) != Ok(2)
    assert Ok(1) != Err(1)
    assert hash(Ok("a")) == hash(Ok("a"))
    assert len({Err("x"), Err("x"), Ok("x")}) == 2


def test_instances_are_immutable() -> None:
    ok = Ok(1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        ok.value = 2  # type: ignore[misc]
    err = Err("x")
    with pytest.raises(dataclasses.FrozenInstanceError):
        err.error = "y"  # type: ignore[misc]


def test_instances_have_no_dict() -> None:
    assert not hasattr(Ok(1), "__dict__")
    assert not hasattr(Err(1), "__dict__")


def describe(result: Result[int, str]) -> str:
    match result:
        case Ok(value):
            return f"ok:{value}"
        case Err(error):
            return f"err:{error}"


def test_pattern_matching_discriminates() -> None:
    assert describe(Ok(7)) == "ok:7"
    assert describe(Err("F-24")) == "err:F-24"
