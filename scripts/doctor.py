from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values
    for raw in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def present(env: dict[str, str], key: str) -> bool:
    value = env.get(key, "").strip()
    return bool(value) and value.lower() not in {"changeme", "change-me", "your_token", "your_key"}


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def health() -> tuple[bool, str]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2) as response:
            body = json.loads(response.read().decode("utf-8"))
            return response.status == 200, f"HTTP {response.status} · {body.get('service', 'nexus-ai')} {body.get('version', '')}".strip()
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return False, f"not reachable ({type(exc).__name__})"


def status(label: str, ok: bool, detail: str) -> None:
    tag = "READY" if ok else "NEEDS SETUP"
    print(f"[{tag:11}] {label:<21} {detail}")


def main() -> int:
    env = load_env()
    print("NEXUS CONNECTION DOCTOR — SAFE REPORT")
    print("No secret values are printed. You can send this output for debugging.\n")

    if not ENV_FILE.exists():
        print("[INFO] .env is missing; safe built-in demo defaults are still available.\n")

    backend_ok, backend_detail = health()
    status("Backend", backend_ok, backend_detail)
    status("Python", sys.version_info >= (3, 11), sys.version.split()[0])
    status("Node", shutil.which("node") is not None, shutil.which("node") or "not found")

    print("\nPRIMARY SIH SOURCE READINESS")
    raw_channels = env.get("TELEGRAM_PUBLIC_CHANNELS", "").strip() or "NexusSIHDemo"
    channels = [item.strip().lstrip("@").strip("/") for item in raw_channels.replace(";", ",").split(",") if item.strip()]
    status(
        "Telegram monitored",
        bool(channels),
        f"{len(channels)} public channel(s): {', '.join(channels[:5])} · automatic Fresh Search" if channels else "no monitored channels configured",
    )
    status(
        "Telegram public manual",
        True,
        "zero-key public-preview path available for a supplied public channel username",
    )
    status(
        "Telegram Bot API",
        present(env, "TELEGRAM_BOT_TOKEN"),
        "bot token configured for authorized live channel/chat updates" if present(env, "TELEGRAM_BOT_TOKEN") else "optional; zero-key monitored-channel mode already works for the SIH demo",
    )
    status(
        "X public URL oEmbed",
        True,
        "FREE official no-auth path ready; paste public X Post URL(s) into Free Source Lab",
    )
    status(
        "X official search",
        present(env, "X_BEARER_TOKEN"),
        "X_BEARER_TOKEN configured" if present(env, "X_BEARER_TOKEN") else "optional pay-per-use search not configured; free global X search is not claimed",
    )
    status(
        "X RSS/Atom bridge",
        present(env, "X_PUBLIC_RSS_URL_TEMPLATE"),
        "permitted bridge template configured" if present(env, "X_PUBLIC_RSS_URL_TEMPLATE") else "optional; explicit X Post URL oEmbed still works without it",
    )

    print("\nSECONDARY SOURCE READINESS")
    status(
        "YouTube zero-key",
        module_available("yt_dlp"),
        "yt-dlp module installed" if module_available("yt_dlp") else "backend dependencies need yt-dlp",
    )
    status(
        "YouTube official",
        present(env, "YOUTUBE_API_KEY"),
        "YOUTUBE_API_KEY configured" if present(env, "YOUTUBE_API_KEY") else "optional: add YOUTUBE_API_KEY",
    )
    status(
        "Instagram public",
        module_available("instaloader"),
        "Instaloader fallback installed; runtime access still depends on Instagram" if module_available("instaloader") else "backend dependencies need Instaloader",
    )
    ig_official = present(env, "META_ACCESS_TOKEN") and present(env, "META_INSTAGRAM_ACCOUNT_ID")
    status(
        "Instagram Meta",
        ig_official,
        "Meta token + Instagram account ID configured" if ig_official else "set META_ACCESS_TOKEN + META_INSTAGRAM_ACCOUNT_ID after Meta authorization",
    )
    fb_official = present(env, "META_ACCESS_TOKEN") and present(env, "META_FACEBOOK_PAGE_ID")
    status(
        "Facebook Meta",
        fb_official,
        "Meta token + Facebook Page ID configured" if fb_official else "optional: set META_ACCESS_TOKEN + META_FACEBOOK_PAGE_ID",
    )
    status("Bluesky", True, "zero-key public AT Protocol path implemented; network dependent")
    status("Reddit", True, "public low-volume path implemented; may be 403/429 depending on network")
    status(
        "Mastodon",
        present(env, "MASTODON_BASE_URL"),
        f"instance configured: {env.get('MASTODON_BASE_URL', '')}" if present(env, "MASTODON_BASE_URL") else "default instance is mastodon.social",
    )

    print("\nWHAT TO SEND FOR DEBUGGING")
    print("1. This doctor output.")
    print("2. Screenshot of Posts / Explorer and Connection Center.")
    print("3. The exact SEARCH QUERY you tested.")
    print("4. Telegram: public channel usernames you want monitored (public names are safe to share).")
    print("5. X: one or more PUBLIC Post URLs you tested (public URLs are safe to share).")
    print("6. API-provider error text/screenshots with all tokens and keys hidden.")
    print("7. Never send bearer tokens, bot tokens, API secrets, passwords, cookies, session files, or .env contents.")

    if not backend_ok:
        print("\nNEXT: start NEXUS with scripts\\start_demo.bat, then run this doctor again.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
