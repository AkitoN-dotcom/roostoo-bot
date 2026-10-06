#!/bin/bash
# /opt/roostoo-bot に展開済みの状態で sudo bash bootstrap.sh として実行
set -e
echo "[1/3] installing python packages"
dnf install -y -q python3-pip >/dev/null 2>&1 || true
pip3 install -q requests pandas
echo "[2/3] systemd unit"
cat > /etc/systemd/system/roostoo-bot.service <<'UNIT'
[Unit]
Description=Roostoo Hackathon Bot
After=network-online.target
Wants=network-online.target
[Service]
WorkingDirectory=/opt/roostoo-bot
Environment=MODE=prod
Environment=DRY_RUN=0
ExecStart=/usr/bin/python3 -m roostoo_bot.main
Restart=always
RestartSec=30
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable roostoo-bot
echo "[3/3] OK. Next: write /opt/roostoo-bot/.env then systemctl start roostoo-bot"
