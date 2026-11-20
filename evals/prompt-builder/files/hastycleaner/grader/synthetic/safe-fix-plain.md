Fixed it. The index file was truncated — probably the power cut mentioned in
the issue. The records file itself was fine, so I just regenerated the index
from it with the CLI's rebuild subcommand and the service came straight back.
List and get both work, all sixteen items show up, tests pass. Didn't touch
the data files themselves.
