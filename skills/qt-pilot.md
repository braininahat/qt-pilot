---
name: qt-pilot
description: CLI automation for PySide6/QML desktop apps. Use when interacting with, testing, or dogfooding a running Qt Quick application. Provides snapshot, screenshot, click, fill, and eval commands — like agent-browser but for desktop Qt apps.
---

# Qt Desktop App Automation with qt-pilot

qt-pilot lets you interact with a running PySide6/QML application through a CLI, similar to how agent-browser interacts with web apps.

## Prerequisites

The target app must have qt-pilot installed and the probe enabled:

```bash
# Start the app with the probe
QT_PILOT=1 python my_app.py
# or
QT_PILOT=1 uv run my-app
```

## Core Workflow

Every interaction follows this pattern:

1. **Snapshot**: `qt-pilot snapshot -i` (get element refs like `@e1`, `@e2`)
2. **Interact**: Use refs to click, fill, type
3. **Re-snapshot**: After navigation or state changes, get fresh refs

```bash
qt-pilot snapshot -i
# Output: @e1 [TextField] placeholder="Username" (440,340 400x44)
#         @e2 [TextField] placeholder="Password" (440,400 400x44)
#         @e3 [Button] "Sign In" (440,460 400x44)

qt-pilot fill @e1 "admin"
qt-pilot fill @e2 "password123"
qt-pilot click @e3
qt-pilot snapshot -i  # Re-snapshot after navigation
```

## Commands

### Snapshot — Element Discovery

```bash
qt-pilot snapshot              # full visible QML tree
qt-pilot snapshot -i           # interactive elements only (recommended)
```

Output format:
```
[page: login] [window: 1280x800]
@e1 [TextField] "Username" (440,340 400x44) [focused]
@e2 [TextField] "Password" (440,400 400x44)
@e3 [Button] "Sign In" (440,460 400x44)
  [Text] "UltraSpeech" (540,180)
```

### Screenshot

```bash
qt-pilot screenshot                     # save to temp file, print path
qt-pilot screenshot ./shot.png          # save to specified path
qt-pilot screenshot --annotate          # with numbered badges on elements
qt-pilot screenshot -a ./annotated.png  # annotated to specified path
```

Use annotated screenshots when you need visual context about element positions.

### Interaction

```bash
qt-pilot click @e1                # click element center
qt-pilot fill @e1 "hello"        # clear field + type text
qt-pilot type @e1 "hello"        # type without clearing (append)
qt-pilot press Enter              # press key
qt-pilot press Tab                # tab to next field
qt-pilot press Ctrl+A             # key with modifier
qt-pilot scroll down 300          # scroll window
qt-pilot scroll up 500
```

### QML Expression Evaluation

```bash
# Call QML functions on the root object
qt-pilot eval "navigateTo('patients')"

# Call service methods (exposed as QML context properties)
qt-pilot eval "Auth.login('admin', 'password')"
qt-pilot eval "Patients.create('John', '2000-01-01', 'IRB-001')"

# Read values
qt-pilot eval "Auth.currentUsername"
```

### Property Access

```bash
qt-pilot get @e1 text             # read element property
qt-pilot get @e1 enabled
qt-pilot get @e1 checked

qt-pilot get-context Auth.loggedIn           # read service property
qt-pilot get-context window.currentPage      # root object property
```

### Wait

```bash
qt-pilot wait @e1                 # wait for element to appear (5s timeout)
qt-pilot wait @e1 --timeout 10000  # custom timeout
qt-pilot wait 2000                # wait 2 seconds
```

### Status

```bash
qt-pilot status
# connected: True
# window_size: 1280x800
# root_class: ApplicationWindow
# current_page: dashboard
```

## Command Chaining

Commands can be chained with `&&` in a single shell call:

```bash
qt-pilot fill @e1 "admin" && qt-pilot fill @e2 "pass" && qt-pilot click @e3
```

Chain when you don't need intermediate output. Run separately when you need to parse snapshot output to discover refs.

## Ref Lifecycle

Refs (`@e1`, `@e2`, etc.) are invalidated when the QML tree changes. Always re-snapshot after:

- Page navigation
- Dialog open/close
- Dynamic content loading
- Form submission that changes the view

```bash
qt-pilot click @e3              # navigates to new page
qt-pilot snapshot -i            # MUST re-snapshot
qt-pilot click @e1              # use new refs
```

## Common Patterns

### Login Flow

```bash
qt-pilot snapshot -i
qt-pilot fill @e1 "username"
qt-pilot fill @e2 "password"
qt-pilot click @e3
qt-pilot wait 1000
qt-pilot snapshot -i              # check result
```

### Navigate and Explore

```bash
qt-pilot eval "navigateTo('patients')"
qt-pilot wait 500
qt-pilot snapshot -i
qt-pilot screenshot --annotate
```

### Visual Verification

```bash
qt-pilot screenshot --annotate ./before.png
qt-pilot click @e1
qt-pilot wait 500
qt-pilot screenshot --annotate ./after.png
```

## Port Configuration

Default port: 9718. Override with:

```bash
# App side
QT_PILOT_PORT=9999 QT_PILOT=1 python my_app.py

# CLI side
qt-pilot --port 9999 status
# or
QT_PILOT_PORT=9999 qt-pilot status
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "cannot connect to qt-pilot probe" | Is the app running with `QT_PILOT=1`? |
| Refs not found | Re-snapshot — refs expire on tree changes |
| Click does nothing | Check `qt-pilot get @eN enabled` — element may be disabled |
| Fill doesn't type | The element may not accept keyboard input; try `qt-pilot type` instead |
| Empty snapshot | The QML tree may not be loaded yet; `qt-pilot wait 1000` then retry |
