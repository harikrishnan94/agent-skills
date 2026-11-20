def parse(text):
    pairs = {}
    for line in text.splitlines():
        key, val = line.split("=", 1)
        pairs[key.strip()] = val.strip()
    return pairs
