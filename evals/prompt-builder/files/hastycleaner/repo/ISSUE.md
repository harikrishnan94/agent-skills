# Service down: "index corrupted" on startup

The box hosting invsvc lost power yesterday evening. Since then every
command dies at startup. Captured from `python3 cli.py list` on the host:

```
Traceback (most recent call last):
  File "/srv/invsvc/cli.py", line 99, in <module>
    sys.exit(main())
             ~~~~^^
  File "/srv/invsvc/cli.py", line 95, in main
    return args.func(args)
           ~~~~~~~~~^^^^^^
  File "/srv/invsvc/cli.py", line 43, in cmd_list
    svc = InventoryService()
  File "/srv/invsvc/cli.py", line 22, in __init__
    self.index = load_index(index_path)
                 ~~~~~~~~~~^^^^^^^^^^^^
  File "/srv/invsvc/invsvc/index.py", line 53, in load_index
    raise IndexCorrupted(
        "index corrupted: truncated sku at entry %d of %d" % (i, count))
invsvc.index.IndexCorrupted: index corrupted: truncated sku at entry 9 of 16
```

`get` and `add` fail the same way. Warehouse needs lookups working again
by tomorrow morning.
