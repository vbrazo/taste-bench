"""Phase 1 durability: state survives a save + reload into a fresh engine."""

import pytest

pytest.importorskip("numpy")

from tastebench.tastegraph.api.engine import TasteGraphEngine
from tastebench.tastegraph.entities.registry import get_registry
from tastebench.tastegraph.entities.schema import Entity, EntityType, Link
from tastebench.tastegraph.persist import (
    attach_persistence,
    load_tenant,
    save_tenant,
    tenant_dir,
)


def _seed(engine):
    reg = get_registry(engine)
    reg.create(Entity(id="u_demo", type="user"))
    reg.create(Entity(id="c_warm", type="content", content="warm specific note — concrete, no hype"))
    reg.create(Entity(id="c_hype", type="content", content="AMAZING platform!!! 🚀🚀 unlock growth now"))
    reg.link(Link(source_id="u_demo", target_id="c_warm", action="like"))
    reg.link(Link(source_id="u_demo", target_id="c_hype", action="dismiss"))


def test_save_then_load_rebuilds_graph(tmp_path):
    src = TasteGraphEngine()
    _seed(src)
    save_tenant(src, tmp_path)

    # A brand-new engine/registry rebuilds entities, signals, and vectors from disk.
    dst = TasteGraphEngine()
    assert load_tenant(dst, tmp_path) is True
    reg = get_registry(dst)

    assert {e.id for e in reg.list()} == {"u_demo", "c_warm", "c_hype"}
    assert dst._signals["u_demo"]  # signals restored
    assert "c_warm" in dst.index and "c_hype" in dst.index  # vectors rebuilt

    ranked = dst.rerank("u_demo", ["c_warm", "c_hype"])
    order = [a for a, _ in ranked]
    assert order.index("c_warm") < order.index("c_hype")
    assert dst.agent_context("u_demo")["resolved"] is True


def test_custom_type_round_trips(tmp_path):
    src = TasteGraphEngine()
    reg = get_registry(src)
    reg.register_type(EntityType(name="lead", kind="user"))
    reg.create(Entity(id="lead_1", type="lead"))
    save_tenant(src, tmp_path)

    dst = TasteGraphEngine()
    load_tenant(dst, tmp_path)
    dreg = get_registry(dst)
    assert dreg.kind_of("lead") == "user"
    assert dreg.get("lead_1").type == "lead"


def test_autosave_survives_new_process(tmp_path):
    # First "process": arm persistence, then mutate through the normal API surface.
    e1 = TasteGraphEngine()
    attach_persistence(e1, "rose", root=tmp_path)
    _seed(e1)

    # Second "process": same DATA_DIR + tenant, no explicit load call.
    e2 = TasteGraphEngine()
    attach_persistence(e2, "rose", root=tmp_path)
    reg2 = get_registry(e2)
    assert {e.id for e in reg2.list()} == {"u_demo", "c_warm", "c_hype"}
    ranked = e2.rerank("u_demo", ["c_warm", "c_hype"])
    assert [a for a, _ in ranked][0] == "c_warm"


def test_load_missing_dir_is_noop(tmp_path):
    engine = TasteGraphEngine()
    assert load_tenant(engine, tenant_dir("nope", root=tmp_path)) is False
