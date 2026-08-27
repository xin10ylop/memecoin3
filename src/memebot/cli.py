"""memebot CLI.

  memebot backtest    --db data/panel.db --strategy dip_reclaim
  memebot grid        --db data/panel.db --strategy grad_momentum -o grid.csv
  memebot walkforward --db data/panel.db --strategy dip_reclaim --folds 3
  memebot panel       --db data/panel.db          # dataset summary
  memebot paper       [--config my.yaml]          # 24/7 paper trading
  memebot live        [--config my.yaml]          # requires MEMEBOT_LIVE=YES
  memebot safety      --mint <MINT>               # debug one token
  memebot report      [--config my.yaml]          # live/paper P&L so far
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from . import config as configmod
from .backtest.costs import CostModel
from .backtest.engine import RiskParams, run_backtest
from .backtest.metrics import summarize
from .backtest.walkforward import GridSpec, grid_report, walk_forward
from .data.store import load_panel, panel_summary, trending_first_seen
from .strategy import DEFAULTS, ExitRules, make_strategy


def _logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _cost_model(cfg) -> CostModel:
    return CostModel(dex_fee_bps=cfg.costs.dex_fee_bps,
                     adverse_bps=cfg.costs.adverse_bps,
                     priority_fee_usd=cfg.costs.priority_fee_usd,
                     rug_exit_impact_mult=cfg.costs.rug_exit_impact_mult)


def _risk_params(cfg) -> RiskParams:
    return RiskParams(starting_usd=cfg.capital.starting_usd,
                      risk_per_trade_usd=cfg.capital.risk_per_trade_usd,
                      max_concurrent=cfg.capital.max_concurrent,
                      daily_loss_limit_frac=cfg.capital.daily_loss_limit_frac,
                      max_pool_share=cfg.capital.max_pool_share)


def _exit_rules(cfg) -> ExitRules:
    return ExitRules(stop_frac=cfg.exits.stop_frac,
                     trail_frac=cfg.exits.trail_frac,
                     tp_levels=tuple(tuple(x) for x in cfg.exits.tp_levels),
                     max_hold_min=cfg.exits.max_hold_minutes,
                     liq_drop_exit_frac=cfg.exits.liquidity_drop_exit_frac)


def cmd_backtest(args, cfg) -> int:
    pools = load_panel(args.db, min_max_reserve=args.min_reserve)
    print(f"panel: {len(pools)} pools", file=sys.stderr)
    events = trending_first_seen(args.db) if args.strategy == "trending_follow" else {}
    params = json.loads(args.params) if args.params else {}
    strat = make_strategy(args.strategy, params, _exit_rules(cfg), events=events)
    res = run_backtest(pools, strat, _cost_model(cfg), _risk_params(cfg))
    s = summarize(res, label=args.strategy)
    print(json.dumps(s, indent=2, default=str))
    if args.trades_out:
        res.trades_df().to_csv(args.trades_out, index=False)
        print(f"trades -> {args.trades_out}", file=sys.stderr)
    return 0


def cmd_panel(args, cfg) -> int:
    pools = load_panel(args.db, min_max_reserve=args.min_reserve)
    df = panel_summary(pools)
    print(df.describe(include="all").to_string())
    if args.out:
        df.to_csv(args.out, index=False)
    return 0


def cmd_grid(args, cfg) -> int:
    pools = load_panel(args.db, min_max_reserve=args.min_reserve)
    grid = GridSpec(strategy=args.strategy,
                    param_grid=json.loads(args.param_grid),
                    exit_grid=json.loads(args.exit_grid))
    df = grid_report(pools, grid, _cost_model(cfg), _risk_params(cfg))
    df.to_csv(args.out, index=False)
    print(df.sort_values("expectancy_ci_lo", ascending=False)
            .head(20).to_string())
    return 0


def cmd_walkforward(args, cfg) -> int:
    pools = load_panel(args.db, min_max_reserve=args.min_reserve)
    grid = GridSpec(strategy=args.strategy,
                    param_grid=json.loads(args.param_grid),
                    exit_grid=json.loads(args.exit_grid))
    out = walk_forward(pools, grid, _cost_model(cfg), _risk_params(cfg),
                       n_folds=args.folds, min_trades=args.min_trades)
    print(json.dumps(out, indent=2, default=str))
    return 0


def cmd_trade(args, cfg, live: bool) -> int:
    from .live.trader import LiveTrader
    if live:
        cfg._d["mode"] = "live"
    trader = LiveTrader(cfg)
    trader.run()
    return 0


def cmd_safety(args, cfg) -> int:
    from .data.jupiter import Jupiter
    from .data.rpc import SolanaRpc
    from .safety import SafetyGate
    gate = SafetyGate(cfg, SolanaRpc(), Jupiter())
    v = gate.check_onchain(args.mint)
    print("onchain:", v.ok, v.reason)
    v2 = gate.check_sellability(args.mint, 50.0, 100.0)
    print("sellability:", v2.ok, v2.reason)
    return 0


def cmd_report(args, cfg) -> int:
    from .live.state import StateStore
    st = StateStore(cfg.live.state_db)
    print(json.dumps(st.pnl_summary(), indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="memebot")
    ap.add_argument("--config", help="override yaml on top of config/default.yaml")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_bt_args(p):
        p.add_argument("--db", default="data/panel.db")
        p.add_argument("--min-reserve", type=float, default=2000.0)

    p = sub.add_parser("backtest")
    add_bt_args(p)
    p.add_argument("--strategy", choices=sorted(DEFAULTS), required=True)
    p.add_argument("--params", help="json overrides for entry params")
    p.add_argument("--trades-out")

    p = sub.add_parser("panel")
    add_bt_args(p)
    p.add_argument("--out")

    p = sub.add_parser("grid")
    add_bt_args(p)
    p.add_argument("--strategy", choices=sorted(DEFAULTS), required=True)
    p.add_argument("--param-grid", required=True, help="json {param: [values]}")
    p.add_argument("--exit-grid", default="{}", help="json {exit_param: [values]}")
    p.add_argument("-o", "--out", default="grid.csv")

    p = sub.add_parser("walkforward")
    add_bt_args(p)
    p.add_argument("--strategy", choices=sorted(DEFAULTS), required=True)
    p.add_argument("--param-grid", required=True)
    p.add_argument("--exit-grid", default="{}")
    p.add_argument("--folds", type=int, default=3)
    p.add_argument("--min-trades", type=int, default=20)

    sub.add_parser("paper")
    sub.add_parser("live")

    p = sub.add_parser("safety")
    p.add_argument("--mint", required=True)

    sub.add_parser("report")

    args = ap.parse_args()
    _logging(args.verbose)
    cfg = configmod.load(args.config)

    if args.cmd == "backtest":
        return cmd_backtest(args, cfg)
    if args.cmd == "panel":
        return cmd_panel(args, cfg)
    if args.cmd == "grid":
        return cmd_grid(args, cfg)
    if args.cmd == "walkforward":
        return cmd_walkforward(args, cfg)
    if args.cmd == "paper":
        return cmd_trade(args, cfg, live=False)
    if args.cmd == "live":
        return cmd_trade(args, cfg, live=True)
    if args.cmd == "safety":
        return cmd_safety(args, cfg)
    if args.cmd == "report":
        return cmd_report(args, cfg)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
