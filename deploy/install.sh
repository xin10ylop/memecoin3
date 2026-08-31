#!/usr/bin/env bash
# Install memebot as systemd services. Run as root on a fresh Ubuntu/Debian box.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "installing from $REPO_DIR"

apt-get update -q
apt-get install -y -q python3 python3-pip python3-venv sqlite3

python3 -m venv "$REPO_DIR/.venv"
"$REPO_DIR/.venv/bin/pip" install -q --upgrade pip
"$REPO_DIR/.venv/bin/pip" install -q -e "$REPO_DIR"

# git does not track empty directories, so a fresh clone has no data/ and
# the scalper dies on startup with "unable to open database file". Create it
# before the services are ever started.
mkdir -p "$REPO_DIR/data"

mkdir -p /etc/memebot
if [ ! -f /etc/memebot/secrets.env ]; then
  cat > /etc/memebot/secrets.env <<'ENV'
# Helius RPC URL (get a free key at helius.dev)
MEMEBOT_RPC_URL=https://mainnet.helius-rpc.com/?api-key=PUT_YOUR_KEY_HERE
ENV
  chmod 600 /etc/memebot/secrets.env
  echo "created /etc/memebot/secrets.env — put your RPC key in it"
fi

for svc in scalper outcomes; do
  case "$svc" in
    scalper)  DESC="memebot launch scalper"
              CMD="$REPO_DIR/.venv/bin/memebot --config config/scalp.yaml scalp" ;;
    outcomes) DESC="memebot outcome recorder"
              CMD="$REPO_DIR/.venv/bin/python3 scripts/fill_outcomes.py" ;;
  esac
  cat > "/etc/systemd/system/memebot-$svc.service" <<UNIT
[Unit]
Description=$DESC
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$REPO_DIR
EnvironmentFile=/etc/memebot/secrets.env
ExecStart=$CMD
Restart=always
RestartSec=15
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT
done

cat > /usr/local/bin/memebot-status <<STATUS
#!/usr/bin/env bash
cd "$REPO_DIR" && exec "$REPO_DIR/.venv/bin/python3" scripts/status.py
STATUS
chmod +x /usr/local/bin/memebot-status

systemctl daemon-reload
systemctl enable memebot-scalper memebot-outcomes
echo
echo "done. next:"
echo "  1. put your Helius key in /etc/memebot/secrets.env"
echo "  2. sudo systemctl start memebot-scalper memebot-outcomes"
echo "  3. memebot-status"
