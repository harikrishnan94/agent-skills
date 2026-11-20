def totals_by_customer(orders):
    totals = {}
    for o in orders:
        totals[o.customer] = totals.get(o.customer, 0) + o.amount_cents
    return totals


def totals_by_region(orders):
    totals = {}
    for o in orders:
        totals[o.region] = totals.get(o.region, 0) + o.amount_cents
    return totals


def emails_by_customer(orders):
    emails = {}
    for o in orders:
        emails.setdefault(o.customer, set()).add(o.email)
    return emails


def format_totals(totals):
    lines = []
    for key in sorted(totals):
        cents = totals[key]
        lines.append("%s: %d.%02d" % (key, cents // 100, cents % 100))
    return lines
