class BatchWriter:
    def __init__(self, out):
        self.out = out
        self.count = 0

    def write(self, rows):
        for row in rows:
            self.out.write(row + "\n")
        self.count += len(rows)
