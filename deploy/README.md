# Running memebot 24/7

The research container this was built in suspends when the session goes
idle, and every background process dies with it. Two nights of live data
were lost that way — the bot is fine, the host is not. Anything that must
run unattended needs a host that stays awake.

## What you need

Any always-on Linux box. A $5/month VPS (Hetzner, DigitalOcean, Vultr) is
ample: the bot uses well under 200 MB of RAM and almost no CPU. It spends
its time waiting on network calls.

## Setup (about five minutes)

```bash
git clone <this repo> memebot && cd memebot
sudo bash deploy/install.sh          # installs python deps + services
sudo nano /etc/memebot/secrets.env   # paste your Helius RPC URL
sudo systemctl start memebot-scalper memebot-outcomes
```

## Check on it

```bash
memebot-status                    # trades, P&L, win rate, death rate
journalctl -u memebot-scalper -f  # live log
```

## What runs

| service           | what it does                                       |
|-------------------|----------------------------------------------------|
| memebot-scalper   | watches launches, applies the filters, paper trades |
| memebot-outcomes  | fills in what happened to every candidate seen      |

systemd restarts either one automatically if it crashes or the box
reboots — which is exactly what the research container could not do.

## Paper vs real money

It ships in PAPER mode and stays there until you deliberately change it.
Going live needs BOTH `mode: live` in `config/scalp.yaml` AND the
environment variable `MEMEBOT_LIVE=YES`. Two switches, on purpose.

**Do not go live yet.** As of the last evaluation the edge is not
established: the live sample is 14 trades at -$30.77, all under a rule
since replaced, and the best backtested configuration has an
out-of-sample p-value of 0.09. Run it in paper mode until the live
numbers say otherwise.
