#!/usr/bin/env bash
set -euo pipefail
[[ $(uname -s) == Linux && $(hostname) == tradeops && $EUID == 0 ]] || { echo 'Run as root inside the tradeops Ubuntu VM'; exit 1; }
root=$(cd "$(dirname "$0")/.." && pwd)
apt-get update -qq
apt-get install -y -qq python3 curl cron logrotate iproute2 iptables util-linux
id tradeops >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin tradeops
install -d /opt/tradeops/services /opt/tradeops/scripts /opt/tradeops/runbooks /etc/tradeops /var/lib/tradeops
install -d -o tradeops -g tradeops /var/log/tradeops
install -m 644 "$root"/services/*.py /opt/tradeops/services/
install -m 755 "$root"/scripts/* /opt/tradeops/scripts/
install -m 644 "$root"/runbooks/*.md /opt/tradeops/runbooks/
install -m 644 "$root"/systemd/*.service /etc/systemd/system/
install -m 644 "$root"/cron/tradeops-cron /etc/cron.d/tradeops
cat > /etc/logrotate.d/tradeops <<'ROTATE'
# Python owns rotation of service logs. Rotate only the Bash/cron logs here;
# two independent rotators on the same file would risk lost records.
/var/log/tradeops/alerts.log /var/log/tradeops/cron.log {
    daily
    rotate 7
    missingok
    notifempty
    copytruncate
    su tradeops tradeops
}
ROTATE
touch /var/log/tradeops/alerts.log /var/log/tradeops/cron.log
chown tradeops:tradeops /var/log/tradeops/{alerts,cron}.log
systemctl daemon-reload
systemctl enable --now cron tradeops-feed tradeops-orders
systemctl restart tradeops-feed tradeops-orders
sleep 3
systemctl --no-pager --full status tradeops-feed tradeops-orders
