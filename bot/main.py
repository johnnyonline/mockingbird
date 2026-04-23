import asyncio
import html
import logging

from telegram import Bot, LinkPreviewOptions
from telethon import TelegramClient, events

from bot.classifier import is_exploit
from bot.config import (
    BOT_ACCESS_TOKEN,
    GROUP_CHAT_ID,
    MONITOR_CHAT_IDS,
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
    TELEGRAM_SESSION,
)
from bot.fetchers import TWEET_URL_PATTERN, expand_tweets


def _source_link(username: str | None, chat_id: int, message_id: int) -> str:
    if username:
        return f"https://t.me/{username}/{message_id}"
    return f"https://t.me/c/{str(chat_id).replace('-100', '', 1)}/{message_id}"


async def _send_alert(text: str, preview_url: str | None) -> None:
    tg = Bot(token=BOT_ACCESS_TOKEN)
    if preview_url:
        opts = LinkPreviewOptions(is_disabled=False, url=preview_url, prefer_small_media=True)
    else:
        opts = LinkPreviewOptions(is_disabled=True)
    try:
        await tg.send_message(
            chat_id=GROUP_CHAT_ID,
            text=text,
            parse_mode="HTML",
            link_preview_options=opts,
        )
    except Exception as e:
        print(f"[_send_alert] failed: {e}")


async def _on_message(event: events.NewMessage.Event) -> None:
    msg = event.message
    text = msg.message or ""
    if not text.strip():
        return

    expanded = await asyncio.to_thread(expand_tweets, text)

    if not await is_exploit(expanded):
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
        f"<blockquote>{body}</blockquote>",
        preview_url=preview_url,
    )


async def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    client = TelegramClient(TELEGRAM_SESSION, TELEGRAM_API_ID, TELEGRAM_API_HASH)
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
    await client.run_until_disconnected()
