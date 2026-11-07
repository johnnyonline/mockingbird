import asyncio
import html
import logging
import re
import urllib.error
from datetime import datetime, timezone

from telegram import Bot, LinkPreviewOptions
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from bot.classifier import is_exploit
from bot.config import (
    BOT_ACCESS_TOKEN,
    FLEX_CHAT_ID,
    GROUP_CHAT_ID,
    MONITOR_CHAT_IDS,
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
    TELEGRAM_STRING_SESSION,
)
from bot.fetchers import TWEET_URL_PATTERN, expand_tweets, fetch_x_posts

# Patterns for messages we never want to classify (automated forwards,
# bots re-broadcasting onchain activity, etc.)
SKIP_PATTERNS = [
    re.compile(r"onchain\s+messages?", re.IGNORECASE),
]

URL_PATTERN = re.compile(r"https?://\S+")

# Services we already pinged about running out of credits; cleared when a call to that service succeeds again
_out_of_credits: set[str] = set()


def _source_link(username: str | None, chat_id: int, message_id: int) -> str:
    if username:
        return f"https://t.me/{username}/{message_id}"
    return f"https://t.me/c/{str(chat_id).replace('-100', '', 1)}/{message_id}"


async def _send_alert(text: str, preview_url: str | None, chat_id: int = GROUP_CHAT_ID) -> None:
    tg = Bot(token=BOT_ACCESS_TOKEN)
    if preview_url:
        opts = LinkPreviewOptions(is_disabled=False, url=preview_url, prefer_small_media=True)
    else:
        opts = LinkPreviewOptions(is_disabled=True)
    try:
        await tg.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            link_preview_options=opts,
        )
    except Exception as e:
        print(f"[_send_alert] failed: {e}")


async def _ping_if_out_of_credits(service: str, e: Exception) -> None:
    if isinstance(e, urllib.error.HTTPError) and e.code == 402 and service not in _out_of_credits:
        _out_of_credits.add(service)
        await _send_alert(f"🪫 <b>{service} is out of credits</b>\n\n<b>ping</b> @johnnyonline", preview_url=None)


async def _on_message(event: events.NewMessage.Event) -> None:
    msg = event.message
    text = msg.message or ""
    if not text.strip():
        return

    if any(p.search(text) for p in SKIP_PATTERNS):
        return

    # Skip messages containing non-tweet URLs (unless a tweet is also present to anchor context)
    if URL_PATTERN.search(text) and not TWEET_URL_PATTERN.search(text):
        return

    expanded = await asyncio.to_thread(expand_tweets, text)

    try:
        hit = await is_exploit(expanded)
    except Exception as e:
        await _ping_if_out_of_credits("OpenRouter", e)
        raise
    _out_of_credits.discard("OpenRouter")
    if not hit:
        return

    sender = await msg.get_sender()
    if sender and getattr(sender, "username", None):
        who = f"@{sender.username}"
    elif sender:
        name = f"{getattr(sender, 'first_name', '') or ''} {getattr(sender, 'last_name', '') or ''}".strip()
        who = html.escape(name or "unknown")
    else:
        who = "unknown"

    chat = await msg.get_chat()
    chat_title = html.escape(getattr(chat, "title", None) or "unknown")
    chat_username = getattr(chat, "username", None)
    link = _source_link(chat_username, event.chat_id, msg.id)

    tweet_match = TWEET_URL_PATTERN.search(text)
    preview_url = tweet_match.group(0) if tweet_match else None
    body = html.escape((text if preview_url else expanded)[:1500])

    await _send_alert(
        f"⚠️ <b>possible incident</b>\n\n"
        f"<b>by</b> {who}\n"
        f"<b>in</b> <a href='{link}'>{chat_title}</a>\n\n"
        f"<blockquote>{body}</blockquote>\n\n"
        f"<b>ping</b> @johnnyonline",
        preview_url=preview_url,
    )


async def _poll_x() -> None:
    # start_time: don't re-share old posts after a restart; since_id takes over once set
    params = {
        "exclude": "replies",
        "tweet.fields": "referenced_tweets",
        "start_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    while True:
        await asyncio.sleep(60)
        try:
            posts = await asyncio.to_thread(fetch_x_posts, params)
            _out_of_credits.discard("X")
            if posts:
                params["since_id"] = posts[0]["id"]
            for post in reversed(posts):
                refs = {r["type"]: r["id"] for r in post.get("referenced_tweets", [])}
                if "retweeted" in refs:
                    label, post_id = "🔁 <b>Flex reposted</b>", refs["retweeted"]
                elif "quoted" in refs:
                    label, post_id = "💬 <b>Flex quoted</b>", post["id"]
                else:
                    label, post_id = "🐦 <b>Flex posted</b>", post["id"]
                url = f"https://x.com/i/status/{post_id}"
                await _send_alert(f"{label}\n{url}", preview_url=url, chat_id=FLEX_CHAT_ID)
        except Exception as e:
            print(f"[🐦 mockingbird] x feed failed: {e}")
            await _ping_if_out_of_credits("X", e)


async def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    client = TelegramClient(StringSession(TELEGRAM_STRING_SESSION), TELEGRAM_API_ID, TELEGRAM_API_HASH)
    await client.start()
    me = await client.get_me()
    print(f"[🐦 mockingbird] logged in as @{getattr(me, 'username', None) or me.id}")

    entities = []
    for chat in MONITOR_CHAT_IDS:
        try:
            entity = await client.get_entity(chat)
            title = getattr(entity, "title", None) or getattr(entity, "username", None) or entity.id
            print(f"[🐦 mockingbird] resolved {chat!r} -> {entity.id} ({title})")
            entities.append(entity)
        except Exception as e:
            print(f"[🐦 mockingbird] FAILED to resolve {chat!r}: {e}")

    if not entities:
        raise RuntimeError("no monitored chats could be resolved; check membership and MONITOR_CHAT_IDS")

    client.add_event_handler(_on_message, events.NewMessage(chats=entities))
    poller = asyncio.create_task(_poll_x())
    await client.run_until_disconnected()
    poller.cancel()
