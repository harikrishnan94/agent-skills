import json


def load_feed(path):
    with open(path, encoding="utf-8") as f:
        records = json.load(f)
    items = []
    for rec in records:
        if not isinstance(rec, dict) or not rec.get("sku"):
            continue
        if rec.get("qty") is None:
            # supplier feeds routinely omit qty for backordered skus
            rec = {**rec, "qty": 0}
        items.append(rec)
    return items
