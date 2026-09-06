from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "backend-ai/app/main.py",
    "backend-ai/app/analytics.py",
    "backend-ai/app/stable_alerts.py",
    "backend-ai/app/connectors.py",
    "backend-ai/app/free_connectors.py",
    "backend-ai/app/youtube_official.py",
    "backend-ai/app/meta_discovery.py",
    "backend-ai/app/certificates.py",
    "backend-ai/app/schemas.py",
    "backend-ai/requirements.txt",
    "backend-ai/tests/test_core.py",
    "backend-ai/tests/test_free_connectors.py",
    "backend-ai/tests/test_api_contracts.py",
    "backend-ai/tests/test_telegram_polling.py",
    "backend-ai/tests/test_youtube_official.py",
    "backend-ai/tests/test_meta_discovery.py",
    "backend-ai/tests/test_stable_alerts.py",
    "backend-ai/tests/test_export_converter.py",
    "frontend/src/App.tsx",
    "frontend/src/ConnectionCenter.tsx",
    "frontend/src/FreeConnectorPanel.tsx",
    "frontend/src/PostExplorer.tsx",
    "frontend/src/post-explorer.css",
    "frontend/src/api.ts",
    "frontend/src/main.tsx",
    "frontend/package.json",
    "backend-java/pom.xml",
    "backend-java/src/main/java/in/sih/nexus/controller/GatewayController.java",
    "scripts/start_demo.bat",
    "scripts/start_full.bat",
    "scripts/seed_demo.py",
    "scripts/doctor.py",
    "scripts/convert_social_export.py",
    "data/demo/sample_public_export.csv",
    "data/demo/sample_import.json",
    "docs/FREE_SOURCE_MATRIX.md",
    "docs/JURY_DEMO_5_MIN.md",
    "docs/FINAL_READINESS_CHECKLIST.md",
    "docs/PS26152_TRACEABILITY.md",
    "docs/WHAT_I_NEED_FROM_YOU.md",
    "docs/PRODUCTION_GAP_AUDIT.md",
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


def check_node_version(node: str) -> tuple[bool, str]:
    code, output = run([node, "--version"], ROOT)
    raw = output.splitlines()[0].strip() if output else ""
    if code != 0:
        return False, raw or "unable to execute node --version"
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+).*", raw)
    if not match:
        return False, raw or "unrecognized Node version"
    major, minor, _patch = map(int, match.groups())
    supported = (major == 20 and minor >= 19) or (major == 22 and minor >= 12) or major > 22
    return supported, raw


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

    syntax_failures = 0
    for root_dir in (ROOT / "backend-ai", ROOT / "scripts"):
        for path in sorted(root_dir.rglob("*.py")):
            if any(part in {".venv", "venv", "__pycache__"} for part in path.parts):
                continue
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                fail(f"Python syntax: {path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")
                failures += 1
                syntax_failures += 1
    if syntax_failures == 0:
        ok("Python source, tests and scripts parse successfully")

    package_path = ROOT / "frontend" / "package.json"
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
        if "build" in package.get("scripts", {}):
            ok("frontend package.json is valid and has build script")
        else:
            fail("frontend package.json has no build script")
            failures += 1
        if any(value == "latest" for section in ("dependencies", "devDependencies") for value in package.get(section, {}).values()):
            fail("frontend package.json still contains moving 'latest' dependencies")
            failures += 1
        else:
            ok("frontend top-level dependencies are version-pinned")
    except Exception as exc:
        fail(f"frontend package.json invalid: {exc}")
        failures += 1

    required_env_keys = {
        "NEXUS_DB_URL",
        "X_BEARER_TOKEN",
        "TELEGRAM_BOT_TOKEN",
        "YOUTUBE_API_KEY",
        "META_ACCESS_TOKEN",
        "META_INSTAGRAM_ACCOUNT_ID",
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

    python = sys.executable or shutil.which("python") or shutil.which("python3")
    if python:
        ok(f"Python active interpreter: {python}")
        backend = ROOT / "backend-ai"
        try:
            import pytest  # noqa: F401
        except Exception:
            warn("pytest not installed in this interpreter; install backend requirements plus pytest")
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

    node = shutil.which("node")
    if not node:
        fail("Node.js not found; Vite 8 requires Node 20.19+ or 22.12+")
        failures += 1
    else:
        supported, version = check_node_version(node)
        if supported:
            ok(f"Node runtime compatible with Vite 8: {version}")
        else:
            fail(f"Unsupported Node runtime {version}; install Node 20.19+ or 22.12+")
            failures += 1

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
        fail("npm not found")
        failures += 1

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
