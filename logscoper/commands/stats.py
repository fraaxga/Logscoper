from __future__ import annotations
import argparse
import sys
from typing import Dict, List
import re
import json
from collections import Counter, defaultdict
from logscoper.models.log_parser import _parse_iso, _status_filter, _iter_entries, _apply_filters, _percentile

def cmd_stats(args: argparse.Namespace) -> int:
    try:
        since = _parse_iso(args.since) if args.since else None
        until = _parse_iso(args.until) if args.until else None
    except Exception:
        raise SystemExit(2)
    st_ok = _status_filter(args.status)
    path_re = re.compile(args.grep) if args.grep else None
    total = 0
    status_counter: Dict[int, int] = defaultdict(int)
    paths: Counter[str] = Counter()
    rts_ms: List[float] = []
    try:
        for e in _iter_entries(args.path):
            if not _apply_filters(e, since, until, st_ok, path_re):
                continue
            total += 1
            status_counter[e["status"]] += 1
            paths[e["path"]] += 1
            if e["rt_s"] is not None:
                rts_ms.append(e["rt_s"] * 1000.0)
    except FileNotFoundError:
        print("[error] file not found", file=sys.stderr)
        return 2
    avg = sum(rts_ms) / len(rts_ms) if rts_ms else None
    p95 = _percentile(rts_ms, 95) if rts_ms else None
    p99 = _percentile(rts_ms, 99) if rts_ms else None
    top_paths = paths.most_common(args.top or 10)
    if args.json:
        out = {
            "total": total,
            "status": {str(k): v for k, v in sorted(status_counter.items())},
            "rt_avg_ms": round(avg, 2) if avg is not None else None,
            "rt_p95_ms": round(p95, 2) if p95 is not None else None,
            "rt_p99_ms": round(p99, 2) if p99 is not None else None,
            "top_paths": [[p, c] for p, c in top_paths],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    print(f"Total: {total}")
    print("By status:")
    for code, cnt in sorted(status_counter.items()):
        print(f"  {code}: {cnt}")
    print(f"Avg RT (ms): {'n/a' if avg is None else f'{avg:.2f}'}")
    print(f"P95 RT (ms): {'n/a' if p95 is None else f'{p95:.2f}'}")
    print(f"P99 RT (ms): {'n/a' if p99 is None else f'{p99:.2f}'}")
    print("Top paths:")
    if top_paths:
        w = max(len(str(c)) for _, c in top_paths)
        for path, cnt in top_paths:
            print(f"{cnt:>{w}}  {path}")
    return 0

