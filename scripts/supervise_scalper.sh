#!/usr/bin/env bash
# Keep the scalper alive across transient infrastructure failures.
#
# It died once already and stayed dead for 90 minutes: the outbound proxy
# restarted on a new port, every HTTP call started failing, and the process
# exited. That is not a trading error, it is an environment change, and a
# 24/7 system must not need a human to notice it. The proxy address is
# re-read from the environment on every restart, so a moved port is picked
# up automatically.
cd /home/user/memecoin3 || exit 1
while true; do
  # shellcheck disable=SC1091
  source data/secrets.env
  echo "$(date -u +%FT%TZ) supervisor: starting scalper" >> data/scalp.log
  memebot --config config/scalp.yaml scalp >> data/scalp.log 2>&1
  code=$?
  echo "$(date -u +%FT%TZ) supervisor: scalper exited ($code), restarting in 15s" >> data/scalp.log
  sleep 15
done
