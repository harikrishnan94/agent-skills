from .pricing import legacy_price_rules
from .util import parse_timestamp


def build_rows(items, tier="retail", region="us"):
    rows = []
    for item in items:
        rows.append({
            "sku": item.get("sku"),
            "qty": item.get("qty", 0),
            "total_cents": legacy_price_rules(item, tier, region),
            "updated": item.get("updated"),
        })
    rows.sort(key=lambda r: parse_timestamp(r["updated"]) if r["updated"] else 0.0)
    return rows
