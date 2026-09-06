from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend-ai"))

from app.config import get_settings  # noqa: E402


async def main() -> None:
    settings = get_settings()
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise SystemExit("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env first. Get them from Telegram's official developer portal.")
    try:
        from telethon import TelegramClient
    except ImportError as exc:
        raise SystemExit("Telethon is not installed. Run scripts/setup_windows.bat or pip install -r backend-ai/requirements.txt") from exc

    client = TelegramClient(settings.telegram_session_name, int(settings.telegram_api_id), settings.telegram_api_hash)
    print("Authorizing the local Telegram MTProto session. Telegram may ask for your phone number, login code and 2FA password.")
    await client.start()
    me = await client.get_me()
    print(f"Session authorized for Telegram account id={getattr(me, 'id', 'unknown')}. You can now enable TELEGRAM_MTPROTO_ENABLED=true.")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
