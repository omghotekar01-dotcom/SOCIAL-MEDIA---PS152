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
    "START_HERE.md",
    "backend-ai/app/main.py",
    "backend-ai/app/analytics.py",
    "backend-ai/app/stable_alerts.py",
    "backend-ai/app/connectors.py",
    "backend-ai/app/free_connectors.py",
    "backend-ai/app/priority_free_connectors.py",
    "backend-ai/app/resilient_connectors.py",
    "backend-ai/app/youtube_official.py",
    "backend-ai/app/meta_discovery.py",
    "backend-ai/app/certificates.py",
    "backend-ai/app/schemas.py",
    "backend-ai/requirements.txt",
    "backend-ai/tests/test_core.py",
    "backend-ai/tests/test_free_connectors.py",
    "backend-ai/tests/test_priority_free_connectors.py",
    "backend-ai/tests/test_resilient_connectors.py",
    "backend-ai/tests/test_api_contracts.py",
    "backend-ai/tests/test_telegram_polling.py",
    "backend-ai/tests/test_youtube_official.py",
    "backend-ai/tests/test_meta_discovery.py",
    "backend-ai/tests/test_stable_alerts.py",
    "backend-ai/tests/test_export_converter.py",
    "frontend/public/nexus.svg",
    "frontend/src/App.tsx",
    "frontend/src/AppPro.tsx",
    "frontend/src/AppErrorBoundary.tsx",
    "frontend/src/ConnectionCenter.tsx",
    "frontend/src/FreeConnectorPanel.tsx",
    "frontend/src/PostExplorer.tsx",
    "frontend/src/TimelinePro.tsx",
    "frontend/src/NetworkPro.tsx",
    "frontend/src/EvidenceLedger.tsx",
    "frontend/src/ThemeController.tsx",
    "frontend/src/styles.css",
    "frontend/src/post-explorer.css",
    "frontend/src/premium-ui.css",
    "frontend/src/post-toolbar.css",
    "frontend/src/command-center.css",
    "frontend/src/responsive-pro.css",
    "frontend/src/resilience.css",
    "frontend/src/brand-polish.css",
    "frontend/src/product-polish.css",
    "frontend/src/analysis-pro.css",
    "frontend/src/source-pro.css",
    "frontend/src/api.ts",
    "frontend/src/main.tsx",
    "frontend/package.json",
    "backend-java/pom.xml",
    "backend-java/src/main/java/in/sih/nexus/controller/GatewayController.java",
    "scripts/start_demo.bat",
    "scripts/start_full.bat",
    "scripts/export_submission.bat",
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
    "docs/UI_PRODUCT_GUIDE.md",
    "prompts/MASTER_SUPER_PROMPT.md",
]

UI_CONTRACTS: dict[str, tuple[str, ...]] = {
    "frontend/src/AppPro.tsx": (
        "TimelinePro",
        "NetworkPro",
        "EvidenceLedger",
        "Fresh Search",
        "LIVE / REPLAY / IMPORT disclosed",
    ),
    "frontend/src/TimelinePro.tsx": (
        "ComposedChart",
        "bucketEvents",
        "Conversation volume & sentiment movement",
        "No timeline evidence yet",
    ),
    "frontend/src/NetworkPro.tsx": (
        "Community & influence map",
        "Node inspector",
        "High Reach Node",
        "Bridge Node",
    ),
    "frontend/src/EvidenceLedger.tsx": (
        "Export visible CSV",
        "Search text, author, hashtag",
        "LIVE",
        "IMPORT",
    ),
    "frontend/src/PostExplorer.tsx": (
        "ModeFilter",
        "post-local-search",
        "official_x_oembed",
        "Newest first",
    ),
    "frontend/src/ThemeController.tsx": (
        "nexus-theme",
        "dataset.theme",
        "theme-color",
    ),
    "frontend/src/main.tsx": (
        "AppPro",
        "AppErrorBoundary",
        "nexus:workspace-updated",
        "analysis-pro.css",
        "source-pro.css",
    ),
    "frontend/src/FreeConnectorPanel.tsx": (
        "Enrich All Available",
        "xOfficial",
        "instagramMeta",
        "facebookMeta",
        "nexus:workspace-updated",
    ),
    "frontend/src/ConnectionCenter.tsx": (
        "ConnectionFilter",
        "High priority",
        "aria-modal",
    ),
}

BACKEND_CONTRACTS: dict[str, tuple[str, ...]] = {
    "backend-ai/app/__init__.py": (
        "reddit_resilient_search",
        "mastodon_resilient_search",
        "instagram_resilient_profile",
        "telegram_monitored_search",
        "x_oembed_or_bridge",
    ),
    "backend-ai/app/resilient_connectors.py": (
        "_reddit_oauth_search",
        "reddit_resilient_search",
        "mastodon_resilient_search",
        "instagram_resilient_profile",
    ),
}


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


def check_contracts(group: str, contracts: dict[str, tuple[str, ...]]) -> int:
    failures = 0
    for rel, required_tokens in contracts.items():
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        missing = [token for token in required_tokens if token not in text]
        if missing:
            fail(f"{group} contract missing in {rel}: {', '.join(missing)}")
            failures += 1
        else:
            ok(f"{group} contract: {rel}")
    return failures


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

    failures += check_contracts("modern UI", UI_CONTRACTS)
    failures += check_contracts("connector resilience", BACKEND_CONTRACTS)

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
        scripts = package.get("scripts", {})
        missing_scripts = sorted({"build", "typecheck"} - set(scripts))
        if missing_scripts:
            fail("frontend package.json missing scripts: " + ", ".join(missing_scripts))
            failures += 1
        else:
            ok("frontend package.json has build + typecheck scripts")
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
        "X_PUBLIC_RSS_URL_TEMPLATE",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_PUBLIC_CHANNELS",
        "YOUTUBE_API_KEY",
        "META_ACCESS_TOKEN",
        "META_INSTAGRAM_ACCOUNT_ID",
        "META_FACEBOOK_PAGE_ID",
        "INSTAGRAM_PUBLIC_RSS_URL_TEMPLATE",
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "MASTODON_BASE_URL",
        "MASTODON_FALLBACK_BASE_URLS",
    }
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8") if (ROOT / ".env.example").exists() else ""
    missing_env = sorted(key for key in required_env_keys if f"{key}=" not in env_example)
    if missing_env:
        fail(".env.example missing: " + ", ".join(missing_env))
        failures += 1
    else:
        ok(".env.example exposes official + resilient free/public connector configuration")

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
                print(output[-5000:])
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
            code, output = run([npm, "run", "typecheck"], ROOT / "frontend")
            if code == 0:
                ok("frontend TypeScript typecheck")
            else:
                fail("frontend TypeScript typecheck failed")
                print(output[-5000:])
                failures += 1
            code, output = run([npm, "run", "build"], ROOT / "frontend")
            if code == 0:
                ok("frontend production build")
            else:
                fail("frontend production build failed")
                print(output[-5000:])
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
