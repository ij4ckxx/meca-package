"""Shared fixtures for golden-file regression tests.

References the 3 real sample zips directly from the project's `Input/`
directory (one level above `meca-engine/`) rather than copying them into
`tests/golden/fixtures/` — the copies would add ~110MB of binary content
to a project that is not yet even a git repository (see `meca-engine/README.md`
"Known Limitations"). `Input/*.zip` is read-only here: every fixture below
only extracts from it into a pytest-managed temporary directory, never
writes back.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import NamedTuple

import pytest

_INPUT_DIR = Path(__file__).resolve().parents[3] / "Input"

REAL_SAMPLES = (
    ("CS-2025-6808", "CS-2025-6808.zip", "CS-2025-6808/cs-2025-6808.xml"),
    ("CS-2025-8493_C", "CS-2025-8493_C.zip", "CS-2025-8493/cs-2025-8493_C.xml"),
    ("cs-2025-8827", "cs-2025-8827.zip", "cs-2025-8827/cs-2025-8827.xml"),
)


class ExtractedSample(NamedTuple):
    """One real sample package, extracted into a temporary directory."""

    article_id: str
    xml_path: Path
    staged_root: Path


def extract_sample(
    article_id: str, zip_name: str, xml_member: str, destination: Path
) -> ExtractedSample:
    """Extract one real sample zip's XML and round folders into ``destination``.

    Args:
        article_id: The article id this sample represents.
        zip_name: The zip file's name under ``Input/``.
        xml_member: The zip member path of the article's root XML file.
        destination: An empty directory to extract into (typically a
            pytest ``tmp_path``).

    Returns:
        The extracted sample's paths.
    """
    zip_path = _INPUT_DIR / zip_name
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(destination)
    xml_path = destination / xml_member
    staged_root = xml_path.parent
    return ExtractedSample(article_id=article_id, xml_path=xml_path, staged_root=staged_root)


@pytest.fixture(params=REAL_SAMPLES, ids=[sample[0] for sample in REAL_SAMPLES])
def real_sample(request: pytest.FixtureRequest, tmp_path: Path) -> ExtractedSample:
    """Parametrized fixture yielding each of the 3 real sample packages, extracted."""
    article_id, zip_name, xml_member = request.param
    return extract_sample(article_id, zip_name, xml_member, tmp_path)
