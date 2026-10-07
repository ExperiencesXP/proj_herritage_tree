from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def person_cls():
    from model import person

    return person.Person


@pytest.fixture()
def family(person_cls):
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
    return graph_model_module.build_family_graph(
        [family["ada"], family["mia"], family["dan"], family["kid"], family["solo"]]
    )


@pytest.fixture(scope="session")
def graph_model_module():
    from model import graph_model

    return graph_model


@pytest.fixture(scope="session")
def search_module():
    from model import search

    return search


@pytest.fixture(scope="session")
def cluster_map_module():
    from model import cluster_map

    return cluster_map


@pytest.fixture(scope="session")
def draw_module():
    import draw

    return draw
