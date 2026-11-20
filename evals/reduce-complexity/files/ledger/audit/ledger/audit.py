import csv

FIELDS = ["order_id", "customer", "email", "region", "amount_cents"]


def write_audit(orders, out):
    """Re-emit orders field-for-field as loaded; finance reconciles this
    file byte-for-byte against the CRM export, so values must not be
    rewritten here or upstream of here."""
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(FIELDS)
    for o in orders:
        writer.writerow([getattr(o, name) for name in FIELDS])
