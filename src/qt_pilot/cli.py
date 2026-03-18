"""qt-pilot CLI: thin TCP client that talks to the in-app probe."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from typing import Any


DEFAULT_PORT = 9718


def _rpc(method: str, port: int = DEFAULT_PORT, **params: Any) -> Any:
    """Send a JSON-RPC 2.0 request and return the result."""
    addr = ("localhost", port)
    try:
        sock = socket.create_connection(addr, timeout=10)
    except (ConnectionRefusedError, OSError) as exc:
        print(
            f"Error: cannot connect to qt-pilot probe on localhost:{port}\n"
            f"Is the app running with QT_PILOT=1?",
            file=sys.stderr,
        )
        sys.exit(2)

    request = json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
    })
    sock.sendall(request.encode("utf-8") + b"\n")

    buf = b""
    while b"\n" not in buf:
        chunk = sock.recv(65536)
        if not chunk:
            break
        buf += chunk
    sock.close()

    if not buf.strip():
        print("Error: empty response from probe", file=sys.stderr)
        sys.exit(1)

    resp = json.loads(buf.split(b"\n", 1)[0])
    if "error" in resp:
        msg = resp["error"].get("message", "unknown error")
        print(f"Error: {msg}", file=sys.stderr)
        sys.exit(1)

    return resp.get("result")


def _port(args: argparse.Namespace) -> int:
    return args.port or int(os.environ.get("QT_PILOT_PORT", str(DEFAULT_PORT)))


# -- Subcommands ----------------------------------------------------------

def cmd_snapshot(args: argparse.Namespace) -> None:
    result = _rpc("snapshot", port=_port(args), interactive_only=args.interactive)
    print(result["tree"])


def cmd_screenshot(args: argparse.Namespace) -> None:
    kwargs: dict[str, Any] = {"annotate": args.annotate}
    if args.path:
        kwargs["path"] = args.path
    result = _rpc("screenshot", port=_port(args), **kwargs)
    print(result["path"])
    if result.get("legend"):
        for line in result["legend"]:
            print(line)


def cmd_click(args: argparse.Namespace) -> None:
    _rpc("click", port=_port(args), ref=args.ref)


def cmd_fill(args: argparse.Namespace) -> None:
    _rpc("fill", port=_port(args), ref=args.ref, text=args.text)


def cmd_type(args: argparse.Namespace) -> None:
    _rpc("type_text", port=_port(args), ref=args.ref, text=args.text)


def cmd_press(args: argparse.Namespace) -> None:
    kwargs: dict[str, Any] = {"key": args.key}
    if args.ref:
        kwargs["ref"] = args.ref
    _rpc("press", port=_port(args), **kwargs)


def cmd_scroll(args: argparse.Namespace) -> None:
    _rpc("scroll", port=_port(args),
         direction=args.direction, amount=args.amount)


def cmd_eval(args: argparse.Namespace) -> None:
    result = _rpc("eval", port=_port(args), expression=args.expression)
    if result.get("error"):
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)
    if result.get("result") is not None:
        print(result["result"])


def cmd_get(args: argparse.Namespace) -> None:
    result = _rpc("get", port=_port(args), ref=args.ref, prop=args.prop)
    val = result.get("value")
    print(val if val is not None else "(null)")


def cmd_get_context(args: argparse.Namespace) -> None:
    result = _rpc("get_context", port=_port(args), path=args.path)
    val = result.get("value")
    print(val if val is not None else "(null)")


def cmd_wait(args: argparse.Namespace) -> None:
    kwargs: dict[str, Any] = {}
    if args.target.startswith("@"):
        kwargs["ref"] = args.target
    else:
        try:
            kwargs["ms"] = int(args.target)
        except ValueError:
            print(f"Error: '{args.target}' is not a ref (@eN) or milliseconds",
                  file=sys.stderr)
            sys.exit(1)
    if args.timeout:
        kwargs["timeout"] = args.timeout
    result = _rpc("wait", port=_port(args), **kwargs)
    elapsed = result.get("elapsed_ms")
    if elapsed is not None:
        print(f"ok ({elapsed}ms)")
    else:
        print("ok")


def cmd_status(args: argparse.Namespace) -> None:
    result = _rpc("status", port=_port(args))
    for key, val in result.items():
        print(f"{key}: {val}")


# -- Main -----------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="qt-pilot",
        description="CLI automation for PySide6/QML apps",
    )
    parser.add_argument(
        "--port", "-p", type=int, default=None,
        help=f"probe port (default: ${DEFAULT_PORT}, or QT_PILOT_PORT env)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # snapshot
    p = sub.add_parser("snapshot", help="QML element tree with @refs")
    p.add_argument("-i", "--interactive", action="store_true",
                   help="interactive elements only")
    p.set_defaults(func=cmd_snapshot)

    # screenshot
    p = sub.add_parser("screenshot", help="capture window screenshot")
    p.add_argument("path", nargs="?", default=None, help="output path")
    p.add_argument("--annotate", "-a", action="store_true",
                   help="overlay numbered badges on interactive elements")
    p.set_defaults(func=cmd_screenshot)

    # click
    p = sub.add_parser("click", help="click an element")
    p.add_argument("ref", help="element ref (e.g., @e1)")
    p.set_defaults(func=cmd_click)

    # fill
    p = sub.add_parser("fill", help="clear field and type text")
    p.add_argument("ref", help="element ref")
    p.add_argument("text", help="text to type")
    p.set_defaults(func=cmd_fill)

    # type
    p = sub.add_parser("type", help="type text without clearing")
    p.add_argument("ref", help="element ref")
    p.add_argument("text", help="text to type")
    p.set_defaults(func=cmd_type)

    # press
    p = sub.add_parser("press", help="press a key")
    p.add_argument("key", help="key name (e.g., Enter, Tab, Ctrl+A)")
    p.add_argument("--ref", default=None, help="target element ref")
    p.set_defaults(func=cmd_press)

    # scroll
    p = sub.add_parser("scroll", help="scroll the window")
    p.add_argument("direction", choices=["up", "down", "left", "right"])
    p.add_argument("amount", type=int, nargs="?", default=300,
                   help="scroll amount in pixels (default: 300)")
    p.set_defaults(func=cmd_scroll)

    # eval
    p = sub.add_parser("eval", help="evaluate QML/JS expression")
    p.add_argument("expression", help="JavaScript expression")
    p.set_defaults(func=cmd_eval)

    # get
    p = sub.add_parser("get", help="read a property from a ref'd element")
    p.add_argument("ref", help="element ref (e.g., @e1)")
    p.add_argument("prop", help="property name")
    p.set_defaults(func=cmd_get)

    # get-context
    p = sub.add_parser("get-context", help="read a context property")
    p.add_argument("path", help="dotted path (e.g., Auth.loggedIn)")
    p.set_defaults(func=cmd_get_context)

    # wait
    p = sub.add_parser("wait", help="wait for element or duration")
    p.add_argument("target", help="ref (@eN) or milliseconds")
    p.add_argument("--timeout", type=int, default=None,
                   help="timeout in ms (default: 5000)")
    p.set_defaults(func=cmd_wait)

    # status
    p = sub.add_parser("status", help="check probe connection and window info")
    p.set_defaults(func=cmd_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
