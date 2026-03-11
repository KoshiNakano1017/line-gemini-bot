from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ReplyTokenDeduper:
    ttl_seconds: int = 600
    _seen: dict[str, float] = field(default_factory=dict)

    def _gc(self) -> None:
        now = time.time()
        cutoff = now - self.ttl_seconds
        to_del = [k for k, t in self._seen.items() if t < cutoff]
        for k in to_del:
            del self._seen[k]

    def should_process(self, reply_token: str) -> bool:
        token = (reply_token or "").strip()
        if not token:
            return False
        self._gc()
        if token in self._seen:
            return False
        self._seen[token] = time.time()
        return True

