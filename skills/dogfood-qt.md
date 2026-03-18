---
name: dogfood-qt
description: Systematically explore and test a PySide6/QML desktop application to find bugs, UX issues, and other problems. Use when asked to "dogfood", "QA", "test this app", or review a Qt Quick desktop application.
---

# Dogfood a Qt Desktop App

Systematically explore a running PySide6/QML app to find bugs and UX issues.

## Prerequisites

The app must be running with `QT_PILOT=1`. If not running, start it:

```bash
QT_PILOT=1 uv run <app-command> &
sleep 15
```

## Workflow

**This is interactive exploration, not scripted testing.** Use qt-pilot commands one at a time, observe the result, decide what to do next.

```
1. Orient        Take initial snapshot + screenshot
2. Explore       Visit pages, test interactions
3. Document      Screenshot each issue as found
4. Report        Summarize findings
```

### 1. Orient

```bash
qt-pilot status
```

```bash
qt-pilot snapshot -i
```

```bash
qt-pilot screenshot --annotate ./dogfood/initial.png
```

### 2. Explore

Work through the app systematically:

- Start from the initial page (login or dashboard)
- Navigate to each page — snapshot at each one
- Test interactive elements: click buttons, fill forms, open dialogs
- Try realistic workflows (create, edit, delete)
- Check edge cases: empty fields, long text, special characters

**At each page:**
```bash
qt-pilot snapshot -i           # see what elements exist
qt-pilot screenshot ./dogfood/page-name.png  # visual record
```

**Test an interaction:**
```bash
qt-pilot click @e3             # perform action
qt-pilot snapshot -i           # observe result
```

### 3. Document Issues

When you find something wrong:

1. Take a screenshot showing the issue
2. Note the steps that led to it
3. Classify severity (Critical / Major / Minor)

Categories:
- **Functional**: buttons that don't work, data not saving
- **Visual**: clipping, overlap, misalignment, wrong colors
- **UX**: confusing labels, missing feedback, unintuitive flow
- **State**: stale data after navigation, inconsistent UI
- **Desktop-specific**: resize behavior, keyboard nav, focus order

### 4. Report

Summarize: total issues, breakdown by severity, most critical items.

## Tips

- **One command per tool call** — read the result before deciding the next action
- **Snapshot after every navigation** — refs change when the page changes
- **Use annotated screenshots** for visual bugs
- **Use `eval` for setup** — `qt-pilot eval "Auth.login('admin','pass')"` to quickly reach authenticated pages
- **Check disabled states** — `qt-pilot get @eN enabled`
- **Duplicate refs** — StackView can show two copies; use the one with `[focused]`
- **Aim for 5-10 well-documented issues** — quality over quantity
