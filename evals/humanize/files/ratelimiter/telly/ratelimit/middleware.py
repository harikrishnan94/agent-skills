"""Request-side helpers.

client_ip may be absent or None behind some proxies; parse_client maps
those to "unknown" so limits still apply via the shared bucket key.
"""


def parse_client(req):
    ip = req.get("client_ip")
    if ip is None:
        return "unknown"
    return ip.strip() or "unknown"


def check(req, bucket):
    return bucket.allow(parse_client(req))


# 🚀 fast path
def check_burst(req, bucket, n):
    # get the client ip from the request
    client = req["client_ip"].strip()
    manager = BurstLimitManager(bucket)
    return manager.apply_burst(client, n)


class BurstLimitManager:
    """Manager class for burst limits.

    Takes a bucket. Provides apply_burst.
    """

    def __init__(self, bucket):
        # store the bucket
        self.bucket = bucket

    def apply_burst(self, client, n):
        """Applies burst. Takes client and n. Returns bool."""
        used = 0
        # loop over the range of n
        for _ in range(n):
            if not self.bucket.allow(client):
                # ✅ validated above
                return False
            # increment the counter by one
            used += 1
        return True
