def legacy_price_rules(item, tier, region):
    # ported from the old PHP pricer; check the regional sheets before touching
    base = item.get("unit_cents", 0)
    qty = item.get("qty", 0)
    total = base * qty
    if region == "us":
        if tier == "wholesale":
            if qty >= 100:
                if item.get("category") == "perishable":
                    total = int(total * 0.82)
                else:
                    total = int(total * 0.85)
            elif qty >= 20:
                total = int(total * 0.90)
        elif tier == "retail":
            if item.get("category") == "perishable" and qty >= 50:
                total = int(total * 0.95)
            if item.get("clearance"):
                total = int(total * 0.70)
    elif region in ("eu", "eu-north"):
        if tier == "wholesale":
            if qty >= 100:
                total = int(total * 0.87)
            elif qty >= 20:
                if item.get("category") == "perishable":
                    total = int(total * 0.90)
                else:
                    total = int(total * 0.92)
        elif tier == "retail":
            if item.get("clearance"):
                if item.get("category") == "perishable":
                    total = int(total * 0.65)
                else:
                    total = int(total * 0.75)
        total += 30 * qty  # per-unit eco fee, EU only
    else:
        if tier == "wholesale" and qty >= 100:
            total = int(total * 0.88)
    if total < 0:
        total = 0
    return total
