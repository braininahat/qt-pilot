---
name: dogfood-qt
description: Systematically explore and test a PySide6/QML desktop application to find bugs, UX issues, and other problems. Use when asked to "dogfood", "QA", "test this app", or review a Qt Quick desktop application. Produces a structured report with screenshot evidence.
---

# Dogfood a Qt Desktop App

Systematically explore a PySide6/QML desktop application, find issues, and produce a report with screenshot evidence.

## Prerequisites

- The app must have `qt-pilot` integrated (`from qt_pilot import install; install(engine)`)
- The app must be running with `QT_PILOT=1`
- If not running, start it: `QT_PILOT=1 uv run <app-command> &`

## Setup

| Parameter | Default | Override |
|-----------|---------|----------|
| **App command** | _(required)_ | `QT_PILOT=1 uv run ultraspeech` |
| **Output directory** | `./dogfood-output/` | User-specified |
| **Scope** | Full app | `Focus on the login page` |
| **Port** | 9718 | `QT_PILOT_PORT=9999` |

## Workflow

```
1. Initialize    Create output dirs, start app if needed
2. Orient        Take initial snapshot + screenshot, map navigation
3. Explore       Visit each page, test interactions
4. Document      Screenshot each issue as found
5. Wrap up       Summarize findings, close
```

### 1. Initialize

```bash
mkdir -p {OUTPUT_DIR}/screenshots
```

Create the report file from scratch:

```markdown
# Dogfood Report: {APP_NAME}
Date: {DATE}
Scope: {SCOPE}

## Summary
- Critical: 0
- Major: 0
- Minor: 0
- Total: 0

## Issues
```

Verify connection:

```bash
qt-pilot status
```

### 2. Orient

Take initial annotated screenshot and snapshot:

```bash
qt-pilot screenshot --annotate {OUTPUT_DIR}/screenshots/initial.png
qt-pilot snapshot -i
```

Identify navigation structure — which pages exist, how to reach them.

### 3. Explore

**Strategy — work through the app systematically:**

- Start from the initial page (usually login or dashboard)
- Navigate to each page using `qt-pilot eval "navigateTo('pageName')"`
- At each page, snapshot and test interactive elements
- Try realistic workflows (create, edit, delete)
- Check edge cases: empty fields, long text, special characters

**At each page:**

```bash
qt-pilot snapshot -i
qt-pilot screenshot --annotate {OUTPUT_DIR}/screenshots/{page-name}.png
```

### 4. Document Issues

Document issues as you find them. Every issue needs:

1. **Screenshot evidence** (annotated when relevant)
2. **Steps to reproduce**
3. **Expected vs actual behavior**
4. **Severity** (Critical / Major / Minor)

```bash
# Before the issue
qt-pilot screenshot {OUTPUT_DIR}/screenshots/issue-{NNN}-before.png

# Trigger the issue
qt-pilot click @e1  # or whatever action
qt-pilot wait 500

# After — capture the broken state
qt-pilot screenshot --annotate {OUTPUT_DIR}/screenshots/issue-{NNN}-after.png
```

**Issue template:**

```markdown
### ISSUE-{NNN}: {Title}
**Severity:** Critical | Major | Minor
**Page:** {page name}
**Category:** {Functional | Visual | UX | Performance | State}

**Steps to reproduce:**
1. Navigate to {page}
2. {action}
3. {action}

**Expected:** {what should happen}
**Actual:** {what actually happens}

**Screenshots:**
- Before: screenshots/issue-{NNN}-before.png
- After: screenshots/issue-{NNN}-after.png
```

### 5. Wrap Up

After exploring, update summary counts and summarize findings.

## Issue Categories

### Functional
- Buttons that don't work
- Forms that don't submit
- Navigation that goes to wrong page
- Data not saving/loading
- Service errors

### Visual / Layout
- Elements overlapping
- Text truncation or clipping
- Misalignment
- Wrong colors or fonts
- Elements outside viewport

### UX
- Confusing labels
- Missing feedback (no loading indicator)
- Unclear error messages
- Unintuitive workflows
- Missing keyboard navigation

### State
- Stale data after navigation
- UI not updating after action
- Inconsistent state between pages
- Back navigation losing data

### Desktop-Specific
- Window resize behavior
- Keyboard shortcuts not working
- Focus order (Tab navigation)
- High-DPI scaling issues

## Tips

- **Take annotated screenshots liberally** — they're your evidence
- **Snapshot after every navigation** — refs change when the page changes
- **Try both happy path and edge cases** — empty inputs, very long text, special characters
- **Check disabled states** — `qt-pilot get @eN enabled` reveals if elements are active
- **Use eval for setup** — `qt-pilot eval "Auth.login('admin','pass')"` to quickly reach authenticated pages
- **Test window resize** — many layout bugs only appear at smaller sizes
- **Aim for 5-10 well-documented issues** — quality over quantity
