from bs4 import BeautifulSoup

from app.x_embed_resilience import _readable_oembed_text, extract_x_post_urls


def test_user_copied_x_share_url_is_canonicalized():
    raw = "https://x.com/GIFs_22/status/2096882240097824954?s=20"
    assert extract_x_post_urls(raw) == ["https://x.com/GIFs_22/status/2096882240097824954"]


def test_media_only_x_embed_is_not_rejected():
    soup = BeautifulSoup('<blockquote class="twitter-tweet"><img alt="Animated GIF" /></blockquote>', "html.parser")
    text, media_only, alt = _readable_oembed_text(soup, "GIFs_22")
    assert media_only is True
    assert text
    assert "GIFs_22" in text or alt


def test_normal_x_embed_text_remains_normal_text():
    soup = BeautifulSoup('<blockquote class="twitter-tweet"><p>Public post text #demo</p></blockquote>', "html.parser")
    text, media_only, alt = _readable_oembed_text(soup, "demo")
    assert text == "Public post text #demo"
    assert media_only is False
    assert alt == []
