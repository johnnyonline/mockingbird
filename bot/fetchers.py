import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any

from bot.config import FLEX_X_USER_ID, X_BEARER_TOKEN

TWEET_URL_PATTERN = re.compile(r"https?://(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+")


class _TweetHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_p = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "p":
            self._in_p = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "p":
            self._in_p = False

    def handle_data(self, data: str) -> None:
        if self._in_p:
            self.parts.append(data)


def _fetch_tweet(url: str) -> str | None:
    oembed = "https://publish.twitter.com/oembed?" + urllib.parse.urlencode(
        {"url": url, "hide_thread": "true", "dnt": "true"}
    )
    try:
        with urllib.request.urlopen(oembed, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"[fetchers] oembed failed for {url}: {e}")
        return None

    parser = _TweetHTMLParser()
    parser.feed(data.get("html", ""))
    text = " ".join(p.strip() for p in parser.parts if p.strip()).strip()
    if not text:
        return None
    author = data.get("author_name", "").strip()
    return f"Tweet by {author}: {text}" if author else f"Tweet: {text}"


def has_tweet_url(text: str) -> bool:
    return bool(TWEET_URL_PATTERN.search(text))


def expand_tweets(text: str) -> str:
    """If text contains tweet URLs, append the fetched tweet contents."""
    urls = TWEET_URL_PATTERN.findall(text)
    if not urls:
        return text
    seen: set[str] = set()
    expansions: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        content = _fetch_tweet(url)
        if content:
            expansions.append(content)
    if not expansions:
        return text
    return text + "\n\n---\n" + "\n\n".join(expansions)


def fetch_x_posts(params: dict[str, str]) -> list[dict[str, Any]]:
    """Newest-first posts by FLEX_X_USER_ID via the official X API."""
    url = f"https://api.x.com/2/users/{FLEX_X_USER_ID}/tweets?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {X_BEARER_TOKEN}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        posts: list[dict[str, Any]] = json.loads(resp.read().decode()).get("data", [])
    return posts
