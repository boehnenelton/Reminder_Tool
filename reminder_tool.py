#!/data/data/com.termux/files/usr/bin/env python3
"""
Tool Name   : reminder_tool.py
Rel. Path   : reminder_tool.py
Family      : System Management / Reminders
Purpose     : Authoritative BEJSON 104a Reminder Management Engine & CLI Interface.
              Stores active reminders in formal BEJSON schemas:
                - Active Reminders:    data/reminders.104a.bejson
                - Completed Reminders: data/completed_reminders.104a.bejson
              Removes reminders from active queue on completion.
              Integrates directly with Termux ~/.bashrc to surface active
              reminders automatically on terminal launch.
Version     : 1.0.0
Author      : Elton Boehnen · boehnenelton2024@gmail.com · boehnenelton2024.pages.dev · github.com/boehnenelton
Date        : 2026-11-09
RELATIONAL_ID : 7a2b918c-3914-41d8-a15d-f19b48c66e42
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Dynamic Path Resolution (Policy §4.1 & §4.5) ─────────────────────────────
def get_script_path() -> Path:
    """Resolve and return script directory."""
    return Path(__file__).resolve().parent

SCRIPT_PATH: Path = get_script_path()
LOCAL_DATA_DIRECTORY: Path = SCRIPT_PATH / "data"
LOCAL_CONFIG_DIRECTORY: Path = SCRIPT_PATH / "config"
DEFINITIONS_STORE_PATH: Path = Path("/storage/emulated/0/.env/user/definitions.json")

DEFAULT_REMINDERS_REGISTRY: Path = LOCAL_DATA_DIRECTORY / "reminders.104a.bejson"
DEFAULT_COMPLETED_REGISTRY: Path = LOCAL_DATA_DIRECTORY / "completed_reminders.104a.bejson"


def resolve_canonical_paths() -> Dict[str, Path]:
    """Resolve paths dynamically from definitions.json or local fallbacks."""
    paths_map: Dict[str, Path] = {
        "TOOL_ROOT": SCRIPT_PATH,
        "DATA_ROOT": LOCAL_DATA_DIRECTORY,
        "REMINDERS_REGISTRY": DEFAULT_REMINDERS_REGISTRY,
        "COMPLETED_REGISTRY": DEFAULT_COMPLETED_REGISTRY,
    }

    if DEFINITIONS_STORE_PATH.exists():
        try:
            with open(DEFINITIONS_STORE_PATH, "r", encoding="utf-8") as handle:
                doc = json.load(handle)
                for row in doc.get("Values", []):
                    if isinstance(row, list) and len(row) >= 2:
                        k, v = str(row[0]).strip(), str(row[1]).strip()
                        if k == "REMINDER_TOOL_ROOT":
                            paths_map["TOOL_ROOT"] = Path(v)
                            paths_map["DATA_ROOT"] = Path(v) / "data"
                        elif k == "REMINDERS_REGISTRY":
                            paths_map["REMINDERS_REGISTRY"] = Path(v)
                            paths_map["COMPLETED_REGISTRY"] = Path(v).parent / "completed_reminders.104a.bejson"
        except Exception:
            pass

    return paths_map


# ── Policy §8.1 Tri-Color Palette & 57-Column Discipline ─────────────────────
COLOR_HEX_RED: str = "\033[38;2;222;38;38m"  # Policy §8.1 #DE2626 Truecolor
COLOR_ANSI_RED: str = "\033[1;31m"          # ANSI Bold Red fallback
COLOR_RESET: str = "\033[0m"
COLOR_DIM: str = "\033[2m"
COLOR_BOLD: str = "\033[1m"
COLOR_WHITE_BOLD: str = "\033[1;37m"

NO_COLOR: bool = os.getenv("NO_COLOR") is not None
COLORTERM: str = os.getenv("COLORTERM", "").lower()
SUPPORTS_TRUECOLOR: bool = "truecolor" in COLORTERM or "24bit" in COLORTERM

ACCENT: str = (COLOR_HEX_RED if SUPPORTS_TRUECOLOR else COLOR_ANSI_RED) if not NO_COLOR and sys.stdout.isatty() else ""
RESET: str = COLOR_RESET if not NO_COLOR and sys.stdout.isatty() else ""
DIM: str = COLOR_DIM if not NO_COLOR and sys.stdout.isatty() else ""
BOLD: str = COLOR_BOLD if not NO_COLOR and sys.stdout.isatty() else ""
WHITE_BOLD: str = COLOR_WHITE_BOLD if not NO_COLOR and sys.stdout.isatty() else ""

DIVIDER_57: str = "=" * 57
SUBDIVIDER_57: str = "-" * 57

# ── Canonical BEJSON 104a Schemas ────────────────────────────────────────────
REMINDERS_FIELDS: List[Dict[str, str]] = [
    {"name": "reminder_id", "type": "string", "description": "Unique identifier for reminder"},
    {"name": "reminder_text", "type": "string", "description": "Content of reminder message"},
    {"name": "priority", "type": "string", "description": "Priority: urgent, high, normal, low"},
    {"name": "status", "type": "string", "description": "Status: active"},
    {"name": "creation_date", "type": "string", "description": "ISO 8601 UTC creation timestamp"},
    {"name": "due_date", "type": "string", "description": "Optional deadline or target date"},
    {"name": "tags", "type": "string", "description": "Comma-separated classification tags"},
]

COMPLETED_FIELDS: List[Dict[str, str]] = [
    {"name": "reminder_id", "type": "string", "description": "Unique identifier for reminder"},
    {"name": "reminder_text", "type": "string", "description": "Content of reminder message"},
    {"name": "priority", "type": "string", "description": "Priority: urgent, high, normal, low"},
    {"name": "creation_date", "type": "string", "description": "ISO 8601 UTC creation timestamp"},
    {"name": "completion_date", "type": "string", "description": "ISO 8601 UTC completion timestamp"},
    {"name": "tags", "type": "string", "description": "Comma-separated classification tags"},
]


def compile_bejson_field_map(doc_payload: Dict[str, Any]) -> Dict[str, int]:
    """Compile O(1) field name to column index lookup cache per Policy §6.2."""
    fields: List[Dict[str, Any]] = doc_payload.get("Fields", [])
    return {f.get("name", ""): idx for idx, f in enumerate(fields) if f.get("name")}


def load_bejson_file(file_path: Path, default_fields: List[Dict[str, str]], schema_name: str) -> Dict[str, Any]:
    """Load a BEJSON 104a file or initialize template if missing."""
    if file_path.is_file():
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as exc:
            sys.stderr.write(f"Warning: Failed to load {file_path.name}: {exc}\n")

    return {
        "Format": "BEJSON",
        "Format_Version": "104a",
        "Format_Creator": "Elton Boehnen",
        "Schema_Name": schema_name,
        "Schema_Version": "1.0.0",
        "Records_Type": [schema_name.replace(" ", "")],
        "Fields": default_fields,
        "Values": [],
    }


def save_bejson_atomic(file_path: Path, doc_payload: Dict[str, Any]) -> None:
    """Save BEJSON document atomically via temporary swap."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = file_path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(doc_payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    tmp_path.replace(file_path)


# ── Reminder Engine ─────────────────────────────────────────────────────────
class ReminderEngine:
    """
    Authoritative Reminder Management Engine.
    Handles adding, listing, completing (removing from active), and Termux rendering.
    """

    def __init__(self) -> None:
        self.paths: Dict[str, Path] = resolve_canonical_paths()
        self.ensure_storage_directories()

    def ensure_storage_directories(self) -> None:
        """Ensure directories and registries exist."""
        self.paths["DATA_ROOT"].mkdir(parents=True, exist_ok=True)

        if not self.paths["REMINDERS_REGISTRY"].exists():
            save_bejson_atomic(
                self.paths["REMINDERS_REGISTRY"],
                load_bejson_file(self.paths["REMINDERS_REGISTRY"], REMINDERS_FIELDS, "Reminders Registry Schema"),
            )

        if not self.paths["COMPLETED_REGISTRY"].exists():
            save_bejson_atomic(
                self.paths["COMPLETED_REGISTRY"],
                load_bejson_file(self.paths["COMPLETED_REGISTRY"], COMPLETED_FIELDS, "Completed Reminders Archive Schema"),
            )

    def get_reminders_registry(self) -> Dict[str, Any]:
        return load_bejson_file(self.paths["REMINDERS_REGISTRY"], REMINDERS_FIELDS, "Reminders Registry Schema")

    def get_completed_registry(self) -> Dict[str, Any]:
        return load_bejson_file(self.paths["COMPLETED_REGISTRY"], COMPLETED_FIELDS, "Completed Reminders Archive Schema")

    def list_active(self) -> List[Dict[str, Any]]:
        """Return list of all active reminders."""
        doc = self.get_reminders_registry()
        fmap = compile_bejson_field_map(doc)
        results = []
        for idx, row in enumerate(doc.get("Values", []), 1):
            results.append({
                "index": idx,
                "reminder_id": str(row[fmap.get("reminder_id", 0)]),
                "reminder_text": str(row[fmap.get("reminder_text", 1)]),
                "priority": str(row[fmap.get("priority", 2)]),
                "status": str(row[fmap.get("status", 3)]),
                "creation_date": str(row[fmap.get("creation_date", 4)]),
                "due_date": str(row[fmap.get("due_date", 5)]),
                "tags": str(row[fmap.get("tags", 6)]),
            })
        return results

    def list_completed(self) -> List[Dict[str, Any]]:
        """Return list of all archived completed reminders."""
        doc = self.get_completed_registry()
        fmap = compile_bejson_field_map(doc)
        results = []
        for idx, row in enumerate(doc.get("Values", []), 1):
            results.append({
                "index": idx,
                "reminder_id": str(row[fmap.get("reminder_id", 0)]),
                "reminder_text": str(row[fmap.get("reminder_text", 1)]),
                "priority": str(row[fmap.get("priority", 2)]),
                "creation_date": str(row[fmap.get("creation_date", 3)]),
                "completion_date": str(row[fmap.get("completion_date", 4)]),
                "tags": str(row[fmap.get("tags", 5)]),
            })
        return results

    def add_reminder(
        self,
        text: str,
        priority: str = "normal",
        due_date: str = "",
        tags: str = "",
    ) -> Dict[str, Any]:
        """Add new reminder to active registry."""
        doc = self.get_reminders_registry()
        fmap = compile_bejson_field_map(doc)

        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        stamp_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        reminder_id = f"rem_{stamp_slug}"

        new_row = [
            reminder_id,
            text.strip(),
            priority.lower().strip(),
            "active",
            now_utc,
            due_date.strip(),
            tags.strip(),
        ]

        doc.get("Values", []).append(new_row)
        save_bejson_atomic(self.paths["REMINDERS_REGISTRY"], doc)

        return {
            "reminder_id": reminder_id,
            "reminder_text": text.strip(),
            "priority": priority.lower().strip(),
            "creation_date": now_utc,
            "due_date": due_date.strip(),
            "tags": tags.strip(),
        }

    def complete_reminder(self, target_query: str) -> Optional[Dict[str, Any]]:
        """
        Mark reminder complete: REMOVES it from active registry and archives to completed.
        Query can be 1-based index ('1'), reminder_id ('rem_20261109...'), or substring.
        """
        doc = self.get_reminders_registry()
        fmap = compile_bejson_field_map(doc)
        id_idx = fmap.get("reminder_id", 0)
        text_idx = fmap.get("reminder_text", 1)
        prio_idx = fmap.get("priority", 2)
        date_idx = fmap.get("creation_date", 4)
        tags_idx = fmap.get("tags", 6)

        target_clean = target_query.strip().lower()
        rows = doc.get("Values", [])
        matched_idx: Optional[int] = None
        matched_row: Optional[List[Any]] = None

        # Check numeric index
        if target_clean.isdigit():
            idx_num = int(target_clean) - 1
            if 0 <= idx_num < len(rows):
                matched_idx = idx_num
                matched_row = rows[idx_num]

        # Check reminder_id or text
        if matched_row is None:
            for idx, r in enumerate(rows):
                r_id = str(r[id_idx]).strip().lower()
                r_txt = str(r[text_idx]).strip().lower()
                if target_clean in (r_id, r_txt) or target_clean in r_txt:
                    matched_idx = idx
                    matched_row = r
                    break

        if matched_row is None or matched_idx is None:
            return None

        # Pop from active registry
        removed_row = rows.pop(matched_idx)
        save_bejson_atomic(self.paths["REMINDERS_REGISTRY"], doc)

        # Archive to completed registry
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        completed_doc = self.get_completed_registry()
        comp_fmap = compile_bejson_field_map(completed_doc)

        archive_row = [
            str(removed_row[id_idx]),
            str(removed_row[text_idx]),
            str(removed_row[prio_idx]),
            str(removed_row[date_idx]),
            now_utc,
            str(removed_row[tags_idx]),
        ]
        completed_doc.get("Values", []).append(archive_row)
        save_bejson_atomic(self.paths["COMPLETED_REGISTRY"], completed_doc)

        return {
            "reminder_id": str(removed_row[id_idx]),
            "reminder_text": str(removed_row[text_idx]),
            "priority": str(removed_row[prio_idx]),
            "creation_date": str(removed_row[date_idx]),
            "completion_date": now_utc,
        }

    def delete_reminder(self, target_query: str) -> bool:
        """Permanently delete reminder from active queue without archiving."""
        doc = self.get_reminders_registry()
        fmap = compile_bejson_field_map(doc)
        id_idx = fmap.get("reminder_id", 0)
        text_idx = fmap.get("reminder_text", 1)

        target_clean = target_query.strip().lower()
        rows = doc.get("Values", [])

        if target_clean.isdigit():
            idx_num = int(target_clean) - 1
            if 0 <= idx_num < len(rows):
                rows.pop(idx_num)
                save_bejson_atomic(self.paths["REMINDERS_REGISTRY"], doc)
                return True

        for idx, r in enumerate(rows):
            if target_clean in (str(r[id_idx]).lower(), str(r[text_idx]).lower()):
                rows.pop(idx)
                save_bejson_atomic(self.paths["REMINDERS_REGISTRY"], doc)
                return True

        return False


# ── Terminal Display Formatting (Policy §8.1 Tri-Color) ───────────────────────
def print_termux_launch_banner(engine: ReminderEngine) -> None:
    """
    Render compact, visual active reminders banner for Termux startup.
    Outputs NOTHING if there are no active reminders (zero noise).
    """
    active_items = engine.list_active()
    if not active_items:
        return

    count = len(active_items)
    print("=" * 57)
    print(f" {ACCENT}[REMINDERS]{RESET} {WHITE_BOLD}ACTIVE PENDING TASKS ({count}){RESET}")
    print("-" * 57)
    for item in active_items:
        prio = item["priority"].upper()
        prio_color = ACCENT if prio in ("URGENT", "HIGH") else DIM
        date_short = item["creation_date"][:10]
        text_disp = item["reminder_text"]

        print(f"  {ACCENT}[{item['index']}]{RESET} {prio_color}[{prio}]{RESET} {WHITE_BOLD}{text_disp}{RESET}")
        print(f"      {DIM}Added: {date_short} | ID: {item['reminder_id']}{RESET}")
    print("-" * 57)
    print(f"  {DIM}Complete task via:{RESET} {WHITE_BOLD}remind done <#>{RESET}")
    print("=" * 57)


def print_active_table(active_items: List[Dict[str, Any]]) -> None:
    """Print full active reminders table in 57-column discipline."""
    print(DIVIDER_57)
    print(f" {ACCENT}ACTIVE REMINDERS REGISTRY{RESET}")
    print(SUBDIVIDER_57)
    if not active_items:
        print(f" {DIM}No active reminders.{RESET}")
        print(f" {DIM}Add one with: remind add \"<text>\" [-p urgent|high|normal]{RESET}")
    else:
        print(f" {ACCENT}{'#':<3} {'PRIO':<8} {'DATE':<11} {'REMINDER'}{RESET}")
        print(SUBDIVIDER_57)
        for item in active_items:
            prio = f"[{item['priority'][:6]}]"
            date_str = item["creation_date"][:10]
            txt = item["reminder_text"][:30]
            print(f" {item['index']:<3} {prio:<8} {date_str:<11} {txt}")
    print(DIVIDER_57)


def print_completed_table(completed_items: List[Dict[str, Any]]) -> None:
    """Print archived completed reminders table."""
    print(DIVIDER_57)
    print(f" {ACCENT}COMPLETED REMINDERS ARCHIVE{RESET}")
    print(SUBDIVIDER_57)
    if not completed_items:
        print(f" {DIM}No completed reminders recorded.{RESET}")
    else:
        print(f" {ACCENT}{'#':<3} {'DONE DATE':<11} {'REMINDER'}{RESET}")
        print(SUBDIVIDER_57)
        for item in completed_items:
            date_str = item["completion_date"][:10]
            txt = item["reminder_text"][:38]
            print(f" {item['index']:<3} {date_str:<11} {txt}")
    print(DIVIDER_57)


def print_ai_help() -> None:
    """Print AI-optimized command specification."""
    print(DIVIDER_57)
    print(f" {ACCENT}REMINDER TOOL - AI-OPTIMIZED SPECIFICATION{RESET}")
    print(SUBDIVIDER_57)
    print("USAGE:")
    print("  remind add <text...> [-p <urgent|high|normal|low>]")
    print("  remind done <index|id|term>     (removes & archives)")
    print("  remind rm <index|id>            (deletes permanently)")
    print("  remind list                     (displays active)")
    print("  remind completed                (displays history)")
    print("  remind print / --print-termux   (used by ~/.bashrc)")
    print("  remind --json                   (emits JSON state)")
    print(DIVIDER_57)


# ── Main Entrypoint ──────────────────────────────────────────────────────────
def main() -> int:
    """Main CLI routine."""
    engine = ReminderEngine()
    arguments: List[str] = sys.argv[1:]

    if not arguments:
        items = engine.list_active()
        if items:
            print_active_table(items)
        else:
            print_ai_help()
        return 0

    first_arg: str = arguments[0].strip().lower()

    # Universal Help & AI Context
    if first_arg in ("-h", "--help", "help"):
        print_ai_help()
        return 0

    if first_arg in ("--json", "--agent-context"):
        payload = {
            "active_reminders": engine.list_active(),
            "completed_reminders": engine.list_completed(),
            "paths": {k: str(v) for k, v in engine.paths.items()},
        }
        print(json.dumps(payload, indent=2))
        return 0

    # Termux startup hook
    if first_arg in ("--print-termux", "print", "launch"):
        print_termux_launch_banner(engine)
        return 0

    # Add reminder: 'add' or 'new'
    if first_arg in ("add", "new", "create"):
        sub_args = arguments[1:]
        if not sub_args:
            print(f"{ACCENT}[✗] Error:{RESET} Reminder text required. Example: remind add Update documentation", file=sys.stderr)
            return 1

        priority = "normal"
        tags = ""
        due_date = ""

        # Parse flags if present
        text_tokens: List[str] = []
        i = 0
        while i < len(sub_args):
            tok = sub_args[i]
            if tok in ("-p", "--priority") and i + 1 < len(sub_args):
                priority = sub_args[i + 1]
                i += 2
            elif tok in ("-t", "--tags") and i + 1 < len(sub_args):
                tags = sub_args[i + 1]
                i += 2
            elif tok in ("-d", "--due") and i + 1 < len(sub_args):
                due_date = sub_args[i + 1]
                i += 2
            else:
                text_tokens.append(tok)
                i += 1

        reminder_text = " ".join(text_tokens).strip()
        if not reminder_text:
            print(f"{ACCENT}[✗] Error:{RESET} Reminder text cannot be empty.", file=sys.stderr)
            return 1

        created = engine.add_reminder(reminder_text, priority=priority, due_date=due_date, tags=tags)
        print(DIVIDER_57)
        print(f" {ACCENT}[✓] REMINDER ADDED{RESET}")
        print(SUBDIVIDER_57)
        print(f" {ACCENT}Text:{RESET}     {created['reminder_text']}")
        print(f" {ACCENT}Priority:{RESET} [{created['priority'].upper()}]")
        print(f" {ACCENT}ID:{RESET}       {created['reminder_id']}")
        print(DIVIDER_57)
        return 0

    # Complete reminder: 'done', 'complete', 'finish'
    if first_arg in ("done", "complete", "finish", "check"):
        if len(arguments) < 2:
            print(f"{ACCENT}[✗] Error:{RESET} Target identifier or index required: remind done <index|id>", file=sys.stderr)
            return 1
        target = arguments[1]
        completed = engine.complete_reminder(target)
        if completed:
            print(DIVIDER_57)
            print(f" {ACCENT}[✓] REMINDER COMPLETED & REMOVED{RESET}")
            print(SUBDIVIDER_57)
            print(f" {ACCENT}Text:{RESET}      {completed['reminder_text']}")
            print(f" {ACCENT}Completed:{RESET} {completed['completion_date']}")
            print(SUBDIVIDER_57)
            print(f" {DIM}Removed from active queue; archived in completed_reminders.104a.bejson.{RESET}")
            print(DIVIDER_57)
            return 0
        else:
            print(f"{ACCENT}[✗] Error:{RESET} Reminder '{target}' not found.", file=sys.stderr)
            return 1

    # Remove reminder permanently: 'rm', 'del', 'delete'
    if first_arg in ("rm", "del", "delete", "remove"):
        if len(arguments) < 2:
            print(f"{ACCENT}[✗] Error:{RESET} Target required: remind rm <index|id>", file=sys.stderr)
            return 1
        target = arguments[1]
        success = engine.delete_reminder(target)
        if success:
            print(f"{ACCENT}[✓] Reminder '{target}' permanently deleted.{RESET}")
            return 0
        else:
            print(f"{ACCENT}[✗] Error:{RESET} Reminder '{target}' not found.", file=sys.stderr)
            return 1

    # List active
    if first_arg in ("list", "ls", "active"):
        print_active_table(engine.list_active())
        return 0

    # List completed
    if first_arg in ("completed", "history", "archive", "log"):
        print_completed_table(engine.list_completed())
        return 0

    # Fallback: treat unrecognized arguments as text to add
    # e.g. 'remind "buy milk"' or 'remind buy milk'
    reminder_text = " ".join(arguments).strip()
    created = engine.add_reminder(reminder_text, priority="normal")
    print(DIVIDER_57)
    print(f" {ACCENT}[✓] REMINDER ADDED{RESET}")
    print(SUBDIVIDER_57)
    print(f" {ACCENT}Text:{RESET}     {created['reminder_text']}")
    print(f" {ACCENT}Priority:{RESET} [{created['priority'].upper()}]")
    print(f" {ACCENT}ID:{RESET}       {created['reminder_id']}")
    print(DIVIDER_57)
    return 0


if __name__ == "__main__":
    sys.exit(main())
