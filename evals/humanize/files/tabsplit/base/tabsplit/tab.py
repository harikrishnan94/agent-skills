from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class Member:
    name: str
    pays_in: str  # ISO 4217 code of the account the member pays from


@dataclass
class Tab:
    cur: str
    members: list
    spent: dict = field(default_factory=dict)  # member name -> paid for the group

    def add(self, payer, amount):
        self.spent[payer] = self.spent.get(payer, Decimal(0)) + amount

    def balance(self, name):
        """What `name` still owes the group, in `cur`; negative if owed money.

        Exact, not rounded: an even share of 10.00 among three is 3.3333...
        """
        total = sum(self.spent.values(), Decimal(0))
        return total / len(self.members) - self.spent.get(name, Decimal(0))
