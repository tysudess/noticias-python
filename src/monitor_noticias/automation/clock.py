from __future__ import annotations
from datetime import datetime
import time


class SystemClock:
    def now_ms(self) -> int:
        return int(time.time() * 1000)

    def local_datetime(self) -> datetime:
        # Equivale a LocalDateTime.now(): timezone local do sistema, sem conversão UTC.
        return datetime.now()
