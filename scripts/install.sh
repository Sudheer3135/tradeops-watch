#!/usr/bin/env bash
set -euo pipefail
[[ $(uname -s) == Linux && $(hostname) == tradeops && $EUID == 0 ]] || { echo 'Run as root inside the tradeops Ubuntu VM'; exit 1; }
root=$(cd "$(dirname "$0")/.." && pwd)
apt-get update -qq
apt-get install -y -qq python3 python3-venv curl cron logrotate iproute2 iptables util-linux
id tradeops >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin tradeops
install -d /opt/tradeops/releases /opt/tradeops/services /opt/tradeops/scripts /opt/tradeops/runbooks /etc/tradeops /var/lib/tradeops
install -d -o tradeops -g tradeops /var/log/tradeops
python3 -m venv /opt/tradeops/venv
install -m 644 "$root"/requirements.txt /opt/tradeops/requirements.txt
/opt/tradeops/venv/bin/python -m pip install --disable-pip-version-check -r /opt/tradeops/requirements.txt
install -m 644 "$root"/services/*.py /opt/tradeops/services/
install -m 755 "$root"/scripts/*.sh "$root"/scripts/*.py /opt/tradeops/scripts/
install -m 644 "$root"/runbooks/*.md /opt/tradeops/runbooks/
# Bootstrap once; subsequent source changes use the transactional deploy script.
if [[ ! -L /opt/tradeops/current ]]; then
    baseline="/opt/tradeops/releases/bootstrap-$(date -u +%Y%m%dT%H%M%S)"
    install -d "$baseline/services" "$baseline/scripts" "$baseline/runbooks"
    install -m 644 "$root"/services/*.py "$baseline/services/"
    install -m 755 "$root"/scripts/*.sh "$root"/scripts/*.py "$baseline/scripts/"
    install -m 644 "$root"/runbooks/*.md "$baseline/runbooks/"
    install -m 644 "$root/requirements.txt" "$baseline/requirements.txt"
    date -u +%FT%TZ > "$baseline/.tradeops-release"
    ln -s "$baseline" /opt/tradeops/current
fi
install -m 644 "$root"/systemd/*.service /etc/systemd/system/
install -m 644 "$root"/cron/tradeops-cron /etc/cron.d/tradeops
cat > /etc/logrotate.d/tradeops <<'ROTATE'
# Python owns rotation of service logs. Rotate only the Bash/cron logs here;
# two independent rotators on the same file would risk lost records.
/var/log/tradeops/alerts.log /var/log/tradeops/cron.log /var/log/tradeops/deploy.log {
    daily
    rotate 7
    missingok
    notifempty
    copytruncate
    su tradeops tradeops
}
ROTATE
touch /var/log/tradeops/alerts.log /var/log/tradeops/cron.log /var/log/tradeops/deploy.log
chown tradeops:tradeops /var/log/tradeops/{alerts,cron,deploy}.log
systemctl daemon-reload
systemctl enable --now cron tradeops-feed tradeops-orders
if python3 - "$root" <<'PYCODE'
from pathlib import Path
import sys
source = Path(sys.argv[1]) / 'services'
current = Path('/opt/tradeops/current/services')
files = sorted(source.glob('*.py'))
raise SystemExit(0 if all((current / p.name).exists() and (current / p.name).read_bytes() == p.read_bytes() for p in files) and {p.name for p in files} == {p.name for p in current.glob('*.py')} else 1)
PYCODE
then
    systemctl restart tradeops-feed tradeops-orders
else
    TRADEOPS_SOURCE_DIR="$root" /opt/tradeops/scripts/deploy.sh "install-$(date -u +%Y%m%dT%H%M%S)-$$"
fi
sleep 3
systemctl --no-pager --full status tradeops-feed tradeops-orders
