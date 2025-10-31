from __future__ import annotations
import argparse
from typing import Optional
from logscoper.commands.hist import cmd_hist
from logscoper.commands.stats import cmd_stats
from logscoper.commands.filter import cmd_filter

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logscoper",
        description="Simple access log analyzer",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    ps = sub.add_parser("stats", help="Show aggregated stats")
    ps.add_argument("--path", required=True)
    ps.add_argument("--top", type=int, default=10)
    ps.add_argument("--since")
    ps.add_argument("--until")
    ps.add_argument("--status")
    ps.add_argument("--grep")
    ps.add_argument("--json", action="store_true")
    ps.set_defaults(func=cmd_stats)
    pf = sub.add_parser("filter", help="Filter and print normalized lines")
    pf.add_argument("--path", required=True)
    pf.add_argument("--since")
    pf.add_argument("--until")
    pf.add_argument("--status")
    pf.add_argument("--grep")
    pf.add_argument("--out")
    pf.set_defaults(func=cmd_filter)
    ph = sub.add_parser("hist", help="Request time histogram")
    ph.add_argument("--path", required=True)
    ph.add_argument("--bucket-ms", type=int, default=100, dest="bucket_ms")
    ph.add_argument("--since")
    ph.add_argument("--until")
    ph.add_argument("--status")
    ph.add_argument("--grep")
    ph.add_argument("--json", action="store_true")
    ph.add_argument("--strict", action="store_true")
    ph.set_defaults(func=cmd_hist)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func") or args.func is None:
        parser.print_help()
        return 2
    return args.func(args)
