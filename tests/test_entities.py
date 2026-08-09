import pytest

pytest.importorskip("numpy")

from tastebench.tastegraph import TasteGraphEngine
from tastebench.tastegraph.entities.registry import EntityError, get_registry
from tastebench.tastegraph.entities.schema import Entity, EntityType, Link


@pytest.fixture
def reg():
    return get_registry(TasteGraphEngine())


def _content(reg, id, text):
    return reg.create(Entity(id=id, type="content", content=text))


def test_create_user_and_content(reg):
    reg.create(Entity(id="u1", type="user"))
    _content(reg, "c1", "minimal linen dress")
    assert reg.get("u1").type == "user"
    assert "c1" in reg.visible_content_ids()


def test_content_requires_content_or_uri(reg):
    with pytest.raises(EntityError):
        reg.create(Entity(id="bad", type="content"))


def test_link_builds_taste_and_rerank_follows(reg):
    reg.create(Entity(id="u1", type="user"))
    _content(reg, "minimal", "minimal linen quiet luxury dress")
    _content(reg, "street", "neon streetwear bold hoodie")
    _content(reg, "minimal2", "understated minimal cashmere knit")

    reg.link(Link(source_id="u1", target_id="minimal", action="like"))
    reg.link(Link(source_id="u1", target_id="street", action="dismiss"))

    ranked = reg.engine.rerank("u1", ["street", "minimal2"])
    order = [a for a, _ in ranked]
    assert order.index("minimal2") < order.index("street")


def test_soft_delete_hides_content(reg):
    _content(reg, "c1", "x")
    reg.delete("c1")
    assert "c1" not in reg.visible_content_ids()
    with pytest.raises(EntityError):
        reg.get("c1")


def test_delete_user_clears_signals(reg):
    reg.create(Entity(id="u1", type="user"))
    _content(reg, "c1", "minimal dress")
    reg.link(Link(source_id="u1", target_id="c1", action="like"))
    assert reg.engine._signals.get("u1")
    reg.delete("u1")
    assert not reg.engine._signals.get("u1")


def test_custom_type_registers(reg):
    reg.register_type(EntityType(name="product", kind="content"))
    reg.create(Entity(id="p1", type="product", content="a product"))
    assert "p1" in reg.visible_content_ids()
    assert any(t.name == "product" for t in reg.list_types())


def test_link_rejects_bad_action(reg):
    reg.create(Entity(id="u1", type="user"))
    _content(reg, "c1", "x")
    with pytest.raises(EntityError):
        reg.link(Link(source_id="u1", target_id="c1", action="teleport"))
