# mockingbird

Early-warning monitor for DeFi exploit news. Classifies every message, pings on hits.

Signs into a Telegram **user account** via Telethon, watches listed chats, runs each message through an LLM classifier, and forwards hits to an alert group via a separate **bot**.

## Installation

1. **Clone**
   ```bash
   git clone https://github.com/johnnyonline/mockingbird.git
   cd mockingbird
   ```

2. **Virtual env + deps**
   ```bash
   uv venv
   source .venv/bin/activate
   uv sync
   ```

3. **Get Telethon credentials.** Go to https://my.telegram.org/apps → create an app → copy the `api_id` and `api_hash`.

4. **Environment**
   ```bash
   cp .env.example .env
   # Fill BOT_ACCESS_TOKEN (for alerts), GROUP_CHAT_ID (alert target),
   # TELEGRAM_API_ID, TELEGRAM_API_HASH (from my.telegram.org),
   # MONITOR_CHAT_IDS (comma-separated IDs or @usernames),
   # OPENROUTER_API_KEY
   export $(grep -v '^#' .env | xargs)
   ```

5. **First login (one-time, interactive).** Telethon needs to log in as your user. Run locally in a terminal where you can type the SMS code:
   ```bash
   mkdir -p data
   TELEGRAM_SESSION=./data/user python -u -m bot
   ```
   Enter phone, SMS code, 2FA password if applicable. A `./data/user.session` file gets created — this is your login. Keep it secret (gitignored by default).

6. **Add the alert bot to the alert group.** Momo (or whichever bot token you use) must be a member of `GROUP_CHAT_ID` to post alerts.

## Usage

```shell
python -u -m bot
```

Or via docker compose (mount `./data` so the session persists):
```shell
docker compose up --build
```

## Monitoring new chats

Just join the group as your user (manually in Telegram), then add its ID or `@username` to `MONITOR_CHAT_IDS` and restart. No bot invites, no admin permissions needed.

## Code Style

```bash
ruff format .
ruff check .
mypy bot
```
