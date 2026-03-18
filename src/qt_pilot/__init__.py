"""qt-pilot: CLI automation for PySide6/QML apps."""

from __future__ import annotations

import logging
import os
import sys

log = logging.getLogger(__name__)


def install(engine: object, port: int | None = None) -> None:
    """Install qt-pilot probe into a running QQmlApplicationEngine.

    Call this after ``engine.load()``. The probe activates only when
    ``QT_PILOT=1`` is set in the environment or ``--pilot`` appears
    in ``sys.argv``. Otherwise this is a no-op.

    Usage::

        from qt_pilot import install
        install(engine)
    """
    if not os.environ.get("QT_PILOT") and "--pilot" not in sys.argv:
        return

    port = port or int(os.environ.get("QT_PILOT_PORT", "9718"))

    from qt_pilot.probe import Probe
    from qt_pilot.server import PilotServer

    probe = Probe(engine, parent=engine)
    server = PilotServer(probe, parent=engine)

    if not server.start(port):
        raise RuntimeError(f"qt-pilot: failed to listen on localhost:{port}")

    # Prevent garbage collection by stashing on the engine.
    engine._qt_pilot_probe = probe  # type: ignore[attr-defined]
    engine._qt_pilot_server = server  # type: ignore[attr-defined]
