"""Shared fixtures for the test suite of `docs/cluster_map_and_recursive_search.md`.

The tests import sibling modules (``main``, ``graph_model``, ``search``, ``cluster_map``,
``draw``) as top-level names; that works because ``pyproject.toml`` puts ``src`` on
``sys.path`` via ``[tool.pytest.ini_options] pythonpath``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1]
if str(SRC) not in sys.path:  # standalone `pytest src/tests` also works
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def person_cls():
    """The ``Person`` type, imported lazily so collection never fails on missing deps."""
    import main

    return main.Person


@pytest.fixture()
def family(person_cls):
    """A two-cluster family used across fixtures (§1.3):

    * ``collapse`` cluster — pedigree collapse (I3): ``kid``'s mom ``mia`` and dad ``dan``
      share the ancestor ``ada`` (mia's dad == dan's dad == ada), so
      |Anc(kit)| < 2^{g+1} - 1.
    * ``solo`` cluster — an unrelated single person (edges never cross clusters).
    """
    ada = person_cls("ada")
    mia = person_cls("mia", mom=ada)
    dan = person_cls("dan", dad=ada)
    kid = person_cls("kid", mom=mia, dad=dan)
    solo = person_cls("solo")
    return {
        "ada": ada,
        "mia": mia,
        "dan": dan,
        "kid": kid,
        "solo": solo,
        "collapse_members": {ada, mia, dan, kid},
    }


@pytest.fixture()
def family_graph(family, graph_model_module):
    """The :class:`FamilyGraph` view over :func:`family`'s five persons."""
    return graph_model_module.build_family_graph(
        [family["ada"], family["mia"], family["dan"], family["kid"], family["solo"]]
    )


@pytest.fixture(scope="session")
def graph_model_module():
    import graph_model

    return graph_model


@pytest.fixture(scope="session")
def search_module():
    import search

    return search


@pytest.fixture(scope="session")
def cluster_map_module():
    import cluster_map

    return cluster_map


@pytest.fixture(scope="session")
def draw_module():
    import draw

    return draw