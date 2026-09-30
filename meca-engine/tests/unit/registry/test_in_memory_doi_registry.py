"""Unit tests for meca_engine.registry.backends.in_memory.InMemoryDoiRegistry."""

from __future__ import annotations

import threading

import pytest

from meca_engine.registry.backends.in_memory import InMemoryDoiRegistry

pytestmark = pytest.mark.unit


@pytest.fixture
def registry() -> InMemoryDoiRegistry:
    return InMemoryDoiRegistry()


def test_first_reservation_of_a_doi_succeeds(registry: InMemoryDoiRegistry) -> None:
    assert registry.reserve("10.1042/cs20256808", article_id="CS-2025-6808") is True


def test_second_reservation_of_the_same_doi_fails(registry: InMemoryDoiRegistry) -> None:
    registry.reserve("10.1042/cs20256808", article_id="CS-2025-6808")

    ok = registry.reserve("10.1042/cs20256808", article_id="CS-2025-9999")

    assert ok is False


def test_re_reserving_the_same_doi_by_the_same_article_succeeds(
    registry: InMemoryDoiRegistry,
) -> None:
    """A failed build's redo-from-scratch retry (ADR-017) must not be
    permanently blocked by its own earlier, successful reservation."""
    assert registry.reserve("10.1042/cs20256808", article_id="CS-2025-6808") is True

    assert registry.reserve("10.1042/cs20256808", article_id="CS-2025-6808") is True


def test_different_dois_can_both_be_reserved(registry: InMemoryDoiRegistry) -> None:
    assert registry.reserve("10.1042/cs20256808", article_id="CS-2025-6808") is True
    assert registry.reserve("10.1042/cs20258827", article_id="cs-2025-8827") is True


def test_is_reserved_reflects_reservation_state(registry: InMemoryDoiRegistry) -> None:
    assert registry.is_reserved("10.1042/cs20256808") is False

    registry.reserve("10.1042/cs20256808", article_id="CS-2025-6808")

    assert registry.is_reserved("10.1042/cs20256808") is True


def test_reset_clears_all_reservations(registry: InMemoryDoiRegistry) -> None:
    registry.reserve("10.1042/cs20256808", article_id="CS-2025-6808")

    registry.reset()

    assert registry.is_reserved("10.1042/cs20256808") is False
    assert registry.reserve("10.1042/cs20256808", article_id="CS-2025-9999") is True


def test_concurrent_reservations_of_the_same_doi_serialize_to_exactly_one_winner(
    registry: InMemoryDoiRegistry,
) -> None:
    results: list[bool] = []
    lock = threading.Lock()

    def attempt(article_id: str) -> None:
        ok = registry.reserve("10.1042/cs20256808", article_id=article_id)
        with lock:
            results.append(ok)

    threads = [threading.Thread(target=attempt, args=(f"ART-{i}",)) for i in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results.count(True) == 1
    assert results.count(False) == 9
