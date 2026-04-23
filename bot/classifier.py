import asyncio
import json
import urllib.request

from bot.config import EXPLOIT_CLASSIFIER_PROMPT, OPENROUTER_API_KEY, OPENROUTER_MODEL


def _classify_sync(text: str) -> bool:
    body = json.dumps(
        {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": EXPLOIT_CLASSIFIER_PROMPT},
                {"role": "user", "content": text},
            ],
            "temperature": 0,
        }
    ).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    answer = data["choices"][0]["message"]["content"].strip().upper()
    return answer.startswith("YES")


async def is_exploit(text: str) -> bool:
    return await asyncio.to_thread(_classify_sync, text)
