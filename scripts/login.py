"""One-time Telethon login. Generates a StringSession for TELEGRAM_STRING_SESSION.

Usage:
    python scripts/login.py

Requires TELEGRAM_API_ID and TELEGRAM_API_HASH in env (or enter at prompt).
Asks for phone, code, 2FA password. Prints the session string on success.
Copy the printed string into your .env (or Railway env vars) as
TELEGRAM_STRING_SESSION, then run the bot normally.
"""

import os

from telethon.sessions import StringSession
from telethon.sync import TelegramClient


def main() -> None:
    api_id = int(os.environ.get("TELEGRAM_API_ID") or input("API ID: "))
    api_hash = os.environ.get("TELEGRAM_API_HASH") or input("API hash: ")

    client = TelegramClient(StringSession(), api_id, api_hash)
    client.start()
    session_string = client.session.save()
    client.disconnect()

    print("\n=== copy this into TELEGRAM_STRING_SESSION ===\n")
    print(session_string)
    print("\n===============================================")


if __name__ == "__main__":
    main()
