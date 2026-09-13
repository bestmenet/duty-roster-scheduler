#!/usr/bin/env python3
"""Self-cleanup for the disposable duty-roster-scheduler skill.

The script removes only the local `duty-roster-scheduler` installation. It never
removes generated roster files, input spreadsheets, or the remote GitHub repo.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

SKILL_NAME = "duty-roster-scheduler"


def run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 90) -> dict:
    try:
        cp = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "cmd": cmd,
            "returncode": cp.returncode,
            "stdout": cp.stdout[-4000:],
            "stderr": cp.stderr[-4000:],
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {"cmd": cmd, "returncode": 127, "stdout": "", "stderr": str(exc)}


def contains_skill(text: str, name: str) -> bool:
    return name.casefold() in (text or "").casefold()


def remove_exact_root(root: Path, name: str) -> tuple[bool, str]:
    """Fallback: remove only an exact local skill directory/symlink.

    A git checkout is deliberately protected from fallback deletion; in that
    case only Skills CLI removal is allowed.
    """
    root = root.expanduser()
    if root.name != name:
        return False, f"refused fallback deletion: unexpected root name {root.name!r}"
    if not root.exists() and not root.is_symlink():
        return True, "skill root already absent"
    if (root / ".git").exists():
        return False, "refused fallback deletion of a git checkout"
    try:
        if root.is_symlink() or root.is_file():
            root.unlink()
        else:
            shutil.rmtree(root)
        return (not root.exists() and not root.is_symlink()), "removed exact local skill root"
    except OSError as exc:
        return False, f"fallback deletion failed: {exc}"


def cleanup(skill_name: str, skill_root: Path, project_dir: Path | None, dry_run: bool = False) -> dict:
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    result = {
        "skill": skill_name,
        "skill_root": str(skill_root),
        "project_dir": str(project_dir) if project_dir else None,
        "dry_run": dry_run,
        "commands": [],
        "fallback": None,
        "verified_removed": False,
    }

    if dry_run:
        result["npx"] = npx
        result["planned_commands"] = [
            [npx or "npx", "--yes", "skills", "remove", skill_name, "-g", "-y"],
            [npx or "npx", "--yes", "skills", "remove", skill_name, "-y"],
            [npx or "npx", "--yes", "skills", "list", "-g"],
            [npx or "npx", "--yes", "skills", "list"],
        ]
        return result

    # First use the official Skills CLI. Try global scope, then project scope.
    if npx:
        result["commands"].append(
            run_cmd([npx, "--yes", "skills", "remove", skill_name, "-g", "-y"], cwd=Path(tempfile.gettempdir()))
        )
        if project_dir and project_dir.exists():
            result["commands"].append(
                run_cmd([npx, "--yes", "skills", "remove", skill_name, "-y"], cwd=project_dir)
            )

        checks = [run_cmd([npx, "--yes", "skills", "list", "-g"], cwd=Path(tempfile.gettempdir()))]
        if project_dir and project_dir.exists():
            checks.append(run_cmd([npx, "--yes", "skills", "list"], cwd=project_dir))
        result["commands"].extend(checks)
        listed = any(
            c["returncode"] == 0 and contains_skill(c["stdout"] + c["stderr"], skill_name)
            for c in checks
        )
        root_gone = not skill_root.exists() and not skill_root.is_symlink()
        if not listed and root_gone:
            result["verified_removed"] = True
            return result

    # Stronger execution layer: if CLI removal is unavailable/incomplete, delete
    # only this exact local package. Never touch arbitrary directories.
    ok, message = remove_exact_root(skill_root, skill_name)
    result["fallback"] = {"ok": ok, "message": message}
    result["verified_removed"] = ok and not skill_root.exists() and not skill_root.is_symlink()
    return result


def main() -> int:
    p = argparse.ArgumentParser(description="Remove the disposable duty-roster-scheduler skill after use.")
    p.add_argument("--skill-name", default=SKILL_NAME)
    p.add_argument("--skill-root", type=Path, required=True)
    p.add_argument("--project-dir", type=Path)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    result = cleanup(args.skill_name, args.skill_root, args.project_dir, args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.dry_run:
        return 0
    return 0 if result.get("verified_removed") else 4


if __name__ == "__main__":
    raise SystemExit(main())
