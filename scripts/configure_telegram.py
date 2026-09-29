#!/usr/bin/env python3
"""Generate a private Alertmanager config; never copy the bot token into YAML."""

import argparse
import os
import platform
import re
import subprocess
from pathlib import Path


def render_config(config, chat):
    for receiver in ("p1", "p2", "p3"):
        config = config.replace(
            f"  - name: {receiver}\n",
            f"""  - name: {receiver}
    telegram_configs:
      - bot_token_file: /etc/alertmanager-secrets/telegram_bot_token
        chat_id: {int(chat)}
        parse_mode: ''
        send_resolved: true
        message: '{{{{ .Status | toUpper }}}} {{{{ .CommonLabels.severity }}}} {{{{ .CommonLabels.alertname }}}} service={{{{ .CommonLabels.service }}}}. {{{{ range .Alerts }}}}{{{{ .Annotations.summary }}}} Runbook: {{{{ .Annotations.runbook }}}} {{{{ end }}}}'
""",
        )
    return config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--disable", action="store_true")
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.node() != "tradeops" or os.geteuid() != 0:
        raise SystemExit("Run with sudo inside tradeops")
    root = Path(__file__).resolve().parent.parent / "monitoring"
    config_name = "alertmanager.yml"
    if not args.disable:
        secret_dir = root / "secrets"
        token_file = secret_dir / "telegram_bot_token"
        chat_file = secret_dir / "telegram_chat_id"
        token = token_file.read_text().strip()
        chat = chat_file.read_text().strip()
        if not token or not re.fullmatch(r"-?[1-9][0-9]*", chat):
            raise SystemExit("Token must be nonempty; chat ID must be a nonzero integer")
        os.chown(secret_dir, 0, 65534)
        secret_dir.chmod(0o750)
        for path in (token_file, chat_file):
            os.chown(path, 0, 65534)
            path.chmod(0o640)
        config = render_config((root / "alertmanager/alertmanager.yml").read_text(), chat)
        generated = root / "alertmanager/generated"
        generated.mkdir(mode=0o750, exist_ok=True)
        os.chown(generated, 0, 65534)
        output = generated / "alertmanager.yml"
        output.write_text(config)
        os.chown(output, 0, 65534)
        output.chmod(0o640)
        config_name = "generated/alertmanager.yml"
    # Validate before changing the live configuration selector.
    subprocess.run(
        [
            "docker",
            "compose",
            "run",
            "--rm",
            "--no-deps",
            "--entrypoint",
            "amtool",
            "alertmanager",
            "check-config",
            f"/etc/alertmanager/{config_name}",
        ],
        cwd=root,
        check=True,
    )
    env = root / ".env"
    entries = [
        line for line in env.read_text().splitlines() if not line.startswith("ALERTMANAGER_CONFIG=")
    ]
    entries.append(f"ALERTMANAGER_CONFIG={config_name}")
    env.write_text("\n".join(entries) + "\n")
    env.chmod(0o600)
    subprocess.run(["docker", "compose", "up", "-d", "alertmanager"], cwd=root, check=True)
    print(
        "Telegram disabled; alerts remain in UI"
        if args.disable
        else "Telegram configuration enabled; confirm delivery in your chat"
    )


if __name__ == "__main__":
    main()
