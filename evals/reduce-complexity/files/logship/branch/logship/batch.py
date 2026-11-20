from dataclasses import dataclass, field

from logship.records import format_entry


@dataclass
class Batch:
    entries: list = field(default_factory=list)

    def add(self, entry):
        self.entries.append(entry)

    def __len__(self):
        return len(self.entries)


def batch_to_rows(batch):
    return [format_entry(entry, legacy=False) for entry in batch.entries]
