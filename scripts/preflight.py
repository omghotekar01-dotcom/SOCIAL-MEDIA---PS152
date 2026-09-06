from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "backend-ai/app/main.py",
    "backend-ai/app/analytics.py",
    "backend-ai/app/connectors.py",
    "backend-ai/app/free_connectors.py",
    "backend-ai/app/certificates.py",
    "backend-ai/app/schemas.py",
    "backend-ai/requirements.txt",
    "frontend/src/App.tsx",
    "frontend/src/FreeConnectorPanel.tsx",
    "frontend/src/api.ts",
    "frontend/package.json",
    "backend-java/pom.xml",
    "scripts/start_demo.bat",
    "prompts/MASTER_SUPER_PROMPT.md",
]


def ok(message: str) -> None:
    print(f"[PASS] {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def fail(message: str) -> None:
    print(f"[FAIL] {message}")


def run(command: list[str], cwd: Path) -> tuple[int, str]:
    try:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=180)
        output = (result.stdout + "\n" + result.stderr).strip()
        return result.returncode, output
    except Exception as exc:
        return 99, str(exc)


def main() -> int:
    failures = 0
    print("NEXUS / SIH26152 PRE-FLIGHT\n")

    for rel in REQUIRED:
        path = ROOT / rel
        if path.exists():
            ok(f"required file: {rel}")
        else:
            fail(f"missing required file: {rel}")
            failures += 1

    for path in sorted((ROOT / "backend-ai").rglob("*.py")):
        if any(part in {".venv", "venv", "__pycache__"} for part in path.parts):
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            fail(f"Python syntax: {path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")
            failures += 1
    if failures == 0:
        ok("Python source files parse successfully")

    package_path = ROOT / "frontend" / "package.json"
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
        if "build" in package.get("scripts", {}):
            ok("frontend package.json is valid and has build script")
        else:
            fail("frontend package.json has no build script")
            failures += 1
    except Exception as exc:
        fail(f"frontend package.json invalid: {exc}")
        failures += 1

    required_env_keys = {
        "NEXUS_DB_URL",
        "X_BEARER_TOKEN",
        "TELEGRAM_BOT_TOKEN",
        "YOUTUBE_API_KEY",
        "META_ACCESS_TOKEN",
        "X_PUBLIC_RSS_URL_TEMPLATE",
        "MASTODON_BASE_URL",
    }
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8") if (ROOT / ".env.example").exists() else ""
    missing_env = sorted(key for key in required_env_keys if f"{key}=" not in env_example)
    if missing_env:
        fail(".env.example missing: " + ", ".join(missing_env))
        failures += 1
    else:
        ok(".env.example exposes official + free/public connector configuration")

    python = shutil.which("python") or shutil.which("python3")
    if python:
        ok(f"Python available: {python}")
        backend = ROOT / "backend-ai"
        # Full tests are optional here because dependency installation may not have happened yet.
        try:
            import pytest  # noqa: F401
        except Exception:
            warn("pytest not installed in this interpreter; run backend requirements then pytest -q")
        else:
            code, output = run([python, "-m", "pytest", "-q"], backend)
            if code == 0:
                ok("backend pytest suite")
            else:
                fail("backend pytest suite failed")
                print(output[-4000:])
                failures += 1
    else:
        warn("Python executable not found")

    npm = shutil.which("npm")
    if npm:
        ok(f"npm available: {npm}")
        if (ROOT / "frontend" / "node_modules").exists():
            code, output = run([npm, "run", "build"], ROOT / "frontend")
            if code == 0:
                ok("frontend production build")
            else:
                fail("frontend production build failed")
                print(output[-4000:])
                failures += 1
        else:
            warn("frontend/node_modules absent; run npm install before production build")
    else:
        warn("npm not found")

    mvn = shutil.which("mvn")
    if mvn:
        ok(f"Maven available: {mvn}")
    else:
        warn("Maven not found; only needed for optional Spring gateway")

    print("\nRESULT:")
    if failures:
        print(f"PRE-FLIGHT FAILED with {failures} blocking issue(s).")
        return 1
    print("PRE-FLIGHT PASSED. Remaining warnings are environment/dependency setup items, not source-structure failures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
