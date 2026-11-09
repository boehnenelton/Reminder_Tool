# Reminder Management Engine

> Authoritative dual-registry reminder and active task engine with automatic completion removal and terminal startup integration.

[![Platform](https://img.shields.io/badge/Platform-Linux%20%2F%20Android%20Termux-blue.svg)](#prerequisites--setup)
[![Format](https://img.shields.io/badge/Format-BEJSON%20104a-DE2626.svg)](#technical-specifications--storage-schemas)
[![Discipline](https://img.shields.io/badge/Discipline-57--Column%20Portrait-black.svg)](#terminal-display--color-standards)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#license--attribution)

---

## Table of Contents

- [Prerequisites & Setup](#prerequisites--setup)
- [System Architecture & Dual Registries](#system-architecture--dual-registries)
- [Terminal Launch Integration](#terminal-launch-integration)
- [Core Features & Priority Model](#core-features--priority-model)
- [Terminal Display & Color Standards](#terminal-display--color-standards)
- [CLI Reference Guide](#cli-reference-guide)
- [Technical Specifications & Storage Schemas](#technical-specifications--storage-schemas)
- [Verification & Testing](#verification--testing)
- [License & Attribution](#license--attribution)

---

## Prerequisites & Setup

### Environment Requirements
- **Python**: 3.10 or higher
- **Shell**: Bash / Zsh
- **Platform**: Linux / Android Termux

### Installation & Global Wrapper
To make `remind` accessible globally in your interactive shell:

```bash
# Clone or navigate to the repository
cd reminder_tool

# Create a symlink or executable wrapper in your PATH (e.g. ~/.local/bin)
mkdir -p ~/.local/bin
cat << 'EOF' > ~/.local/bin/remind
#!/usr/bin/env bash
exec python3 "$PROJECT_ROOT/reminder_tool.py" "$@"
EOF
chmod +x ~/.local/bin/remind
```

---

## System Architecture & Dual Registries

The Reminder Engine maintains strict separation of active task state and archived history across two discrete tabular registries:

```
                  ┌────────────────────────────────────────┐
                  │       remind (reminder_tool.py)        │
                  │        [REMINDER CLI INTERFACE]        │
                  └───────────────────┬────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              │                                               │
              ▼                                               ▼
   ┌──────────────────────┐                       ┌──────────────────────┐
   │    Active Queue      │                       │  Completed Archive   │
   │ reminders.104a.bejson│                       │completed_reminders...│
   └──────────┬───────────┘                       └──────────┬───────────┘
              │                                               ▲
              │          remind done <id|index>               │
              └───────────────────────────────────────────────┘
                     (atomic transfer & removal)
```

1. **Active Queue (`data/reminders.104a.bejson`)**:
   Contains all currently pending reminders.
2. **Completed Archive (`data/completed_reminders.104a.bejson`)**:
   Permanent historical ledger containing completion timestamps and resolution records.
3. **Atomic Removal on Completion**:
   Executing `remind done <id|index>` extracts the target entry from active storage, mints an ISO 8601 UTC completion timestamp, and appends the finalized record to the archive in a single atomic transaction.

---

## Terminal Launch Integration

The engine is engineered to hook cleanly into interactive shell startup (`~/.bashrc` or `~/.zshrc`).

Add the execution check to your shell configuration:

```bash
# ~/.bashrc
if [ -x "$HOME/.local/bin/remind" ]; then
    remind --print-termux
fi
```

### Zero-Clutter Behavior
- When **active reminders exist**, the engine renders a clean 57-column box highlighting priority tags, indices, and reminder content.
- When **zero active reminders exist**, the command outputs absolutely nothing and exits immediately with code `0`, preserving clean terminal real estate.

---

## Core Features & Priority Model

### Priority Levels
- **Urgent (`urgent`)**: Critical items surfaced with prominent emphasis.
- **High (`high`)**: Priority tasks surfaced ahead of standard reminders.
- **Normal (`normal`)**: Default priority level for standard work items.
- **Low (`low`)**: Secondary or background reminders.

---

## Terminal Display & Color Standards

Output adheres to 57-column portrait discipline and high-contrast tri-color styling:

| Element | Format | Color Sequence |
|---|---|---|
| **Headers & Labels** | Section titles, indices, field labels | `#DE2626` Truecolor (`\033[38;2;222;38;38m`) / ANSI Bold Red (`\033[1;31m`) |
| **Status (Positive)** | `[✓]` with message in **white lowercase** | `\033[1;37m[✓] reminder added: ...\033[0m` |
| **Failures & Errors** | `[✗]` with message in **#DE2626 UPPERCASE RED** | `\033[38;2;222;38;38m[✗] REMINDER NOT FOUND.\033[0m` |
| **Neutral Text** | Reminder content, dates, IDs | Standard White (`\033[0;37m` / `\033[1;37m`) |

---

## CLI Reference Guide

```bash
# Add a new reminder
remind add "Audit database migration script" -p urgent
remind add "Refactor notes exporter" -p high -t "notes,dev"
remind add "Update documentation"

# Complete and remove reminder (by numerical index or reminder ID)
remind done 1
remind done rem_20261109_024441

# Permanently delete reminder without archiving
remind rm 2

# List all active reminders
remind list

# View historical completed reminders
remind completed

# Print startup banner (used by ~/.bashrc)
remind print
remind --print-termux

# Emit machine-readable JSON state
remind --json
remind --agent-context
```

---

## Technical Specifications & Storage Schemas

### Active Reminders Table Schema
- **Identifier**: `reminder_id` (string, e.g. `rem_YYYYMMDD_HHMMSS`)
- **Text**: `reminder_text` (string)
- **Priority**: `priority` (string: `urgent`, `high`, `normal`, `low`)
- **Status**: `status` (string: `active`)
- **Creation Date**: `creation_date` (ISO 8601 UTC timestamp)
- **Due Date**: `due_date` (string, optional)
- **Tags**: `tags` (string, comma-separated)

### Completed Reminders Archive Schema
- **Identifier**: `reminder_id` (string)
- **Text**: `reminder_text` (string)
- **Priority**: `priority` (string)
- **Status**: `status` (string: `completed`)
- **Creation Date**: `creation_date` (ISO 8601 UTC)
- **Completion Date**: `completion_date` (ISO 8601 UTC)
- **Due Date**: `due_date` (string)
- **Tags**: `tags` (string)

---

## Verification & Testing

Verify end-to-end reminder lifecycle:

```bash
# 1. Add test item
remind add "System verification test" -p normal

# 2. Inspect active queue
remind list

# 3. Complete item
remind done 1

# 4. Confirm item moved to completed archive
remind completed

# 5. Confirm terminal launch hook emits 0 lines when empty
remind print
```

---

## License & Attribution

Authored by **Elton Boehnen** (`boehnenelton2024@gmail.com`).  
Project Website: [boehnenelton2024.pages.dev](https://boehnenelton2024.pages.dev) · GitHub: [boehnenelton](https://github.com/boehnenelton)  
Licensed under the **MIT License**.
