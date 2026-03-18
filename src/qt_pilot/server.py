"""QTcpServer JSON-RPC 2.0 server — runs on the Qt event loop (main/GUI thread)."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from PySide6.QtCore import QObject, Slot
from PySide6.QtNetwork import QHostAddress, QTcpServer

log = logging.getLogger(__name__)

ERROR_METHOD_NOT_FOUND = -32601
ERROR_INVALID_REQUEST = -32600
ERROR_INVALID_PARAMS = -32602
ERROR_INTERNAL = -32000


def _pop_line(buf: bytes) -> tuple[bytes | None, bytes]:
    idx = buf.find(b"\n")
    if idx == -1:
        return None, buf
    return buf[:idx], buf[idx + 1:]


class PilotServer(QObject):
    """JSON-RPC 2.0 server integrated with the Qt event loop via QTcpServer.

    Because QTcpServer callbacks run on the thread that owns the server (the
    main/GUI thread), the RPC handler has direct, safe access to all Qt objects
    — no cross-thread marshaling needed.
    """

    def __init__(self, probe: Any, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._probe = probe
        self._server = QTcpServer(self)
        self._server.newConnection.connect(self._on_connection)
        self._buffers: dict[Any, bytes] = {}

    def start(self, port: int = 9718) -> bool:
        ok = self._server.listen(QHostAddress.SpecialAddress.LocalHost, port)
        if ok:
            log.info("qt-pilot probe listening on localhost:%d", self._server.serverPort())
        else:
            log.error("qt-pilot: failed to listen on port %d", port)
        return ok

    def port(self) -> int:
        return self._server.serverPort()

    @Slot()
    def _on_connection(self) -> None:
        sock = self._server.nextPendingConnection()
        if sock is None:
            return
        self._buffers[sock] = b""
        sock.readyRead.connect(lambda s=sock: self._on_data(s))
        sock.disconnected.connect(lambda s=sock: self._cleanup(s))

    def _on_data(self, sock: Any) -> None:
        raw = bytes(sock.readAll())
        self._buffers[sock] = self._buffers.get(sock, b"") + raw
        while True:
            line, self._buffers[sock] = _pop_line(self._buffers[sock])
            if line is None:
                break
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                continue
            self._handle_request(sock, req)

    def _handle_request(self, sock: Any, req: Any) -> None:
        if not isinstance(req, dict):
            self._write(sock, {
                "jsonrpc": "2.0",
                "error": {"code": ERROR_INVALID_REQUEST,
                          "message": "Invalid Request"},
                "id": None,
            })
            return

        method = req.get("method", "")
        params = req.get("params") or {}
        request_id = req.get("id")

        if not isinstance(params, dict):
            self._write(sock, {
                "jsonrpc": "2.0",
                "error": {"code": ERROR_INVALID_PARAMS,
                          "message": "params must be an object"},
                "id": request_id,
            })
            return

        try:
            result = self._dispatch(method, params)
            self._write(sock, {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id,
            })
        except Exception as exc:
            self._write(sock, {
                "jsonrpc": "2.0",
                "error": {"code": ERROR_INTERNAL, "message": str(exc)},
                "id": request_id,
            })

    def _dispatch(self, method: str, params: dict) -> Any:
        dispatch_table: dict[str, Callable[[], Any]] = {
            "snapshot": lambda: self._probe.snapshot(**params),
            "screenshot": lambda: self._probe.screenshot(**params),
            "click": lambda: self._probe.click(**params),
            "fill": lambda: self._probe.fill(**params),
            "type_text": lambda: self._probe.type_text(**params),
            "press": lambda: self._probe.press(**params),
            "scroll": lambda: self._probe.scroll(**params),
            "eval": lambda: self._probe.eval_js(**params),
            "get": lambda: self._probe.get_property(**params),
            "get_context": lambda: self._probe.get_context_property(**params),
            "wait": lambda: self._probe.wait(**params),
            "status": lambda: self._probe.status(),
        }
        handler = dispatch_table.get(method)
        if handler is None:
            raise ValueError(f"Unknown method: {method}")
        return handler()

    def _write(self, sock: Any, resp: dict) -> None:
        sock.write(json.dumps(resp).encode("utf-8") + b"\n")
        sock.flush()

    def _cleanup(self, sock: Any) -> None:
        self._buffers.pop(sock, None)
        try:
            sock.deleteLater()
        except RuntimeError:
            pass
