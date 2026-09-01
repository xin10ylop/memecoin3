#!/usr/bin/env python3
"""Is this thing actually going to produce trades overnight?

Written after three nights that produced nothing. Every time, some layer
was healthy and reported so, while a layer beneath it was dead: the process
was up but the feed thread had died; the feed ran but candidates were
silently dropped; candidates flowed but the journal could not write; the
journal wrote but the deployed module was months stale.

So this checks each stage against EVIDENCE FROM THE LAST HOUR rather than
asking whether a component exists, and ends with the only question that
matters: at the rate now observable, how many trades should appear by
morning?
"""
from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "scalp.db")
OK, BAD, WARN = "PASS", "FAIL", "WARN"
results: list[tuple[str, str, str]] = []


def check(name: str, status: str, detail: str = "") -> None:
    results.append((name, status, detail))


def journal(unit: str, since: str = "-60 min") -> str:
    try:
        return subprocess.run(["journalctl", "-u", unit, "--since", since,
                               "--no-pager", "-q"], capture_output=True,
                              text=True, timeout=60).stdout
    except Exception:
        return ""


def main() -> int:
    print("=" * 64)
    print("PREFLIGHT — will this produce trades overnight?")
    print("=" * 64)

    # EFFECTIVE CONFIGURATION.
    #
    # Most of today's lost hours were not logic errors: a stale
    # MEMEBOT_FEED=portal silently disabled a second feed; a column added
    # to CREATE TABLE was never ALTERed onto the live database; a backfill
    # query could not pick up columns added after a row existed. In every
    # case the code was right and the RUNNING SYSTEM was configured
    # differently from what I was reasoning about, with no visible symptom.
    #
    # So print what is actually in force, and flag every value overridden
    # from its default. A wrong number here is findable in seconds; the
    # same wrong number invisible costs a day.
    try:
        # Read the SERVICE's environment file, not this process's. Preflight
        # runs as a separate command and never sources it, so reading
        # os.environ showed defaults and labelled them current -- a config
        # display that could not see a config change is precisely the blind
        # spot this section exists to remove, and I built it with that spot
        # intact. MEMEBOT_MIN_ACCEL=0 was set, the service used it, and this
        # screen still printed 1.0.
        envfile = {}
        for path in ("/etc/memebot/secrets.env",
                     os.path.join(REPO, "data", "secrets.env")):
            try:
                with open(path) as fh:
                    for line in fh:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, _, v = line.partition("=")
                            envfile[k.strip()] = v.strip().strip('"').strip("'")
                break
            except OSError:
                continue

        sys.path.insert(0, os.path.join(REPO, "src"))
        # import the module with the SERVICE's values in place, so the
        # thresholds printed are the ones actually in force
        for k, v in envfile.items():
            os.environ.setdefault(k, v)
        import memebot.live.scalper as sc
        import importlib
        importlib.reload(sc)
        defaults = {"MEMEBOT_FEED": "both", "MEMEBOT_MIN_RANGE": "0.172",
                    "MEMEBOT_MIN_ACCEL": "1.0", "MEMEBOT_MAX_ACCEL": "10.0",
                    "MEMEBOT_MAX_DRAWDOWN": "1.0",
                    "MEMEBOT_PORTAL_STREAM": "migration",
                    "MEMEBOT_HELIUS_HOURLY_CAP": "200",
                    "MEMEBOT_TRAIL": "0.10"}
        print()
        print(f"effective configuration, read from the SERVICE env file "
              f"({len(envfile)} vars)  * = overridden")
        for k, dflt in defaults.items():
            cur = envfile.get(k)
            mark = " *" if cur is not None and cur != dflt else "  "
            print(f"  {mark} {k:<28} {cur if cur is not None else dflt}")
        print(f"     thresholds in force        range>={sc.MIN_RANGE} "
              f"accel {sc.MIN_ACCEL}-{sc.MAX_ACCEL} "
              f"drawdown<={sc.MAX_DRAWDOWN} trail={sc.TRAIL}")
        print()
    except Exception as e:
        print(f"  (could not read effective config: {e})")

    # 1. the deployed code is the code we think it is. A tar flag silently
    #    froze src/memebot/data for a day; nothing else noticed.
    try:
        hel = open(os.path.join(REPO, "src/memebot/data/helius.py")).read()
        scl = open(os.path.join(REPO, "src/memebot/live/scalper.py")).read()
        missing = [n for n, src in (("swaps_since", hel),
                                    ("volume_buckets", hel),
                                    ("MAX_DRAWDOWN", scl),
                                    ("anchor_ts", hel))
                   if n not in src]
        check("deployed code is current", OK if not missing else BAD,
              "all expected symbols present" if not missing
              else f"MISSING {missing} — re-extract WITHOUT --exclude=data")
    except Exception as e:
        check("deployed code is current", BAD, str(e))

    # 2. services
    for unit in ("memebot-scalper", "memebot-outcomes"):
        try:
            r = subprocess.run(["systemctl", "is-active", unit],
                               capture_output=True, text=True, timeout=20)
            st = r.stdout.strip()
            check(f"{unit} running", OK if st == "active" else BAD, st)
        except Exception as e:
            check(f"{unit} running", BAD, str(e))

    log = journal("memebot-scalper")

    # every feed the configuration asks for must actually connect. A feed
    # that never starts is indistinguishable from a feed with nothing to
    # report, which is how a disabled second feed went unnoticed for hours.
    want = os.environ.get("MEMEBOT_FEED", "both")
    expected = ({"portal", "narrow"} if want == "both"
                else {"portal"} if want == "portal"
                else {"websocket"} if want == "websocket" else {"poll"})
    connected = set()
    if "portal launch feed connected" in log:
        connected.add("portal")
    if "narrow rpc feed connected" in log:
        connected.add("narrow")
    if "realtime launch feed connected" in log:
        connected.add("websocket")
    if "polling launch feed started" in log:
        connected.add("poll")
    missing = expected - connected
    check("all configured feeds connected", OK if not missing else BAD,
          f"{sorted(connected) or 'none'} connected"
          + (f" — MISSING {sorted(missing)}" if missing else ""))

    # a schema the code expects but the database lacks silently disables
    # whatever depends on it
    try:
        db0 = sqlite3.connect(DB)
        cols = {r[1] for r in
                db0.execute("PRAGMA table_info(candidate_journal)")}
        need = {"feed", "drawdown", "drift", "vol2", "outcome",
                "out_trail30", "out_tp2x", "out_time30"}
        gone = need - cols
        check("journal schema complete", OK if not gone else BAD,
              "all columns present" if not gone
              else f"MISSING {sorted(gone)} — restart to migrate")
        db0.close()
    except Exception as e:
        check("journal schema complete", BAD, str(e))

    # 3. the feed is connected AND delivering, not merely constructed
    connected = "launch feed connected" in log
    watching = len(re.findall(r"watching \w+", log))
    check("feed connected", OK if connected else WARN,
          "saw a connect in the last hour" if connected
          else "no connect line in the last hour (may predate the window)")
    check("launches arriving", OK if watching >= 5 else BAD,
          f"{watching} in the last hour")

    # 4. candidates are being RECORDED, not just seen
    try:
        db = sqlite3.connect(DB)
        cut = time.time() - 3600
        row = db.execute(
            "SELECT COUNT(*), SUM(samples>=3 AND range_frac>=0.172 "
            "AND drawdown<=0.10), SUM(accel IS NOT NULL), SUM(taken) "
            "FROM candidate_journal WHERE ts > ?", (cut,)).fetchone()
        cands, gate, accel, taken = (row[0] or 0, row[1] or 0,
                                     row[2] or 0, row[3] or 0)
        check("journal recording", OK if cands >= 5 else BAD,
              f"{cands} candidates written in the last hour")
        check("free filters passing", OK if gate > 0 else WARN,
              f"{gate}/{cands} cleared range+drawdown")
        # the failure that cost a full day: gate passed, acceleration never
        # computed, and every other indicator looked healthy
        if gate > 0:
            ok = accel >= gate
            check("acceleration computed when gated", OK if ok else BAD,
                  f"{accel} readings for {gate} gated candidates"
                  + ("" if ok else " — paid lookup is failing"))
        else:
            check("acceleration computed when gated", WARN,
                  "nothing reached the paid check this hour")
        check("entries", OK if taken > 0 else WARN,
              f"{taken} taken in the last hour")

        # 5. outcomes must fill or the shadow dataset is dead weight
        settled = db.execute(
            "SELECT COUNT(*) FROM candidate_journal WHERE outcome IS NOT NULL"
            " AND outcome_ts > ?", (time.time() - 7200,)).fetchone()[0]
        check("outcomes filling", OK if settled > 0 else WARN,
              f"{settled} settled in the last 2h")

        trades = db.execute("SELECT COUNT(*), ROUND(SUM(pnl_usd),2) "
                            "FROM trades").fetchone()
    except Exception as e:
        check("journal recording", BAD, str(e))
        cands = gate = accel = taken = 0
        trades = (0, 0)

    # 6. nothing is quietly capped or erroring
    capped = log.count("hourly cap")
    check("credit budget", OK if capped == 0 else WARN,
          "not capped" if capped == 0 else f"cap hit {capped}x")
    broken = log.count("acceleration is BROKEN") + log.count("journal write FAILED")
    check("no self-reported faults", OK if broken == 0 else BAD,
          "clean" if broken == 0 else f"{broken} fault lines")

    print()
    width = max(len(n) for n, _, _ in results)
    for name, status, detail in results:
        mark = {OK: "  ok ", BAD: " FAIL", WARN: " warn"}[status]
        print(f"[{mark}] {name:<{width}}  {detail}")

    fails = [n for n, s, _ in results if s == BAD]
    print()
    print(f"ledger: {trades[0]} trades, ${trades[1] or 0:+.2f}")
    if cands:
        per_h = cands
        rate = (taken / cands) if cands else 0
        print(f"observed rate: {per_h} candidates/h, {taken} entered "
              f"({rate:.1%})")
        print(f"projection for 8 hours: ~{taken*8} trades "
              f"({'enough to read' if taken*8 >= 10 else 'TOO FEW to conclude'})")
    print()
    if fails:
        print("VERDICT: do NOT leave it — " + "; ".join(fails))
        return 1
    if taken == 0:
        print("VERDICT: pipeline is healthy but nothing entered this hour.")
        print("The rule is strict; entries are expected to be sparse. If the")
        print("morning shows zero trades AND zero gated candidates, the")
        print("thresholds are wrong for this feed, not the plumbing.")
        return 0
    print("VERDICT: healthy end to end, trades flowing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
