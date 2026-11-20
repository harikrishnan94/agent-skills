from logship.batch import Batch, batch_to_rows
from logship.records import format_entry, parse_line
from logship.writer import BatchWriter


def _chunk(records, size):
    batch = []
    for rec in records:
        batch.append(rec)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def export_lines(lines, out):
    n = 0
    for line in lines:
        if not line.strip():
            continue
        out.write(format_entry(parse_line(line), legacy=False) + "\n")
        n += 1
    return n


def export_batches(lines, out, size=100):
    writer = BatchWriter(out)
    batch = Batch()
    for line in lines:
        if not line.strip():
            continue
        batch.add(parse_line(line))
        if len(batch) == size:
            writer.write(batch_to_rows(batch))
            batch = Batch()
    if len(batch):
        writer.write(batch_to_rows(batch))
    return writer.count
