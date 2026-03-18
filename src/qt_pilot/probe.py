"""Probe: QML tree walking, screenshots, event injection, property access."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from PySide6.QtCore import (
    QEvent,
    QObject,
    QPointF,
    QRectF,
    Qt,
)
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtWidgets import QApplication

from qt_pilot.registry import RefRegistry

log = logging.getLogger(__name__)

# Qt Quick Controls types that accept user interaction.
_INTERACTIVE_SUFFIXES = frozenset({
    "Button", "TextField", "TextInput", "TextArea",
    "ComboBox", "CheckBox", "Switch", "Slider",
    "SpinBox", "RadioButton", "TabButton", "MenuItem",
    "ScrollBar", "Dial", "RangeSlider", "Tumbler",
})

# QML properties that commonly hold user-visible text.
_TEXT_PROPS = ("text", "placeholderText", "currentText", "displayText",
               "title", "label", "description")

DEFAULT_WAIT_TIMEOUT_MS = 5000
WAIT_POLL_MS = 50


class Probe(QObject):
    """In-process automation probe for PySide6/QML apps."""

    def __init__(self, engine: Any, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._registry = RefRegistry()
        self._shot_counter = 0
        # Cache for annotated screenshot legend
        self._ref_info: list[tuple[str, str, str | None, QRectF]] = []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _root_window(self) -> QQuickWindow:
        roots = self._engine.rootObjects()
        if not roots:
            raise RuntimeError("No root objects in QML engine")
        root = roots[0]
        if isinstance(root, QQuickWindow):
            return root
        raise RuntimeError(f"Root object is {type(root).__name__}, expected QQuickWindow")

    @staticmethod
    def _display_cls(item: QQuickItem) -> str:
        cls = item.metaObject().className()
        # Strip QML type suffix: "LoginPage_QMLTYPE_42" → "LoginPage"
        name = cls.split("_QMLTYPE_")[0]
        # Strip C++ namespace: "QQuick::Button" → "Button"
        return name.rsplit("::", 1)[-1]

    @staticmethod
    def _is_interactive(display_cls: str) -> bool:
        return any(display_cls.endswith(s) for s in _INTERACTIVE_SUFFIXES)

    @staticmethod
    def _read_text(item: QQuickItem) -> str | None:
        for prop in _TEXT_PROPS:
            try:
                val = item.property(prop)
            except RuntimeError:
                continue
            if val and isinstance(val, str) and val.strip():
                return val.strip()
        return None

    @staticmethod
    def _scene_rect(item: QQuickItem) -> QRectF:
        top_left = item.mapToScene(QPointF(0, 0))
        return QRectF(top_left.x(), top_left.y(), item.width(), item.height())

    def _send_key(self, window: QQuickWindow, key: int,
                  modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
                  text: str = "") -> None:
        press = QKeyEvent(QEvent.Type.KeyPress, key, modifiers, text)
        release = QKeyEvent(QEvent.Type.KeyRelease, key, modifiers, text)
        QApplication.sendEvent(window, press)
        QApplication.sendEvent(window, release)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self, interactive_only: bool = False) -> dict:
        """Walk QML visual tree, assign refs, return text snapshot."""
        window = self._root_window()
        content = window.contentItem()
        self._registry.clear()
        self._ref_info.clear()
        lines: list[str] = []

        # Header with page context
        root = self._engine.rootObjects()[0]
        page = root.property("currentPage")
        header_parts = []
        if page:
            header_parts.append(f"[page: {page}]")
        header_parts.append(f"[window: {window.width()}x{window.height()}]")
        lines.append(" ".join(header_parts))

        self._walk_item(content, 0, interactive_only, lines)

        return {"tree": "\n".join(lines), "generation": self._registry.generation}

    def _walk_item(self, item: QQuickItem, depth: int,
                   interactive_only: bool, lines: list[str]) -> None:
        try:
            if not item.isVisible() or item.width() <= 0 or item.height() <= 0:
                return
        except RuntimeError:
            return  # C++ object deleted

        display_cls = self._display_cls(item)
        is_interactive = self._is_interactive(display_cls)
        text = self._read_text(item)
        scene_rect = self._scene_rect(item)

        if is_interactive:
            ref = self._registry.register(item)
            indent = "  " * depth
            parts = [f"{indent}{ref} [{display_cls}]"]
            if text:
                parts.append(f'"{text}"')
            parts.append(
                f"({int(scene_rect.x())},{int(scene_rect.y())} "
                f"{int(scene_rect.width())}x{int(scene_rect.height())})"
            )
            if not item.isEnabled():
                parts.append("[disabled]")
            checked = item.property("checked")
            if checked:
                parts.append("[checked]")
            if item.hasActiveFocus():
                parts.append("[focused]")
            lines.append(" ".join(parts))
            self._ref_info.append((ref, display_cls, text, scene_rect))
        elif not interactive_only and text:
            indent = "  " * depth
            lines.append(
                f'{indent}[{display_cls}] "{text}" '
                f'({int(scene_rect.x())},{int(scene_rect.y())})'
            )

        try:
            children = item.childItems()
        except RuntimeError:
            return
        for child in children:
            self._walk_item(child, depth + 1, interactive_only, lines)

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def screenshot(self, path: str | None = None, annotate: bool = False) -> dict:
        """Grab window contents as PNG."""
        window = self._root_window()
        image = window.grabWindow()

        if image.isNull():
            raise RuntimeError("grabWindow() returned null image")

        if annotate:
            # Ensure we have refs
            if not self._registry:
                self.snapshot(interactive_only=True)
            from qt_pilot.annotate import annotate_image
            image = annotate_image(image, self._ref_info)

        if not path:
            os.makedirs("/tmp/qt-pilot", exist_ok=True)
            self._shot_counter += 1
            path = f"/tmp/qt-pilot/screenshot-{self._shot_counter:03d}.png"
        else:
            parent_dir = os.path.dirname(os.path.abspath(path))
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

        image.save(path)

        result: dict[str, Any] = {
            "path": path,
            "width": image.width(),
            "height": image.height(),
        }
        if annotate:
            result["legend"] = [
                f"[{i}] {ref} {cls}" + (f' "{text}"' if text else "")
                for i, (ref, cls, text, _) in enumerate(self._ref_info, 1)
            ]
        return result

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def click(self, ref: str) -> dict:
        """Click the center of an element."""
        item = self._registry.resolve_or_raise(ref)
        if not isinstance(item, QQuickItem):
            raise ValueError(f"Ref {ref} is not a QQuickItem")
        window = item.window()
        if window is None:
            raise RuntimeError(f"Item for {ref} has no window")

        center = QPointF(item.width() / 2, item.height() / 2)
        scene_pos = item.mapToScene(center)
        global_pos = QPointF(window.mapToGlobal(scene_pos.toPoint()))

        press = QMouseEvent(
            QEvent.Type.MouseButtonPress, scene_pos, global_pos,
            Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        release = QMouseEvent(
            QEvent.Type.MouseButtonRelease, scene_pos, global_pos,
            Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(window, press)
        QApplication.sendEvent(window, release)
        QApplication.processEvents()
        return {"ok": True}

    def fill(self, ref: str, text: str) -> dict:
        """Clear field and type text."""
        item = self._registry.resolve_or_raise(ref)
        if not isinstance(item, QQuickItem):
            raise ValueError(f"Ref {ref} is not a QQuickItem")
        window = item.window()
        if window is None:
            raise RuntimeError(f"Item for {ref} has no window")

        # Click to focus
        self.click(ref)
        item.forceActiveFocus()
        QApplication.processEvents()

        # Select all + delete
        self._send_key(window, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        self._send_key(window, Qt.Key.Key_Delete)
        QApplication.processEvents()

        # Type each character
        for char in text:
            press = QKeyEvent(QEvent.Type.KeyPress, 0,
                              Qt.KeyboardModifier.NoModifier, char)
            release = QKeyEvent(QEvent.Type.KeyRelease, 0,
                                Qt.KeyboardModifier.NoModifier, char)
            QApplication.sendEvent(window, press)
            QApplication.sendEvent(window, release)

        QApplication.processEvents()
        return {"ok": True}

    def type_text(self, ref: str, text: str) -> dict:
        """Type text without clearing first."""
        item = self._registry.resolve_or_raise(ref)
        if not isinstance(item, QQuickItem):
            raise ValueError(f"Ref {ref} is not a QQuickItem")
        window = item.window()
        if window is None:
            raise RuntimeError(f"Item for {ref} has no window")

        # Click to focus
        self.click(ref)
        item.forceActiveFocus()
        QApplication.processEvents()

        for char in text:
            press = QKeyEvent(QEvent.Type.KeyPress, 0,
                              Qt.KeyboardModifier.NoModifier, char)
            release = QKeyEvent(QEvent.Type.KeyRelease, 0,
                                Qt.KeyboardModifier.NoModifier, char)
            QApplication.sendEvent(window, press)
            QApplication.sendEvent(window, release)

        QApplication.processEvents()
        return {"ok": True}

    def press(self, key: str, ref: str | None = None) -> dict:
        """Press a key (e.g., 'Enter', 'Tab', 'Escape', 'Ctrl+A')."""
        if ref:
            item = self._registry.resolve_or_raise(ref)
            if not isinstance(item, QQuickItem):
                raise ValueError(f"Ref {ref} is not a QQuickItem")
            window = item.window()
            item.forceActiveFocus()
        else:
            window = self._root_window()

        qt_key, qt_mods, text = _parse_key(key)
        self._send_key(window, qt_key, qt_mods, text)
        QApplication.processEvents()
        return {"ok": True}

    def scroll(self, direction: str = "down", amount: int = 300) -> dict:
        """Scroll the window."""
        from PySide6.QtGui import QWheelEvent

        window = self._root_window()
        center = QPointF(window.width() / 2, window.height() / 2)
        global_center = QPointF(window.mapToGlobal(center.toPoint()))

        dy = -amount if direction == "down" else amount
        dx = amount if direction == "right" else (-amount if direction == "left" else 0)
        if direction in ("up", "down"):
            dx = 0
        if direction in ("left", "right"):
            dy = 0

        from PySide6.QtCore import QPoint
        event = QWheelEvent(
            center, global_center,
            QPoint(0, 0),       # pixelDelta
            QPoint(dx, dy),     # angleDelta
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        QApplication.sendEvent(window, event)
        QApplication.processEvents()
        return {"ok": True}

    # ------------------------------------------------------------------
    # Eval / Properties
    # ------------------------------------------------------------------

    def eval_js(self, expression: str) -> dict:
        """Evaluate JavaScript in the QML root context."""
        from PySide6.QtQml import QQmlExpression

        root = self._engine.rootObjects()[0]
        ctx = self._engine.rootContext()
        expr = QQmlExpression(ctx, root, expression)
        result = expr.evaluate()
        if expr.hasError():
            return {"error": expr.error().toString()}
        return {"result": _json_safe(result)}

    def get_property(self, ref: str, prop: str) -> dict:
        """Read a property from a ref'd QML item."""
        item = self._registry.resolve_or_raise(ref)
        val = item.property(prop)
        return {"value": _json_safe(val)}

    def get_context_property(self, path: str) -> dict:
        """Read 'Service.property' or 'rootProp' from QML context."""
        parts = path.split(".", 1)
        ctx = self._engine.rootContext()
        if len(parts) == 2:
            service = ctx.contextProperty(parts[0])
            if service is None:
                raise ValueError(f"Unknown context property: {parts[0]}")
            val = service.property(parts[1])
        else:
            root = self._engine.rootObjects()[0]
            val = root.property(parts[0])
        return {"value": _json_safe(val)}

    # ------------------------------------------------------------------
    # Wait
    # ------------------------------------------------------------------

    def wait(self, ref: str | None = None, ms: int | None = None,
             timeout: int = DEFAULT_WAIT_TIMEOUT_MS) -> dict:
        """Wait for an element to appear or a fixed duration."""
        if ms is not None:
            # Fixed wait
            deadline = time.monotonic() + ms / 1000.0
            while time.monotonic() < deadline:
                QApplication.processEvents()
                time.sleep(0.01)
            return {"ok": True, "elapsed_ms": ms}

        if ref is not None:
            # Wait for element with matching ref to appear in a new snapshot
            start = time.monotonic()
            deadline = start + timeout / 1000.0
            while time.monotonic() < deadline:
                QApplication.processEvents()
                self.snapshot(interactive_only=True)
                if self._registry.resolve(ref) is not None:
                    elapsed = int((time.monotonic() - start) * 1000)
                    return {"ok": True, "elapsed_ms": elapsed}
                time.sleep(WAIT_POLL_MS / 1000.0)
            raise TimeoutError(
                f"Timed out after {timeout}ms waiting for {ref}"
            )

        raise ValueError("Provide ref or ms")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Connection check and basic window info."""
        window = self._root_window()
        root = self._engine.rootObjects()[0]
        return {
            "connected": True,
            "window_size": f"{window.width()}x{window.height()}",
            "root_class": root.metaObject().className(),
            "current_page": root.property("currentPage") or None,
            "visible": window.isVisible(),
        }


# ------------------------------------------------------------------
# Key parsing
# ------------------------------------------------------------------

_MODIFIER_MAP = {
    "ctrl": Qt.KeyboardModifier.ControlModifier,
    "shift": Qt.KeyboardModifier.ShiftModifier,
    "alt": Qt.KeyboardModifier.AltModifier,
    "meta": Qt.KeyboardModifier.MetaModifier,
}

_KEY_MAP: dict[str, int] = {
    "return": Qt.Key.Key_Return,
    "enter": Qt.Key.Key_Return,
    "escape": Qt.Key.Key_Escape,
    "esc": Qt.Key.Key_Escape,
    "tab": Qt.Key.Key_Tab,
    "backspace": Qt.Key.Key_Backspace,
    "delete": Qt.Key.Key_Delete,
    "space": Qt.Key.Key_Space,
    "up": Qt.Key.Key_Up,
    "down": Qt.Key.Key_Down,
    "left": Qt.Key.Key_Left,
    "right": Qt.Key.Key_Right,
    "home": Qt.Key.Key_Home,
    "end": Qt.Key.Key_End,
    "pageup": Qt.Key.Key_PageUp,
    "pagedown": Qt.Key.Key_PageDown,
}
for i in range(1, 13):
    _KEY_MAP[f"f{i}"] = getattr(Qt.Key, f"Key_F{i}")


def _parse_key(key_str: str) -> tuple[int, Qt.KeyboardModifier, str]:
    parts = key_str.split("+")
    modifiers = Qt.KeyboardModifier.NoModifier
    key_part = parts[-1]
    for mod_str in parts[:-1]:
        mod = _MODIFIER_MAP.get(mod_str.lower())
        if mod:
            modifiers = modifiers | mod

    key_lower = key_part.lower()
    if key_lower in _KEY_MAP:
        return _KEY_MAP[key_lower], modifiers, ""

    if len(key_part) == 1:
        return ord(key_part.upper()), modifiers, key_part

    return 0, modifiers, key_part


def _json_safe(val: Any) -> Any:
    """Convert a value to something JSON-serializable."""
    if val is None or isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, (list, tuple)):
        return [_json_safe(v) for v in val]
    if isinstance(val, dict):
        return {str(k): _json_safe(v) for k, v in val.items()}
    return repr(val)
