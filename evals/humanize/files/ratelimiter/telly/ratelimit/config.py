import json

DEFAULT_CFG = {"rate": 5.0, "cap": 10, "burst": 0}


def load_cfg(path):
    # read the config file from the path
    try:
        with open(path) as f:
            cfg = json.load(f)
        return {**DEFAULT_CFG, **cfg}
    except Exception:
        # something went wrong so just use defaults
        return DEFAULT_CFG
