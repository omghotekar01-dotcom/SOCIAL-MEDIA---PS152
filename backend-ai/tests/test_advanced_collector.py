from app.advanced_collector import AdvancedCollectorStartRequest


def test_continuous_collector_defaults_to_free_public_sources():
    config = AdvancedCollectorStartRequest(query="RiverLink")
    assert config.enable_telegram_public is True
    assert config.enable_bluesky is True
    assert config.enable_reddit is True
    assert config.enable_mastodon is True
    assert config.enable_x is False
    assert config.enable_youtube is False
    assert config.enable_instagram_authorized is False
    assert config.enable_facebook_authorized is False


def test_continuous_collector_keeps_minimum_sixty_second_interval():
    config = AdvancedCollectorStartRequest(query="RiverLink", interval_seconds=60)
    assert config.interval_seconds == 60
