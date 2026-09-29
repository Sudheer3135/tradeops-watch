# Optional Telegram alerts

Alerts always remain visible in Alertmanager at port 9093. P1 routes repeat
at most every 30 minutes, P2 every 2 hours, P3 every 4 hours. Grouping uses
alert name and service. A P1 ServiceDown inhibits smaller alerts for the same
service/environment. It does not hide unrelated services.

Telegram delivery has **not** been tested: no real credentials were supplied.
The optional generated receiver configuration passed `amtool check-config`
using a clearly synthetic token in a container with networking disabled.

## Create your bot and secret files

1. In Telegram, open the official **@BotFather**, send `/newbot`, and follow
   its instructions. Keep the resulting token private.
2. Open your new bot and send `/start`, then a short message. This creates an
   update from which you can read your chat ID. For a group, add the bot to the
   intended group and send it a command there.
3. Open `multipass shell tradeops`, then run these commands. The token prompt
   is hidden and the token is not written into shell history:

```bash
cd /home/ubuntu/tradeops-watch/monitoring
sudo install -d -m 750 -o root -g 65534 secrets
read -rsp 'Telegram bot token: ' telegram_token; echo
printf '%s' "$telegram_token" | sudo tee secrets/telegram_bot_token >/dev/null
unset telegram_token
sudo chown root:65534 secrets/telegram_bot_token
sudo chmod 640 secrets/telegram_bot_token
sudo python3 - <<'PY'
import json
from pathlib import Path
import urllib.request
token = Path('secrets/telegram_bot_token').read_text().strip()
with urllib.request.urlopen('https://api.telegram.org/bot' + token + '/getUpdates') as response:
    updates = json.load(response)
for update in updates.get('result', []):
    message = update.get('message', update.get('channel_post', {}))
    if 'chat' in message:
        print('Chat ID:', message['chat']['id'], 'type:', message['chat']['type'])
PY
read -rp 'Your intended chat ID (may be negative for a group): ' telegram_chat
printf '%s' "$telegram_chat" | sudo tee secrets/telegram_chat_id >/dev/null
unset telegram_chat
sudo chown root:65534 secrets/telegram_chat_id
sudo chmod 640 secrets/telegram_chat_id
sudo python3 ../scripts/configure_telegram.py
```

If there are no updates, send the bot a new message and run the lookup again.
Do not paste the token into Git, logs, screenshots, or chat. Both secret files,
`monitoring/.env`, and the generated configuration directory are ignored by Git.
The numeric chat ID is read from its secret file and rendered into ignored YAML;
Alertmanager requires `chat_id` as an integer and does not expand environment
variables in its configuration. The token stays in its file via `bot_token_file`.

The script validates the generated config **before** choosing it in `.env`
and restarting Alertmanager. Enabling this receiver authorizes sending lab
alerts to that chat. Use an actual later lab incident to confirm firing and
resolved messages; a successful config check does not prove Telegram delivery.

To return to UI-only alerts:

```bash
sudo python3 ../scripts/configure_telegram.py --disable
```

The script does not delete your secrets. Docker's Alertmanager process runs as
UID/GID 65534; it has read access through the secret directory's group, while
other ordinary users do not. No token is embedded in a Docker command argument.

References: [Telegram BotFather tutorial](https://core.telegram.org/bots/tutorial),
[Alertmanager receiver and inhibition configuration](https://prometheus.io/docs/alerting/latest/configuration/).
