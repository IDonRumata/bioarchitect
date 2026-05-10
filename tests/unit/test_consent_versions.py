"""Тесты констант домена consent."""

from __future__ import annotations

import pytest

from src.domains.consent.enums import ConsentType
from src.domains.consent.service import CONSENT_VERSIONS


@pytest.mark.unit
def test_all_consent_types_have_version() -> None:
    """Каждый ConsentType должен иметь зарегистрированную версию документа."""
    for ct in ConsentType:
        assert ct in CONSENT_VERSIONS, f"Missing version for {ct.value}"


@pytest.mark.unit
def test_consent_versions_are_non_empty() -> None:
    for ct, ver in CONSENT_VERSIONS.items():
        assert ver, f"Empty version for {ct.value}"
        assert len(ver) <= 16, f"Version too long for {ct.value}: {ver}"
