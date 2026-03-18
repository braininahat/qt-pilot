"""Ref registry: maps string refs (@e1, @e2, ...) to live QQuickItem instances."""

from __future__ import annotations

import builtins


class RefRegistry:
    """Ephemeral ref-to-object mapping, rebuilt on each snapshot."""

    def __init__(self) -> None:
        self._counter = 0
        self._generation = 0
        self._refs: dict[str, object] = {}
        self._reverse: dict[int, str] = {}

    @property
    def generation(self) -> int:
        return self._generation

    def clear(self) -> None:
        self._counter = 0
        self._generation += 1
        self._refs.clear()
        self._reverse.clear()

    def register(self, obj: object) -> str:
        obj_id = builtins.id(obj)
        existing = self._reverse.get(obj_id)
        if existing is not None:
            return existing
        self._counter += 1
        ref = f"@e{self._counter}"
        self._refs[ref] = obj
        self._reverse[obj_id] = ref
        return ref

    def resolve(self, ref: str) -> object | None:
        return self._refs.get(ref)

    def resolve_or_raise(self, ref: str) -> object:
        obj = self._refs.get(ref)
        if obj is None:
            raise ValueError(
                f"Ref {ref} not found — it may have expired. "
                f"Run `qt-pilot snapshot` to get fresh refs "
                f"(current generation: {self._generation})"
            )
        return obj

    def all_refs(self) -> dict[str, object]:
        return dict(self._refs)

    def __len__(self) -> int:
        return len(self._refs)

    def __bool__(self) -> bool:
        return len(self._refs) > 0
