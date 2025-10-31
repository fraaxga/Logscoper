from __future__ import annotations
import argparse
import sys
from typing import Dict
import re
import json
from collections import defaultdict
from logscoper.models.log_parser import _parse_iso, _status_filter, _iter_entries, _apply_filters

def cmd_hist(args: argparse.Namespace) -> int:
    try:
        since = _parse_iso(args.since) if args.since else None
        until = _parse_iso(args.until) if args.until else None
    except Exception:
        raise SystemExit(2)
    st_ok = _status_filter(args.status)
    path_re = re.compile(args.grep) if args.grep else None
    bucket = max(1, int(args.bucket_ms))
    bins: Dict[int, int] = defaultdict(int)
    total = 0
    missing = 0
    try:
        for e in _iter_entries(args.path):
            if not _apply_filters(e, since, until, st_ok, path_re):
                continue
            total += 1
            if e["rt_s"] is None:
                missing += 1
                if args.strict:
                    print("[error] missing request_time in strict mode", file=sys.stderr)
                    return 2
                continue
            ms = int(e["rt_s"] * 1000.0)
            idx = ms // bucket
            bins[idx] += 1
    except FileNotFoundError:
        print("[error] file not found", file=sys.stderr)
        return 2
    if args.json:
        out: Dict[str, int] = {}
        for idx, cnt in sorted(bins.items()):
            if cnt <= 0:
                continue
            left = idx * bucket
            right = left + bucket
            out[f"{left}-{right}"] = cnt
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    print(f"Bucket: {bucket} ms")
    print(f"Total considered: {total}")
    if missing:
        print(f"Missing rt: {missing}")
    print("Histogram:")
    for idx in sorted(bins.keys()):
        left = idx * bucket
        right = left + bucket
        cnt = bins[idx]
        print(f"{left}-{right}: {cnt}")
    return 0