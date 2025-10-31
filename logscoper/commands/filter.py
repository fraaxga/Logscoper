from __future__ import annotations
import argparse
import sys
import re
from logscoper.models.log_parser import _parse_iso, _status_filter, _iter_entries, _apply_filters

def cmd_filter(args: argparse.Namespace) -> int:
    try:
        since = _parse_iso(args.since) if args.since else None
        until = _parse_iso(args.until) if args.until else None
    except ValueError:
        raise SystemExit(2)
    st_ok = _status_filter(args.status)
    path_re = re.compile(args.grep) if args.grep else None
    out_f = None
    try:
        if args.out:
            out_f = open(args.out, "w", encoding="utf-8")
    except OSError as err:
        print(f"[error] cannot open --out file: {err}", file=sys.stderr)
        return 2

    def emit(s: str) -> None:
        if out_f:
            out_f.write(s + "\n")
        else:
            print(s)

    try:
        for e in _iter_entries(args.path):
            if not _apply_filters(e, since, until, st_ok, path_re):
                continue
            parts = [
                e["ts"].isoformat(),
                e["ip"],
                e["method"],
                e["path"],
                str(e["status"]),
                "-" if e["bytes"] is None else str(e["bytes"]),
            ]
            if e["raw_rt"] is not None:
                parts.append(f"rt={e['raw_rt']}")
            emit(" ".join(parts))
    except FileNotFoundError:
        print("[error] file not found", file=sys.stderr)
        return 2
    finally:
        if out_f:
            out_f.close()
    return 0
