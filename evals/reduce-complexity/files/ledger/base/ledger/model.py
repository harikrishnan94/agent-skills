from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    order_id: str
    customer: str
    email: str
    region: str
    amount_cents: int
