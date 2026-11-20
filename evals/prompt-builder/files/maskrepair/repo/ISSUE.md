# summary crashes on the vendor sample feed

Hit this while prepping the weekly report. Tests are green locally, so no idea
yet. Parking the traceback here — no time to dig in this week.

    $ python3 cli.py summary data/sample.csv
    Traceback (most recent call last):
      File "/Users/ana/work/feedproc/cli.py", line 33, in <module>
        raise SystemExit(main())
                         ~~~~^^
      File "/Users/ana/work/feedproc/cli.py", line 25, in main
        print(render_summary(header, rows))
              ~~~~~~~~~~~~~~^^^^^^^^^^^^^^
      File "/Users/ana/work/feedproc/feedproc/summary.py", line 14, in render_summary
        price = float(row[PRICE])
    ValueError: could not convert string to float: 'Portland'
