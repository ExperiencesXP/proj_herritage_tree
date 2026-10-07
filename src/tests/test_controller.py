from __future__ import annotations

import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")


@pytest.fixture()
def app(person_cls):
    import controller

    ada = person_cls("ada")
    mia = person_cls("mia", mom=ada)
    dan = person_cls("dan", dad=ada)
    kid = person_cls("kid", mom=mia, dad=dan)
    solo = person_cls("solo")
    return controller.FamilyController([ada, mia, dan, kid, solo])


def test_controller_verify_consistency_facts(app):
    facts = app.verify_consistency()
    assert facts == {"n": 5, "m": 4, "k": 2, "s": 3}


def test_controller_queries(app):
    assert {p.name for p in app.cluster_members("kid")} == {"ada", "mia", "dan", "kid"}
    assert {p.name for p in app.ancestors_of("kid")} == {"ada", "mia", "dan", "kid"}
    assert {p.name for p in app.descendants_of("ada")} == {"mia", "dan", "kid"}
    assert app.find_person("kid", lambda p: p.name == "solo") is None
    assert app.find_person("kid", lambda p: p.name == "ada").name == "ada"
    with pytest.raises(ValueError):
        app.person("nobody")


def test_controller_render_writes_png_per_cluster(app, tmp_path):
    written = app.render(out_dir=tmp_path, highlight={app.person("kid")})
    assert len(written) == 2
    for path in written:
        assert path.suffix == ".png"
        assert path.exists() and path.stat().st_size > 0


def test_controller_answers_kinship_question(app):
    assert [p.name for p in app.find_common_ancestor("mia", "dan")] == ["ada"]
    assert app.is_related("mia", "dan") is True
    assert app.is_related("kid", "solo") is False


def test_export_orientation_via_controller(app):
    text = app.mermaid_of("kid")
    assert text.startswith("flowchart TB")
    assert text.count("-->") == 4
    assert "rankdir=TB" in app.dot_of("kid")
