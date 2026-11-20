def parse(text):
    pairs = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, val = line.split("=", 1)
        pairs[key.strip()] = val.strip()
    return pairs
