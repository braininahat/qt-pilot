"""Tests for RefRegistry."""

from qt_pilot.registry import RefRegistry


class TestRefRegistry:
    def test_register_returns_ref(self):
        reg = RefRegistry()
        obj = object()
        ref = reg.register(obj)
        assert ref == "@e1"

    def test_register_increments(self):
        reg = RefRegistry()
        r1 = reg.register(object())
        r2 = reg.register(object())
        assert r1 == "@e1"
        assert r2 == "@e2"

    def test_register_deduplicates(self):
        reg = RefRegistry()
        obj = object()
        r1 = reg.register(obj)
        r2 = reg.register(obj)
        assert r1 == r2
        assert len(reg) == 1

    def test_resolve(self):
        reg = RefRegistry()
        obj = object()
        ref = reg.register(obj)
        assert reg.resolve(ref) is obj

    def test_resolve_missing(self):
        reg = RefRegistry()
        assert reg.resolve("@e99") is None

    def test_resolve_or_raise(self):
        reg = RefRegistry()
        obj = object()
        ref = reg.register(obj)
        assert reg.resolve_or_raise(ref) is obj

    def test_resolve_or_raise_missing(self):
        reg = RefRegistry()
        try:
            reg.resolve_or_raise("@e1")
            assert False, "should have raised"
        except ValueError as exc:
            assert "@e1" in str(exc)

    def test_clear(self):
        reg = RefRegistry()
        reg.register(object())
        assert len(reg) == 1
        gen_before = reg.generation
        reg.clear()
        assert len(reg) == 0
        assert reg.generation == gen_before + 1

    def test_clear_resets_counter(self):
        reg = RefRegistry()
        reg.register(object())
        reg.register(object())
        reg.clear()
        ref = reg.register(object())
        assert ref == "@e1"  # counter reset

    def test_bool_empty(self):
        reg = RefRegistry()
        assert not reg

    def test_bool_nonempty(self):
        reg = RefRegistry()
        reg.register(object())
        assert reg

    def test_all_refs(self):
        reg = RefRegistry()
        o1, o2 = object(), object()
        reg.register(o1)
        reg.register(o2)
        refs = reg.all_refs()
        assert len(refs) == 2
        assert refs["@e1"] is o1
        assert refs["@e2"] is o2
