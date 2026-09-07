from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(ROOT_DIR / ".env"), str(ROOT_DIR / "backend-ai" / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    nexus_env: str = "demo"
    nexus_db_url: str = "sqlite:///./nexus.db"
    nexus_api_host: str = "127.0.0.1"
    nexus_api_port: int = 8000
    nexus_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"
    k_anon_min_group: int = 10
    pseudonym_salt: str = "change-me-for-non-demo-use"
    public_http_timeout_seconds: int = 15

    x_bearer_token: str = ""
    x_max_results_per_run: int = 50
    x_max_pages_per_run: int = 2
    x_request_timeout_seconds: int = 15
    x_public_rss_url_template: str = ""

    telegram_bot_token: str = ""
    telegram_allowed_chat_ids: str = ""
    telegram_public_channels: str = ""
    telegram_poll_timeout_seconds: int = 5
    telegram_mtproto_enabled: bool = False
    telegram_api_id: str = ""
    telegram_api_hash: str = ""
    telegram_session_name: str = "nexus_sih"

    youtube_api_key: str = ""
    youtube_max_videos_per_run: int = 5
    youtube_max_comments_per_video: int = 30

    meta_graph_version: str = "v23.0"
    meta_access_token: str = ""
    meta_instagram_account_id: str = ""
    meta_facebook_page_id: str = ""
    instagram_public_rss_url_template: str = ""

    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "NEXUS-SIH26152/0.4"
    reddit_enabled: bool = True

    mastodon_base_url: str = "https://mastodon.social"

    nexus_enable_transformers: bool = False
    nexus_sentiment_model: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    nexus_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    nexus_cluster_similarity_threshold: float = 0.42
    nexus_alert_trend_threshold: float = 0.62

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.nexus_cors_origins.split(",") if item.strip()]

    @property
    def telegram_allowed_chat_id_set(self) -> set[int]:
        values: set[int] = set()
        for raw in self.telegram_allowed_chat_ids.split(","):
            raw = raw.strip()
            if not raw:
                continue
            try:
                values.add(int(raw))
            except ValueError:
                continue
        return values

    @property
    def telegram_public_channel_list(self) -> list[str]:
        values: list[str] = []
        for raw in self.telegram_public_channels.replace(";", ",").split(","):
            clean = raw.strip().lstrip("@").strip("/")
            if clean and clean not in values:
                values.append(clean)
        return values[:12]

    @property
    def sqlite_path(self) -> Path:
        prefix = "sqlite:///"
        if not self.nexus_db_url.startswith(prefix):
            return ROOT_DIR / "nexus.db"
        raw = self.nexus_db_url[len(prefix) :]
        path = Path(raw)
        if not path.is_absolute():
            path = ROOT_DIR / path
        return path.resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
