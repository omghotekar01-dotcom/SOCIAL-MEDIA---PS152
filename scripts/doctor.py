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
    tag = "READY" if ok else "OPTIONAL/SETUP"
    print(f"[{tag:14}] {label:<24} {detail}")


def main() -> int:
    env = load_env()
    print("NEXUS CONNECTION DOCTOR — SAFE REPORT")
    print("No secret values are printed. You can send this output for debugging.\n")

    if not ENV_FILE.exists():
        print("[INFO] .env is missing; built-in zero-key demo defaults are still available.\n")

    backend_ok, backend_detail = health()
    status("Backend", backend_ok, backend_detail)
    status("Python", sys.version_info >= (3, 11), sys.version.split()[0])
    status("Node", shutil.which("node") is not None, shutil.which("node") or "not found")

    print("\nPRIMARY / CONTROLLED SOURCES")
    raw_channels = env.get("TELEGRAM_PUBLIC_CHANNELS", "").strip() or "NexusSIHDemo"
    channels = [item.strip().lstrip("@").strip("/") for item in raw_channels.replace(";", ",").split(",") if item.strip()]
    status("Telegram monitored", bool(channels), f"{len(channels)} public channel(s): {', '.join(channels[:5])} · automatic query filtering")
    status("Telegram public manual", True, "zero-key public-preview path implemented for supplied public channels")
    status("Telegram Bot API", present(env, "TELEGRAM_BOT_TOKEN"), "authorized bot live updates configured" if present(env, "TELEGRAM_BOT_TOKEN") else "optional; public monitored-channel path still available")

    status("X public URL oEmbed", True, "official no-auth explicit public Post URL path implemented")
    status("X official search", present(env, "X_BEARER_TOKEN"), "authorized recent-search configured" if present(env, "X_BEARER_TOKEN") else "requires X developer access/credits; free global keyword search is not claimed")
    status("X permitted bridge", present(env, "X_PUBLIC_RSS_URL_TEMPLATE"), "configured RSS/Atom bridge available" if present(env, "X_PUBLIC_RSS_URL_TEMPLATE") else "optional; X URL oEmbed remains available")

    print("\nSEARCH / DISCOVERY SOURCES")
    status("YouTube zero-key", module_available("yt_dlp"), "yt-dlp public video metadata installed" if module_available("yt_dlp") else "install backend dependencies")
    status("YouTube Data API", present(env, "YOUTUBE_API_KEY"), "official video/comment path configured" if present(env, "YOUTUBE_API_KEY") else "optional; zero-key mode still available")
    status("Bluesky", True, "zero-key public AT Protocol search implemented; runtime network dependent")

    reddit_oauth = present(env, "REDDIT_CLIENT_ID") and present(env, "REDDIT_CLIENT_SECRET")
    status("Reddit public", True, "low-volume public search attempted where permitted")
    status("Reddit authorized", reddit_oauth, "approved OAuth credentials configured; NEXUS tries this before public fallback" if reddit_oauth else "optional; provider/network policy can restrict anonymous Reddit access")

    preferred_mastodon = env.get("MASTODON_BASE_URL", "").strip() or "https://mastodon.social"
    fallback_mastodon = env.get("MASTODON_FALLBACK_BASE_URLS", "").strip() or "https://mastodon.online,https://fosstodon.org"
    fallback_count = len([item for item in fallback_mastodon.replace(";", ",").split(",") if item.strip()])
    status("Mastodon resilient", True, f"preferred {preferred_mastodon} + {fallback_count} configured fallback instance(s)")

    print("\nMETA / PROFILE SOURCES")
    instagram_bridge = present(env, "INSTAGRAM_PUBLIC_RSS_URL_TEMPLATE")
    status("Instagram bridge", instagram_bridge, "permitted public bridge configured and tried first" if instagram_bridge else "optional")
    status("Instagram public", module_available("instaloader"), "public-profile fallback installed; provider restrictions still apply" if module_available("instaloader") else "install backend dependencies")
    ig_official = present(env, "META_ACCESS_TOKEN") and present(env, "META_INSTAGRAM_ACCOUNT_ID")
    status("Instagram Meta", ig_official, "authorized Meta account path configured" if ig_official else "requires Meta authorization + Instagram professional account ID")
    fb_official = present(env, "META_ACCESS_TOKEN") and present(env, "META_FACEBOOK_PAGE_ID")
    status("Facebook Meta", fb_official, "authorized Facebook Page path configured" if fb_official else "requires Meta authorization + Page ID")

    print("\nALWAYS AVAILABLE FALLBACK")
    status("IMPORT / REPLAY", True, "deterministic import/replay works offline and remains explicitly labelled")

    print("\nWHAT TO SEND FOR DEBUGGING")
    print("1. This doctor output.")
    print("2. The PRE-FLIGHT result block.")
    print("3. Screenshot of the affected tab / Social Source Lab.")
    print("4. Exact public search query tested.")
    print("5. Public Telegram usernames / public X Post URLs are safe to share.")
    print("6. Provider error messages are safe after hiding tokens/keys.")
    print("7. Never send bearer tokens, bot tokens, client secrets, passwords, cookies, session files, or .env contents.")

    if not backend_ok:
        print("\nNEXT: start NEXUS with scripts\\start_demo.bat, then run this doctor again.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
