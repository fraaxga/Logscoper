from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass(frozen=True)
class LogEntry:
    ip: str
    ts: datetime
    method: str
    path: str
    status: int
    bytes_sent: Optional[int]
    request_time_s: Optional[float]
