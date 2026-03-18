---
name: qt-pilot
description: CLI automation for PySide6/QML desktop apps. Use when interacting with, testing, or dogfooding a running Qt Quick application. Provides snapshot, screenshot, click, fill, and eval commands — like agent-browser but for desktop Qt apps.
---

# Qt Desktop App Automation with qt-pilot

qt-pilot lets you interact with a running PySide6/QML application through a CLI, similar to how agent-browser interacts with web apps.

## Prerequisites

The target app must have qt-pilot installed and the probe enabled:

```bash
QT_PILOT=1 uv run my-app
```

## Core Workflow

**This is an interactive tool, not a scripting framework.** Each command is a separate Bash tool call. You read the output, think about what to do next, then run the next command.

```
1. Snapshot    →  see what's on screen, get @refs
2. Think       →  decide what to interact with
3. Act         →  click, fill, type, eval
4. Re-snapshot →  observe the result
5. Repeat
```

**Never chain multiple qt-pilot commands in one Bash call.** Each command should be its own tool call so you can read the result before deciding the next action.

### Example: Login flow

```bash
# Step 1: See what's on screen
qt-pilot snapshot -i
```
Output: `@e1 [TextField] "Username" ... @e2 [TextField] "Password" ... @e3 [Button] "Sign In"`

```bash
# Step 2: Fill username
qt-pilot fill @e1 "admin"
```

```bash
# Step 3: Fill password
qt-pilot fill @e2 "password"
```

```bash
# Step 4: Click sign in
qt-pilot click @e3
```

```bash
# Step 5: See what happened
qt-pilot snapshot -i
```
Output: `[page: dashboard] @e1 [Button] "Start Session" ...` — login worked.

## Commands

### Snapshot — Element Discovery

```bash
qt-pilot snapshot              # full visible QML tree
qt-pilot snapshot -i           # interactive elements only (recommended)
```

Output format:
```
[page: dashboard] [window: 1280x800]
@e1 [Button] "Start Session" (1098,107 150x44)
@e2 [Button] "View All" (1144,421 80x46)
  [Text] "Welcome back, admin" (30,90)
```

### Screenshot

```bash
qt-pilot screenshot                     # save to temp file, print path
qt-pilot screenshot ./shot.png          # save to specified path
qt-pilot screenshot --annotate          # with numbered badges on elements
```

Use screenshots when you need visual context (layout verification, checking colors, reading non-interactive text). Use snapshot for element discovery and interaction.

### Interaction

```bash
qt-pilot click @e1                # click element center
qt-pilot fill @e1 "hello"        # clear field + type text
qt-pilot type @e1 "hello"        # type without clearing (append)
qt-pilot press Enter              # press key
qt-pilot press Tab                # tab to next field
qt-pilot press Ctrl+A             # key with modifier
qt-pilot scroll down 300          # scroll window
```

### QML Expression Evaluation

For app-specific actions that don't map to UI elements:

```bash
qt-pilot eval "navigateTo('patients')"
qt-pilot eval "Auth.login('admin', 'password')"
```

### Property Access

```bash
qt-pilot get @e1 text             # read element property
qt-pilot get @e1 enabled
qt-pilot get-context Auth.loggedIn
qt-pilot get-context window.currentPage
```

### Wait

```bash
qt-pilot wait @e1                 # wait for element to appear
qt-pilot wait 2000                # wait 2 seconds
```

### Status

```bash
qt-pilot status                   # connection check + window info
```

## Ref Lifecycle

Refs (`@e1`, `@e2`) are invalidated when the QML tree changes. **Always re-snapshot after:**

- Clicking a button that navigates
- Opening/closing dialogs
- Any action that changes the visible UI

## Port Configuration

```bash
QT_PILOT_PORT=9999 QT_PILOT=1 uv run my-app   # app side
qt-pilot --port 9999 status                      # CLI side
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "cannot connect to probe" | App not running with `QT_PILOT=1` |
| Refs not found | Re-snapshot — refs expire on tree changes |
| Click does nothing | Check `qt-pilot get @eN enabled` |
| Duplicate refs | StackView artifact — use the refs with `[focused]` |
