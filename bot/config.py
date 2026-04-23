import os
from pathlib import Path


def _require_env(name: str) -> str:
    val = os.getenv(name, "")
    if not val:
        raise RuntimeError(f"!{name}")
    return val


def _parse_chats(raw: str) -> list[int | str]:
    chats: list[int | str] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if item.startswith("@") or not item.lstrip("-").isdigit():
            chats.append(item.lstrip("@"))
        else:
            chats.append(int(item))
    return chats


# Alert side (bot)
BOT_ACCESS_TOKEN = _require_env("BOT_ACCESS_TOKEN")
GROUP_CHAT_ID = int(_require_env("GROUP_CHAT_ID"))

# Read side (user account)
TELEGRAM_API_ID = int(_require_env("TELEGRAM_API_ID"))
TELEGRAM_API_HASH = _require_env("TELEGRAM_API_HASH")
TELEGRAM_STRING_SESSION = _require_env("TELEGRAM_STRING_SESSION")

# Source chats
MONITOR_CHAT_IDS = _parse_chats(_require_env("MONITOR_CHAT_IDS"))

# Classifier
OPENROUTER_API_KEY = _require_env("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "z-ai/glm-5")

_prompts = Path(__file__).parent / "prompts"
EXPLOIT_CLASSIFIER_PROMPT = (_prompts / "exploit-classifier.md").read_text()
