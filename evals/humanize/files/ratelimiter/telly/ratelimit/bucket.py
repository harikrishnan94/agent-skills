import time


class TokenBucket:
    def __init__(self, rate, cap):
        self.rate = rate
        self.cap = cap
        self._toks = {}  # key -> (tokens, last_ts)

    def allow(self, key, now=None):

        now = time.monotonic() if now is None else now

        toks, last = self._toks.get(key, (self.cap, now))
        toks = min(self.cap, toks + ((now - last) * self.rate))

        if toks < 1:
            self._toks[key] = (toks, now)
            return False

        self._toks[key] = (toks - 1, now)

        return True
