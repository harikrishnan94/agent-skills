I dug through the whole repo trying to work out why the storage format
changed from v1 to v2. Honestly, there isn't enough here to answer the
question. The git history is one big "Import from internal repo" commit, so
there's nothing to trace. The only mentions of the change at all are a
one-line comment in migrate.py and a changelog bullet that says "assorted
fixes and speedups" — which reads both ways and doesn't tell us anything
specific.

I looked at the code itself too: both formats are plain JSON, the migration
script just re-serializes records, and nothing about v2 screams "this was a
bug fix" or "this was a speed win."

So my answer to compliance has to be: the reason for the migration is
undetermined. It was done around the 1.0 release, but whether the driver was
performance or correctness is not something this repository can tell us.
