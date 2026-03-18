# qt-pilot

CLI automation for PySide6/QML apps — like Playwright, but for Qt Quick.

```
qt-pilot snapshot -i          # list interactive elements with @refs
qt-pilot screenshot --annotate  # annotated screenshot
qt-pilot click @e1            # click element
qt-pilot fill @e1 "hello"    # type into field
qt-pilot eval "doSomething()" # run QML/JS expression
```

## Quick Start

### 1. Install

```bash
pip install qt-pilot
# or
uv add qt-pilot
```

### 2. Add to your app (2 lines)

```python
# In your main(), after engine.load():
from qt_pilot import install
install(engine)
```

### 3. Run your app with the probe enabled

```bash
QT_PILOT=1 python my_app.py
```

### 4. Use the CLI

```bash
qt-pilot status                    # check connection
qt-pilot snapshot -i               # interactive elements
qt-pilot screenshot --annotate     # annotated screenshot
qt-pilot click @e1                 # click
qt-pilot fill @e2 "hello world"   # type into field
```

## How It Works

qt-pilot embeds a lightweight probe (QObject + QTcpServer) into your running PySide6/QML app. The probe:

- Walks the QQuickItem visual tree to discover elements
- Captures screenshots via `QQuickWindow.grabWindow()`
- Injects mouse/keyboard events via `QApplication.sendEvent()`
- Evaluates QML/JavaScript expressions in the root context

The CLI (`qt-pilot`) is a separate process that talks to the probe over localhost TCP using JSON-RPC 2.0.

## Commands

| Command | Description |
|---------|-------------|
| `snapshot [-i]` | QML element tree with @refs (`-i` = interactive only) |
| `screenshot [path] [--annotate]` | Capture window as PNG |
| `click @eN` | Click element center |
| `fill @eN "text"` | Clear + type text |
| `type @eN "text"` | Type without clearing |
| `press Key` | Press key (e.g., `Enter`, `Tab`, `Ctrl+A`) |
| `scroll direction [amount]` | Scroll window |
| `eval "expression"` | Evaluate QML/JS on root object |
| `get @eN prop` | Read property from element |
| `get-context Path.prop` | Read context property (service) |
| `wait @eN \| ms` | Wait for element or duration |
| `status` | Connection and window info |

## Requirements

- **Host app**: PySide6 >= 6.6 (Qt Quick)
- **CLI**: Python >= 3.10 (stdlib only, no extra dependencies)

## License

MIT
