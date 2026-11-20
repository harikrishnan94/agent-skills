import json

DEFAULT_CFG = {"rate": 5.0, "cap": 10}


def load_cfg(path):
    with open(path) as f:
        cfg = json.load(f)
    return {**DEFAULT_CFG, **cfg}
