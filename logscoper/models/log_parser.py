from __future__ import annotations
from typing import Optional, List, Set, Callable, Pattern, TypedDict
import re
from datetime import datetime, timezone

LOG_RE = re.compile(
    r'(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<ts>[^\]]+)\]\s+'
    r'"(?P<method>[A-Z]+)\s+(?P<path>.*?)(?:\s+HTTP/\d\.\d)?"\s+'
    r'(?P<status>\d{3})\s+(?P<bytes>\S+)'
    r'(?:\s+"[^"]*"\s+"[^"]*")?'
    r'(?:\s+(?P<rt>\d+\.\d+)|\s+rt=(?P<rt_kv>\d+\.\d+))?'
)
RT_KV_RE = re.compile(r'(?:^|\s)rt=(?P<rt>\d+\.\d+)\b')
NGINX_TS_FMT = "%d/%b/%Y:%H:%M:%S %z"

class Entry(TypedDict):
    ip: str
    ts: datetime
    method: str
    path: str
    status: int
    bytes: Optional[int]
    rt_s: Optional[float]
    raw_rt: Optional[str]

def _parse_ts(raw: str) -> datetime:
    dt = datetime.strptime(raw, NGINX_TS_FMT)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_line(line: str) -> Optional[Entry]:
    m = LOG_RE.search(line)
    if not m:
        return None
    d = m.groupdict()
    try:
        ts = _parse_ts(d["ts"])
    except Exception:
        return None
    try:
        status = int(d["status"])
    except Exception:
        return None
    rb = d.get("bytes")
    if rb == "-":
        bytes_sent: Optional[int] = None
    else:
        try:
            bytes_sent = int(rb) if rb is not None else None
        except Exception:
            bytes_sent = None
    raw_rt = d.get("rt") or d.get("rt_kv")
    if raw_rt is None:
        kv = RT_KV_RE.search(line)
        raw_rt = kv.group("rt") if kv else None
    rt_s: Optional[float] = float(raw_rt) if raw_rt is not None else None
    return Entry(
        ip=d.get("ip") or "-",
        ts=ts,
        method=d.get("method") or "-",
        path=(d.get("path") or "-").strip(),
        status=status,
        bytes=bytes_sent,
        rt_s=rt_s,
        raw_rt=raw_rt,
    )

def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    t = s
    if t.endswith("Z"):
        t = t[:-1] + "+0000"
    if len(t) >= 6 and (t[-6] in "+-") and t[-3:-2] == ":":
        t = t[:-3] + t[-2:]
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(t, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    raise ValueError

def _status_filter(expr: Optional[str]) -> Callable[[int], bool]:
    if not expr:
        return lambda st: True
    expr = expr.strip()
    if expr.endswith("xx") and len(expr) == 3 and expr[0].isdigit():
        base = int(expr[0])
        return lambda st: st // 100 == base
    allowed: Set[int] = set()
    for p in expr.split(","):
        p = p.strip()
        if not p:
            continue
        if p.endswith("xx") and len(p) == 3 and p[0].isdigit():
            base = int(p[0])
            allowed.update(range(base * 100, base * 100 + 100))
        else:
            try:
                allowed.add(int(p))
            except ValueError:
                pass
    return lambda st: st in allowed if allowed else True

def _iter_entries(path: str) -> list[Entry]:
    entries = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            entry = _parse_line(line)
            if entry:
                entries.append(entry)
    return entries

def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    arr = sorted(vals)
    k = max(1, min(int(round((p / 100) * len(arr))), len(arr)))
    return arr[k - 1]

def _apply_filters(
    e: Entry,
    since: Optional[datetime],
    until: Optional[datetime],
    st_ok: Callable[[int], bool],
    path_re: Optional[Pattern[str]],
) -> bool:
    if since and e["ts"] < since:
        return False
    if until and e["ts"] >= until:
        return False
    if not st_ok(e["status"]):
        return False
    if path_re and not path_re.search(e["path"]):
        return False
    return True

